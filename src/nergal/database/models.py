"""Database models for user memory management.

This module defines Pydantic models that represent database tables
for users, profiles, and conversation history.
"""

from datetime import date, datetime
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

    # Retry information
    retry_count: int = 0
    retry_reasons: list[str] = Field(default_factory=list)
    total_retry_delay_ms: int | None = None

    # Error classification
    error_category: str | None = None  # transient, auth, quota, service_error, etc.

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


class UserIntegration(BaseModel):
    """User integration with external services (e.g., Todoist)."""
    
    id: UUID | None = None
    user_id: int
    integration_type: str  # "todoist", "notion", etc.
    encrypted_token: str | None = None
    token_hash: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BloodPressureMeasurement(BaseModel):
    """Blood pressure measurement record.
    
    Stores a single blood pressure measurement session with three readings
    as is standard practice for accurate blood pressure monitoring.
    """
    
    id: UUID | None = None
    user_id: int
    
    # Measurement time (in user's timezone, stored as UTC)
    measured_at: datetime
    
    # Three consecutive readings (systolic/diastolic in mmHg)
    # Reading 1
    systolic_1: int
    diastolic_1: int
    
    # Reading 2
    systolic_2: int
    diastolic_2: int
    
    # Reading 3
    systolic_3: int
    diastolic_3: int
    
    # Calculated averages (stored for quick retrieval)
    systolic_avg: float
    diastolic_avg: float
    
    # Optional notes
    notes: str | None = None
    
    # User's timezone at time of measurement
    user_timezone: str | None = None
    
    created_at: datetime | None = None
    
    @property
    def is_valid_reading(self) -> bool:
        """Check if systolic is greater than diastolic for all readings.
        
        Physiologically, systolic should always be higher than diastolic.
        Returns False if any reading has systolic <= diastolic.
        """
        return (
            self.systolic_1 > self.diastolic_1 and
            self.systolic_2 > self.diastolic_2 and
            self.systolic_3 > self.diastolic_3 and
            self.systolic_avg > self.diastolic_avg
        )
    
    @property
    def has_extreme_values(self) -> bool:
        """Check if any values are in extreme/dangerous ranges.
        
        Returns True if readings suggest medical emergency.
        """
        # Check for extremely low (shock) or extremely high (crisis) values
        return (
            self.systolic_avg < 90 or self.diastolic_avg < 60 or  # Too low
            self.systolic_avg > 180 or self.diastolic_avg > 120   # Crisis level
        )
    
    @property
    def category(self) -> str:
        """Classify blood pressure category based on average values.
        
        Based on American Heart Association guidelines.
        Order matters: check most severe conditions first.
        """
        # Hypertensive crisis - check first (most severe)
        if self.systolic_avg > 180 or self.diastolic_avg > 120:
            return "Гипертонический кризис"
        # Hypertension Stage 2: ≥140 OR ≥90
        elif self.systolic_avg >= 140 or self.diastolic_avg >= 90:
            return "Гипертония 2 стадии"
        # Hypertension Stage 1: 130-139 OR 80-89
        elif self.systolic_avg >= 130 or self.diastolic_avg >= 80:
            return "Гипертония 1 стадии"
        # Elevated: 120-129 AND <80
        elif self.systolic_avg >= 120 and self.diastolic_avg < 80:
            return "Повышенное"
        # Normal: <120 AND <80
        else:
            return "Нормальное"
    
    def to_table_row(self) -> str:
        """Format measurement as a table row for display."""
        return (
            f"| {self.measured_at.strftime('%d.%m %H:%M')} | "
            f"{self.systolic_1}/{self.diastolic_1} | "
            f"{self.systolic_2}/{self.diastolic_2} | "
            f"{self.systolic_3}/{self.diastolic_3} | "
            f"**{self.systolic_avg:.0f}/{self.diastolic_avg:.0f}** |"
        )


class HealthReminder(BaseModel):
    """Health reminder for scheduled notifications.
    
    Stores user-configured reminders for health-related tasks
    like measuring blood pressure.
    """
    
    id: UUID | None = None
    user_id: int
    
    # Reminder type (blood_pressure, weight, medication, etc.)
    reminder_type: str
    
    # Reminder time (hour and minute in user's timezone)
    reminder_time: str  # Format: "HH:MM"
    
    # User's timezone
    user_timezone: str | None = None
    
    # Whether reminder is active
    is_active: bool = True
    
    # Last reminder sent
    last_sent_at: datetime | None = None
    
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    def format_time(self) -> str:
        """Format reminder time for display."""
        return self.reminder_time


class GeneralReminder(BaseModel):
    """General-purpose reminder for scheduled notifications.
    
    Stores user-configured reminders for any purpose,
    supporting both one-time and recurring reminders.
    """
    
    id: UUID | None = None
    user_id: int
    
    # Reminder content
    title: str
    description: str | None = None
    
    # Reminder time (hour and minute in user's timezone)
    reminder_time: str  # Format: "HH:MM"
    
    # Date for one-time reminders (None for recurring)
    reminder_date: date | None = None
    
    # User's timezone
    user_timezone: str | None = None
    
    # Whether reminder is active
    is_active: bool = True
    
    # Whether this is a recurring reminder
    is_recurring: bool = False
    
    # Days of week for recurring reminders (0=Monday, 6=Sunday)
    recurring_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    
    # Last reminder sent
    last_sent_at: datetime | None = None
    
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    def format_time(self) -> str:
        """Format reminder time for display."""
        return self.reminder_time
    
    def format_days(self) -> str:
        """Format recurring days for display in Russian."""
        if not self.is_recurring:
            return ""
        
        day_names = {
            0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"
        }
        return ", ".join(day_names.get(d, str(d)) for d in sorted(self.recurring_days))


class UserMemoryContext(BaseModel):
    """Complete memory context for a user, used by agents."""

    user: User
    profile: UserProfile | None = None
    facts: list[ProfileFact] = Field(default_factory=list)
    recent_messages: list[ConversationMessage] = Field(default_factory=list)
    current_session: ConversationSession | None = None
    integrations: list[UserIntegration] = Field(default_factory=list)

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
