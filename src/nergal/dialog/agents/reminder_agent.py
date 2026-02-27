"""Reminder agent for handling general-purpose reminders.

This module provides an agent that can help users set, list, and delete
general-purpose reminders that trigger at specific times.
"""

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

from pytz import timezone as pytz_timezone
from pytz import UTC

from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


REMINDER_SYSTEM_PROMPT = """Ты — помощник для управления напоминаниями. Ты помогаешь пользователю создавать, просматривать и удалять напоминания.

Твои возможности:
- Создавать напоминания на определённое время
- Создавать повторяющиеся напоминания (каждый день, по будням, и т.д.)
- Показывать список всех напоминаний
- Удалять напоминания

Важные правила:
1. Отвечай на русском языке
2. Будь кратким и точным
3. Используй эмодзи для визуального оформления (⏰ 📅 🔔 ✅ ❌)
4. Всегда уточняй время, если оно не указано явно

При создании напоминания:
- Если не указана дата, напоминание считается повторяющимся ежедневно
- Если указана конкретная дата, напоминание сработает только один раз
- По умолчанию используй таймзону Europe/Moscow если не указана другая

Примеры запросов:
- "напомни мне в19:30 позвонить маме" — повторяющееся напоминание
- "напомни завтра в10:00 о встрече" — одноразовое напоминание
- "напомни каждый будний день в09:00 проверить почту" — по будням
- "покажи мои напоминания" — список всех напоминаний
- "удали напоминание в19:30" — удалить напоминание"""


