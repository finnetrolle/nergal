"""Code analysis agent for answering questions about codebase.

This agent searches code repositories, explains code, and provides
insights about code architecture and patterns.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class CodeAnalysisAgent(BaseAgent):
    """Agent for analyzing and explaining code.
    
    This agent searches code repositories, explains code snippets,
    and provides insights about architecture and patterns.
    
    Use cases:
    - Explain how code works
    - Find usage examples in codebase
    - Analyze architecture patterns
    - Review code structure
    """
    
    # Code-related keywords
    CODE_KEYWORDS = [
        "код", "функция", "метод", "класс", "модуль", "файл",
        "реализация", "где используется", "где определен",
        "как работает", "объясни код", "что делает",
        "import", "def ", "func ", "class ", "fn ",
        "репозиторий", "github", "gitlab",
    ]
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        code_connectors: dict[str, Any] | None = None,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the code analysis agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            code_connectors: Connectors for code repositories.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)
        self._code_connectors = code_connectors or {}
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.CODE_ANALYSIS
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент анализа кода. Твоя задача — помогать с вопросами
по кодовой базе проекта.

Ты можешь:
- Объяснять работу кода
- Находить использования функций и классов
- Анализировать архитектуру
- Предлагать улучшения

При ответе:
1. Приводи примеры кода
2. Объясняй логику работы
3. Указывай файлы и строки
4. Предлагай лучшие практики

Формат ответа:
## Краткое объяснение
[Суть в 1-2 предложениях]

## Детали
[Подробное объяснение]

## Пример кода
```язык
// пример
```

## Связанные файлы
- `path/to/file.py` — описание"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for code-related questions.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for code keywords
        keyword_matches = sum(
            1 for kw in self.CODE_KEYWORDS
            if kw in message_lower
        )
        
        if keyword_matches >= 2:
            return 0.85
        elif keyword_matches == 1:
            return 0.7
        
        # Check for code patterns in message
        code_patterns = ["()", "=>", "{}", "::", "->", "self.", "this."]
        if any(pattern in message for pattern in code_patterns):
            return 0.75
        
        # Questions about implementation
        impl_patterns = ["как реализован", "где находится", "где определен"]
        if any(pattern in message_lower for pattern in impl_patterns):
            return 0.7
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by analyzing code.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with code analysis.
        """
        # Determine query type
        query_type = self._determine_query_type(message)
        
        # Search code if connectors available
        code_results = await self._search_code(message, context)
        
        # Generate response
        tokens_used = None
        if code_results:
            response, tokens_used = await self._generate_code_response(
                message, code_results, query_type
            )
            confidence = 0.9
        else:
            response, tokens_used = await self._generate_general_response(message, query_type)
            confidence = 0.6
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=confidence,
            metadata={
                "query_type": query_type,
                "files_found": len(code_results) if code_results else 0,
                "files": [r.get("file") for r in code_results] if code_results else [],
            },
            tokens_used=tokens_used,
        )
    
    def _determine_query_type(self, message: str) -> str:
        """Determine the type of code query.
        
        Args:
            message: User message.
            
        Returns:
            Query type identifier.
        """
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["где используется", "найди использование", "usage"]):
            return "usage_search"
        elif any(kw in message_lower for kw in ["где определен", "найди определение", "definition"]):
            return "definition_search"
        elif any(kw in message_lower for kw in ["как работает", "объясни", "что делает"]):
            return "explanation"
        elif any(kw in message_lower for kw in ["архитектура", "структура", "как устроен"]):
            return "architecture"
        else:
            return "general"
    
    async def _search_code(
        self,
        query: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search code repositories.
        
        Args:
            query: Search query.
            context: Dialog context.
            
        Returns:
            List of code search results.
        """
        results = []
        
        for name, connector in self._code_connectors.items():
            try:
                if hasattr(connector, "search"):
                    connector_results = await connector.search(query, limit=5)
                    results.extend(connector_results)
                elif hasattr(connector, "search_code"):
                    connector_results = await connector.search_code(query, limit=5)
                    results.extend(connector_results)
            except Exception as e:
                logger.warning(f"Code connector {name} failed: {e}")
        
        return results
    
    async def _generate_code_response(
        self,
        message: str,
        code_results: list[dict[str, Any]],
        query_type: str,
    ) -> tuple[str, int | None]:
        """Generate response based on code search results.
        
        Args:
            message: Original message.
            code_results: Code search results.
            query_type: Type of query.
            
        Returns:
            Tuple of (generated response, tokens used or None).
        """
        # Format code results
        code_context = "\n\n".join([
            f"Файл: {r.get('file', 'unknown')}\n"
            f"Строка: {r.get('line', '?')}\n"
            f"```\n{r.get('code', r.get('content', ''))}\n```"
            for r in code_results[:5]
        ])
        
        prompt = f"""На основе найденного кода ответь на вопрос.

Вопрос: {message}

Найденный код:
{code_context[:3000]}

Дай структурированный ответ с объяснением."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1200)
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used
    
    async def _generate_general_response(
        self,
        message: str,
        query_type: str,
    ) -> tuple[str, int | None]:
        """Generate general response when no code found.
        
        Args:
            message: Original message.
            query_type: Type of query.
            
        Returns:
            Tuple of (generated response, tokens used or None).
        """
        prompt = f"""Ответь на вопрос по коду, используя свои знания.

Вопрос: {message}

Если нужен доступ к конкретному коду — сообщи об этом."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1000)
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used
    
    def add_code_connector(self, name: str, connector: Any) -> None:
        """Add a code repository connector.
        
        Args:
            name: Connector name.
            connector: Connector with search method.
        """
        self._code_connectors[name] = connector
    
    async def find_usages(self, symbol: str) -> list[dict[str, Any]]:
        """Find all usages of a symbol in codebase.
        
        Args:
            symbol: Symbol to search for.
            
        Returns:
            List of usage locations.
        """
        results = await self._search_code(symbol, {})
        return [
            {
                "file": r.get("file"),
                "line": r.get("line"),
                "context": r.get("code", "")[:200],
            }
            for r in results
        ]
    
    async def explain_code(self, code: str, language: str = "python") -> str:
        """Explain a code snippet.
        
        Args:
            code: Code to explain.
            language: Programming language.
            
        Returns:
            Explanation text.
        """
        prompt = f"""Объясни следующий код на {language}:

```{language}
{code}
```

Дай подробное объяснение того, что делает этот код."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1000)
        return response.content
    
    async def analyze_architecture(
        self,
        module_or_path: str,
        context: dict[str, Any],
    ) -> str:
        """Analyze architecture of a module or path.
        
        Args:
            module_or_path: Module or path to analyze.
            context: Dialog context.
            
        Returns:
            Architecture analysis.
        """
        # Search for files in the module
        results = await self._search_code(module_or_path, context)
        
        if not results:
            return f"Не найден код для анализа: {module_or_path}"
        
        # Format results for analysis
        files_summary = "\n".join([
            f"- {r.get('file')}: {r.get('code', '')[:100]}..."
            for r in results[:10]
        ])
        
        prompt = f"""Проанализируй архитектуру модуля: {module_or_path}

Найденные файлы:
{files_summary}

Опиши:
1. Назначение модуля
2. Основные компоненты
3. Зависимости
4. Паттерны проектирования"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1500)
        return response.content
