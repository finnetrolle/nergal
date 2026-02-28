"""Telegram bot message handlers.

This module contains all message handlers for bot (text and voice messages).
"""

import logging
import re
import time

from telegram import Update
from telegram.ext import ContextTypes

from nergal.utils import markdown_to_telegram_html
from stt_lib import AudioTooLongError, convert_ogg_to_wav

logger = logging.getLogger(__name__)


def should_respond_in_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if bot should respond to a message in a group chat.

    Args:
        update: Telegram update object.
        context: Callback context.

    Returns:
        True if bot should respond, False otherwise.
    """
    # Import here to avoid circular imports
    from nergal.main import BotApplication

    app = BotApplication.get_instance()
    settings = app._settings.group_chat

    # If group chats are disabled, don't respond
    if not settings.enabled:
        logger.debug("Group chats disabled in config")
        return False

    message = update.message
    if not message:
        return False

    # Check if this is a private chat - always respond
    chat_type = message.chat.type
    if chat_type == "private":
        return True

    # Get bot username - prefer settings, fallback to context
    bot_username = settings.bot_username or (context.bot.username if context.bot else "")
    bot_name = settings.bot_name

    logger.debug(
        "Checking group chat message: chat_type=%s, chat_id=%s, text=%s, username=%s, name=%s, has_reply=%s",
        chat_type,
        message.chat.id,
        message.text[:50] if message.text else None,
        bot_username,
        bot_name,
        message.reply_to_message is not None,
    )

    # For group/supergroup chats, check conditions
    if chat_type in ("group", "supergroup"):
        # Check if message is a reply to bot's message
        if settings.respond_to_replies and message.reply_to_message:
            replied_message = message.reply_to_message
            # Check if the replied message is from bot
            if replied_message.from_user:
                # Check by username
                if bot_username and replied_message.from_user.username:
                    if replied_message.from_user.username.lower() == bot_username.lower():
                        logger.debug("Responding: reply to bot's message (by username)")
                        return True
                # Check by is_bot flag
                if replied_message.from_user.is_bot:
                    logger.debug("Responding: reply to bot's message (is_bot=True)")
                    return True

        # Check for bot mention in message text
        if settings.respond_to_mentions and message.text:
            text = message.text
            bot_name_lower = bot_name.lower() if bot_name else ""
            bot_username_lower = bot_username.lower() if bot_username else ""

            # Check for name mention (case-insensitive)
            if bot_name_lower and bot_name_lower in text.lower():
                logger.debug("Responding: bot name mentioned in text")
                return True

            # Check for @username mention
            if bot_username_lower and f"@{bot_username_lower}" in text.lower():
                logger.debug("Responding: @username mentioned in text")
                return True

            # Also check for @bot_username from Telegram's entity parsing
            if message.entities:
                for entity in message.entities:
                    if entity.type == "mention":
                        mention_text = text[entity.offset : entity.offset + entity.length]
                        if bot_username_lower and mention_text.lower() == f"@{bot_username_lower}":
                            logger.debug("Responding: @username in entities")
                            return True
                    elif entity.type == "text_mention" and entity.user:
                        # Text mention without username (user ID mention)
                        if entity.user.is_bot:
                            logger.debug("Responding: text_mention to bot")
                            return True

        # Don't respond in group chat if no conditions met
        logger.debug("Not responding: no mention or reply in group chat")
        return False

    # Default: respond (for channel or unknown types, we allow)
    return True


def clean_message_text(text: str, bot_username: str) -> str:
    """Remove bot username mention from message text.

    Args:
        text: Original message text.
        bot_username: Bot's username to remove.

    Returns:
        Cleaned message text.
    """
    if not bot_username or not text:
        return text

    # Remove @username mention (case-insensitive)
    pattern = re.compile(rf"@{re.escape(bot_username)}\b", re.IGNORECASE)
    return pattern.sub("", text).strip()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all incoming text messages using dialog manager."""
    if not (update.message and update.message.text):
        return

    # Import here to avoid circular imports
    from nergal.main import BotApplication

    # Log all incoming messages for debugging
    logger.info(
        "Received message: chat_id=%s, chat_type=%s, user_id=%s, text=%s, has_reply=%s",
        update.message.chat.id,
        update.message.chat.type,
        update.effective_user.id if update.effective_user else None,
        update.message.text[:100] if update.message.text else None,
        update.message.reply_to_message is not None,
    )

    # Check if bot should respond in this context (group chat filtering)
    if not should_respond_in_group(update, context):
        logger.debug(
            "Skipping message in group chat - no mention or reply: chat_id=%s, chat_type=%s",
            update.message.chat.id,
            update.message.chat.type,
        )
        return

    logger.info("Processing message from group chat")

    # Get bot username for mention cleaning
    app = BotApplication.get_instance()
    bot_username = app._settings.group_chat.bot_username or (
        context.bot.username if context.bot else ""
    )

    # Clean message text (remove bot username mention)
    user_text = (
        clean_message_text(update.message.text, bot_username)
        if bot_username
        else update.message.text
    )
    user_info = {
        "first_name": update.effective_user.first_name if update.effective_user else None,
        "last_name": update.effective_user.last_name if update.effective_user else None,
        "username": update.effective_user.username if update.effective_user else None,
        "language_code": update.effective_user.language_code if update.effective_user else None,
    }
    user_id = update.effective_user.id if update.effective_user else 0

    # Log incoming message
    logger.debug(
        "Processing message",
        user_id=user_id,
        message_length=len(user_text),
    )

    start_time = time.time()
    try:
        result = await app.dialog_manager.process_message(
            user_id=user_id,
            message=user_text,
            user_info=user_info,
        )

        # Convert Markdown to Telegram HTML format
        html_response = markdown_to_telegram_html(result.response)

        # Send with HTML parsing enabled
        await update.message.reply_text(html_response, parse_mode="HTML")

        # Log successful processing
        duration = time.time() - start_time
        logger.info(
            "Message processed successfully: user_id=%s, duration=%.3fs, agent=%s",
            user_id,
            round(duration, 3),
            result.agent_type.value,
        )

    except Exception as e:
        logger.error(
            "Error processing message: user_id=%s, error=%s: %s",
            user_id,
            type(e).__name__,
            str(e),
            exc_info=True,
        )
        await update.message.reply_text(
            "Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте позже."
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages using STT and dialog manager."""
    if not (update.message and update.message.voice):
        return

    # Import here to avoid circular imports
    from nergal.main import BotApplication

    # Check if bot should respond in this context (group chat filtering)
    if not should_respond_in_group(update, context):
        logger.debug(
            "Skipping voice message in group chat - no mention or reply: chat_id=%s, chat_type=%s",
            update.message.chat.id,
            update.message.chat.type,
        )
        return

    app = BotApplication.get_instance()
    settings = app._settings

    user_id = update.effective_user.id if update.effective_user else 0

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
        # Download voice message
        voice = update.message.voice
        new_file = await voice.get_file()
        audio_bytes = await new_file.download_as_bytearray()

        # Convert OGG to WAV and check duration
        try:
            wav_audio, duration = convert_ogg_to_wav(
                bytes(audio_bytes),
                max_duration_seconds=settings.stt.max_duration_seconds,
            )
            logger.info("Converted voice message: duration=%.1fs", round(duration, 1))
        except AudioTooLongError as e:
            await update.message.reply_text(
                f"Голосовое сообщение слишком длинное ({e.duration_seconds:.0f}с). "
                f"Максимум {e.max_seconds}с. Пожалуйста, запишите короче или напишите текстом."
            )
            return

        # Transcribe audio with timeout handling
        try:
            transcription = await stt.transcribe(
                wav_audio,
                language=settings.stt.language,
            )
        except TimeoutError:
            logger.error(
                "Voice transcription timed out: user_id=%s, timeout=%s",
                user_id,
                settings.stt.timeout,
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

        logger.info("Transcription completed: %s", transcription[:100])

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
                "Voice message processed successfully: user_id=%s, duration=%.3fs, audio=%.1fs",
                user_id,
                round(duration, 3),
                round(duration, 1),
            )

        except Exception as e:
            logger.error(
                "Error processing voice transcription: user_id=%s, error=%s",
                user_id,
                str(e),
                exc_info=True,
            )
            await update.message.reply_text(
                "Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте позже."
            )

    except Exception as e:
        logger.error(
            "Error processing voice message: %s: %s",
            type(e).__name__,
            str(e),
            exc_info=True,
        )
        await update.message.reply_text(
            "Произошла ошибка при обработке голосового сообщения. "
            "Пожалуйста, попробуйте ещё раз или напишите текстом."
        )
