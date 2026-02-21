"""Todoist API integration service.

This module provides a service for interacting with the Todoist API,
allowing users to manage their tasks, projects, and labels.

Each user has their own API token stored securely in the database.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TodoistPriority(int, Enum):
    """Todoist task priority levels."""
    
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TodoistTask:
    """Represents a Todoist task."""
    
    id: str
    content: str
    project_id: str | None = None
    section_id: str | None = None
    parent_id: str | None = None
    priority: int = 1
    due_string: str | None = None
    due_date: str | None = None
    is_completed: bool = False
    labels: list[str] | None = None
    order: int | None = None
    url: str | None = None
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TodoistTask":
        """Create a TodoistTask from API response data."""
        due = data.get("due", {}) or {}
        return cls(
            id=data["id"],
            content=data["content"],
            project_id=data.get("projectId") or data.get("project_id"),
            section_id=data.get("sectionId") or data.get("section_id"),
            parent_id=data.get("parentId") or data.get("parent_id"),
            priority=data.get("priority", 1),
            due_string=due.get("string"),
            due_date=due.get("date"),
            is_completed=data.get("isCompleted", False),
            labels=data.get("labels"),
            order=data.get("order"),
            url=data.get("url"),
        )


@dataclass
class TodoistProject:
    """Represents a Todoist project."""
    
    id: str
    name: str
    color: str | None = None
    is_favorite: bool = False
    is_inbox_project: bool = False
    parent_id: str | None = None
    order: int | None = None
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TodoistProject":
        """Create a TodoistProject from API response data."""
        return cls(
            id=data["id"],
            name=data["name"],
            color=data.get("color"),
            is_favorite=data.get("isFavorite", False),
            is_inbox_project=data.get("isInboxProject", False),
            parent_id=data.get("parentId") or data.get("parent_id"),
            order=data.get("order"),
        )


@dataclass
class TodoistLabel:
    """Represents a Todoist label."""
    
    id: str
    name: str
    color: str | None = None
    order: int | None = None
    
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "TodoistLabel":
        """Create a TodoistLabel from API response data."""
        return cls(
            id=data["id"],
            name=data["name"],
            color=data.get("color"),
            order=data.get("order"),
        )


class TodoistError(Exception):
    """Base exception for Todoist API errors."""
    
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TodoistAuthError(TodoistError):
    """Authentication error with Todoist API."""
    pass


class TodoistRateLimitError(TodoistError):
    """Rate limit exceeded error."""
    pass


class TodoistService:
    """Service for interacting with the Todoist API.
    
    This service provides methods for managing tasks, projects, and labels
    in Todoist. Each user must have their own API token.
    
    Attributes:
        base_url: Base URL for the Todoist API.
        timeout: Request timeout in seconds.
    """
    
    BASE_URL = "https://api.todoist.com/api/v1"
    SYNC_URL = "https://api.todoist.com/sync/v9"
    TIMEOUT = 30.0
    
    def __init__(self, api_token: str, timeout: float | None = None):
        """Initialize the Todoist service.
        
        Args:
            api_token: User's Todoist API token.
            timeout: Request timeout in seconds.
        """
        self._api_token = api_token
        self._timeout = timeout or self.TIMEOUT
        self._client: httpx.AsyncClient | None = None
    
    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self._api_token}",
            "Content-Type": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._get_headers(),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request.
        
        Args:
            method: HTTP method.
            endpoint: API endpoint.
            base_url: Override base URL (for sync API).
            **kwargs: Additional request parameters.
            
        Returns:
            API response data.
            
        Raises:
            TodoistAuthError: If authentication fails.
            TodoistRateLimitError: If rate limit is exceeded.
            TodoistError: For other API errors.
        """
        client = await self._get_client()
        url = f"{base_url or self.BASE_URL}{endpoint}"
        
        try:
            response = await client.request(method, url, **kwargs)
            
            if response.status_code == 401:
                raise TodoistAuthError(
                    "Invalid API token. Please check your Todoist API token.",
                    status_code=401,
                )
            
            if response.status_code == 429:
                raise TodoistRateLimitError(
                    "Rate limit exceeded. Please try again later.",
                    status_code=429,
                )
            
            response.raise_for_status()
            
            # Handle empty responses
            if not response.content:
                return {}
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Todoist API error: {e.response.status_code} - {e.response.text}")
            raise TodoistError(
                f"API request failed: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Todoist request error: {e}")
            raise TodoistError(f"Request failed: {str(e)}") from e
    
    # =========================================================================
    # Task Operations
    # =========================================================================
    
    async def get_tasks(
        self,
        project_id: str | None = None,
        section_id: str | None = None,
        label: str | None = None,
        filter_expr: str | None = None,
        lang: str | None = None,
        ids: list[str] | None = None,
    ) -> list[TodoistTask]:
        """Get tasks from Todoist.
        
        Args:
            project_id: Filter by project ID.
            section_id: Filter by section ID.
            label: Filter by label name.
            filter_expr: Todoist filter expression (e.g., "today", "overdue").
            lang: Language for filter expression.
            ids: List of task IDs to fetch.
            
        Returns:
            List of tasks.
        """
        params: dict[str, Any] = {}
        
        if project_id:
            params["projectId"] = project_id
        if section_id:
            params["sectionId"] = section_id
        if label:
            params["label"] = label
        if filter_expr:
            params["filter"] = filter_expr
        if lang:
            params["lang"] = lang
        if ids:
            params["ids"] = ",".join(ids)
        
        data = await self._request("GET", "/tasks", params=params)
        return [TodoistTask.from_api(task) for task in data.get("results", data) if isinstance(task, dict)]
    
    async def get_task(self, task_id: str) -> TodoistTask | None:
        """Get a single task by ID.
        
        Args:
            task_id: Task ID.
            
        Returns:
            Task or None if not found.
        """
        try:
            data = await self._request("GET", f"/tasks/{task_id}")
            return TodoistTask.from_api(data)
        except TodoistError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def create_task(
        self,
        content: str,
        project_id: str | None = None,
        section_id: str | None = None,
        parent_id: str | None = None,
        priority: int | None = None,
        due_string: str | None = None,
        due_date: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> TodoistTask:
        """Create a new task.
        
        Args:
            content: Task content/title.
            project_id: Project ID to add task to.
            section_id: Section ID within project.
            parent_id: Parent task ID for subtasks.
            priority: Task priority (1-4).
            due_string: Natural language due date (e.g., "tomorrow", "next monday").
            due_date: Specific due date (YYYY-MM-DD or ISO format).
            labels: List of label names.
            description: Task description.
            
        Returns:
            Created task.
        """
        payload: dict[str, Any] = {"content": content}
        
        if project_id:
            payload["projectId"] = project_id
        if section_id:
            payload["sectionId"] = section_id
        if parent_id:
            payload["parentId"] = parent_id
        if priority is not None:
            payload["priority"] = priority
        if due_string:
            payload["dueString"] = due_string
        if due_date:
            payload["dueDate"] = due_date
        if labels:
            payload["labels"] = labels
        if description:
            payload["description"] = description
        
        data = await self._request("POST", "/tasks", json=payload)
        return TodoistTask.from_api(data)
    
    async def update_task(
        self,
        task_id: str,
        content: str | None = None,
        project_id: str | None = None,
        priority: int | None = None,
        due_string: str | None = None,
        due_date: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> TodoistTask:
        """Update an existing task.
        
        Args:
            task_id: Task ID to update.
            content: New task content.
            project_id: Move to different project.
            priority: New priority.
            due_string: New due date in natural language.
            due_date: New due date in specific format.
            labels: New labels.
            description: New description.
            
        Returns:
            Updated task.
        """
        payload: dict[str, Any] = {}
        
        if content is not None:
            payload["content"] = content
        if project_id is not None:
            payload["projectId"] = project_id
        if priority is not None:
            payload["priority"] = priority
        if due_string is not None:
            payload["dueString"] = due_string
        if due_date is not None:
            payload["dueDate"] = due_date
        if labels is not None:
            payload["labels"] = labels
        if description is not None:
            payload["description"] = description
        
        data = await self._request("POST", f"/tasks/{task_id}", json=payload)
        return TodoistTask.from_api(data)
    
    async def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed.
        
        Args:
            task_id: Task ID to complete.
            
        Returns:
            True if successful.
        """
        await self._request("POST", f"/tasks/{task_id}/close")
        return True
    
    async def reopen_task(self, task_id: str) -> bool:
        """Reopen a completed task.
        
        Args:
            task_id: Task ID to reopen.
            
        Returns:
            True if successful.
        """
        await self._request("POST", f"/tasks/{task_id}/reopen")
        return True
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task.
        
        Args:
            task_id: Task ID to delete.
            
        Returns:
            True if successful.
        """
        await self._request("DELETE", f"/tasks/{task_id}")
        return True
    
    # =========================================================================
    # Project Operations
    # =========================================================================
    
    async def get_projects(self) -> list[TodoistProject]:
        """Get all projects.
        
        Returns:
            List of projects.
        """
        data = await self._request("GET", "/projects")
        return [TodoistProject.from_api(proj) for proj in data.get("results", data) if isinstance(proj, dict)]
    
    async def get_project(self, project_id: str) -> TodoistProject | None:
        """Get a single project by ID.
        
        Args:
            project_id: Project ID.
            
        Returns:
            Project or None if not found.
        """
        try:
            data = await self._request("GET", f"/projects/{project_id}")
            return TodoistProject.from_api(data)
        except TodoistError as e:
            if e.status_code == 404:
                return None
            raise
    
    async def create_project(
        self,
        name: str,
        parent_id: str | None = None,
        color: str | None = None,
        is_favorite: bool = False,
    ) -> TodoistProject:
        """Create a new project.
        
        Args:
            name: Project name.
            parent_id: Parent project ID for sub-projects.
            color: Project color.
            is_favorite: Mark as favorite.
            
        Returns:
            Created project.
        """
        payload: dict[str, Any] = {"name": name}
        
        if parent_id:
            payload["parentId"] = parent_id
        if color:
            payload["color"] = color
        if is_favorite:
            payload["isFavorite"] = True
        
        data = await self._request("POST", "/projects", json=payload)
        return TodoistProject.from_api(data)
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project.
        
        Args:
            project_id: Project ID to delete.
            
        Returns:
            True if successful.
        """
        await self._request("DELETE", f"/projects/{project_id}")
        return True
    
    # =========================================================================
    # Label Operations
    # =========================================================================
    
    async def get_labels(self) -> list[TodoistLabel]:
        """Get all labels.
        
        Returns:
            List of labels.
        """
        data = await self._request("GET", "/labels")
        return [TodoistLabel.from_api(label) for label in data.get("results", data) if isinstance(label, dict)]
    
    async def create_label(
        self,
        name: str,
        color: str | None = None,
    ) -> TodoistLabel:
        """Create a new label.
        
        Args:
            name: Label name.
            color: Label color.
            
        Returns:
            Created label.
        """
        payload: dict[str, Any] = {"name": name}
        
        if color:
            payload["color"] = color
        
        data = await self._request("POST", "/labels", json=payload)
        return TodoistLabel.from_api(data)
    
    # =========================================================================
    # Quick Add (Natural Language)
    # =========================================================================
    
    async def quick_add_task(self, text: str) -> TodoistTask:
        """Add a task using natural language parsing.
        
        This uses Todoist's natural language processing to parse the task
        content and extract due dates, projects, labels, and priority.
        
        Args:
            text: Task text with natural language elements.
                  Example: "Buy milk tomorrow #Shopping @groceries p2"
            
        Returns:
            Created task.
        """
        payload = {"text": text}
        data = await self._request("POST", "/tasks/quick", json=payload)
        return TodoistTask.from_api(data)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    async def test_connection(self) -> bool:
        """Test the API connection and token validity.
        
        Returns:
            True if connection is successful.
        """
        try:
            await self.get_projects()
            return True
        except TodoistAuthError:
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def get_today_tasks(self) -> list[TodoistTask]:
        """Get all tasks due today.
        
        Returns:
            List of tasks due today.
        """
        return await self.get_tasks(filter_expr="today")
    
    async def get_overdue_tasks(self) -> list[TodoistTask]:
        """Get all overdue tasks.
        
        Returns:
            List of overdue tasks.
        """
        return await self.get_tasks(filter_expr="overdue")
    
    async def get_upcoming_tasks(self, days: int = 7) -> list[TodoistTask]:
        """Get tasks due in the next N days.
        
        Args:
            days: Number of days to look ahead.
            
        Returns:
            List of upcoming tasks.
        """
        return await self.get_tasks(filter_expr=f"{days} days")
    
    def format_task_list(self, tasks: list[TodoistTask], include_project: bool = True) -> str:
        """Format a list of tasks for display.
        
        Args:
            tasks: List of tasks to format.
            include_project: Whether to include project name.
            
        Returns:
            Formatted string.
        """
        if not tasks:
            return "Нет задач для отображения."
        
        lines = []
        for i, task in enumerate(tasks, 1):
            # Priority indicators
            priority_icons = {4: "🔴", 3: "🟠", 2: "🟡", 1: "⚪"}
            priority_icon = priority_icons.get(task.priority, "⚪")
            
            # Due date
            due_info = ""
            if task.due_string:
                due_info = f" 📅 {task.due_string}"
            elif task.due_date:
                due_info = f" 📅 {task.due_date}"
            
            # Completion status
            status = "✅" if task.is_completed else "⬜"
            
            line = f"{i}. {status} {priority_icon} {task.content}{due_info}"
            lines.append(line)
        
        return "\n".join(lines)
