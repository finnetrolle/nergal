"""Tests for typed agent metadata classes."""

import pytest

from nergal.dialog.base import AgentResult, AgentType
from nergal.dialog.metadata import (
    AnalysisMetadata,
    BaseAgentMetadata,
    CodeAnalysisMetadata,
    ComparisonMetadata,
    create_metadata_from_dict,
    DefaultMetadata,
    FactCheckMetadata,
    get_metadata_class,
    KnowledgeBaseMetadata,
    MetricsMetadata,
    NewsMetadata,
    SummaryMetadata,
    TechDocsMetadata,
    TodoistMetadata,
    WebSearchMetadata,
)


class TestBaseAgentMetadata:
    """Tests for BaseAgentMetadata class."""

    def test_default_values(self) -> None:
        """Test default values for base metadata."""
        metadata = BaseAgentMetadata()

        assert metadata.tokens_used is None
        assert metadata.model is None
        assert metadata.processing_time_ms is None

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        metadata = BaseAgentMetadata(
            tokens_used=100,
            model="test-model",
            processing_time_ms=50.5,
        )

        result = metadata.to_dict()

        assert result["tokens_used"] == 100
        assert result["model"] == "test-model"
        assert result["processing_time_ms"] == 50.5

    def test_to_dict_excludes_none(self) -> None:
        """Test that None values are excluded from dict."""
        metadata = BaseAgentMetadata(tokens_used=100)

        result = metadata.to_dict()

        assert "tokens_used" in result
        assert "model" not in result
        assert "processing_time_ms" not in result

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "tokens_used": 200,
            "model": "gpt-4",
            "processing_time_ms": 100.0,
        }

        metadata = BaseAgentMetadata.from_dict(data)

        assert metadata.tokens_used == 200
        assert metadata.model == "gpt-4"
        assert metadata.processing_time_ms == 100.0

    def test_from_dict_ignores_unknown_fields(self) -> None:
        """Test that unknown fields are ignored."""
        data = {
            "tokens_used": 100,
            "unknown_field": "should be ignored",
        }

        metadata = BaseAgentMetadata.from_dict(data)

        assert metadata.tokens_used == 100
        assert not hasattr(metadata, "unknown_field")


class TestWebSearchMetadata:
    """Tests for WebSearchMetadata class."""

    def test_default_values(self) -> None:
        """Test default values."""
        metadata = WebSearchMetadata()

        assert metadata.query == ""
        assert metadata.sources == []
        assert metadata.result_count == 0
        assert metadata.search_time_ms is None
        assert metadata.search_provider is None
        assert metadata.cached is False

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = WebSearchMetadata(
            query="Python tutorial",
            sources=["https://example.com", "https://test.com"],
            result_count=10,
            search_time_ms=150.5,
            search_provider="google",
            cached=True,
            tokens_used=500,
        )

        assert metadata.query == "Python tutorial"
        assert len(metadata.sources) == 2
        assert metadata.result_count == 10
        assert metadata.search_time_ms == 150.5
        assert metadata.search_provider == "google"
        assert metadata.cached is True
        assert metadata.tokens_used == 500

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization."""
        original = WebSearchMetadata(
            query="test query",
            sources=["source1", "source2"],
            result_count=5,
        )

        data = original.to_dict()
        restored = WebSearchMetadata.from_dict(data)

        assert restored.query == original.query
        assert restored.sources == original.sources
        assert restored.result_count == original.result_count


class TestTodoistMetadata:
    """Tests for TodoistMetadata class."""

    def test_default_values(self) -> None:
        """Test default values."""
        metadata = TodoistMetadata()

        assert metadata.action == ""
        assert metadata.task_count == 0
        assert metadata.project_name is None
        assert metadata.task_id is None
        assert metadata.due_date is None

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = TodoistMetadata(
            action="create_task",
            task_count=3,
            project_name="Work",
            task_id="12345",
            due_date="2024-12-31",
        )

        assert metadata.action == "create_task"
        assert metadata.task_count == 3
        assert metadata.project_name == "Work"
        assert metadata.task_id == "12345"
        assert metadata.due_date == "2024-12-31"


class TestNewsMetadata:
    """Tests for NewsMetadata class."""

    def test_default_values(self) -> None:
        """Test default values."""
        metadata = NewsMetadata()

        assert metadata.sources == []
        assert metadata.clusters == 0
        assert metadata.sentiment is None
        assert metadata.topics == []
        assert metadata.time_range is None

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = NewsMetadata(
            sources=["BBC", "CNN", "Reuters"],
            clusters=5,
            sentiment="neutral",
            topics=["politics", "economy"],
            time_range="24h",
        )

        assert len(metadata.sources) == 3
        assert metadata.clusters == 5
        assert metadata.sentiment == "neutral"
        assert metadata.topics == ["politics", "economy"]
        assert metadata.time_range == "24h"


class TestAnalysisMetadata:
    """Tests for AnalysisMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = AnalysisMetadata(
            data_sources=["database", "api"],
            insights_count=7,
            analysis_type="trend",
            confidence=0.85,
        )

        assert metadata.data_sources == ["database", "api"]
        assert metadata.insights_count == 7
        assert metadata.analysis_type == "trend"
        assert metadata.confidence == 0.85


