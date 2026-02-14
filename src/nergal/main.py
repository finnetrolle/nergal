"""Main entry point for the Telegram bot."""

import logging
import re

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from nergal.config import get_settings
from nergal.dialog import DialogManager
from nergal.dialog.web_search_agent import WebSearchAgent
from nergal.llm import create_llm_provider
from nergal.stt import AudioTooLongError, convert_ogg_to_wav, create_stt_provider
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
    """

    _instance: "BotApplication | None" = None

    def __init__(self) -> None:
        """Initialize the bot application."""
        self._dialog_manager: DialogManager | None = None
        self._web_search_provider: ZaiMcpHttpSearchProvider | None = None
        self._stt_provider: BaseSTTProvider | None = None
        self._settings = get_settings()
        self._logger = logging.getLogger(__name__)

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
        )
        self._logger.info(
            f"Initialized STT provider: {provider.provider_name}, "
            f"model: {self._settings.stt.model}"
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
            f"Initialized ZaiMcpHttpSearchProvider with MCP URL: {self._settings.web_search.mcp_url}"
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
            f"Initialized DialogManager with LLM provider: {llm_provider.provider_name}, "
            f"style: {self._settings.style.value}"
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


def configure_logging(log_level: str) -> None:
    """Configure logging for the application.

    Args:
        log_level: The logging level to use.
    """
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger().setLevel(getattr(logging, log_level.upper()))

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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all incoming text messages using the dialog manager."""
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

    app = BotApplication.get_instance()
    result = await app.dialog_manager.process_message(
        user_id=user_id,
        message=user_text,
        user_info=user_info,
    )

    await update.message.reply_text(result.response)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages using STT and dialog manager."""
    logger = logging.getLogger(__name__)

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
            logger.info(f"Converted voice message: {duration:.1f}s")
        except AudioTooLongError as e:
            await update.message.reply_text(
                f"Голосовое сообщение слишком длинное ({e.duration_seconds:.0f}с). "
                f"Максимум {e.max_seconds}с. Пожалуйста, запишите короче или напишите текстом."
            )
            return

        # Transcribe the audio
        transcription = await stt.transcribe(
            wav_audio,
            language=settings.stt.language,
        )

        if not transcription.strip():
            await update.message.reply_text(
                "Не удалось распознать речь в сообщении. Пожалуйста, попробуйте ещё раз или напишите текстом."
            )
            return

        logger.info(f"Transcription: {transcription[:100]}...")

        # Process the transcribed text through dialog manager
        user_info = {
            "first_name": update.effective_user.first_name if update.effective_user else None,
            "last_name": update.effective_user.last_name if update.effective_user else None,
            "username": update.effective_user.username if update.effective_user else None,
            "language_code": update.effective_user.language_code if update.effective_user else None,
        }
        user_id = update.effective_user.id if update.effective_user else 0

        result = await app.dialog_manager.process_message(
            user_id=user_id,
            message=transcription,
            user_info=user_info,
        )

        await update.message.reply_text(result.response)

    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при обработке голосового сообщения. "
            "Пожалуйста, попробуйте ещё раз или напишите текстом."
        )


def main() -> None:
    """Start the bot."""
    settings = get_settings()
    configure_logging(settings.log_level)

    if not settings.llm.api_key:
        logging.getLogger(__name__).warning(
            "LLM_API_KEY is not set. Bot will not be able to generate AI responses."
        )

    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add voice message handler if STT is enabled
    if settings.stt.enabled:
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        logging.getLogger(__name__).info("Voice message handler registered")

    logging.getLogger(__name__).info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
