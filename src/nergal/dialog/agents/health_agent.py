"""Health agent for tracking health metrics.

This module provides an agent that can help users track their health metrics
like blood pressure, and provide insights and reminders.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from pytz import timezone as pytz_timezone

from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


HEALTH_SYSTEM_PROMPT = """Ты — помощник для отслеживания здоровья. Ты помогаешь пользователю записывать и анализировать показатели здоровья, особенно артериальное давление.

Твои возможности:
- Записывать измерения артериального давления (три измерения с усреднением)
- Показывать историю измерений в виде таблицы
- Настраивать напоминания о необходимости измерить давление (несколько раз в день)
- Анализировать тренды и давать рекомендации

Важные правила:
1. Отвечай на русском языке
2. Будь заботливым и внимательным
3. Используй эмодзи для визуального оформления (❤️ 💉 📊 ⏰ 💊)
4. Форматируй таблицы красиво
5. Объясняй показатели понятным языком

Категории артериального давления (по AHA):
- Нормальное: <120/80 мм рт.ст.
- Повышенное: 120-129/<80 мм рт.ст.
- Гипертония 1 стадии: 130-139/80-89 мм рт.ст.
- Гипертония 2 стадии: ≥140/90 мм рт.ст.
- Гипертонический кризис: >180/120 мм рт.ст.

При записи измерений:
- Пользователь может указать время измерения или использовать текущее
- Можно записывать несколько измерений в течение дня
- Нужно записать три измерения для точности
- Показать среднее значение и категорию

При настройке напоминаний:
- Можно настро несколько напоминаний на разное день
- Формат: "напомни измерить давление в 09:00 и 21:00"