class TestComparisonMetadata:
    """Tests for ComparisonMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = ComparisonMetadata(
            items_compared=["React", "Vue", "Angular"],
            criteria=["performance", "ease of use", "community"],
            winner="React",
            comparison_count=3,
        )

        assert len(metadata.items_compared) == 3
        assert len(metadata.criteria) == 3
        assert metadata.winner == "React"
        assert metadata.comparison_count == 3


class TestFactCheckMetadata:
    """Tests for FactCheckMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = FactCheckMetadata(
            claims_checked=5,
            verified_claims=3,
            false_claims=1,
            uncertain_claims=1,
            sources=["snopes.com", "factcheck.org"],
        )

        assert metadata.claims_checked == 5
        assert metadata.verified_claims == 3
        assert metadata.false_claims == 1
        assert metadata.uncertain_claims == 1
        assert len(metadata.sources) == 2


class TestSummaryMetadata:
    """Tests for SummaryMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = SummaryMetadata(
            original_length=5000,
            summary_length=500,
            compression_ratio=0.1,
            key_points=5,
        )

        assert metadata.original_length == 5000
        assert metadata.summary_length == 500
        assert metadata.compression_ratio == 0.1
        assert metadata.key_points == 5


class TestCodeAnalysisMetadata:
    """Tests for CodeAnalysisMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = CodeAnalysisMetadata(
            language="Python",
            files_analyzed=10,
            issues_found=3,
            suggestions_count=7,
        )

        assert metadata.language == "Python"
        assert metadata.files_analyzed == 10
        assert metadata.issues_found == 3
        assert metadata.suggestions_count == 7


class TestMetricsMetadata:
    """Tests for MetricsMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = MetricsMetadata(
            metrics_retrieved=15,
            time_range="7d",
            data_points=1000,
            aggregation="avg",
        )

        assert metadata.metrics_retrieved == 15
        assert metadata.time_range == "7d"
        assert metadata.data_points == 1000
        assert metadata.aggregation == "avg"


class TestKnowledgeBaseMetadata:
    """Tests for KnowledgeBaseMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = KnowledgeBaseMetadata(
            queries=["how to deploy", "configuration"],
            documents_found=5,
            relevance_score=0.92,
            categories=["deployment", "config"],
        )

        assert metadata.queries == ["how to deploy", "configuration"]
        assert metadata.documents_found == 5
        assert metadata.relevance_score == 0.92
        assert metadata.categories == ["deployment", "config"]


