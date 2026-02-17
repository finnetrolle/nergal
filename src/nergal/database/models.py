"""Database models for user memory management.

This module defines Pydantic models that represent database tables
for users, profiles, and conversation history.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class User(BaseModel):
    """User model representing a Telegram user."""

    id: int  # Telegram user ID
    telegram_username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None
    is_allowed: bool = False  # Whether user is allowed to use the bot
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or f"User {self.id}"

    @property
    def display_name(self) -> str:
        """Get a display name for the user."""
        if self.telegram_username:
            return f"@{self.telegram_username}"
        return self.full_name


class UserProfile(BaseModel):
    """User profile model for long-term memory."""

    id: UUID | None = None
    user_id: int

    # Personal information
    preferred_name: str | None = None
    age: int | None = None
    location: str | None = None
    timezone: str | None = None
    occupation: str | None = None
    languages: list[str] = Field(default_factory=list)

    # Preferences
    interests: list[str] = Field(default_factory=list)
    expertise_areas: list[str] = Field(default_factory=list)
    communication_style: str | None = None

    # Custom attributes
    custom_attributes: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProfileFact(BaseModel):
    """A single fact about a user stored in long-term memory."""

    id: UUID | None = None
    user_id: int

    fact_type: str  # e.g., "personal", "preference", "interest"
    fact_key: str  # e.g., "favorite_color", "location"
    fact_value: str  # The actual value
    confidence: float = 1.0  # 0-1 confidence level
    source: str | None = None  # How this fact was learned

    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None


class ConversationMessage(BaseModel):
    """A single message in a conversation (short-term memory)."""

    id: UUID | None = None
    user_id: int
    session_id: str

    role: str  # 'user', 'assistant', or 'system'
    content: str

    # Metadata
    agent_type: str | None = None
    tokens_used: int | None = None
    processing_time_ms: int | None = None

    created_at: datetime | None = None


class ConversationSession(BaseModel):
    """A conversation session."""

    id: str  # Session identifier
    user_id: int

    started_at: datetime | None = None
    ended_at: datetime | None = None
    message_count: int = 0

    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryExtractionEvent(BaseModel):
    """Event recording extraction of facts from a message."""

    id: UUID | None = None
    user_id: int
    message_id: UUID | None = None

    extracted_facts: dict[str, Any]  # Facts extracted from the message
    extraction_confidence: float | None = None
    was_applied: bool = False

    created_at: datetime | None = None


class WebSearchTelemetry(BaseModel):
    """Telemetry data for web search operations.

    Captures comprehensive information about search requests,
    responses, and any errors that occur.
    """

    id: UUID | None = None

    # Request information
    query: str
    user_id: int | None = None
    session_id: str | None = None

    # Request parameters
    result_count_requested: int = 10
    recency_filter: str | None = None
    domain_filter: str | None = None

    # Response information
    status: str  # success, error, timeout, empty
    results_count: int = 0
    results: list[dict[str, Any]] = Field(default_factory=list)

    # Error information
    error_type: str | None = None
    error_message: str | None = None
    error_stack_trace: str | None = None

    # API response details
    http_status_code: int | None = None
    api_response_time_ms: int | None = None
    api_session_id: str | None = None

    # Raw response data for debugging
    raw_response: dict[str, Any] | None = None
    raw_response_truncated: bool = False

    # Timing information
    total_duration_ms: int | None = None
    init_duration_ms: int | None = None
    tools_list_duration_ms: int | None = None
    search_call_duration_ms: int | None = None

    # Provider information
    provider_name: str | None = None
    tool_used: str | None = None

    created_at: datetime | None = None

    def is_success(self) -> bool:
        """Check if the search was successful."""
        return self.status == "success"

    def has_results(self) -> bool:
        """Check if the search returned results."""
        return self.results_count > 0

    def is_error(self) -> bool:
        """Check if the search resulted in an error."""
        return self.status in ("error", "timeout")

    def get_error_summary(self) -> str | None:
        """Get a summary of the error if one occurred."""
        if not self.is_error():
            return None

        parts = []
        if self.error_type:
            parts.append(self.error_type)
        if self.error_message:
            parts.append(self.error_message)
        if self.http_status_code:
            parts.append(f"HTTP {self.http_status_code}")

        return ": ".join(parts) if parts else None


class UserMemoryContext(BaseModel):
    """Complete memory context for a user, used by agents."""

    user: User
    profile: UserProfile | None = None
    facts: list[ProfileFact] = Field(default_factory=list)
    recent_messages: list[ConversationMessage] = Field(default_factory=list)
    current_session: ConversationSession | None = None

    def get_profile_summary(self) -> str:
        """Get a human-readable summary of the user's profile."""
        parts = []

        if self.profile:
            if self.profile.preferred_name:
                parts.append(f"Имя: {self.profile.preferred_name}")
            elif self.user.first_name:
                parts.append(f"Имя: {self.user.first_name}")

            if self.profile.age:
                parts.append(f"Возраст: {self.profile.age}")

            if self.profile.location:
                parts.append(f"Местоположение: {self.profile.location}")

            if self.profile.occupation:
                parts.append(f"Род занятий: {self.profile.occupation}")

            if self.profile.interests:
                parts.append(f"Интересы: {', '.join(self.profile.interests)}")

            if self.profile.expertise_areas:
                parts.append(f"Экспертиза: {', '.join(self.profile.expertise_areas)}")

        # Add facts
        if self.facts:
            for fact in self.facts[:5]:  # Limit to top 5 facts
                parts.append(f"{fact.fact_key}: {fact.fact_value}")

        return "\n".join(parts) if parts else "Информация о пользователе отсутствует."

    def get_conversation_summary(self, max_messages: int = 10) -> str:
        """Get a summary of recent conversation."""
        if not self.recent_messages:
            return "История беседы пуста."

        messages = self.recent_messages[-max_messages:]
        parts = []

        for msg in messages:
            role = "Пользователь" if msg.role == "user" else "Ассистент"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            parts.append(f"{role}: {content}")

        return "\n".join(parts)
