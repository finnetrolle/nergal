"""Todoist agent for task management.

This module provides an agent that can interact with Todoist API
to help users manage their tasks, projects, and labels.
"""

import logging
import re
from typing import Any

from nergal.database.repositories import UserIntegrationRepository
from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.integrations.todoist import (
    TodoistError,
    TodoistProject,
    TodoistService,
    TodoistTask,
)
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


TODOIST_SYSTEM_PROMPT = """Ты — умный помощник для управления задачами в Todoist. Ты помогаешь пользователю работать с задачами, проектами и метками.

Твои возможности:
- Создавать новые задачи (с датами, приоритетами, проектами)
- Показывать задачи (сегодня, просроченные, все, по проектам)
- Завершать задачи
- Удалять задачи
- Создавать и показывать проекты
- Быстрое добавление задач на естественном языке

Важные правила:
1. Отвечай на русском языке
2. Будь кратким и информативным
3. Используй эмодзи для визуального оформления (✅ ⬜ 🔴 🟠 🟡 ⚪ 📅 📁)
4. Форматируй списки задач красиво
5. Если что-то пошло не так, объясни понятным языком

Приоритеты задач:
- 🔴 (p1/4) — срочно
- 🟠 (p2/3) — важно  
- 🟡 (p3/2) — средний
- ⚪ (p4/1) — низкий

Когда показываешь задачи, указывай:
- Статус (выполнено/не выполнено)
- Приоритет
- Срок выполнения
- Проект (если есть)"""