При запросе истории:
- Показать таблицу с измерениями по дням и часам
- Выделить средние значения
- Указать категорию для каждого измерения"""


class HealthAgent(BaseSpecializedAgent):
    """Agent for tracking health metrics like blood pressure.
    
    This agent handles health-related queries and helps users track
    their blood pressure and other health metrics.
    
    Attributes:
        _keywords: Keywords that trigger this agent.
        _patterns: Regex patterns for more complex matching.
    """
    
    _keywords: list[str] = [
        "давление", "артериальное", "кровяное", "ад",
        "измерить", "измерение", "замер", "тонометр",
        "здоровье", "health", "bp", "blood pressure",
        "систол", "диастол", "пульс",
        "напомни", "напоминание", "напомнить",
        "таблетк", "лекарств", "медикамент",
        "показател", "метрик", "статистик",
        "история измерений", "журнал", "дневник",
    ]
    
    _patterns: list[str] = [
        r"запис[аиы]\s+(давление|измерение|показател)",
        r"измер[ия]\s+(давление|ад)",
        r"мо[ёе]\s+давление",
        r"систолическое|диастолическое",
        r"\d{2,3}/\d{2,3}",  # Blood pressure format like 120/80
        r"напомни\s+(измерить|принять|выпить)",
        r"покажи\s+(историю|измерения|статистику)",
        r"таблица\s+(измерений|давления)",
        r"дневник\s+(здоровья|давления)",
    ]
    
    # Higher base confidence since this is a specialized agent
    _base_confidence: float = 0.3
    _keyword_boost: float = 0.2
    _max_keyword_boost: float = 0.6
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        health_repo: "HealthMetricsRepository | None" = None,
        profile_repo: "ProfileRepository | None" = None,
    ) -> None:
        """Initialize the Health agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            health_repo: Repository for health metrics (optional, uses DI container if not provided).
            profile_repo: Repository for user profiles (optional, for timezone lookup).
        """
        super().__init__(llm_provider, style_type)
        self._health_repo = health_repo
        self._profile_repo = profile_repo
    
    def _get_health_repo(self) -> "HealthMetricsRepository":
        """Get or create the health metrics repository using DI container."""
        if self._health_repo is None:
            from nergal.container import get_container
            container = get_container()
            self._health_repo = container.health_metrics_repository()
        return self._health_repo
    
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
        return AgentType.HEALTH
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return HEALTH_SYSTEM_PROMPT
    
    async def _calculate_custom_confidence(
        self, message: str, context: dict[str, Any]
    ) -> float:
        """Calculate custom confidence based on context.
        
        Checks for blood pressure patterns in the message.
        
        Args:
            message: User message.
            context: Dialog context.
            
        Returns:
            Additional confidence score.
        """
        # Check for blood pressure pattern (e.g., "120/80")
        bp_pattern = r"\d{2,3}/\d{2,3}"
        if re.search(bp_pattern, message):
            return 0.4  # High confidence for BP readings
        
        # Check for reminder-related keywords
        reminder_keywords = ["напомни", "напоминание", "пора", "время"]
        if any(kw in message.lower() for kw in reminder_keywords):
            if any(hk in message.lower() for hk in ["давление", "измерить", "здоровье"]):
                return 0.3
        
        return 0.0
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by handling health-related queries.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with health data.
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
        if self._is_record_request(message_lower):
            response = await self._handle_record_request(user_id, message, context)
        elif self._is_history_request(message_lower):
            response = await self._handle_history_request(user_id, message, context)
        elif self._is_reminder_request(message_lower):
            response = await self._handle_reminder_request(user_id, message, context)
        else:
            # General health query - use LLM
            response = await self._handle_general_query(message, context, history)
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={"query_type": "health_metrics"},
        )
    
    def _is_record_request(self, message: str) -> bool:
        """Check if this is a request to record measurements."""
        record_patterns = [
            r"запис[аиы]",
            r"измер[ия].*\d+",
            r"добавь",
            r"сохрани",
            r"\d{2,3}/\d{2,3}",  # Blood pressure format
        ]
        return any(re.search(p, message) for p in record_patterns)
    
    def _is_history_request(self, message: str) -> bool:
        """Check if this is a request to show history."""
        history_patterns = [
            r"истори[яю]",
            r"покажи.*измерен",
            r"таблиц[ау]",
            r"дневник",
            r"журнал",
            r"статистик[ау]",
            r"все\s+измерен",
        ]
        return any(re.search(p, message) for p in history_patterns)
    
    def _is_reminder_request(self, message: str) -> bool:
        """Check if this is a reminder request."""
        reminder_patterns = [
            r"напомни",
            r"напоминание",
            r"пора",
            r"время\s+(измерить|принять)",
            r"напомнить",
        ]
        return any(re.search(p, message) for p in reminder_patterns)
    
    async def _handle_record_request(
        self,
        user_id: int,
        message: str,
        context: dict[str, Any],
    ) -> str:
        """Handle a request to record blood pressure measurements."""
        # Try to parse blood pressure readings from the message
        readings = self._parse_blood_pressure_readings(message)
        
        if not readings:
            # Ask user for readings
            return (
                "Пожалуйста, укажите измерения артериального давления в формате:\n\n"
                "`120/80 125/82 122/78` — три измерения\n\n"
                "Или с указанием времени:\n"
                "`в 10:30 120/80 125/82 122/78`\n\n"
                "Если время не указано, будет использовано текущее."
            )
        
        # Get user's timezone
        user_timezone = await self._get_user_timezone(user_id)
        
        # Parse time from message or use current time
        measured_at = self._parse_time_from_message(message, user_timezone)
        
        # Validate we have 3 readings
        if len(readings) < 3:
            missing = 3 - len(readings)
            return (
                f"Получено {len(readings)} измерений. Для точности нужно 3 измерения.\n"
                f"Пожалуйста, добавьте ещё {missing} измерени{'е' if missing == 1 else 'я' if missing == 2 else 'й'}."
            )
        
        # Take only first 3 readings if more provided
        readings = readings[:3]
        
        try:
            repo = self._get_health_repo()
            measurement = await repo.create_blood_pressure_measurement(
                user_id=user_id,
                measured_at=measured_at,
                systolic_1=readings[0][0],
                diastolic_1=readings[0][1],
                systolic_2=readings[1][0],
                diastolic_2=readings[1][1],
                systolic_3=readings[2][0],
                diastolic_3=readings[2][1],
                user_timezone=user_timezone,
            )
            
            # Format response
            local_time = measured_at
            if user_timezone:
                try:
                    tz = pytz_timezone(user_timezone)
                    local_time = measured_at.astimezone(tz)
                except Exception:
                    pass
            
            # Build response with optional warnings
            warnings = []
            
            # Check for invalid readings (systolic <= diastolic)
            if not measurement.is_valid_reading:
                warnings.append(
                    "⚠️ **Внимание:** Систолическое давление должно быть выше диастолического. "
                    "Проверьте правильность введённых данных."
                )
            
            # Check for extreme values
            if measurement.has_extreme_values:
                if measurement.systolic_avg > 180 or measurement.diastolic_avg > 120:
                    warnings.append(
                        "🚨 **КРИТИЧЕСКОЕ ЗНАЧЕНИЕ!** Пожалуйста, немедленно обратитесь за медицинской помощью!"
                    )
                elif measurement.systolic_avg < 90 or measurement.diastolic_avg < 60:
                    warnings.append(
                        "⚠️ **Низкое давление.** Если вы чувствуете себя плохо, обратитесь к врачу."
                    )
            
            response = (
                f"✅ **Измерение записано!**\n\n"
                f"📅 Время: {local_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"📍 Таймзона: {user_timezone or 'UTC'}\n\n"
                f"📊 **Измерения:**\n"
                f"| # | Систола | Диастола |\n"
                f"|---|---------|----------|\n"
                f"| 1 | {readings[0][0]} | {readings[0][1]} |\n"
                f"| 2 | {readings[1][0]} | {readings[1][1]} |\n"
                f"| 3 | {readings[2][0]} | {readings[2][1]} |\n\n"
                f"📈 **Среднее: {measurement.systolic_avg:.0f}/{measurement.diastolic_avg:.0f} мм рт.ст.**\n"
                f"🏷 Категория: **{measurement.category}**"
            )
            
            # Add warnings if any
            if warnings:
                response += "\n\n" + "\n\n".join(warnings)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to save blood pressure measurement: {e}", exc_info=True)
            return f"❌ Не удалось сохранить измерение. Пожалуйста, попробуйте ещё раз."
    
    async def _handle_history_request(
        self,
        user_id: int,
        message: str,
        context: dict[str, Any],
    ) -> str:
        """Handle a request to show measurement history."""
        # Parse number of days from message (default 7)
        days = 7
        days_match = re.search(r"за\s+(\d+)\s+дн", message)
        if days_match:
            days = int(days_match.group(1))
        
        try:
            repo = self._get_health_repo()
            measurements_by_day = await repo.get_blood_pressure_by_day(user_id, days)
            
            if not measurements_by_day:
                return (
                    f"📊 За последние {days} дней измерений не найдено.\n\n"
                    "Чтобы записать измерение, отправьте три показания в формате:\n"
                    "`120/80 125/82 122/78`"
                )
            
            # Get user's timezone
            user_timezone = await self._get_user_timezone(user_id)
            
            # Build response
            response_parts = [f"📊 **История измерений за {days} дней:**\n"]
            
            for date_str in sorted(measurements_by_day.keys(), reverse=True):
                measurements = measurements_by_day[date_str]
                response_parts.append(f"\n### 📅 {date_str}")
                response_parts.append(
                    "| Время | 1-е | 2-е | 3-е | Среднее |"
                )
                response_parts.append(
                    "|-------|-----|-----|-----|---------|"
                )
                
                for m in measurements:
                    local_time = m.measured_at
                    if user_timezone:
                        try:
                            tz = pytz_timezone(user_timezone)
                            local_time = m.measured_at.astimezone(tz)
                        except Exception:
                            pass
                    
                    response_parts.append(
                        f"| {local_time.strftime('%H:%M')} | "
                        f"{m.systolic_1}/{m.diastolic_1} | "
                        f"{m.systolic_2}/{m.diastolic_2} | "
                        f"{m.systolic_3}/{m.diastolic_3} | "
                        f"**{m.systolic_avg:.0f}/{m.diastolic_avg:.0f}** |"
                    )
            
            # Add statistics
            stats = await repo.get_blood_pressure_stats(user_id, days)
            if stats["total_measurements"] > 0:
                response_parts.append(f"\n### 📈 Статистика:")
                response_parts.append(f"- Всего измерений: {stats['total_measurements']}")
                if stats["avg_systolic"]:
                    response_parts.append(
                        f"- Среднее АД: {stats['avg_systolic']:.0f}/{stats['avg_diastolic']:.0f} мм рт.ст."
                    )
                if stats["min_systolic"] and stats["max_systolic"]:
                    response_parts.append(
                        f"- Диапазон систолы: {stats['min_systolic']:.0f} - {stats['max_systolic']:.0f}"
                    )
                    response_parts.append(
                        f"- Диапазон диастолы: {stats['min_diastolic']:.0f} - {stats['max_diastolic']:.0f}"
                    )
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Failed to get blood pressure history: {e}", exc_info=True)
            return "❌ Не удалось получить историю измерений. Пожалуйста, попробуйте позже."
    
    async def _handle_reminder_request(
        self,
        user_id: int,
        message: str,
        context: dict[str, Any],
    ) -> str:
        """Handle a reminder request.
        
        Supports:
        - Setting single reminder: "напомни измерить давление в 09:00"
        - Setting multiple reminders: "напомни измерить давление в 09:00 и 21:00"
        - Listing reminders: "покажи напоминания"
        - Deleting reminders: "удали напоминание в 09:00"
        """
        # Check if user has timezone set
        user_timezone = await self._get_user_timezone(user_id)
        
        if not user_timezone:
            return (
                "⏰ Чтобы настроить напоминания, мне нужно знать ваш часовой пояс.\n\n"
                "Пожалуйста, укажите ваш часовой пояс, например:\n"
                "- `Europe/Moscow`\n"
                "- `Asia/Yekaterinburg`\n"
                "- `America/New_York`\n\n"
                "Или скажите ваш город, и я попробую определить таймзону."
            )
        
        message_lower = message.lower()
        
        # Check for delete request
        if "удали" in message_lower or "delete" in message_lower or "отключи" in message_lower:
            return await self._handle_delete_reminder(user_id, message, user_timezone)
        
        # Check for list request
        if "покажи" in message_lower or "список" in message_lower or "какие" in message_lower:
            return await self._handle_list_reminders(user_id, user_timezone)
        
        # Parse times from message (can be multiple)
        time_pattern = r"в\s+(\d{1,2}):(\d{2})"
        times = re.findall(time_pattern, message)
        
        if not times:
            return (
                "⏰ Во сколько вам напомнить измерить давление?\n\n"
                "Укажите время в формате:\n"
                "- `напомни измерить давление в 09:00`\n"
                "- `напомни в 09:00 и 21:00 измерить давление`\n"
                "- `напомни измерять давление каждое утро в 08:00 и вечером в 20:00`\n\n"
                "Можно настроить до 5 напоминаний в день."
            )
        
        if len(times) > 5:
            return (
                f"⚠️ Слишком много напоминаний! Максимум 5 напоминаний в день.\n\n"
                f"Вы указали {len(times)} времен. Пожалуйста, выберите до 5."
            )
        
        # Create reminders
        try:
            repo = self._get_health_repo()
            created_reminders = []
            
            for time_match in times:
                hour = int(time_match[0])
                minute = int(time_match[1])
                
                # Validate time range
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    return (
                        f"⚠️ Некорректное время: {hour:02d}:{minute:02d}.\n\n"
                        "Используйте формат ЧЧ:ММ (00:00 - 23:59)."
                    )
                
                time_str = f"{hour:02d}:{minute:02d}"
                
                reminder = await repo.create_reminder(
                    user_id=user_id,
                    reminder_type="blood_pressure",
                    reminder_time=time_str,
                    user_timezone=user_timezone,
                )
                created_reminders.append(reminder)
            
            # Format response
            times_str = ", ".join([r.reminder_time for r in created_reminders])
            
            return (
                f"✅ Напоминания настроены!\n\n"
                f"⏰ Время: {times_str}\n"
                f"📍 Таймзона: {user_timezone}\n\n"
                f"Я буду напоминать вам измерить давление в указанное время.\n\n"
                f"📋 Для управления напоминаниями используйте:\n"
                f"- `покажи напоминания` — список all reminders\n"
                f"- `удали напоминание в HH:MM` — удалить reminder"
            )
            
        except Exception as e:
            logger.error(f"Failed to create reminder: {e}", exc_info=True)
            return "❌ Не удалось создать напоминание. Пожалуйста, попробуйте ещё раз."
    
    async def _handle_list_reminders(
        self,
        user_id: int,
        user_timezone: str,
    ) -> str:
        """Show list of active reminders."""
        try:
            repo = self._get_health_repo()
            reminders = await repo.get_reminders_for_user(
                user_id=user_id,
                reminder_type="blood_pressure",
                active_only=True,
            )
            
            if not reminders:
                return (
                    "📋 У вас нет активных напоминаний.\n\n"
                    "Чтобы добавить напоминание, используйте:\n"
                    "`напомни измерить давление в 09:00`"
                )
            
            # Format reminder list
            lines = ["📋 **Ваши напоминания:**\n"]
            for r in reminders:
                lines.append(f"⏰ {r.reminder_time} — {r.user_timezone or user_timezone}")
            
            lines.append("\nДля удаления используйте: `удали напоминание в HH:MM`")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to list reminders: {e}", exc_info=True)
            return "❌ Не удалось получить список напоминаний. Пожалуйста, попробуйте позже."
    
    async def _handle_delete_reminder(
        self,
        user_id: int,
        message: str,
        user_timezone: str,
    ) -> str:
        """Delete a reminder."""
        # Parse time from message
        time_pattern = r"в\s+(\d{1,2}):(\d{2})"
        time_match = re.search(time_pattern, message)
        
        if not time_match:
            return (
                "⚠️ Укажите время напоминания для удаления.\n\n"
                "Пример: `удали напоминание в 09:00`"
            )
        
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        
        # Validate time range
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return (
                f"⚠️ Некорректное время: {hour:02d}:{minute:02d}.\n\n"
                "Используйте формат ЧЧ:ММ (00:00 - 23:59)."
            )
        
        time_str = f"{hour:02d}:{minute:02d}"
        
        try:
            repo = self._get_health_repo()
            deleted = await repo.delete_reminder(
                user_id=user_id,
                reminder_type="blood_pressure",
                reminder_time=time_str,
            )
            
            if deleted:
                return (
                    f"✅ Напоминание в {time_str} удалено.\n\n"
                    "Остальные напоминания можно посмотреть команд: `покажи напоминания`"
                )
            else:
                return f"⚠️ Напоминание в {time_str} не найдено."
                
        except Exception as e:
            logger.error(f"Failed to delete reminder: {e}", exc_info=True)
            return "❌ Не удалось удалить напоминание. Пожалуйста, попробуйте позже."
    
    async def _handle_general_query(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> str:
        """Handle general health-related queries using LLM."""
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
        ]
        
        # Add recent history for context
        for msg in history[-5:]:
            messages.append(msg)
        
        messages.append(LLMMessage(role=MessageRole.USER, content=message))
        
        response = await self.llm_provider.generate(messages, max_tokens=1000)
        return response.content
    
    def _parse_blood_pressure_readings(self, message: str) -> list[tuple[int, int]]:
        """Parse blood pressure readings from message.
        
        Looks for patterns like "120/80" in the message.
        
        Args:
            message: User message.
            
        Returns:
            List of (systolic, diastolic) tuples.
        """
        readings = []
        # Find all BP patterns
        pattern = r"(\d{2,3})/(\d{2,3})"
        matches = re.findall(pattern, message)
        
        for match in matches:
            systolic = int(match[0])
            diastolic = int(match[1])
            
            # Validate ranges
            if 60 <= systolic <= 250 and 40 <= diastolic <= 150:
                readings.append((systolic, diastolic))
        
        return readings
    
    def _parse_time_from_message(
        self,
        message: str,
        user_timezone: str | None,
    ) -> datetime:
        """Parse measurement time from message or return current time.
        
        Args:
            message: User message.
            user_timezone: User's timezone.
            
        Returns:
            datetime in UTC.
        """
        # Try to parse time from message
        time_match = re.search(r"в\s+(\d{1,2}):(\d{2})", message)
        date_match = re.search(r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?", message)
        
        now = datetime.now(timezone.utc)
        
        if user_timezone:
            try:
                tz = pytz_timezone(user_timezone)
                now = datetime.now(tz)
            except Exception:
                pass
        
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = int(date_match.group(3)) if date_match.group(3) else now.year
                if year < 100:
                    year += 2000
                
                try:
                    if user_timezone:
                        tz = pytz_timezone(user_timezone)
                        local_dt = tz.localize(datetime(year, month, day, hour, minute))
                        return local_dt.astimezone(timezone.utc)
                except Exception:
                    pass
            else:
                # Use today's date with specified time
                try:
                    if user_timezone:
                        tz = pytz_timezone(user_timezone)
                        local_dt = tz.localize(datetime(now.year, now.month, now.day, hour, minute))
                        return local_dt.astimezone(timezone.utc)
                except Exception:
                    pass
        
        # Return current time in UTC
        return datetime.now(timezone.utc)
    
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
        
        return None
    
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
