"""Knowledge base agent for searching corporate documentation.

This agent searches internal knowledge bases, documentation systems,
and corporate wikis to find relevant information for user queries.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage

logger = logging.getLogger(__name__)


class KnowledgeBaseAgent(BaseAgent):
    """Agent for searching corporate knowledge base.
    
    This agent searches internal documentation systems like Confluence,
    Notion, or custom knowledge bases to find relevant information.
    
    Attributes:
        knowledge_sources: List of configured knowledge sources.
    """
    
    # Keywords that indicate internal/company context
    INTERNAL_KEYWORDS = [
        "у нас", "наша компания", "наш процесс", "наш стандарт",
        "как мы", "по нашим", "в компании", "наш проект",
        "наша архитектура", "наша команда", "наш регламент",
        "наши правила", "наша политика", "наш гайдлайн",
    ]
    
    PROCESS_KEYWORDS = [
        "процесс", "регламент", "стандарт", "политика",
        "правило", "процедура", "инструкция", "гайдлайн",
        "требование", "норма", "порядок",
    ]
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        knowledge_sources: list[Any] | None = None,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the knowledge base agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            knowledge_sources: List of knowledge source connectors.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)
        self._knowledge_sources = knowledge_sources or []
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.KNOWLEDGE_BASE
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент поиска по корпоративной базе знаний.

Твоя задача — найти релевантную информацию во внутренних документах компании
и предоставить её в удобном формате.

Правила:
- Используй только предоставленный контекст из базы знаний
- Если информация не найдена — честно скажи об этом
- Указывай источники информации
- Структурируй ответ с использованием заголовков и списков
- Если информация устарела или неполная — предупреди об этом"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for messages about internal processes,
        company standards, or corporate knowledge.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # High confidence for internal context keywords
        for keyword in self.INTERNAL_KEYWORDS:
            if keyword in message_lower:
                return 0.85
        
        # Medium-high confidence for process-related questions
        for keyword in self.PROCESS_KEYWORDS:
            if keyword in message_lower:
                return 0.7
        
        # Check if knowledge sources are available
        if self._knowledge_sources:
            return 0.3
        
        return 0.1
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by searching knowledge base.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with found information or not found message.
        """
        # Search knowledge sources
        search_results = await self._search_knowledge_base(message, context)
        
        if not search_results:
            return AgentResult(
                response="В корпоративной базе знаний не найдено релевантной информации по вашему запросу.",
                agent_type=self.agent_type,
                confidence=0.3,
                metadata={"found": False, "sources": []},
                tokens_used=None,
            )
        
        # Format context for LLM
        context_text = self._format_search_results(search_results)
        
        # Generate response using found context
        enhanced_message = f"""Найденная информация из базы знаний:

{context_text}

Вопрос пользователя: {message}

На основе найденной информации ответь на вопрос. Укажи источники."""
        
        response = await self.generate_response(enhanced_message, history)
        
        # Calculate tokens from response
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        
        return AgentResult(
            response=response.content,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "found": True,
                "sources": [r.get("source", "unknown") for r in search_results],
                "result_count": len(search_results),
            },
            tokens_used=tokens_used,
        )
    
    async def _search_knowledge_base(
        self,
        query: str,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search all configured knowledge sources.
        
        Args:
            query: Search query.
            context: Current context with optional filters.
            
        Returns:
            List of search results with content and metadata.
        """
        results = []
        
        for source in self._knowledge_sources:
            try:
                if hasattr(source, "search"):
                    source_results = await source.search(
                        query=query,
                        limit=context.get("search_limit", 5),
                        filters=context.get("doc_filter"),
                    )
                    results.extend(source_results)
            except Exception as e:
                logger.warning(f"Knowledge source search failed: {e}")
                continue
        
        # Sort by relevance if available
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:10]  # Limit to top 10 results
    
    def _format_search_results(self, results: list[dict[str, Any]]) -> str:
        """Format search results for LLM context.
        
        Args:
            results: List of search results.
            
        Returns:
            Formatted text for LLM.
        """
        formatted = []
        for i, result in enumerate(results, 1):
            source = result.get("source", "Неизвестный источник")
            title = result.get("title", "")
            content = result.get("content", "")
            
            if title:
                formatted.append(f"[{i}] {title} (источник: {source})\n{content}")
            else:
                formatted.append(f"[{i}] (источник: {source})\n{content}")
        
        return "\n\n---\n\n".join(formatted)
    
    def add_knowledge_source(self, source: Any) -> None:
        """Add a knowledge source to the agent.
        
        Args:
            source: Knowledge source connector with search method.
        """
        self._knowledge_sources.append(source)