class TodoistAgent(BaseSpecializedAgent):
    """Agent for managing Todoist tasks.
    
    This agent handles task-related queries and interacts with the Todoist API
    on behalf of the user. Each user has their own API token stored securely.
    
    Attributes:
        _keywords: Keywords that trigger this agent.
        _patterns: Regex patterns for more complex matching.
    """
    
    _keywords: list[str] = [
        "задач", "task", "todo", "todoist",
        "дела", "список дел", "список задач",
        "напомин", "remind", "deadline",
        "создай задачу", "add task", "новая задача",
        "покажи задачи", "show tasks", "мои задачи",
        "завершить задачу", "complete task", "выполнить",
        "удалить задачу", "delete task",
        "просрочен", "overdue", "сегодня", "today",
        "проект", "project",
    ]
    
    _patterns: list[str] = [
        r"добавь?\s+(задачу|дело|task)",
        r"создай?\s+(задачу|дело|task)",
        r"покажи\s+(все\s+)?(задачи|дела|tasks)",
        r"список\s+(задач|дел)",
        r"мои\s+(задачи|дела)",
        r"заверш[иы]\s+(задачу|дело)",
        r"отметь?\s+(задачу|дело).*выполнен",
        r"удали?\s+(задачу|дело)",
        r"задачи?\s+(на\s+)?сегодня",
        r"просроченн?ые?\s*(задачи|дела)?",
        r"quick\s*add",
        r"быстрое?\s+добавление",
    ]
    
    # Higher base confidence since this is a specialized integration
    _base_confidence: float = 0.3
    _keyword_boost: float = 0.2
    _max_keyword_boost: float = 0.6
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        integration_repo: UserIntegrationRepository | None = None,
    ) -> None:
        """Initialize the Todoist agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            integration_repo: Repository for user integrations.
        """
        super().__init__(llm_provider, style_type)
        self._integration_repo = integration_repo
    
    def _get_integration_repo(self) -> UserIntegrationRepository:
        """Get or create the integration repository."""
        if self._integration_repo is None:
            self._integration_repo = UserIntegrationRepository()
        return self._integration_repo
    
    @property
    def agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.TODOIST
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return TODOIST_SYSTEM_PROMPT
    
    async def _calculate_custom_confidence(
        self, message: str, context: dict[str, Any]
    ) -> float:
        """Calculate custom confidence based on context.
        
        Checks if user has Todoist integration configured.
        
        Args:
            message: User message.
            context: Dialog context.
            
        Returns:
            Additional confidence score.
        """
        # Check if user has Todoist integration
        user_id = context.get("user_id")
        if user_id:
            try:
                repo = self._get_integration_repo()
                integration = await repo.get_by_user_and_type(user_id, "todoist")
                if integration and integration.is_active:
                    return 0.15  # Boost confidence if user has active integration
            except Exception as e:
                logger.debug(f"Could not check Todoist integration: {e}")
        
        return 0.0
    
    async def _get_todoist_service(self, user_id: int) -> TodoistService | None:
        """Get a Todoist service for the user.
        
        Args:
            user_id: Telegram user ID.
            
        Returns:
            TodoistService instance or None if not configured.
        """
        try:
            repo = self._get_integration_repo()
            integration = await repo.get_by_user_and_type(user_id, "todoist")
            
            if not integration or not integration.is_active:
                return None
            
            # For now, we store the token directly (in production, use encryption)
            token = integration.encrypted_token
            if not token:
                return None
            
            # Update last used timestamp
            await repo.update_last_used(user_id, "todoist")
            
            return TodoistService(api_token=token)
            
        except Exception as e:
            logger.error(f"Failed to get Todoist service for user {user_id}: {e}")
            return None
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the user message and generate a response.
        
        Args:
            message: User message to process.
            context: Dialog context with user info.
            history: Message history for context.
            
        Returns:
            AgentResult containing the response and metadata.
        """
        user_id = context.get("user_id")
        
        # Check if user has Todoist configured
        if not user_id:
            return AgentResult(
                response="❌ Не могу определить пользователя. Пожалуйста, перезапустите бота.",
                agent_type=self.agent_type,
                confidence=1.0,
            )
        
        todoist_service = await self._get_todoist_service(user_id)
        
        if not todoist_service:
            return AgentResult(
                response="🔗 Для работы с Todoist нужно подключить ваш аккаунт.\n\n"
                        "Для этого:\n"
                        "1. Получите API токен на [todoist.com/app/settings/integrations/developer](https://todoist.com/app/settings/integrations/developer)\n"
                        "2. Отправьте токен командой: `/todoist_token ВАШ_ТОКЕН`\n\n"
                        "Токен хранится безопасно и используется только для работы с вашими задачами.",
                agent_type=self.agent_type,
                confidence=1.0,
            )
        
        try:
            # Parse the user intent and execute actions
            result = await self._process_todoist_request(
                message, context, history, todoist_service
            )
            return result
            
        except TodoistError as e:
            logger.error(f"Todoist API error: {e}")
            error_msg = "❌ Произошла ошибка при работе с Todoist."
            
            if "401" in str(e) or "auth" in str(e).lower():
                error_msg += "\n\n🔑 Похоже, токен устарел или недействителен. Попробуйте подключить аккаунт заново."
            elif "429" in str(e) or "rate" in str(e).lower():
                error_msg += "\n\n⏳ Превышен лимит запросов. Попробуйте через минуту."
            
            return AgentResult(
                response=error_msg,
                agent_type=self.agent_type,
                confidence=1.0,
            )
        finally:
            await todoist_service.close()
    
    async def _process_todoist_request(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
        todoist_service: TodoistService,
    ) -> AgentResult:
        """Process a Todoist request and generate response.
        
        Args:
            message: User message.
            context: Dialog context.
            history: Message history.
            todoist_service: Todoist service instance.
            
        Returns:
            AgentResult with the response.
        """
        message_lower = message.lower()
        
        # Determine the action based on message content
        action = await self._determine_action(message_lower)
        
        # Execute the action and get data
        todoist_data = await self._execute_action(action, message, todoist_service)
        
        # Build context for LLM
        messages = self._build_messages(message, todoist_data, history)
        
        # Generate response using LLM
        response = await self.llm_provider.generate(messages)
        
        # Calculate tokens
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + 
                response.usage.get("completion_tokens", 0)
            )
        
        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=1.0,
            metadata={
                "action": action,
                "usage": response.usage,
                "model": response.model,
            },
            tokens_used=tokens_used,
        )
    
    async def _determine_action(self, message_lower: str) -> str:
        """Determine the action from the message.
        
        Args:
            message_lower: Lowercase message.
            
        Returns:
            Action string.
        """
        # Check for specific actions
        if any(kw in message_lower for kw in ["сегодня", "today"]):
            return "today_tasks"
        
        if any(kw in message_lower for kw in ["просрочен", "overdue"]):
            return "overdue_tasks"
        
        if any(kw in message_lower for kw in ["все задачи", "all tasks", "список задач", "список дел"]):
            return "all_tasks"
        
        if any(kw in message_lower for kw in ["проект", "project"]):
            if "покажи" in message_lower or "список" in message_lower or "show" in message_lower:
                return "list_projects"
            return "projects"
        
        if any(kw in message_lower for kw in ["создай", "добавь", "add", "create", "новая задача", "new task"]):
            return "create_task"
        
        if any(kw in message_lower for kw in ["заверш", "выполн", "complet", "done", "готов"]):
            return "complete_task"
        
        if any(kw in message_lower for kw in ["удали", "delete", "remove"]):
            return "delete_task"
        
        # Default to showing today's tasks
        return "today_tasks"
    
    async def _execute_action(
        self,
        action: str,
        message: str,
        todoist_service: TodoistService,
    ) -> dict[str, Any]:
        """Execute the determined action.
        
        Args:
            action: Action to execute.
            message: Original user message.
            todoist_service: Todoist service.
            
        Returns:
            Data for LLM context.
        """
        data: dict[str, Any] = {"action": action}
        
        try:
            if action == "today_tasks":
                tasks = await todoist_service.get_today_tasks()
                data["tasks"] = [
                    {
                        "id": t.id,
                        "content": t.content,
                        "priority": t.priority,
                        "due": t.due_string or t.due_date,
                        "project_id": t.project_id,
                    }
                    for t in tasks
                ]
                data["summary"] = f"Найдено {len(tasks)} задач на сегодня"
                
            elif action == "overdue_tasks":
                tasks = await todoist_service.get_overdue_tasks()
                data["tasks"] = [
                    {
                        "id": t.id,
                        "content": t.content,
                        "priority": t.priority,
                        "due": t.due_string or t.due_date,
                    }
                    for t in tasks
                ]
                data["summary"] = f"Найдено {len(tasks)} просроченных задач"
                
            elif action == "all_tasks":
                tasks = await todoist_service.get_tasks()
                data["tasks"] = [
                    {
                        "id": t.id,
                        "content": t.content,
                        "priority": t.priority,
                        "due": t.due_string or t.due_date,
                        "project_id": t.project_id,
                        "completed": t.is_completed,
                    }
                    for t in tasks[:50]  # Limit to 50 tasks
                ]
                data["summary"] = f"Всего {len(tasks)} задач"
                
            elif action == "list_projects" or action == "projects":
                projects = await todoist_service.get_projects()
                data["projects"] = [
                    {
                        "id": p.id,
                        "name": p.name,
                        "is_favorite": p.is_favorite,
                        "is_inbox": p.is_inbox_project,
                    }
                    for p in projects
                ]
                data["summary"] = f"Найдено {len(projects)} проектов"
                
            elif action == "create_task":
                # Extract task content from message
                task_content = self._extract_task_content(message)
                
                # Try quick add for natural language parsing
                task = await todoist_service.quick_add_task(task_content)
                data["created_task"] = {
                    "id": task.id,
                    "content": task.content,
                    "priority": task.priority,
                    "due": task.due_string or task.due_date,
                    "project_id": task.project_id,
                }
                data["summary"] = f"Задача создана: {task.content}"
                
            elif action == "complete_task":
                # For now, we need the user to specify the task
                # In a real implementation, we'd have a task selection flow
                data["needs_task_selection"] = True
                data["summary"] = "Укажите номер или название задачи для завершения"
                
            elif action == "delete_task":
                data["needs_task_selection"] = True
                data["summary"] = "Укажите номер или название задачи для удаления"
                
        except TodoistError as e:
            data["error"] = str(e)
            logger.error(f"Todoist action error: {e}")
        
        return data
    
    def _extract_task_content(self, message: str) -> str:
        """Extract task content from user message.
        
        Args:
            message: User message.
            
        Returns:
            Extracted task content.
        """
        # Remove common command prefixes
        prefixes = [
            "создай задачу", "добавь задачу", "новая задача",
            "add task", "create task", "new task",
            "создай", "добавь", "add", "create",
        ]
        
        content = message.lower()
        for prefix in prefixes:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
                break
        
        # Capitalize first letter
        if content:
            content = content[0].upper() + content[1:]
        
        return content or message
    
    def _build_messages(
        self,
        message: str,
        todoist_data: dict[str, Any],
        history: list[LLMMessage],
    ) -> list[LLMMessage]:
        """Build messages for LLM request.
        
        Args:
            message: User message.
            todoist_data: Data from Todoist API.
            history: Message history.
            
        Returns:
            List of messages for LLM.
        """
        messages = [LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt)]
        
        # Add Todoist data as context
        context_parts = []
        
        if "error" in todoist_data:
            context_parts.append(f"Ошибка: {todoist_data['error']}")
        elif "summary" in todoist_data:
            context_parts.append(f"Результат: {todoist_data['summary']}")
        
        if "tasks" in todoist_data:
            tasks_str = self._format_tasks_for_context(todoist_data["tasks"])
            context_parts.append(f"Задачи:\n{tasks_str}")
        
        if "projects" in todoist_data:
            projects_str = self._format_projects_for_context(todoist_data["projects"])
            context_parts.append(f"Проекты:\n{projects_str}")
        
        if "created_task" in todoist_data:
            task = todoist_data["created_task"]
            context_parts.append(
                f"Создана задача: {task['content']}\n"
                f"Приоритет: {task['priority']}\n"
                f"Срок: {task.get('due', 'не указан')}"
            )
        
        if "needs_task_selection" in todoist_data:
            context_parts.append(
                "Требуется уточнение: пользователь должен указать конкретную задачу. "
                "Попроси его указать номер или название задачи."
            )
        
        if context_parts:
            context_content = "\n\n".join(context_parts)
            messages.append(LLMMessage(
                role=MessageRole.SYSTEM,
                content=f"Данные из Todoist:\n{context_content}"
            ))
        
        # Add conversation history (last few messages)
        messages.extend(history[-5:])
        
        # Add user message
        messages.append(LLMMessage(role=MessageRole.USER, content=message))
        
        return messages
    
    def _format_tasks_for_context(self, tasks: list[dict[str, Any]]) -> str:
        """Format tasks for LLM context.
        
        Args:
            tasks: List of task dictionaries.
            
        Returns:
            Formatted string.
        """
        if not tasks:
            return "Нет задач"
        
        lines = []
        for i, task in enumerate(tasks, 1):
            priority_icons = {4: "🔴", 3: "🟠", 2: "🟡", 1: "⚪"}
            icon = priority_icons.get(task.get("priority", 1), "⚪")
            status = "✅" if task.get("completed") else "⬜"
            due = f" 📅 {task.get('due')}" if task.get("due") else ""
            lines.append(f"{i}. {status} {icon} {task['content']}{due}")
        
        return "\n".join(lines)
    
    def _format_projects_for_context(self, projects: list[dict[str, Any]]) -> str:
        """Format projects for LLM context.
        
        Args:
            projects: List of project dictionaries.
            
        Returns:
            Formatted string.
        """
        if not projects:
            return "Нет проектов"
        
        lines = []
        for proj in projects:
            icon = "⭐" if proj.get("is_favorite") else "📁"
            inbox = " (Inbox)" if proj.get("is_inbox") else ""
            lines.append(f"{icon} {proj['name']}{inbox}")
        
        return "\n".join(lines)
