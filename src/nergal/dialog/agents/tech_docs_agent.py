"""Technical documentation agent for searching library/framework docs.

This agent searches official documentation for programming languages,
frameworks, and libraries to provide accurate technical information.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class TechDocsAgent(BaseAgent):
    """Agent for searching technical documentation.
    
    This agent searches official documentation for programming
    languages, frameworks, and libraries.
    
    Use cases:
    - Find API documentation
    - Get code examples from official docs
    - Check latest version features
    - Find best practices from official sources
    """
    
    # Tech-related keywords
    TECH_KEYWORDS = [
        "api", "sdk", "библиотека", "фреймворк", "метод", "функция",
        "класс", "интерфейс", "документация", "пример", "syntax",
        "как использовать", "how to", "tutorial", "гайд",
        "python", "javascript", "typescript", "go", "rust", "java",
        "react", "vue", "angular", "node", "django", "fastapi",
        "kubernetes", "docker", "aws", "azure", "gcp",
    ]
    
    # Known documentation sources
    DOC_SOURCES = {
        "python": "https://docs.python.org/3/",
        "javascript": "https://developer.mozilla.org/",
        "typescript": "https://www.typescriptlang.org/docs/",
        "react": "https://react.dev/",
        "vue": "https://vuejs.org/guide/",
        "django": "https://docs.djangoproject.com/",
        "fastapi": "https://fastapi.tiangolo.com/",
        "kubernetes": "https://kubernetes.io/docs/",
        "docker": "https://docs.docker.com/",
        "go": "https://go.dev/doc/",
        "rust": "https://doc.rust-lang.org/",
    }
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        doc_connectors: dict[str, Any] | None = None,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the tech docs agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            doc_connectors: Optional connectors for doc sources.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)
        self._doc_connectors = doc_connectors or {}
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.TECH_DOCS
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент технической документации. Твоя задача — помочь
с вопросами по программированию, используя официальную документацию.

Ты можешь:
- Объяснять API и методы
- Приводить примеры кода из документации
- Разъяснять концепции и паттерны
- Указывать на best practices

При ответе:
1. Давай точные и актуальные сведения
2. Приводи примеры кода
3. Указывай источник информации
4. Предупреждай о deprecated функциях
5. Предлагай альтернативы если есть

Формат ответа:
## Краткий ответ
[Суть ответа в 1-2 предложениях]

## Подробности
[Детальное объяснение с примерами]

## Пример кода
```язык
// пример
```

## Ссылки
- [Название](URL) - описание"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for technical questions about
        programming languages, frameworks, and libraries.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for tech keywords
        keyword_matches = sum(
            1 for kw in self.TECH_KEYWORDS
            if kw in message_lower
        )
        
        if keyword_matches >= 2:
            return 0.85
        elif keyword_matches == 1:
            return 0.7
        
        # Check for code-related patterns
        code_patterns = ["()", "=>", "{}", "[]", "::", "->", "def ", "func ", "fn "]
        if any(pattern in message for pattern in code_patterns):
            return 0.75
        
        # Questions about usage
        usage_patterns = ["как использовать", "как вызвать", "как работает"]
        if any(pattern in message_lower for pattern in usage_patterns):
            return 0.6
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by searching tech documentation.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with documentation information.
        """
        # Detect technology from message
        technology = self._detect_technology(message)
        
        # Search documentation
        doc_results = await self._search_docs(message, technology, context)
        
        # Generate response
        tokens_used = None
        if doc_results:
            response, tokens_used = await self._generate_doc_response(
                message, doc_results, technology
            )
            confidence = 0.9
        else:
            response, tokens_used = await self._generate_general_response(message, technology)
            confidence = 0.6
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=confidence,
            metadata={
                "technology": technology,
                "docs_found": len(doc_results) if doc_results else 0,
                "sources": [r.get("source") for r in doc_results] if doc_results else [],
            },
            tokens_used=tokens_used,
        )
    
    def _detect_technology(self, message: str) -> str | None:
        """Detect which technology the question is about.
        
        Args:
            message: User message.
            
        Returns:
            Detected technology or None.
        """
        message_lower = message.lower()
        
        for tech in self.DOC_SOURCES:
            if tech in message_lower:
                return tech
        
        return None
    
    async def _search_docs(
        self,
        query: str,
        technology: str | None,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search documentation sources.
        
        Args:
            query: Search query.
            technology: Detected technology.
            context: Dialog context.
            
        Returns:
            List of documentation results.
        """
        results = []
        
        # Use configured connectors
        if technology and technology in self._doc_connectors:
            connector = self._doc_connectors[technology]
            try:
                if hasattr(connector, "search"):
                    connector_results = await connector.search(query, limit=3)
                    results.extend(connector_results)
            except Exception as e:
                logger.warning(f"Doc connector failed for {technology}: {e}")
        
        # Fall back to web search if available
        web_search_result = context.get("agent_results", {}).get("web_search")
        if web_search_result and not results:
            # Extract relevant info from web search
            if isinstance(web_search_result, dict):
                content = web_search_result.get("response", "")
            else:
                content = getattr(web_search_result, "response", "")
            
            if content:
                results.append({
                    "source": "web_search",
                    "content": content,
                    "relevance": 0.7,
                })
        
        return results
    
    async def _generate_doc_response(
        self,
        message: str,
        doc_results: list[dict[str, Any]],
        technology: str | None,
    ) -> tuple[str, int | None]:
        """Generate response based on documentation results.
        
        Args:
            message: Original message.
            doc_results: Documentation search results.
            technology: Detected technology.
            
        Returns:
            Tuple of (generated response, tokens used or None).
        """
        # Combine documentation content
        docs_content = "\n\n".join([
            f"[{r.get('source', 'Unknown')}]\n{r.get('content', '')}"
            for r in doc_results[:3]
        ])
        
        prompt = f"""На основе найденной документации ответь на вопрос.

Вопрос: {message}

Технология: {technology or "не определена"}

Документация:
{docs_content[:3000]}

Дай структурированный ответ с примерами кода."""
        
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
        technology: str | None,
    ) -> tuple[str, int | None]:
        """Generate general response when no docs found.
        
        Args:
            message: Original message.
            technology: Detected technology.
            
        Returns:
            Tuple of (generated response, tokens used or None).
        """
        tech_hint = f" для {technology}" if technology else ""
        
        prompt = f"""Ответь на технический вопрос{tech_hint}, используя свои знания.

Вопрос: {message}

Если не уверен — честно скажи об этом и предложи поискать в официальной документации."""
        
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
    
    def add_doc_connector(self, technology: str, connector: Any) -> None:
        """Add a documentation connector for a technology.
        
        Args:
            technology: Technology name.
            connector: Connector with search method.
        """
        self._doc_connectors[technology] = connector
    
    def get_doc_source_url(self, technology: str) -> str | None:
        """Get official documentation URL for a technology.
        
        Args:
            technology: Technology name.
            
        Returns:
            Documentation URL or None.
        """
        return self.DOC_SOURCES.get(technology.lower())


# Import MessageRole for type hints
from nergal.llm import MessageRole
