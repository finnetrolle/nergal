"""Typed metadata classes for agent results.

This module provides strongly-typed metadata classes for different agent types,
improving type safety and documentation of agent result metadata.
"""

from dataclasses import dataclass, field, fields
from typing import Any


@dataclass
class BaseAgentMetadata:
    """Base class for all agent metadata.

    All agent-specific metadata classes should inherit from this base class.
    Provides common fields and serialization support.

    Attributes:
        tokens_used: Number of tokens consumed by the agent.
        model: Model identifier used for processing.
        processing_time_ms: Time taken to process the request in milliseconds.
    """

    tokens_used: int | None = None
    model: str | None = None
    processing_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization.

        Returns:
            Dictionary representation of the metadata.
        """
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseAgentMetadata":
        """Create metadata instance from dictionary.

        Args:
            data: Dictionary with metadata fields.

        Returns:
            Metadata instance.
        """
        # Get valid field names for this dataclass
        valid_fields = {f.name for f in fields(cls)}
        # Filter data to only include valid fields
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


@dataclass
class WebSearchMetadata(BaseAgentMetadata):
    """Metadata for web search agent results.

    Attributes:
        query: The search query used.
        sources: List of source URLs or names.
        result_count: Number of search results returned.
        search_time_ms: Time taken for the search in milliseconds.
        search_provider: Name of the search provider used.
        cached: Whether the result was retrieved from cache.
    """

    query: str = ""
    sources: list[str] = field(default_factory=list)
    result_count: int = 0
    search_time_ms: float | None = None
    search_provider: str | None = None
    cached: bool = False


@dataclass
class TodoistMetadata(BaseAgentMetadata):
    """Metadata for Todoist agent results.

    Attributes:
        action: The action performed (create_task, complete_task, etc.).
        task_count: Number of tasks affected.
        project_name: Name of the Todoist project.
        task_id: ID of the specific task if applicable.
        due_date: Due date of the task if applicable.
    """

    action: str = ""
    task_count: int = 0
    project_name: str | None = None
    task_id: str | None = None
    due_date: str | None = None


@dataclass
class NewsMetadata(BaseAgentMetadata):
    """Metadata for news agent results.

    Attributes:
        sources: List of news source names.
        clusters: Number of topic clusters identified.
        sentiment: Overall sentiment (positive, negative, neutral).
        topics: List of identified topics.
        time_range: Time range of the news (e.g., '24h', 'week').
    """

    sources: list[str] = field(default_factory=list)
    clusters: int = 0
    sentiment: str | None = None
    topics: list[str] = field(default_factory=list)
    time_range: str | None = None


@dataclass
class AnalysisMetadata(BaseAgentMetadata):
    """Metadata for analysis agent results.

    Attributes:
        data_sources: List of data sources analyzed.
        insights_count: Number of insights generated.
        analysis_type: Type of analysis performed.
        confidence: Overall confidence in the analysis.
    """

    data_sources: list[str] = field(default_factory=list)
    insights_count: int = 0
    analysis_type: str | None = None
    confidence: float | None = None


@dataclass
class ComparisonMetadata(BaseAgentMetadata):
    """Metadata for comparison agent results.

    Attributes:
        items_compared: List of items being compared.
        criteria: Comparison criteria used.
        winner: The recommended choice if applicable.
        comparison_count: Number of items compared.
    """

    items_compared: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    winner: str | None = None
    comparison_count: int = 0


@dataclass
class FactCheckMetadata(BaseAgentMetadata):
    """Metadata for fact-check agent results.

    Attributes:
        claims_checked: Number of claims verified.
        verified_claims: Number of claims confirmed as true.
        false_claims: Number of claims confirmed as false.
        uncertain_claims: Number of claims with uncertain status.
        sources: Sources used for verification.
    """

    claims_checked: int = 0
    verified_claims: int = 0
    false_claims: int = 0
    uncertain_claims: int = 0
    sources: list[str] = field(default_factory=list)


@dataclass
class SummaryMetadata(BaseAgentMetadata):
    """Metadata for summary agent results.

    Attributes:
        original_length: Length of the original text.
        summary_length: Length of the summary.
        compression_ratio: Ratio of summary to original length.
        key_points: Number of key points extracted.
    """

    original_length: int = 0
    summary_length: int = 0
    compression_ratio: float | None = None
    key_points: int = 0


@dataclass
class CodeAnalysisMetadata(BaseAgentMetadata):
    """Metadata for code analysis agent results.

    Attributes:
        language: Programming language analyzed.
        files_analyzed: Number of files analyzed.
        issues_found: Number of issues identified.
        suggestions_count: Number of suggestions made.
    """

    language: str | None = None
    files_analyzed: int = 0
    issues_found: int = 0
    suggestions_count: int = 0


@dataclass
class MetricsMetadata(BaseAgentMetadata):
    """Metadata for metrics agent results.

    Attributes:
        metrics_retrieved: Number of metrics retrieved.
        time_range: Time range for the metrics.
        data_points: Total number of data points.
        aggregation: Type of aggregation applied.
    """

    metrics_retrieved: int = 0
    time_range: str | None = None
    data_points: int = 0
    aggregation: str | None = None


@dataclass
class KnowledgeBaseMetadata(BaseAgentMetadata):
    """Metadata for knowledge base agent results.

    Attributes:
        queries: Search queries used.
        documents_found: Number of documents found.
        relevance_score: Average relevance score.
        categories: Categories searched.
    """

    queries: list[str] = field(default_factory=list)
    documents_found: int = 0
    relevance_score: float | None = None
    categories: list[str] = field(default_factory=list)


@dataclass
class TechDocsMetadata(BaseAgentMetadata):
    """Metadata for technical documentation agent results.

    Attributes:
        library: Library or framework documented.
        version: Version of the library.
        topics: Topics covered.
        code_examples: Number of code examples included.
    """

    library: str | None = None
    version: str | None = None
    topics: list[str] = field(default_factory=list)
    code_examples: int = 0


@dataclass
class DefaultMetadata(BaseAgentMetadata):
    """Metadata for default agent results.

    Attributes:
        conversation_turn: Turn number in the conversation.
        intent: Detected intent of the message.
        entities: Extracted entities from the message.
        sentiment: Detected sentiment.
    """

    conversation_turn: int = 0
    intent: str | None = None
    entities: list[str] = field(default_factory=list)
    sentiment: str | None = None


# Mapping from AgentType to metadata class
METADATA_CLASS_MAP: dict[str, type[BaseAgentMetadata]] = {
    "web_search": WebSearchMetadata,
    "todoist": TodoistMetadata,
    "news": NewsMetadata,
    "analysis": AnalysisMetadata,
    "comparison": ComparisonMetadata,
    "fact_check": FactCheckMetadata,
    "summary": SummaryMetadata,
    "code_analysis": CodeAnalysisMetadata,
    "metrics": MetricsMetadata,
    "knowledge_base": KnowledgeBaseMetadata,
    "tech_docs": TechDocsMetadata,
    "default": DefaultMetadata,
}


def get_metadata_class(agent_type: str) -> type[BaseAgentMetadata]:
    """Get the appropriate metadata class for an agent type.

    Args:
        agent_type: The agent type string.

    Returns:
        The metadata class for the agent type.
    """
    return METADATA_CLASS_MAP.get(agent_type, DefaultMetadata)


def create_metadata_from_dict(agent_type: str, data: dict[str, Any]) -> BaseAgentMetadata:
    """Create a typed metadata instance from a dictionary.

    Args:
        agent_type: The agent type string.
        data: Dictionary with metadata fields.

    Returns:
        Typed metadata instance.
    """
    metadata_class = get_metadata_class(agent_type)
    return metadata_class.from_dict(data)
