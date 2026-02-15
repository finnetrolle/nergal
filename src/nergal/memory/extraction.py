"""Memory extraction service for extracting facts from conversations.

This module provides the MemoryExtractionService that analyzes
user messages and extracts relevant information for long-term memory.
"""

import json
import logging
from typing import Any

from nergal.config import get_settings
from nergal.database.connection import DatabaseConnection, get_database
from nergal.database.models import ConversationMessage
from nergal.database.repositories import ConversationRepository, ProfileRepository
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Ты - система извлечения информации о пользователе из сообщений.

Проанализируй последнее сообщение пользователя и извлеки из него факты о пользователе.
Извлекай только факты, которые:
1. Являются персональной информацией (имя, возраст, местоположение, профессия)
2. Отражают предпочтения или интересы
3. Содержат важные детали, которые стоит запомнить

НЕ извлекай:
- Временную информацию (сегодняшние планы)
- Тривиальные детали
- Информацию о других людях

История беседы:
{conversation_history}

Последнее сообщение пользователя: {user_message}

Ответь в формате JSON:
{{
    "facts": [
        {{
            "fact_type": "тип факта (personal/preference/interest/skill/other)",
            "fact_key": "ключ факта (например: name, age, location, favorite_color)",
            "fact_value": "значение факта",
            "confidence": 0.0-1.0,
            "reasoning": "почему этот факт важен"
        }}
    ],
    "should_update_profile": true/false,
    "profile_updates": {{
        "preferred_name": "имя или null",
        "age": число или null,
        "location": "местоположение или null",
        "occupation": "профессия или null",
        "interests": ["интерес1", "интерес2"] или null,
        "expertise_areas": ["область1"] или null
    }}
}}

