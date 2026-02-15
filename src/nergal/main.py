"""Main entry point for the Telegram bot."""

import asyncio
import logging
import re
import time

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from nergal.config import get_settings
from nergal.dialog import DialogManager
from nergal.dialog.agents.web_search_agent import WebSearchAgent
from nergal.llm import create_llm_provider
from nergal.monitoring import (
    MetricsServer,
    configure_structlog,
    get_health_checker,
    get_logger,
    run_health_checks,
    track_error,
    track_user_activity,
)
from nergal.monitoring.metrics import (
    bot_message_duration_seconds,
    bot_messages_total,
)
from nergal.stt import AudioTooLongError, convert_ogg_to_wav, create_stt_provider
from nergal.stt.base import BaseSTTProvider
from nergal.utils import markdown_to_telegram_html, split_message_for_telegram
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
    """

    _instance: "BotApplication | None" = None

    def __init__(self) -> None:
        """Initialize the bot application."""
        self._dialog_manager: DialogManager | None = None
        self._web_search_provider: ZaiMcpHttpSearchProvider | None = None
        self._stt_provider: BaseSTTProvider | None = None
        self._settings = get_settings()
        self._logger = get_logger(__name__)
        self._metrics_server: MetricsServer | None = None
        self._startup_time: float | None = None

    @classmethod
    def get_instance(cls) -> "BotApplication":
        """Get the singleton instance of the bot application."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def dialog_manager(self) -> DialogManager:
        """Get or create the dialog manager instance."""
        if self._dialog_manager is None:
            self._dialog_manager = self._create_dialog_manager()
        return self._dialog_manager

    @property
    def web_search_provider(self) -> ZaiMcpHttpSearchProvider | None:
        """Get or create the web search provider instance."""
        if self._web_search_provider is None and self._settings.web_search.enabled:
            self._web_search_provider = self._create_web_search_provider()
        return self._web_search_provider

    @property
    def stt_provider(self) -> BaseSTTProvider | None:
        """Get or create the STT provider instance."""
        if self._stt_provider is None and self._settings.stt.enabled:
            self._stt_provider = self._create_stt_provider()
        return self._stt_provider

    def _create_stt_provider(self) -> BaseSTTProvider:
        """Create a new STT provider instance."""
        provider = create_stt_provider(
            provider_type=self._settings.stt.provider,
            model=self._settings.stt.model,
            device=self._settings.stt.device,
            compute_type=self._settings.stt.compute_type,
            api_key=self._settings.stt.api_key or None,
            timeout=self._settings.stt.timeout,
        )
        self._logger.info(
            "Initialized STT provider",
            provider=provider.provider_name,
            model=self._settings.stt.model,
        )
        return provider

    def _create_web_search_provider(self) -> ZaiMcpHttpSearchProvider:
        """Create a new web search provider instance."""
        api_key = self._settings.web_search.api_key or self._settings.llm.api_key
        provider = ZaiMcpHttpSearchProvider(
            api_key=api_key,
            mcp_url=self._settings.web_search.mcp_url,
            timeout=self._settings.web_search.timeout,
        )
        self._logger.info(
            "Initialized web search provider",
            mcp_url=self._settings.web_search.mcp_url,
        )
        return provider

    def _create_dialog_manager(self) -> DialogManager:
        """Create a new dialog manager instance."""
        llm_provider = create_llm_provider(
            provider_type=self._settings.llm.provider,
            api_key=self._settings.llm.api_key,
            model=self._settings.llm.model,
            base_url=self._settings.llm.base_url,
            temperature=self._settings.llm.temperature,
            max_tokens=self._settings.llm.max_tokens,
            timeout=self._settings.llm.timeout,
        )
        manager = DialogManager(
            llm_provider=llm_provider,
            style_type=self._settings.style,
        )
        self._logger.info(
            "Initialized DialogManager",
            llm_provider=llm_provider.provider_name,
            style=self._settings.style.value,
        )

        search_provider = self.web_search_provider
        if search_provider:
            web_search_agent = WebSearchAgent(
                llm_provider=llm_provider,
                search_provider=search_provider,
                style_type=self._settings.style,
                max_search_results=self._settings.web_search.max_results,
            )
            manager.register_agent(web_search_agent)
            self._logger.info("Web search agent registered and enabled")

        return manager

    async def initialize_memory(self) -> None:
        """Initialize the memory service and database connection."""
        try:
            from nergal.database.connection import create_pool
            from nergal.memory.service import MemoryService
            
            # Create database connection pool
            await create_pool(self._settings.database)
            self._logger.info(
                "Database connection pool created",
                host=self._settings.database.host,
                database=self._settings.database.name,
            )
            
            # Initialize memory service in dialog manager
            memory_service = MemoryService()
            self.dialog_manager.set_memory_service(memory_service)
            await self.dialog_manager.initialize_memory()
            
            self._logger.info(
                "Memory service initialized",
                long_term_enabled=self._settings.memory.long_term_enabled,
                extraction_enabled=self._settings.memory.long_term_extraction_enabled,
            )
        except Exception as e:
            self._logger.error(
                "Failed to initialize memory service",
                error=str(e),
                exc_info=True,
            )
            # Continue without memory - it's not critical for bot operation
            self._logger.warning("Bot will continue without persistent memory")

    async def shutdown_memory(self) -> None:
        """Shutdown the memory service and close database connections."""
        try:
            from nergal.database.connection import close_pool
            
            await close_pool()
            self._logger.info("Database connections closed")
        except Exception as e:
            self._logger.error(
                "Error during memory shutdown",
                error=str(e),
            )

    def start_metrics_server(self) -> None:
        """Start the Prometheus metrics server."""
        if self._settings.monitoring.enabled:
            self._metrics_server = MetricsServer(port=self._settings.monitoring.metrics_port)
            self._metrics_server.start()
            self._logger.info(
                "Metrics server started",
                port=self._settings.monitoring.metrics_port,
            )

    def set_startup_time(self) -> None:
        """Record the application startup time."""
        self._startup_time = time.time()
        get_health_checker().set_startup_time(self._startup_time)


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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if update.message:
        await update.message.reply_text("Привет! Я бот Sil. Напиши мне вопрос, и я постараюсь ответить!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if update.message:
        await update.message.reply_text("Просто напиши мне сообщение, и я отвечу с помощью AI!")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command to show bot health."""
    if not update.message:
        return

    app = BotApplication.get_instance()
    checker = get_health_checker()

    # Run health checks
    await run_health_checks(
        llm_provider=app.dialog_manager._llm_provider if app._dialog_manager else None,
        bot_application=app,
        web_search_provider=app.web_search_provider,
        stt_provider=app.stt_provider,
    )

    health = checker.to_dict()
    status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}

    status_text = f"{status_emoji.get(health['status'], '❓')} Статус: {health['status']}\n\n"

    for name, component in health.get("components", {}).items():
        emoji = status_emoji.get(component["status"], "❓")
        status_text += f"{emoji} {name}: {component.get('message', component['status'])}\n"

    if "uptime_seconds" in health:
        uptime = int(health["uptime_seconds"])
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_str = f"{days}д {hours}ч {minutes}м" if days else f"{hours}ч {minutes}м"
        status_text += f"\n⏱ Uptime: {uptime_str}"

    await update.message.reply_text(status_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all incoming text messages using the dialog manager."""
    logger = get_logger(__name__)

    if not (update.message and update.message.text):
        return

    user_text = update.message.text
    user_info = {
        "first_name": update.effective_user.first_name if update.effective_user else None,
        "last_name": update.effective_user.last_name if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "language_code": update.effective_user.language_code if update.effective_user else None,
    }
    user_id = update.effective_user.id if update.effective_user else 0

    # Track user activity for metrics
    track_user_activity(user_id)

    # Log incoming message
    logger.debug(
        "Processing message",
        user_id=user_id,
        message_length=len(user_text),
    )

    app = BotApplication.get_instance()

    start_time = time.time()
    status = "success"
    agent_type = "default"
    try:
        result = await app.dialog_manager.process_message(
            user_id=user_id,
            message=user_text,
            user_info=user_info,
        )
        agent_type = result.agent_type.value

        # Convert Markdown to Telegram HTML format
        html_response = markdown_to_telegram_html(result.response)

        # Send with HTML parsing enabled
        await update.message.reply_text(html_response, parse_mode="HTML")

        # Log successful processing
        duration = time.time() - start_time
        logger.info(
            "Message processed successfully",
            user_id=user_id,
            duration_seconds=round(duration, 3),
            agent_used=result.agent_type.value,
        )

    except Exception as e:
        status = "error"
        track_error(type(e).__name__, "message_handler")
        logger.error(
            "Error processing message",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        await update.message.reply_text(
            "Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте позже."
        )
    finally:
        # Track message metrics
        duration = time.time() - start_time
        bot_messages_total.labels(status=status, agent_type=agent_type).inc()
        bot_message_duration_seconds.labels(agent_type=agent_type).observe(duration)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages using STT and dialog manager."""
    logger = get_logger(__name__)

    if not (update.message and update.message.voice):
        return

    app = BotApplication.get_instance()
    settings = app._settings

    # Check if STT is enabled
    if not settings.stt.enabled:
        await update.message.reply_text(
            "Голосовые сообщения не поддерживаются. Пожалуйста, напишите текстом."
        )
        return

    stt = app.stt_provider
    if stt is None:
        await update.message.reply_text(
            "Ошибка: STT провайдер не инициализирован. Пожалуйста, напишите текстом."
        )
        return

    user_id = update.effective_user.id if update.effective_user else 0
    track_user_activity(user_id)

    # Send typing action to show the bot is processing
    if update.effective_chat:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing",
        )

    try:
        # Download the voice message
        voice = update.message.voice
        new_file = await voice.get_file()
        audio_bytes = await new_file.download_as_bytearray()

        # Convert OGG to WAV and check duration
        try:
            wav_audio, duration = convert_ogg_to_wav(
                bytes(audio_bytes),
                max_duration_seconds=settings.stt.max_duration_seconds,
            )
            logger.info("Converted voice message", duration_seconds=round(duration, 1))
        except AudioTooLongError as e:
            await update.message.reply_text(
                f"Голосовое сообщение слишком длинное ({e.duration_seconds:.0f}с). "
                f"Максимум {e.max_seconds}с. Пожалуйста, запишите короче или напишите текстом."
            )
            return

        # Transcribe the audio with timeout handling
        try:
            transcription = await stt.transcribe(
                wav_audio,
                language=settings.stt.language,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Voice transcription timed out",
                user_id=user_id,
                timeout_seconds=settings.stt.timeout,
            )
            await update.message.reply_text(
                "Превышено время ожидания расшифровки голосового сообщения. "
                "Пожалуйста, попробуйте ещё раз или напишите текстом."
            )
            return

        if not transcription.strip():
            await update.message.reply_text(
                "Не удалось распознать речь в сообщении. Пожалуйста, попробуйте ещё раз или напишите текстом."
            )
            return

        logger.info("Transcription completed", text_preview=transcription[:100])

        # Process the transcribed text through dialog manager
        user_info = {
            "first_name": update.effective_user.first_name if update.effective_user else None,
            "last_name": update.effective_user.last_name if update.effective_user else None,
            "username": update.effective_user.username if update.effective_user else None,
            "language_code": update.effective_user.language_code if update.effective_user else None,
        }

        start_time = time.time()
        try:
            result = await app.dialog_manager.process_message(
                user_id=user_id,
                message=transcription,
                user_info=user_info,
            )

            # Convert Markdown to Telegram HTML format
            html_response = markdown_to_telegram_html(result.response)
            await update.message.reply_text(html_response, parse_mode="HTML")

            duration = time.time() - start_time
            logger.info(
                "Voice message processed successfully",
                user_id=user_id,
                duration_seconds=round(duration, 3),
                audio_duration_seconds=round(duration, 1),
            )

        except Exception as e:
            track_error(type(e).__name__, "voice_handler")
            logger.error(
                "Error processing voice transcription",
                user_id=user_id,
                error=str(e),
            )
            await update.message.reply_text(
                "Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте позже."
            )

    except Exception as e:
        track_error(type(e).__name__, "voice_processing")
        logger.error(
            "Error processing voice message",
            error=str(e),
            error_type=type(e).__name__,
        )
        await update.message.reply_text(
            "Произошла ошибка при обработке голосового сообщения. "
            "Пожалуйста, попробуйте ещё раз или напишите текстом."
        )


def main() -> None:
    """Start the bot."""
    import asyncio
    
    settings = get_settings()

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

    # Initialize memory service (async, in event loop)
    async def post_init(application: Application) -> None:
        """Initialize async resources after application is ready."""
        await app.initialize_memory()
        
        # Mark components as healthy
        from nergal.monitoring import HealthStatus, get_health_checker
        checker = get_health_checker()
        checker.mark_healthy("bot", "Bot application initialized")
        checker.mark_healthy("memory", "Memory service initialized")

    async def post_shutdown(application: Application) -> None:
        """Cleanup async resources on shutdown."""
        await app.shutdown_memory()

    # Mark components as healthy (initial)
    from nergal.monitoring import HealthStatus, get_health_checker
    checker = get_health_checker()
    checker.mark_healthy("bot", "Bot application initialized")

    application = Application.builder().token(settings.telegram_bot_token).post_init(post_init).post_shutdown(post_shutdown).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
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
