"""Main entry point for the Telegram bot."""

# Suppress pydub SyntaxWarning for invalid escape sequences (third-party library issue)
# Must be done before any imports that trigger pydub loading
import warnings
warnings.filterwarnings("ignore", message=".*invalid escape sequence.*", category=SyntaxWarning, module="pydub")

import logging
import re
import time

from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from nergal.config import get_settings
from nergal.container import Container, get_container, init_container
from nergal.dialog import DialogManager
from nergal.handlers import (
    handle_message,
    handle_voice,
    help_command,
    start_command,
    status_command,
    todoist_disconnect_command,
    todoist_token_command,
)
from nergal.llm import create_llm_provider
from nergal.monitoring import (
    MetricsServer,
    configure_structlog,
    get_health_checker,
    get_logger,
)
from nergal.stt import create_stt_provider
from nergal.stt.base import BaseSTTProvider
from nergal.web_search.zai_mcp_http import ZaiMcpHttpSearchProvider


class HttpxLogFilter(logging.Filter):
    """Filter for httpx logs that suppresses successful requests but keeps 4XX errors."""

    _http_status_pattern = re.compile(r'"HTTP/\d\.\d (\d{3})')

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log records based on HTTP status code.

        Args:
            record: The log record to filter.

        Returns:
            True if the record should be logged, False to suppress.
        """
        if record.levelno != logging.INFO:
            return True

        message = record.getMessage()
        match = self._http_status_pattern.search(message)

        if match:
            status_code = int(match.group(1))
            return 400 <= status_code < 500

        return True


class BotApplication:
    """Telegram bot application with singleton pattern.

    Manages dialog manager and web search provider lifecycle.
    This class now delegates to the DI container for dependency management.
    """

    _instance: "BotApplication | None" = None

    def __init__(self) -> None:
        """Initialize the bot application."""
        self._container: Container | None = None
        self._startup_time: float | None = None
        self._admin_server = None  # Admin web interface
        self._admin_runner = None  # aiohttp runner
        self._logger = get_logger(__name__)

    @classmethod
    def get_instance(cls) -> "BotApplication":
        """Get the singleton instance of the bot application."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def container(self) -> Container:
        """Get the DI container instance."""
        if self._container is None:
            self._container = get_container()
        return self._container

    @property
    def dialog_manager(self) -> DialogManager:
        """Get or create the dialog manager instance from DI container."""
        return self.container.dialog_manager()

    @property
    def web_search_provider(self) -> ZaiMcpHttpSearchProvider | None:
        """Get or create the web search provider instance from DI container."""
        return self.container.web_search_provider()

    @property
    def stt_provider(self) -> BaseSTTProvider | None:
        """Get or create the STT provider instance from DI container."""
        return self.container.stt_provider()

    @property
    def _settings(self):
        """Get settings from DI container."""
        return self.container.settings()

    async def initialize_memory(self) -> None:
        """Initialize the memory service and database connection."""
        try:
            from nergal.container import init_database

            settings = self._settings

            # Initialize database connection pool through DI container
            db = await init_database()
            self._logger.info(
                "Database connection pool created",
                host=settings.database.host,
                database=settings.database.name,
            )

            # Run database migrations (always run for integrations)
            await self._run_database_migrations(db)

            # Initialize memory service in dialog manager (if enabled)
            if settings.memory.long_term_enabled:
                memory_service = self.container.memory_service()
                if memory_service:
                    self.dialog_manager.set_memory_service(memory_service)
                    await self.dialog_manager.initialize_memory()

                self._logger.info(
                    "Memory service initialized",
                    long_term_enabled=settings.memory.long_term_enabled,
                    extraction_enabled=settings.memory.long_term_extraction_enabled,
                )
            else:
                self._logger.info("Memory service disabled, but database is available for integrations")

        except Exception as e:
            self._logger.error(
                "Failed to initialize memory service",
                error=str(e),
                exc_info=True,
            )
            # Continue without memory - it's not critical for bot operation
            self._logger.warning("Bot will continue without persistent memory")

    async def _run_database_migrations(self, db) -> None:
        """Run database migrations for schema updates.

        Args:
            db: DatabaseConnection instance from DI container.
        """
        try:
            from nergal.database.migrations import run_migrations

            # Migration 1: Add is_allowed column to users table if not exists
            migration_sql = """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'is_allowed'
                    ) THEN
                        ALTER TABLE users ADD COLUMN is_allowed BOOLEAN DEFAULT FALSE;
                        CREATE INDEX IF NOT EXISTS idx_users_is_allowed ON users(is_allowed) WHERE is_allowed = TRUE;
                    END IF;
                END $$;
            """
            await db.execute(migration_sql)

            # Run structured migrations
            applied = await run_migrations(db)
            if applied:
                self._logger.info("Applied database migrations", migrations=applied)

            self._logger.info("Database migrations completed successfully")
        except Exception as e:
            self._logger.warning(
                "Database migration warning",
                error=str(e),
                note="This may be expected if migrations were already applied",
            )

    async def shutdown_memory(self) -> None:
        """Shutdown the memory service and close database connections."""
        try:
            from nergal.container import shutdown_database

            await shutdown_database()
            self._logger.info("Database connections closed")
        except Exception as e:
            self._logger.error(
                "Error during memory shutdown",
                error=str(e),
            )

    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics server."""
        settings = self._settings
        if settings.monitoring.enabled:
            metrics_server = self.container.metrics_server()
            if metrics_server:
                metrics_server.start()
                self._logger.info(
                    "Metrics server started",
                    port=settings.monitoring.metrics_port,
                )

    def set_startup_time(self) -> None:
        """Record the application startup time."""
        self._startup_time = time.time()
        get_health_checker().set_startup_time(self._startup_time)

    async def start_admin_server(self) -> None:
        """Start the admin web interface server."""
        settings = self._settings
        if not settings.auth.admin_enabled:
            return

        try:
            from aiohttp import web

            from nergal.admin.server import AdminServer

            self._admin_server = AdminServer(
                port=settings.auth.admin_port,
            )
            self._admin_runner = web.AppRunner(self._admin_server.app)
            await self._admin_runner.setup()
            site = web.TCPSite(self._admin_runner, "0.0.0.0", settings.auth.admin_port)
            await site.start()

            self._logger.info(
                "Admin web interface started",
                port=settings.auth.admin_port,
                url=f"http://localhost:{settings.auth.admin_port}/admin",
            )
        except Exception as e:
            self._logger.error(
                "Failed to start admin server",
                error=str(e),
            )

    async def stop_admin_server(self) -> None:
        """Stop the admin web interface server."""
        if self._admin_runner:
            await self._admin_runner.cleanup()
            self._logger.info("Admin web interface stopped")


def configure_logging(log_level: str, json_output: bool = True) -> None:
    """Configure logging for the application.

    Args:
        log_level: The logging level to use.
        json_output: Whether to use JSON format for logs.
    """
    configure_structlog(log_level=log_level, json_output=json_output)

    # Suppress verbose HTTP logs from httpx
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.INFO)
    httpx_logger.addFilter(HttpxLogFilter())
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> None:
    """Start the bot."""
    # Initialize DI container first
    container = init_container()

    settings = container.settings()

    # Configure logging with monitoring settings
    configure_logging(
        log_level=settings.monitoring.log_level or settings.log_level,
        json_output=settings.monitoring.json_logs,
    )

    logger = get_logger(__name__)

    if not settings.llm.api_key:
        logger.warning("LLM_API_KEY is not set. Bot will not be able to generate AI responses.")

    # Initialize bot application
    app = BotApplication.get_instance()
    app.set_startup_time()

    # Start metrics server if monitoring is enabled
    if settings.monitoring.enabled:
        app.start_metrics_server()

    # Pre-initialize components for health checks
    _ = app.dialog_manager  # Initialize dialog manager

    # Pre-load Whisper model if STT is enabled to avoid timeout on first transcription
    if settings.stt.enabled:
        stt_provider = app.stt_provider
        if stt_provider is not None:
            logger.info("Pre-loading Whisper model...")
            stt_provider.preload_model()
            logger.info("Whisper model pre-loaded successfully")

    # Initialize memory service (async, in event loop)
    async def post_init(_application: Application) -> None:
        """Initialize async resources after application is ready."""
        await app.initialize_memory()

        # Start admin web interface
        await app.start_admin_server()

        # Mark components as healthy
        from nergal.monitoring import HealthStatus, get_health_checker

        checker = get_health_checker()
        checker.mark_healthy("bot", "Bot application initialized")
        checker.mark_healthy("memory", "Memory service initialized")

    async def post_shutdown(_application: Application) -> None:
        """Cleanup async resources on shutdown."""
        await app.stop_admin_server()
        await app.shutdown_memory()

    # Mark components as healthy (initial)
    from nergal.monitoring import HealthStatus, get_health_checker

    checker = get_health_checker()
    checker.mark_healthy("bot", "Bot application initialized")

    from telegram import Update

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("todoist_token", todoist_token_command))
    application.add_handler(CommandHandler("todoist_disconnect", todoist_disconnect_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add voice message handler if STT is enabled
    if settings.stt.enabled:
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        logger.info("Voice message handler registered")

    logger.info(
        "Starting bot",
        monitoring_enabled=settings.monitoring.enabled,
        metrics_port=settings.monitoring.metrics_port,
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
