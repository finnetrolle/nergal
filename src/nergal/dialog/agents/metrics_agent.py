"""Metrics agent for retrieving quantitative data and statistics.

This agent fetches metrics, statistics, and quantitative data
from monitoring systems and data sources.
"""

import logging
from typing import Any

from nergal.dialog.base import AgentResult, AgentType, BaseAgent
from nergal.dialog.styles import StyleType
from nergal.llm import BaseLLMProvider, LLMMessage, MessageRole

logger = logging.getLogger(__name__)


class MetricsAgent(BaseAgent):
    """Agent for retrieving and analyzing metrics.
    
    This agent fetches quantitative data from monitoring systems,
    databases, and APIs to provide data-driven insights.
    
    Use cases:
    - Performance metrics
    - Usage statistics
    - KPI tracking
    - Infrastructure metrics
    """
    
    # Metrics-related keywords
    METRICS_KEYWORDS = [
        "метрика", "статистика", "показатель", "kpi", "график",
        "динамика", "тренд", "прирост", "снижение", "рост",
        "количество", "число", "процент", "среднее", "медиана",
        "latency", "throughput", "rps", "uptime", "доступность",
        "время отклика", "нагрузка", "память", "cpu",
    ]
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        metrics_connectors: dict[str, Any] | None = None,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        """Initialize the metrics agent.
        
        Args:
            llm_provider: LLM provider for generating responses.
            metrics_connectors: Connectors for metrics sources.
            style_type: Response style to use.
        """
        super().__init__(llm_provider, style_type)
        self._metrics_connectors = metrics_connectors or {}
    
    @property
    def agent_type(self) -> AgentType:
        """Return the type of this agent."""
        return AgentType.METRICS
    
    @property
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        return """Ты — агент метрик. Твоя задача — предоставлять
количественные данные и анализировать статистику.

Ты можешь:
- Получать метрики производительности
- Анализировать тренды
- Сравнивать показатели за периоды
- Выявлять аномалии

При ответе:
1. Приводи точные цифры
2. Сравнивай с предыдущими периодами
3. Указывай тренды
4. Объясняй причины изменений

Формат ответа:
## Текущие показатели
[Ключевые метрики]

## Динамика
[Изменения относительно прошлого периода]

## Анализ
[Выводы и причины]

## Рекомендации
[Если есть проблемы]"""

    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine if this agent can handle the message.
        
        Higher confidence for metrics-related questions.
        
        Args:
            message: User message to analyze.
            context: Current dialog context.
            
        Returns:
            Confidence score (0.0 to 1.0).
        """
        message_lower = message.lower()
        
        # Check for metrics keywords
        keyword_matches = sum(
            1 for kw in self.METRICS_KEYWORDS
            if kw in message_lower
        )
        
        if keyword_matches >= 2:
            return 0.85
        elif keyword_matches == 1:
            return 0.7
        
        # Questions about numbers/stats
        stats_patterns = ["сколько", "какой процент", "какая доля", "какова частота"]
        if any(pattern in message_lower for pattern in stats_patterns):
            return 0.6
        
        return 0.2
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Process the message by fetching metrics.
        
        Args:
            message: User message to process.
            context: Current dialog context.
            history: Message history.
            
        Returns:
            AgentResult with metrics data.
        """
        # Determine metrics type
        metrics_type = self._determine_metrics_type(message)
        
        # Fetch metrics
        metrics_data = await self._fetch_metrics(message, metrics_type, context)
        
        # Generate response
        if metrics_data:
            response = await self._generate_metrics_response(
                message, metrics_data, metrics_type
            )
            confidence = 0.9
        else:
            response = await self._generate_no_data_response(message, metrics_type)
            confidence = 0.5
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=confidence,
            metadata={
                "metrics_type": metrics_type,
                "data_available": bool(metrics_data),
                "sources": list(metrics_data.keys()) if metrics_data else [],
            }
        )
    
    def _determine_metrics_type(self, message: str) -> str:
        """Determine the type of metrics query.
        
        Args:
            message: User message.
            
        Returns:
            Metrics type identifier.
        """
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["latency", "время отклика", "задержка"]):
            return "latency"
        elif any(kw in message_lower for kw in ["rps", "throughput", "запросы"]):
            return "throughput"
        elif any(kw in message_lower for kw in ["uptime", "доступность", "availability"]):
            return "availability"
        elif any(kw in message_lower for kw in ["cpu", "память", "memory", "нагрузка"]):
            return "resources"
        elif any(kw in message_lower for kw in ["ошибки", "errors", "error rate"]):
            return "errors"
        elif any(kw in message_lower for kw in ["пользовател", "users", "active"]):
            return "users"
        else:
            return "general"
    
    async def _fetch_metrics(
        self,
        query: str,
        metrics_type: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Fetch metrics from configured sources.
        
        Args:
            query: Query string.
            metrics_type: Type of metrics.
            context: Dialog context.
            
        Returns:
            Metrics data or None.
        """
        results = {}
        
        for name, connector in self._metrics_connectors.items():
            try:
                if hasattr(connector, "query"):
                    data = await connector.query(query, metrics_type=metrics_type)
                    results[name] = data
                elif hasattr(connector, "get_metrics"):
                    data = await connector.get_metrics(metrics_type)
                    results[name] = data
            except Exception as e:
                logger.warning(f"Metrics connector {name} failed: {e}")
        
        return results if results else None
    
    async def _generate_metrics_response(
        self,
        message: str,
        metrics_data: dict[str, Any],
        metrics_type: str,
    ) -> str:
        """Generate response based on metrics data.
        
        Args:
            message: Original message.
            metrics_data: Fetched metrics.
            metrics_type: Type of metrics.
            
        Returns:
            Generated response.
        """
        # Format metrics for display
        formatted_metrics = []
        for source, data in metrics_data.items():
            if isinstance(data, dict):
                formatted_metrics.append(f"### {source}")
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        formatted_metrics.append(f"- **{key}**: {value:,.2f}" if isinstance(value, float) else f"- **{key}**: {value:,}")
                    else:
                        formatted_metrics.append(f"- **{key}**: {value}")
            elif isinstance(data, list):
                formatted_metrics.append(f"### {source}")
                for item in data[:5]:
                    formatted_metrics.append(f"- {item}")
        
        metrics_text = "\n".join(formatted_metrics)
        
        prompt = f"""На основе полученных метрик ответь на вопрос.

Вопрос: {message}

Тип метрик: {metrics_type}

Данные:
{metrics_text}

Проанализируй и представь данные в удобном формате."""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await self.llm_provider.generate(messages, max_tokens=1000)
        return response.content
    
    async def _generate_no_data_response(
        self,
        message: str,
        metrics_type: str,
    ) -> str:
        """Generate response when no data available.
        
        Args:
            message: Original message.
            metrics_type: Type of metrics.
            
        Returns:
            Generated response.
        """
        return f"""Не удалось получить данные о метриках типа "{metrics_type}".

Для получения актуальных метрик необходимо:
1. Настроить подключение к системе мониторинга (Grafana, Datadog, Prometheus)
2. Указать конкретные метрики для отслеживания

Проверьте конфигурацию подключений к источникам данных."""
    
    def add_metrics_connector(self, name: str, connector: Any) -> None:
        """Add a metrics source connector.
        
        Args:
            name: Connector name.
            connector: Connector with query method.
        """
        self._metrics_connectors[name] = connector
    
    async def get_metric(
        self,
        metric_name: str,
        time_range: str = "1h",
    ) -> dict[str, Any] | None:
        """Get a specific metric value.
        
        Args:
            metric_name: Name of the metric.
            time_range: Time range for the metric.
            
        Returns:
            Metric data or None.
        """
        for name, connector in self._metrics_connectors.items():
            try:
                if hasattr(connector, "get_metric"):
                    return await connector.get_metric(metric_name, time_range)
            except Exception as e:
                logger.warning(f"Failed to get metric {metric_name}: {e}")
        
        return None
    
    async def compare_periods(
        self,
        metric_name: str,
        period1: str,
        period2: str,
    ) -> dict[str, Any]:
        """Compare metric between two time periods.
        
        Args:
            metric_name: Name of the metric.
            period1: First period.
            period2: Second period.
            
        Returns:
            Comparison result.
        """
        value1 = await self.get_metric(metric_name, period1)
        value2 = await self.get_metric(metric_name, period2)
        
        if value1 and value2:
            v1 = value1.get("value", 0)
            v2 = value2.get("value", 0)
            
            if v1 != 0:
                change_percent = ((v2 - v1) / v1) * 100
            else:
                change_percent = 0
            
            return {
                "period1": {"range": period1, "value": v1},
                "period2": {"range": period2, "value": v2},
                "change": v2 - v1,
                "change_percent": change_percent,
            }
        
        return {"error": "Could not fetch metrics for comparison"}
    
    async def detect_anomalies(
        self,
        metric_name: str,
        threshold: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Detect anomalies in metric data.
        
        Args:
            metric_name: Name of the metric.
            threshold: Standard deviation threshold.
            
        Returns:
            List of detected anomalies.
        """
        # This would typically analyze time series data
        # Simplified implementation
        data = await self.get_metric(metric_name, "24h")
        
        if not data:
            return []
        
        # Placeholder for anomaly detection logic
        return []