class ReminderAgent(BaseSpecializedAgent):
    """Agent for managing general-purpose reminders.
    
    This agent handles reminder-related queries and helps users set,
    view, and delete reminders.
    
    Attributes:
        _keywords: Keywords that trigger this agent.
        _patterns: Regex patterns for more complex matching.
    """
    
    _keywords: list[str] = [
        "напомни", "напоминание", "напомнить",
        "напомни мне", "поставь напоминание",
        "разбуди", "будильник",
        "не забудь", "запомни",
    ]
    
    _patterns: list[str] = [
        r"напомни\s+(мне\s+)?(в|завтра|послезавтра|через)",
        r"напоминание\s+(на|в|о)",
        r"поставь\s+напоминание",
        r"удали\s+напоминание",
        r"покажи\s+(мои\s+)?напоминания",
        r"список\s+напоминаний",
        r"в\s+\d{1,2}:\d{2}\s+напомни",
    ]
    
    # Higher base confidence since this is a specialized agent
    _base_confidence: float = 0.4
    _keyword_boost: float = 0.2
    _max_keyword_boost: float = 0.7
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        reminder_repo: "GeneralReminderRepository | None" = None,
        profile_repo: "ProfileRepository | None" = None,
    ) -> None:
        """Initialize the Reminder agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            reminder_repo: Repository for general reminders (optional).
            profile_repo: Repository for user profiles (optional, for timezone lookup).
        """
        super().__init__(llm_provider, style_type)
        self._reminder_repo = reminder_repo
        self._profile_repo = profile_repo
    
    def _get_reminder_repo(self) -> "GeneralReminderRepository":
        """Get or create the reminder repository using DI container."""
        if self._reminder_repo is None:
            from nergal.container import get_container
            container = get_container()
            self._reminder_repo = container.general_reminder_repository()
        return self._reminder_repo
    
    def _get_profile_repo(self) -> "ProfileRepository":
        """Get or create the profile repository using DI container."""
        if self._profile_repo is None:
            from nergal.container import get_container
            container = get_container()
            self._profile_repo = container.profile_repository()
        return self._profile_repo
    
    @property
    def agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.REMINDER
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return REMINDER_SYSTEM_PROMPT
    
    async def _calculate_custom_confidence(
        self, message: str, context: dict[str, Any]
    ) -> float:
        """Calculate custom confidence based on context.
        
        Checks for reminder-specific patterns in the message.
        
        Args:
            message: User message.
            context: Dialog context.
            
        Returns:
            Additional confidence score.
        """
        message_lower = message.lower()
        
        # High confidence for explicit reminder requests
        if re.search(r"напомни\s+(мне\s+)?в\s+\d", message_lower):
            return 0.5
        
        # Good confidence for reminder management
        if any(kw in message_lower for kw in ["напоминание", "напоминания", "напоминаний"]):
            return 0.4
        
        # Check for time + action pattern
        time_pattern = r"в\s+\d{1,2}:\d{2}"
        if re.search(time_pattern, message_lower):
            action_keywords = ["позвонить", "встретить", "принять", "сделать", "проверить", "пойти"]
            if any(kw in message_lower for kw in action_keywords):
                return 0.3
        
        return 0.0
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by handling reminder-related queries.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with reminder data.
        """
        user_id = context.get("user_id")
        if not user_id:
            return AgentResult(
                response="Не удалось определить пользователя. Пожалуйста, перезапустите бота.",
                agent_type=self.agent_type,
                confidence=0.9,
            )
        
        message_lower = message.lower()
        
        # Determine the type of request
        if self._is_list_request(message_lower):
            response = await self._handle_list_request(user_id)
        elif self._is_delete_request(message_lower):
            response = await self._handle_delete_request(user_id, message)
        else:
            response = await self._handle_create_request(user_id, message)
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={"query_type": "reminder"},
        )
    
    def _is_list_request(self, message: str) -> bool:
        """Check if this is a request to list reminders."""
        list_patterns = [
            r"покажи\s+(мои\s+)?напоминания",
            r"список\s+напоминаний",
            r"какие\s+напоминания",
            r"все\s+напоминания",
            r"мои\s+напоминания",
        ]
        return any(re.search(p, message) for p in list_patterns)
    
    def _is_delete_request(self, message: str) -> bool:
        """Check if this is a request to delete a reminder."""
        delete_patterns = [
            r"удали\s+напоминание",
            r"удалить\s+напоминание",
            r"отключи\s+напоминание",
            r"выключи\s+напоминание",
        ]
        return any(re.search(p, message) for p in delete_patterns)
    
    async def _handle_list_request(self, user_id: int) -> str:
        """Show list of active reminders."""
        try:
            repo = self._get_reminder_repo()
            reminders = await repo.get_reminders_for_user(user_id, active_only=True)
            
            if not reminders:
                return (
                    "📋 У вас нет активных напоминаний.\n\n"
                    "Чтобы создать напоминание, используйте:\n"
                    "`напомни мне в19:30 позвонить маме`"
                )
            
            # Group by recurring vs one-time
            recurring = [r for r in reminders if r.is_recurring]
            onetime = [r for r in reminders if not r.is_recurring]
            
            lines = ["📋 **Ваши напоминания:**\n"]
            
            if recurring:
                lines.append("**Повторяющиеся:**")
                for r in recurring:
                    days_str = r.format_days() if r.recurring_days != [0,1,2,3,4,5,6] else "каждый день"
                    desc = f" — {r.description}" if r.description else ""
                    lines.append(f"⏰ {r.reminder_time} ({days_str}) — {r.title}{desc}")
                lines.append("")
            
            if onetime:
                lines.append("**Одноразовые:**")
                for r in onetime:
                    date_str = f" на {r.reminder_date.strftime('%d.%m.%Y')}" if r.reminder_date else ""
                    desc = f" — {r.description}" if r.description else ""
                    lines.append(f"⏰ {r.reminder_time}{date_str} — {r.title}{desc}")
            
            lines.append("\nДля удаления: `удали напоминание в HH:MM`")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to list reminders: {e}", exc_info=True)
            return "❌ Не удалось получить список напоминаний. Пожалуйста, попробуйте позже."
    
    async def _handle_delete_request(self, user_id: int, message: str) -> str:
        """Delete a reminder."""
        # Parse time from message
        time_pattern = r"в\s*(\d{1,2}):(\d{2})"
        match = re.search(time_pattern, message)
        
        if not match:
            return (
                "⏰ Укажите время напоминания для удаления.\n\n"
                "Пример: `удали напоминание в19:30`"
            )
        
        hour = int(match.group(1))
        minute = int(match.group(2))
        time_str = f"{hour:02d}:{minute:02d}"
        
        try:
            repo = self._get_reminder_repo()
            deleted = await repo.delete_reminder(
                user_id=user_id,
                reminder_time=time_str,
            )
            
            if deleted:
                return f"✅ Напоминание в {time_str} удалено."
            else:
                return f"❌ Напоминание в {time_str} не найдено."
                
        except Exception as e:
            logger.error(f"Failed to delete reminder: {e}", exc_info=True)
            return "❌ Не удалось удалить напоминание. Пожалуйста, попробуйте позже."
    
    async def _handle_create_request(self, user_id: int, message: str) -> str:
        """Create a new reminder."""
        # Get user's timezone
        user_timezone = await self._get_user_timezone(user_id)
        
        # Parse time from message
        time_pattern = r"в\s*(\d{1,2}):(\d{2})"
        time_match = re.search(time_pattern, message.lower())
        
        if not time_match:
            return (
                "⏰ Во сколько вам напомнить?\n\n"
                "Укажите время в формате:\n"
                "- `напомни мне в19:30 позвонить маме`\n"
                "- `напомни завтра в10:00 о встрече`\n"
                "- `напомни каждый день в08:00 принять таблетки`"
            )
        
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        
        # Validate time
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return f"⚠️ Некорректное время: {hour:02d}:{minute:02d}. Используйте формат ЧЧ:ММ (00:00 - 23:59)."
        
        time_str = f"{hour:02d}:{minute:02d}"
        
        # Parse title/description from message
        title = self._extract_title(message)
        
        # Determine if this is recurring or one-time
        is_recurring, reminder_date, recurring_days = self._parse_recurrence(message.lower())
        
        # Create reminder
        try:
            repo = self._get_reminder_repo()
            reminder = await repo.create_reminder(
                user_id=user_id,
                title=title,
                reminder_time=time_str,
                description=None,
                reminder_date=reminder_date,
                user_timezone=user_timezone,
                is_recurring=is_recurring,
                recurring_days=recurring_days,
            )
            
            # Format response
            if is_recurring:
                if recurring_days == [0, 1, 2, 3, 4, 5, 6]:
                    recurrence_str = "каждый день"
                elif recurring_days == [0, 1, 2, 3, 4]:
                    recurrence_str = "по будням"
                elif recurring_days == [5, 6]:
                    recurrence_str = "по выходным"
                else:
                    day_names = {
                        0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"
                    }
                    recurrence_str = "по " + ", ".join(day_names.get(d, str(d)) for d in sorted(recurring_days))
                
                return (
                    f"✅ Напоминание создано!\n\n"
                    f"⏰ Время: {time_str}\n"
                    f"📅 Повторение: {recurrence_str}\n"
                    f"📝 Текст: {title}\n"
                    f"📍 Таймзона: {user_timezone or 'UTC'}\n\n"
                    f"Я буду напоминать вам {recurrence_str} в указанное время."
                )
            else:
                date_str = reminder_date.strftime("%d.%m.%Y") if reminder_date else "сегодня"
                return (
                    f"✅ Напоминание создано!\n\n"
                    f"⏰ Время: {time_str}\n"
                    f"📅 Дата: {date_str}\n"
                    f"📝 Текст: {title}\n"
                    f"📍 Таймзона: {user_timezone or 'UTC'}\n\n"
                    f"Я напомню вам в указанное время."
                )
                
        except Exception as e:
            logger.error(f"Failed to create reminder: {e}", exc_info=True)
            return "❌ Не удалось создать напоминание. Пожалуйста, попробуйте ещё раз."
    
    def _extract_title(self, message: str) -> str:
        """Extract the reminder title from the message."""
        # Remove common prefixes
        text = message.lower()
        prefixes = [
            r"напомни\s+(мне\s+)?",
            r"поставь\s+напоминание\s+",
            r"создай\s+напоминание\s+",
        ]
        for prefix in prefixes:
            text = re.sub(prefix, "", text)
        
        # Remove time patterns
        text = re.sub(r"в\s*\d{1,2}:\d{2}", "", text)
        text = re.sub(r"завтра", "", text)
        text = re.sub(r"послезавтра", "", text)
        text = re.sub(r"каждый\s+(день|будний|сутки)", "", text)
        text = re.sub(r"по\s+(будням|выходным|понедельникам|вторникам|средам|четвергам|пятницам|субботам|воскресеньям)", "", text)
        text = re.sub(r"через\s+\d+\s+(минут|час|день|дня|дней)", "", text)
        
        # Clean up
        text = text.strip(" ,.!")
        
        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]
        
        return text or "Напоминание"
    
    def _parse_recurrence(self, message: str) -> tuple[bool, date | None, list[int]]:
        """Parse recurrence pattern from message.
        
        Returns:
            Tuple of (is_recurring, reminder_date, recurring_days)
        """
        today = date.today()
        
        # Check for specific date keywords
        if "завтра" in message:
            return (False, today + timedelta(days=1), [0, 1, 2, 3, 4, 5, 6])
        if "послезавтра" in message:
            return (False, today + timedelta(days=2), [0, 1, 2, 3, 4, 5, 6])
        
        # Check for recurring patterns
        if "каждый день" in message or "ежедневно" in message:
            return (True, None, [0, 1, 2, 3, 4, 5, 6])
        
        if "по будням" in message or "каждый будний день" in message:
            return (True, None, [0, 1, 2, 3, 4])
        
        if "по выходным" in message or "каждые выходные" in message:
            return (True, None, [5, 6])
        
        # Check for specific days
        day_mapping = {
            "понедельникам": 0, "понедельник": 0, "пн": 0,
            "вторникам": 1, "вторник": 1, "вт": 1,
            "средам": 2, "среда": 2, "ср": 2,
            "четвергам": 3, "четверг": 3, "чт": 3,
            "пятницам": 4, "пятница": 4, "пт": 4,
            "субботам": 5, "суббота": 5, "сб": 5,
            "воскресеньям": 6, "воскресенье": 6, "вс": 6,
        }
        
        recurring_days = []
        for day_name, day_num in day_mapping.items():
            if day_name in message:
                recurring_days.append(day_num)
        
        if recurring_days:
            return (True, None, sorted(set(recurring_days)))
        
        # Default: one-time reminder for today
        return (False, None, [0, 1, 2, 3, 4, 5, 6])
    
    async def _get_user_timezone(self, user_id: int) -> str | None:
        """Get user's timezone from profile.
        
        Args:
            user_id: Telegram user ID.
            
        Returns:
            User's timezone string or None.
        """
        try:
            repo = self._get_profile_repo()
            profile = await repo.get_profile(user_id)
            if profile and profile.timezone:
                return profile.timezone
        except Exception as e:
            logger.warning(f"Failed to get user timezone: {e}", exc_info=True)
        
        # Default timezone for Russian users
        return "Europe/Moscow"
    
    async def set_user_timezone(self, user_id: int, timezone_str: str) -> bool:
        """Set user's timezone in their profile.
        
        Args:
            user_id: Telegram user ID.
            timezone_str: Timezone string (e.g., "Europe/Moscow").
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Validate timezone
            tz = pytz_timezone(timezone_str)
            
            repo = self._get_profile_repo()
            await repo.create_or_update_profile(user_id, timezone=timezone_str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to set user timezone: {e}", exc_info=True)
            return False
