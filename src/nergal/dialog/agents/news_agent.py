"""News aggregation and processing agent.

This agent aggregates news from multiple sources, compares information,
tracks source links, and identifies consensus and discrepancies.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from nergal.dialog.agents.base_specialized import BaseSpecializedAgent
from nergal.dialog.constants import NEWS_KEYWORDS, CREDIBLE_SOURCES, SOURCE_BIAS
from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


@dataclass
class NewsSource:
    """Represents a news source with metadata.
    
    Attributes:
        title: Title of the article/news item.
        url: Source URL.
        snippet: Brief excerpt from the source.
        source_name: Name of the publisher/source.
        published_date: When the news was published (if available).
        credibility_score: Estimated credibility of the source (0.0-1.0).
    """
    title: str
    url: str
    snippet: str
    source_name: str = "Unknown"
    published_date: str | None = None
    credibility_score: float = 0.5


@dataclass
class NewsCluster:
    """A cluster of related news items from different sources.
    
    Attributes:
        topic: Main topic/subject of the cluster.
        sources: List of sources covering this topic.
        consensus: Points agreed upon by multiple sources.
        discrepancies: Points where sources disagree.
        summary: Aggregated summary of the news.
    """
    topic: str
    sources: list[NewsSource] = field(default_factory=list)
    consensus: list[str] = field(default_factory=list)
    discrepancies: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""


class NewsAgent(BaseSpecializedAgent):
    """Agent for aggregating and processing news from multiple sources.
    
    This agent specializes in:
    - Aggregating news from multiple sources
    - Comparing coverage across different outlets
    - Identifying consensus and discrepancies
    - Tracking source links and credibility
    - Detecting bias and perspective differences
    
    Use cases:
    - News aggregation and summarization
    - Cross-source verification
    - Media bias analysis
    - Event timeline construction
    """
    
    # Configure base class behavior - use centralized constants
    _keywords = NEWS_KEYWORDS
    _context_keys = ["search_results", "sources"]
    _base_confidence = 0.25
    _keyword_boost = 0.2
    _context_boost = 0.35
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
        min_sources_for_consensus: int = 2,
        credibility_threshold: float = 0.3,
    ) -> None:
        """Initialize the news agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            style_type: Response style to use.
            min_sources_for_consensus: Minimum sources to establish consensus.
            credibility_threshold: Minimum credibility score to include source.
        """
        super().__init__(llm_provider, style_type)
        self._min_sources_for_consensus = min_sources_for_consensus
        self._credibility_threshold = credibility_threshold
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.NEWS
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент агрегации и обработки новостей. Твоя задача — 
анализировать информацию из нескольких источников, сравнивать их и выявлять:
1. Точки согласия (консенсус)
2. Противоречия и расхождения
3. Уровень достоверности информации
4. Потенциальную предвзятость источников

При анализе новостей:
- Сравнивай факты, а не эмоции
- Указывай источники для каждого утверждения
- Отмечай, когда информация не подтверждена
- Выделяй подтверждённые и непроверенные факты

Формат ответа:
## 📰 Агрегация новостей: [Тема]

### 📌 Основное
[Краткое изложение ключевых фактов с указанием источников]

### ✅ Подтверждённые факты
[Факты, которые подтверждаются несколькими источниками]

### ⚠️ Спорные моменты
[Где источники расходятся в информации]

### 📊 Источники
| Источник | Позиция | Достоверность |
|----------|---------|---------------|
| [Название] | [Кратко] | [Высокая/Средняя/Низкая] |

### 🔗 Ссылки
- [Название источника](URL) — [дата/время]

### 💡 Выводы
[Итоговый анализ ситуации]"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for news-related requests.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for news keywords
        keyword_count = sum(1 for kw in self.NEWS_KEYWORDS if kw in message_lower)
        if keyword_count >= 2:
            return 0.95
        elif keyword_count == 1:
            return 0.8
        
        # Check for news patterns
        news_patterns = [
            "что пишут", "что говорят", "в новостях",
            "what's the news", "in the news", "coverage",
            "сколько источников", "different sources",
            "сравни источники", "compare sources",
        ]
        for pattern in news_patterns:
            if pattern in message_lower:
                return 0.9
        
        # Check context for web search results with multiple sources
        if "web_search" in context.get("agent_results", {}):
            search_result = context["agent_results"]["web_search"]
            if hasattr(search_result, "metadata"):
                sources = getattr(search_result.metadata, "sources", [])
                if len(sources) >= 2:
                    return 0.85
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by aggregating and analyzing news.
        
        Args:
            message: User message to process.
            context: Current dialog context with search results.
            history: Message history.
            
        Returns:
            AgentResult with aggregated news analysis.
        """
        # Extract sources from context (typically from web_search)
        sources = self._extract_sources_from_context(context)
        
        # If no sources found, check if we have raw search data
        if not sources:
            sources = self._extract_sources_from_search_results(context)
        
        # Cluster related news
        clusters = await self._cluster_news(sources, message)
        
        # Analyze each cluster
        for cluster in clusters:
            await self._analyze_cluster(cluster)
        
        # Generate aggregated response
        response, tokens_used = await self._generate_aggregated_response(
            message, clusters, sources
        )
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9 if len(sources) >= 3 else 0.8,
            metadata={
                "sources_count": len(sources),
                "clusters_count": len(clusters),
                "source_urls": [s.url for s in sources],
                "consensus_points": sum(len(c.consensus) for c in clusters),
                "discrepancies_found": sum(len(c.discrepancies) for c in clusters),
            },
            tokens_used=tokens_used,
        )
    
    def _extract_sources_from_context(
        self, context: dict[str, Any]
    ) -> list[NewsSource]:
        """Extract news sources from dialog context.
        
        Args:
            context: Dialog context with previous agent results.
            
        Returns:
            List of NewsSource objects.
        """
        sources = []
        agent_results = context.get("agent_results", {})
        
        # Check web_search results
        if "web_search" in agent_results:
            search_result = agent_results["web_search"]
            
            # Handle different result formats
            if isinstance(search_result, dict):
                raw_sources = search_result.get("sources", [])
                for src in raw_sources:
                    if isinstance(src, dict):
                        sources.append(NewsSource(
                            title=src.get("title", "Unknown"),
                            url=src.get("url", ""),
                            snippet=src.get("snippet", src.get("content", "")),
                            source_name=self._extract_source_name(src.get("url", "")),
                            published_date=src.get("date"),
                            credibility_score=self._estimate_credibility(
                                src.get("url", ""), src.get("source", "")
                            ),
                        ))
            elif hasattr(search_result, "metadata"):
                raw_sources = getattr(search_result.metadata, "sources", [])
                for src in raw_sources:
                    sources.append(NewsSource(
                        title=src.get("title", "Unknown"),
                        url=src.get("url", ""),
                        snippet=src.get("snippet", ""),
                        source_name=self._extract_source_name(src.get("url", "")),
                        credibility_score=self._estimate_credibility(src.get("url", "")),
                    ))
        
        return sources
    
    def _extract_sources_from_search_results(
        self, context: dict[str, Any]
    ) -> list[NewsSource]:
        """Extract sources from raw search results in context.
        
        Args:
            context: Dialog context.
            
        Returns:
            List of NewsSource objects.
        """
        sources = []
        
        # Check for raw search data
        search_data = context.get("search_results", [])
        for item in search_data:
            if isinstance(item, dict):
                sources.append(NewsSource(
                    title=item.get("title", ""),
                    url=item.get("link", item.get("url", "")),
                    snippet=item.get("snippet", item.get("description", "")),
                    source_name=item.get("source", self._extract_source_name(
                        item.get("link", "")
                    )),
                    published_date=item.get("date", item.get("published")),
                    credibility_score=self._estimate_credibility(
                        item.get("link", ""), item.get("source", "")
                    ),
                ))
        
        return sources
    
    def _extract_source_name(self, url: str) -> str:
        """Extract source name from URL.
        
        Args:
            url: Source URL.
            
        Returns:
            Extracted source name.
        """
        if not url:
            return "Unknown"
        
        try:
            # Simple extraction from domain
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                # Remove www. prefix
                if domain.startswith("www."):
                    domain = domain[4:]
                return domain
        except (IndexError, AttributeError):
            pass
        
        return "Unknown"
    
    def _estimate_credibility(self, url: str, source_name: str) -> float:
        """Estimate credibility score for a source.
        
        Args:
            url: Source URL.
            source_name: Name of the source.
            
        Returns:
            Credibility score (0.0 to 1.0).
        """
        combined = (url + " " + source_name).lower()
        
        for credible in self.CREDIBLE_SOURCES:
            if credible in combined:
                return 0.9
        
        # Check for known bias patterns
        for bias_type, sources in self.SOURCE_BIAS.items():
            for src in sources:
                if src in combined:
                    if bias_type == "center":
                        return 0.85
                    elif bias_type in ("left", "right"):
                        return 0.7
                    elif bias_type == "russia_independent":
                        return 0.75
                    elif bias_type == "russia_state":
                        return 0.6
        
        # Default for unknown sources
        return 0.5
    
    def _detect_source_bias(self, url: str, source_name: str) -> str:
        """Detect the bias category of a source.
        
        Args:
            url: Source URL.
            source_name: Name of the source.
            
        Returns:
            Bias category string.
        """
        combined = (url + " " + source_name).lower()
        
        for bias_type, sources in self.SOURCE_BIAS.items():
            for src in sources:
                if src in combined:
                    return bias_type
        
        return "unknown"
    
    async def _cluster_news(
        self,
        sources: list[NewsSource],
        message: str,
    ) -> list[NewsCluster]:
        """Cluster related news items.
        
        Args:
            sources: List of news sources.
            message: Original user message for context.
            
        Returns:
            List of NewsCluster objects.
        """
        if not sources:
            return []
        
        # For small number of sources, treat as single cluster
        if len(sources) <= 3:
            cluster = NewsCluster(
                topic=self._extract_topic(message, sources),
                sources=sources,
            )
            return [cluster]
        
        # For larger sets, use LLM to cluster
        sources_text = "\n".join([
            f"- [{s.source_name}] {s.title}: {s.snippet[:200]}"
            for s in sources[:10]  # Limit for prompt
        ])
        
        prompt = f"""Проанализируй эти источники новостей и сгруппируй их по темам.

Источники:
{sources_text}

Ответь в JSON формате:
{{
    "clusters": [
        {{
            "topic": "название темы",
            "source_indices": [0, 1, 2]
        }}
    ]
}}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content="Ты — аналитик новостей."),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        try:
            response = await self.llm_provider.generate(messages, max_tokens=500)
            start = response.content.find("{")
            end = response.content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(response.content[start:end])
                clusters = []
                for cluster_data in data.get("clusters", []):
                    indices = cluster_data.get("source_indices", [])
                    cluster_sources = [sources[i] for i in indices if i < len(sources)]
                    if cluster_sources:
                        clusters.append(NewsCluster(
                            topic=cluster_data.get("topic", "Unknown"),
                            sources=cluster_sources,
                        ))
                return clusters
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse cluster response: {e}")
        
        # Fallback: single cluster
        return [NewsCluster(
            topic=self._extract_topic(message, sources),
            sources=sources,
        )]
    
    def _extract_topic(
        self, message: str, sources: list[NewsSource]
    ) -> str:
        """Extract the main topic from message and sources.
        
        Args:
            message: User message.
            sources: News sources.
            
        Returns:
            Extracted topic string.
        """
        # Use first source title as topic hint
        if sources and sources[0].title:
            return sources[0].title[:100]
        
        # Extract from message
        words = message.split()[:10]
        return " ".join(words)
    
    async def _analyze_cluster(self, cluster: NewsCluster) -> None:
        """Analyze a news cluster for consensus and discrepancies.
        
        Args:
            cluster: NewsCluster to analyze (modified in place).
        """
        if len(cluster.sources) < 2:
            cluster.summary = cluster.sources[0].snippet if cluster.sources else ""
            return
        
        sources_text = "\n\n".join([
            f"Источник: {s.source_name} (достоверность: {s.credibility_score:.0%})\n"
            f"Заголовок: {s.title}\n"
            f"Текст: {s.snippet}\n"
            f"URL: {s.url}"
            for s in cluster.sources
        ])
        
        prompt = f"""Проанализируй эти источники новостей на одну тему.

