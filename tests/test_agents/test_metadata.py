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


# Parametrized tests for all metadata classes
METADATA_TEST_DATA = [
    (
        WebSearchMetadata,
        "web_search",
        {
            "default_values": {
                "query": "",
                "sources": [],
                "result_count": 0,
                "search_time_ms": None,
                "search_provider": None,
                "cached": False,
            },
            "full_init": {
                "args": {
                    "query": "Python tutorial",
                    "sources": ["https://example.com", "https://test.com"],
                    "result_count": 10,
                    "search_time_ms": 150.5,
                    "search_provider": "google",
                    "cached": True,
                    "tokens_used": 500,
                },
                "expected": {
                    "query": "Python tutorial",
                    "sources": ["https://example.com", "https://test.com"],
                    "result_count": 10,
                    "search_time_ms": 150.5,
                    "search_provider": "google",
                    "cached": True,
                    "tokens_used": 500,
                },
            },
            "roundtrip": {
                "args": {
                    "query": "test query",
                    "sources": ["source1", "source2"],
                    "result_count": 5,
                },
            },
        },
    ),
    (
        TodoistMetadata,
        "todoist",
        {
            "default_values": {
                "action": "",
                "task_count": 0,
                "project_name": None,
                "task_id": None,
                "due_date": None,
            },
            "full_init": {
                "args": {
                    "action": "create_task",
                    "task_count": 3,
                    "project_name": "Work",
                    "task_id": "12345",
                    "due_date": "2024-12-31",
                },
                "expected": {
                    "action": "create_task",
                    "task_count": 3,
                    "project_name": "Work",
                    "task_id": "12345",
                    "due_date": "2024-12-31",
                },
            },
        },
    ),
    (
        NewsMetadata,
        "news",
        {
            "default_values": {
                "sources": [],
                "clusters": 0,
                "sentiment": None,
                "topics": [],
                "time_range": None,
            },
            "full_init": {
                "args": {
                    "sources": ["BBC", "CNN", "Reuters"],
                    "clusters": 5,
                    "sentiment": "neutral",
                    "topics": ["politics", "economy"],
                    "time_range": "24h",
                },
                "expected": {
                    "sources": ["BBC", "CNN", "Reuters"],
                    "clusters": 5,
                    "sentiment": "neutral",
                    "topics": ["politics", "economy"],
                    "time_range": "24h",
                },
            },
        },
    ),
    (
        AnalysisMetadata,
        "analysis",
        {
            "full_init": {
                "args": {
                    "data_sources": ["database", "api"],
                    "insights_count": 7,
                    "analysis_type": "trend",
                    "confidence": 0.85,
                },
                "expected": {
                    "data_sources": ["database", "api"],
                    "insights_count": 7,
                    "analysis_type": "trend",
                    "confidence": 0.85,
                },
            },
        },
    ),
    (
        ComparisonMetadata,
        "comparison",
        {
            "full_init": {
                "args": {
                    "items_compared": ["React", "Vue", "Angular"],
                    "criteria": ["performance", "ease of use", "community"],
                    "winner": "React",
                    "comparison_count": 3,
                },
                "expected": {
                    "items_compared": ["React", "Vue", "Angular"],
                    "criteria": ["performance", "ease of use", "community"],
                    "winner": "React",
                    "comparison_count": 3,
                },
            },
        },
    ),
    (
        FactCheckMetadata,
        "fact_check",
        {
            "full_init": {
                "args": {
                    "claims_checked": 5,
                    "verified_claims": 3,
                    "false_claims": 1,
                    "uncertain_claims": 1,
                    "sources": ["snopes.com", "factcheck.org"],
                },
                "expected": {
                    "claims_checked": 5,
                    "verified_claims": 3,
                    "false_claims": 1,
                    "uncertain_claims": 1,
                    "sources": ["snopes.com", "factcheck.org"],
                },
            },
        },
    ),
    (
        SummaryMetadata,
        "summary",
        {
            "full_init": {
                "args": {
                    "original_length": 5000,
                    "summary_length": 500,
                    "compression_ratio": 0.1,
                    "key_points": 5,
                },
                "expected": {
                    "original_length": 5000,
                    "summary_length": 500,
                    "compression_ratio": 0.1,
                    "key_points": 5,
                },
            },
        },
    ),
    (
        CodeAnalysisMetadata,
        "code_analysis",
        {
            "full_init": {
                "args": {
                    "language": "Python",
                    "files_analyzed": 10,
                    "issues_found": 3,
                    "suggestions_count": 7,
                },
                "expected": {
                    "language": "Python",
                    "files_analyzed": 10,
                    "issues_found": 3,
                    "suggestions_count": 7,
                },
            },
        },
    ),
    (
        MetricsMetadata,
        "metrics",
        {
            "full_init": {
                "args": {
                    "metrics_retrieved": 15,
                    "time_range": "7d",
                    "data_points": 1000,
                    "aggregation": "avg",
                },
                "expected": {
                    "metrics_retrieved": 15,
                    "time_range": "7d",
                    "data_points": 1000,
                    "aggregation": "avg",
                },
            },
        },
    ),
    (
        KnowledgeBaseMetadata,
        "knowledge_base",
        {
            "full_init": {
                "args": {
                    "queries": ["how to deploy", "configuration"],
                    "documents_found": 5,
                    "relevance_score": 0.92,
                    "categories": ["deployment", "config"],
                },
                "expected": {
                    "queries": ["how to deploy", "configuration"],
                    "documents_found": 5,
                    "relevance_score": 0.92,
                    "categories": ["deployment", "config"],
                },
            },
        },
    ),
    (
        TechDocsMetadata,
        "tech_docs",
        {
            "full_init": {
                "args": {
                    "library": "React",
                    "version": "18.2",
                    "topics": ["hooks", "components"],
                    "code_examples": 10,
                },
                "expected": {
                    "library": "React",
                    "version": "18.2",
                    "topics": ["hooks", "components"],
                    "code_examples": 10,
                },
            },
        },
    ),
    (
        DefaultMetadata,
        "default",
        {
            "full_init": {
                "args": {
                    "conversation_turn": 5,
                    "intent": "greeting",
                    "entities": ["name", "date"],
                    "sentiment": "positive",
                },
                "expected": {
                    "conversation_turn": 5,
                    "intent": "greeting",
                    "entities": ["name", "date"],
                    "sentiment": "positive",
                },
            },
        },
    ),
]