Если фактов для извлечения нет, верни пустой список facts.
Отвечай ТОЛЬКО валидным JSON, без дополнительного текста."""


class MemoryExtractionService:
    """Service for extracting facts from user messages.

    This service uses an LLM to analyze user messages and extract
    relevant information for long-term memory storage.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        db: DatabaseConnection | None = None,
    ) -> None:
        """Initialize the extraction service.

        Args:
            llm_provider: LLM provider for text analysis.
            db: Database connection. If not provided, uses the singleton.
        """
        self._llm = llm_provider
        self._db = db or get_database()
        self._profile_repo = ProfileRepository(self._db)
        self._conversation_repo = ConversationRepository(self._db)
        self._settings = get_settings().memory

    async def extract_and_store(
        self,
        user_id: int,
        user_message: str,
        conversation_history: list[ConversationMessage] | None = None,
    ) -> dict[str, Any]:
        """Extract facts from a message and store them.

        Args:
            user_id: Telegram user ID.
            user_message: The user's message to analyze.
            conversation_history: Optional recent conversation history.

        Returns:
            Dictionary with extraction results.
        """
        if not self._settings.long_term_extraction_enabled:
            return {"extracted": False, "reason": "extraction_disabled"}

        try:
            # Format conversation history
            history_text = self._format_history(conversation_history or [])

            # Create prompt
            prompt = EXTRACTION_PROMPT.format(
                conversation_history=history_text,
                user_message=user_message,
            )

            # Call LLM
            messages = [LLMMessage(role=MessageRole.USER, content=prompt)]
            response = await self._llm.generate(messages)

            # Parse response
            result = self._parse_extraction_response(response.content)

            if not result:
                return {"extracted": False, "reason": "parse_error"}

            # Store extracted facts
            stored_facts = []
            for fact in result.get("facts", []):
                if fact.get("confidence", 0) >= self._settings.long_term_confidence_threshold:
                    stored_fact = await self._profile_repo.upsert_fact(
                        user_id=user_id,
                        fact_type=fact["fact_type"],
                        fact_key=fact["fact_key"],
                        fact_value=fact["fact_value"],
                        confidence=fact["confidence"],
                        source="llm_extraction",
                    )
                    stored_facts.append(stored_fact)
                    logger.info(
                        f"Stored fact for user {user_id}: {fact['fact_key']} = {fact['fact_value']}"
                    )

            # Update profile if needed
            profile_updated = False
            if result.get("should_update_profile"):
                profile_updates = result.get("profile_updates", {})
                if any(profile_updates.values()):
                    await self._profile_repo.create_or_update_profile(
                        user_id=user_id,
                        preferred_name=profile_updates.get("preferred_name"),
                        age=profile_updates.get("age"),
                        location=profile_updates.get("location"),
                        occupation=profile_updates.get("occupation"),
                        interests=profile_updates.get("interests"),
                        expertise_areas=profile_updates.get("expertise_areas"),
                    )
                    profile_updated = True
                    logger.info(f"Updated profile for user {user_id}")

            return {
                "extracted": True,
                "facts_count": len(stored_facts),
                "profile_updated": profile_updated,
                "facts": [f.model_dump() for f in stored_facts],
            }

        except Exception as e:
            logger.error(f"Error extracting facts: {e}", exc_info=True)
            return {"extracted": False, "reason": "error", "error": str(e)}

    async def analyze_and_extract(
        self,
        user_id: int,
        message: ConversationMessage,
        recent_messages: list[ConversationMessage],
    ) -> dict[str, Any]:
        """Analyze a message and extract facts.

        This is a convenience method that combines message analysis
        with fact extraction.

        Args:
            user_id: Telegram user ID.
            message: The message to analyze.
            recent_messages: Recent messages for context.

        Returns:
            Dictionary with extraction results.
        """
        if message.role != "user":
            return {"extracted": False, "reason": "not_user_message"}

        return await self.extract_and_store(
            user_id=user_id,
            user_message=message.content,
            conversation_history=recent_messages,
        )

    def _format_history(
        self, history: list[ConversationMessage], max_messages: int = 10
    ) -> str:
        """Format conversation history for the prompt.

        Args:
            history: List of conversation messages.
            max_messages: Maximum number of messages to include.

        Returns:
            Formatted history string.
        """
        if not history:
            return "История пуста."

        # Take last N messages
        messages = history[-max_messages:]
        parts = []

        for msg in messages:
            role = "Пользователь" if msg.role == "user" else "Ассистент"
            # Truncate long messages
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    def _parse_extraction_response(self, response: str) -> dict[str, Any] | None:
        """Parse the LLM extraction response.

        Args:
            response: Raw LLM response.

        Returns:
            Parsed dictionary or None if parsing fails.
        """
        try:
            # Try to extract JSON from the response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                # Remove first and last line if they're code block markers
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response = "\n".join(lines)

            # Parse JSON
            result = json.loads(response)

            # Validate structure
            if "facts" not in result:
                result["facts"] = []

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            return None

    async def batch_extract(
        self,
        user_id: int,
        messages: list[ConversationMessage],
    ) -> list[dict[str, Any]]:
        """Extract facts from multiple messages.

        Args:
            user_id: Telegram user ID.
            messages: List of messages to analyze.

        Returns:
            List of extraction results for each message.
        """
        results = []

        for i, message in enumerate(messages):
            if message.role != "user":
                continue

            # Get context (previous messages)
            context = messages[:i] if i > 0 else []

            result = await self.analyze_and_extract(
                user_id=user_id,
                message=message,
                recent_messages=context,
            )
            results.append(result)

        return results

    async def reanalyze_user_history(
        self,
        user_id: int,
        message_limit: int = 50,
    ) -> dict[str, Any]:
        """Reanalyze a user's conversation history.

        This can be used to extract facts from older conversations
        that were processed before extraction was enabled.

        Args:
            user_id: Telegram user ID.
            message_limit: Maximum number of messages to analyze.

        Returns:
            Dictionary with reanalysis results.
        """
        # Get recent messages
        messages = await self._conversation_repo.get_recent_messages(
            user_id, limit=message_limit
        )

        if not messages:
            return {"analyzed": 0, "extracted": 0}

        # Extract from each message
        results = await self.batch_extract(user_id, messages)

        # Count successes
        extracted_count = sum(1 for r in results if r.get("extracted"))

        return {
            "analyzed": len(messages),
            "extracted": extracted_count,
            "results": results,
        }