{sources_text}

Найди:
1. Факты, которые подтверждаются несколькими источниками (консенсус)
2. Расхождения между источниками
3. Потенциальную предвзятость

Ответь в JSON формате:
{{
    "consensus": ["факт 1", "факт 2"],
    "discrepancies": [
        {{"point": "что расходится", "source_a": "источник A говорит", "source_b": "источник B говорит"}}
    ],
    "summary": "краткое резюме",
    "bias_analysis": "анализ предвзятости"
}}"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        try:
            response = await self.llm_provider.generate(messages, max_tokens=1000)
            start = response.content.find("{")
            end = response.content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(response.content[start:end])
                cluster.consensus = data.get("consensus", [])
                cluster.discrepancies = data.get("discrepancies", [])
                cluster.summary = data.get("summary", "")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse cluster analysis: {e}")
            cluster.summary = "Не удалось проанализировать кластер."
    
    async def _generate_aggregated_response(
        self,
        message: str,
        clusters: list[NewsCluster],
        sources: list[NewsSource],
    ) -> tuple[str, int | None]:
        """Generate the final aggregated response.
        
        Args:
            message: Original user message.
            clusters: Analyzed news clusters.
            sources: All news sources.
            
        Returns:
            Tuple of (aggregated response string, tokens used or None).
        """
        if not clusters:
            return "Не удалось найти источники новостей для анализа.", None
        
        # Build context for LLM
        context_parts = []
        for i, cluster in enumerate(clusters, 1):
            context_parts.append(f"### Кластер {i}: {cluster.topic}")
            context_parts.append(f"\n**Консенсус:**")
            for point in cluster.consensus:
                context_parts.append(f"- {point}")
            context_parts.append(f"\n**Расхождения:**")
            for disc in cluster.discrepancies:
                context_parts.append(f"- {disc}")
            context_parts.append(f"\n**Резюме:** {cluster.summary}")
        
        context_text = "\n".join(context_parts)
        
        sources_table = "\n".join([
            f"| {s.source_name} | {s.snippet[:50]}... | {s.credibility_score:.0%} |"
            for s in sources[:10]
        ])
        
        links_list = "\n".join([
            f"- [{s.source_name}]({s.url})"
            for s in sources[:10] if s.url
        ])
        
        prompt = f"""Сформируй итоговый ответ на основе анализа новостей.

Запрос пользователя: {message}

Анализ кластеров:
{context_text}

Используй этот формат ответа:
## 📰 Агрегация новостей

### 📌 Основное
[Ключевые факты из консенсуса]

### ✅ Подтверждённые факты
[Список фактов с источниками]

### ⚠️ Спорные моменты
[Где источники расходятся]

### 📊 Источники
| Источник | Информация | Достоверность |
{sources_table}

### 🔗 Ссылки
{links_list}

### 💡 Выводы
[Итоговый анализ]"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1500)
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.get("total_tokens") or (
                response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            )
        return response.content, tokens_used
    
    async def compare_sources(
        self,
        topic: str,
        sources: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Compare coverage of a topic across multiple sources.
        
        Args:
            topic: Topic to compare.
            sources: List of source dictionaries with 'name', 'content', 'url'.
            
        Returns:
            Comparison result with consensus and discrepancies.
        """
        news_sources = [
            NewsSource(
                title=f"Source: {s.get('name', 'Unknown')}",
                url=s.get("url", ""),
                snippet=s.get("content", ""),
                source_name=s.get("name", "Unknown"),
                credibility_score=self._estimate_credibility(
                    s.get("url", ""), s.get("name", "")
                ),
            )
            for s in sources
        ]
        
        cluster = NewsCluster(topic=topic, sources=news_sources)
        await self._analyze_cluster(cluster)
        
        return {
            "topic": topic,
            "consensus": cluster.consensus,
            "discrepancies": cluster.discrepancies,
            "summary": cluster.summary,
            "sources_analyzed": len(news_sources),
        }
    
    async def get_source_credibility_report(
        self, urls: list[str]
    ) -> list[dict[str, Any]]:
        """Generate credibility report for a list of source URLs.
        
        Args:
            urls: List of source URLs to analyze.
            
        Returns:
            List of credibility reports for each URL.
        """
        reports = []
        for url in urls:
            source_name = self._extract_source_name(url)
            bias = self._detect_source_bias(url, source_name)
            credibility = self._estimate_credibility(url, source_name)
            
            reports.append({
                "url": url,
                "source_name": source_name,
                "credibility_score": credibility,
                "bias_category": bias,
                "recommendation": self._get_credibility_recommendation(credibility),
            })
        
        return reports
    
    def _get_credibility_recommendation(self, score: float) -> str:
        """Get recommendation text for a credibility score.
        
        Args:
            score: Credibility score (0.0 to 1.0).
            
        Returns:
            Recommendation string.
        """
        if score >= 0.85:
            return "Высокая достоверность — можно цитировать как надёжный источник"
        elif score >= 0.7:
            return "Средняя достоверность — рекомендуется перекрёстная проверка"
        elif score >= 0.5:
            return "Умеренная достоверность — используйте с осторожностью"
        else:
            return "Низкая достоверность — не рекомендуется как единственный источник"