class TestMetadataClassesDefaultValues:
    """Tests for default values of all metadata classes (parametrized)."""

    @pytest.mark.parametrize("metadata_class,agent_type,data", [
        (meta_class, agent_type, data["default_values"])
        for meta_class, agent_type, data in METADATA_TEST_DATA
        if "default_values" in data
    ])
    def test_default_values(self, metadata_class, agent_type, data):
        """Test default values for metadata classes."""
        metadata = metadata_class()

        for key, expected_value in data.items():
            actual_value = getattr(metadata, key)
            assert actual_value == expected_value, f"{agent_type}.{key}: expected {expected_value}, got {actual_value}"


class TestMetadataClassesFullInitialization:
    """Tests for full initialization of all metadata classes (parametrized)."""

    @pytest.mark.parametrize("metadata_class,agent_type,data", [
        (meta_class, agent_type, data["full_init"])
        for meta_class, agent_type, data in METADATA_TEST_DATA
        if "full_init" in data
    ])
    def test_full_initialization(self, metadata_class, agent_type, data):
        """Test full initialization of metadata classes."""
        metadata = metadata_class(**data["args"])

        for key, expected_value in data["expected"].items():
            actual_value = getattr(metadata, key)
            assert actual_value == expected_value, f"{agent_type}.{key}: expected {expected_value}, got {actual_value}"


class TestMetadataClassesSerializationRoundtrip:
    """Tests for serialization/deserialization roundtrip (parametrized)."""

    @pytest.mark.parametrize("metadata_class,agent_type,data", [
        (meta_class, agent_type, data["roundtrip"])
        for meta_class, agent_type, data in METADATA_TEST_DATA
        if "roundtrip" in data
    ])
    def test_serialization_roundtrip(self, metadata_class, agent_type, data):
        """Test serialization and deserialization."""
        original = metadata_class(**data["args"])

        serialized = original.to_dict()
        restored = metadata_class.from_dict(serialized)

        for key, expected_value in data["args"].items():
            actual_value = getattr(restored, key)
            assert actual_value == expected_value, f"{agent_type}.{key}: expected {expected_value}, got {actual_value}"


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

    @pytest.mark.parametrize("agent_type,metadata_class,init_data", [
        ("web_search", WebSearchMetadata, {
            "query": "test query",
            "sources": ["source1"],
            "result_count": 5,
        }),
        ("todoist", TodoistMetadata, {
            "action": "complete_task",
            "task_count": 2,
            "project_name": "Personal",
        }),
    ])
    def test_create_metadata_from_dict(self, agent_type, metadata_class, init_data):
        """Test creating metadata from dict."""
        metadata = create_metadata_from_dict(agent_type, init_data)

        assert isinstance(metadata, metadata_class)
        for key, expected_value in init_data.items():
            actual_value = getattr(metadata, key)
            assert actual_value == expected_value

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