class TestTechDocsMetadata:
    """Tests for TechDocsMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = TechDocsMetadata(
            library="React",
            version="18.2",
            topics=["hooks", "components"],
            code_examples=10,
        )

        assert metadata.library == "React"
        assert metadata.version == "18.2"
        assert metadata.topics == ["hooks", "components"]
        assert metadata.code_examples == 10


class TestDefaultMetadata:
    """Tests for DefaultMetadata class."""

    def test_full_initialization(self) -> None:
        """Test full initialization."""
        metadata = DefaultMetadata(
            conversation_turn=5,
            intent="greeting",
            entities=["name", "date"],
            sentiment="positive",
        )

        assert metadata.conversation_turn == 5
        assert metadata.intent == "greeting"
        assert metadata.entities == ["name", "date"]
        assert metadata.sentiment == "positive"


class TestGetMetadataClass:
    """Tests for get_metadata_class function."""

    def test_known_agent_types(self) -> None:
        """Test getting metadata class for known agent types."""
        assert get_metadata_class("web_search") == WebSearchMetadata
        assert get_metadata_class("todoist") == TodoistMetadata
        assert get_metadata_class("news") == NewsMetadata
        assert get_metadata_class("analysis") == AnalysisMetadata
        assert get_metadata_class("comparison") == ComparisonMetadata
        assert get_metadata_class("fact_check") == FactCheckMetadata
        assert get_metadata_class("summary") == SummaryMetadata
        assert get_metadata_class("code_analysis") == CodeAnalysisMetadata
        assert get_metadata_class("metrics") == MetricsMetadata
        assert get_metadata_class("knowledge_base") == KnowledgeBaseMetadata
        assert get_metadata_class("tech_docs") == TechDocsMetadata
        assert get_metadata_class("default") == DefaultMetadata

    def test_unknown_agent_type_returns_default(self) -> None:
        """Test that unknown agent types return DefaultMetadata."""
        assert get_metadata_class("unknown_type") == DefaultMetadata


class TestCreateMetadataFromDict:
    """Tests for create_metadata_from_dict function."""

    def test_create_web_search_metadata(self) -> None:
        """Test creating WebSearchMetadata from dict."""
        data = {
            "query": "test query",
            "sources": ["source1"],
            "result_count": 5,
        }

        metadata = create_metadata_from_dict("web_search", data)

        assert isinstance(metadata, WebSearchMetadata)
        assert metadata.query == "test query"
        assert metadata.sources == ["source1"]
        assert metadata.result_count == 5

    def test_create_todoist_metadata(self) -> None:
        """Test creating TodoistMetadata from dict."""
        data = {
            "action": "complete_task",
            "task_count": 2,
            "project_name": "Personal",
        }

        metadata = create_metadata_from_dict("todoist", data)

        assert isinstance(metadata, TodoistMetadata)
        assert metadata.action == "complete_task"
        assert metadata.task_count == 2
        assert metadata.project_name == "Personal"

    def test_create_default_for_unknown_type(self) -> None:
        """Test that unknown type creates DefaultMetadata."""
        data = {"tokens_used": 100}

        metadata = create_metadata_from_dict("unknown_type", data)

        assert isinstance(metadata, DefaultMetadata)


class TestAgentResultIntegration:
    """Tests for AgentResult integration with typed metadata."""

    def test_get_typed_metadata_empty(self) -> None:
        """Test get_typed_metadata with empty metadata."""
        result = AgentResult(
            response="Test response",
            agent_type=AgentType.DEFAULT,
        )

        metadata = result.get_typed_metadata()

        assert metadata is None

    def test_get_typed_metadata_web_search(self) -> None:
        """Test get_typed_metadata for web search."""
        result = AgentResult(
            response="Found results",
            agent_type=AgentType.WEB_SEARCH,
            metadata={
                "query": "test",
                "sources": ["a", "b"],
                "result_count": 2,
            },
        )

        metadata = result.get_typed_metadata()

        assert metadata is not None
        assert isinstance(metadata, WebSearchMetadata)
        assert metadata.query == "test"
        assert metadata.sources == ["a", "b"]
        assert metadata.result_count == 2

    def test_get_typed_metadata_todoist(self) -> None:
        """Test get_typed_metadata for Todoist."""
        result = AgentResult(
            response="Task created",
            agent_type=AgentType.TODOIST,
            metadata={
                "action": "create_task",
                "task_count": 1,
                "project_name": "Work",
            },
        )

        metadata = result.get_typed_metadata()

        assert metadata is not None
        assert isinstance(metadata, TodoistMetadata)
        assert metadata.action == "create_task"
        assert metadata.task_count == 1
        assert metadata.project_name == "Work"

    def test_get_typed_metadata_preserves_tokens(self) -> None:
        """Test that tokens_used is preserved in typed metadata."""
        result = AgentResult(
            response="Response",
            agent_type=AgentType.DEFAULT,
            metadata={
                "tokens_used": 150,
                "model": "gpt-4",
            },
            tokens_used=150,
        )

        metadata = result.get_typed_metadata()

        assert metadata is not None
        assert metadata.tokens_used == 150
        assert metadata.model == "gpt-4"
