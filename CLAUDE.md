# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development
```bash
# Install dependencies
uv sync

# Run the bot
uv run bot

# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src/
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/nergal --cov-report=term-missing --cov-report=html tests/

# Run a specific test file
uv run pytest tests/test_dialog/test_manager.py

# Run a specific test function
uv run pytest tests/test_dialog/test_manager.py::test_process_message

# Run tests matching a pattern
uv run pytest -k "cache"
```

### Docker Deployment
```bash
# Start bot
docker compose up -d

# Start with monitoring stack
docker compose --profile monitoring up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Architecture Overview

Nergal is a Telegram AI bot built with Python 3.12 using an agent-based architecture for handling user conversations through LLM integration.

### Dependency Injection

The project uses [`dependency-injector`](src/nergal/container.py:29) for managing application dependencies. The `Container` class ([`container.py`](src/nergal/container.py:53)) provides:

- **Singleton providers**: Database connection, agent cache, dialog manager, metrics server, STT provider, web search provider
- **Factory providers**: All repositories (user_repository, conversation_repository, etc.) and LLM provider
- **Lifecycle management**: Call `init_database()` at startup and `shutdown_database()` at shutdown for proper database connection pool management

Repositories receive their database connection via constructor injection. Use `container.user_repository()`, etc., to get instances.

### Agent System

The agent system in [`src/nergal/dialog/`](src/nergal/dialog/) is organized around these key components:

- **BaseAgent** ([`base.py:209`](src/nergal/dialog/base.py:209)): Abstract base for all agents with `agent_type`, `system_prompt`, `can_handle()`, and `process()` methods
- **AgentRegistry** ([`base.py:316`](src/nergal/dialog/base.py:316)): Manages available agents and determines the best agent for a message
- **AgentType** ([`base.py:30`](src/nergal/dialog/base.py:30)): Enum of all agent types (CORE, INFORMATION, PROCESSING, SPECIALIZED categories)
- **AgentFactory** ([`agent_loader.py:29`](src/nergal/dialog/agent_loader.py:29)): Decorator-based registry for creating agents. Agents register themselves via `@AgentFactory.register(AgentType.WEB_SEARCH, requires_search=True)`
- **DispatcherAgent**: Analyzes requests and creates execution plans with multiple steps
- **DialogManager** ([`manager.py:60`](src/nergal/dialog/manager.py:60)): Orchestrates conversation flow, manages context, executes plans with parallel support

Agent configuration is controlled by environment variables prefixed with `AGENTS_*`. Use `register_configured_agents()` to register agents based on config.

### Execution Plans and Parallel Processing

The dispatcher creates `ExecutionPlan` objects containing `PlanStep` items. Steps can:

- Depend on previous steps via `depends_on` list of step indices
- Run in parallel using `parallel_group` integer ID
- Be marked `is_optional` to skip gracefully if unavailable

`DialogManager._group_steps_by_dependency()` groups steps by dependency level. Steps with no dependencies in the same `parallel_group` execute concurrently via `asyncio.gather()`.

### Dialog Context Management

- **ContextManager** ([`context.py`](src/nergal/dialog/context.py)): Maintains user dialog contexts with conversation history
- **DialogContext**: Per-user state including messages, current agent, user info
- **ExecutionContext**: Shared data structure for passing results between steps in an execution plan

### LLM Providers

LLM providers follow a factory pattern ([`src/nergal/llm/`](src/nergal/llm/)):

- **BaseLLMProvider** ([`base.py:40`](src/nergal/llm/base.py:40)): Abstract base with `generate()`, `generate_stream()`, `provider_name`
- **create_llm_provider()**: Factory function for creating provider instances by type
- **LLMProviderType**: Enum of supported providers (zai, openai, anthropic, minimax)

Only Z.ai (GLM-4) is currently implemented. See [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md) for adding new providers.

### Configuration

Configuration is managed by pydantic-settings ([`config.py`](src/nergal/config.py:1)). All settings are loaded from environment variables or `.env` file. Key sections:

- `LLMSettings`: Provider configuration (provider, api_key, model, temperature, etc.)
- `AgentSettings`: Individual agent enable/disable flags
- `DatabaseSettings`, `WebSearchSettings`, `MonitoringSettings`, etc.

Use `from nergal.config import get_settings` to access configuration.

### Testing

Tests are organized by module: `tests/test_dialog/`, `tests/test_database/`, etc.

Key fixtures in [`conftest.py`](tests/conftest.py:1):
- `mock_llm_provider`: Mocked LLM provider with `generate` as AsyncMock
- `mock_llm_provider_with_response`: Factory for creating providers with custom responses
- `mock_agent`: Mocked BaseAgent with pre-configured behavior
- `agent_registry`: Registry with mock agent registered
- Various context fixtures (`empty_context`, `context_with_search_results`, etc.)

Use `pytest.mark.asyncio` for async test functions.

### Key Entry Points

- **Main bot entry**: [`src/nergal/main.py`](src/nergal/main.py:1) - `main()` function sets up the container, initializes Telegram bot
- **DI container**: [`src/nergal/container.py`](src/nergal/container.py:1) - `get_container()`, `init_database()`, `shutdown_database()`
- **Dialog processing**: [`src/nergal/dialog/manager.py`](src/nergal/dialog/manager.py:211) - `DialogManager.process_message()`
