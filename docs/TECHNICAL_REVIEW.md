# Technical Review - Nergal Bot

This document tracks technical debt, code quality issues, and completed improvements.

## Completed Improvements

### ✅ DI Container Implementation (2026-02-24)

**Status**: Completed

**Problem**: The project used manual dependency management with singleton patterns scattered throughout the codebase. Dependencies were created ad-hoc in `BotApplication` class, making testing difficult and violating the Dependency Inversion Principle.

**Solution**: Implemented a centralized Dependency Injection (DI) container using `dependency-injector` library.

**Changes Made**:

1. **Added dependency-injector to pyproject.toml**
   - Added `dependency-injector>=4.41.0` to dependencies

2. **Created [`src/nergal/container.py`](src/nergal/container.py)**
   - New module with `Container` class extending `containers.DeclarativeContainer`
   - Centralized management of all application dependencies:
     - `settings` - Application configuration (Singleton)
     - `llm_provider` - LLM provider instance (Factory)
     - `stt_provider` - Speech-to-text provider (Singleton)
     - `web_search_provider` - Web search provider (Singleton)
     - `database` - Database connection (Singleton)
     - `memory_service` - Memory service (Singleton)
     - `dialog_manager` - Dialog manager with all dependencies (Singleton)
     - `metrics_server` - Prometheus metrics server (Singleton)
   - Factory functions for each dependency with proper initialization
   - Global container instance management with `get_container()`, `init_container()`
   - Testing support with `override_container()` and `reset_container()`

3. **Refactored [`src/nergal/main.py`](src/nergal/main.py)**
   - `BotApplication` class now delegates to DI container
   - Removed manual dependency creation methods:
     - `_create_dialog_manager()`
     - `_create_web_search_provider()`
     - `_create_stt_provider()`
   - Properties now get dependencies from container:
     - `dialog_manager` → `container.dialog_manager()`
     - `web_search_provider` → `container.web_search_provider()`
     - `stt_provider` → `container.stt_provider()`
   - `main()` function initializes container at startup with `init_container()`

**Benefits**:
- **Testability**: Dependencies can be easily mocked by overriding the container
- **Single source of truth**: All dependency creation logic in one place
- **Loose coupling**: Components depend on abstractions, not concrete implementations
- **Lifecycle management**: Clear control over singleton vs factory patterns
- **Async support**: Works seamlessly with async initialization patterns

**Usage Example**:
```python
# Production usage
from nergal.container import init_container

container = init_container()
dialog_manager = container.dialog_manager()

# Testing with mocks
from nergal.container import override_container, reset_container
from unittest.mock import Mock

mock_container = Container()
mock_container.dialog_manager.override(Mock())
override_container(mock_container)

# ... run tests ...

reset_container()
```

---

## Pending Improvements

### Database Connection Pool Management

**Status**: Pending

**Problem**: Database connection pool is managed with global variables in [`src/nergal/database/connection.py`](src/nergal/database/connection.py).

**Proposed Solution**: Integrate database pool lifecycle into DI container with async initialization.

---

### Repository Pattern Enhancement

**Status**: Pending

**Problem**: Repositories in [`src/nergal/database/repositories.py`](src/nergal/database/repositories.py) create database connections internally.

**Proposed Solution**: Inject database connection through DI container constructor injection.

---

## Architecture Notes

### Current DI Container Structure

```
Container
├── config (Configuration)
├── settings (Singleton) ──────────────────┐
├── llm_provider (Factory)                 │
├── stt_provider (Singleton)               │
├── web_search_provider (Singleton)        │
├── database (Singleton)                   │
├── memory_service (Singleton)             │
├── dialog_manager (Singleton) ◄───────────┘
│   └── Depends on: settings, llm_provider, web_search_provider, memory_service
└── metrics_server (Singleton)
```

### Dependency Flow

```
main.py
  └── BotApplication
        └── Container
              ├── settings()
              ├── dialog_manager()
              │     └── DialogManager(llm_provider, style_type, memory_service)
              ├── web_search_provider()
              │     └── ZaiMcpHttpSearchProvider(api_key, mcp_url, timeout)
              ├── stt_provider()
              │     └── LocalWhisperProvider(model, device, compute_type)
              ├── memory_service()
              │     └── MemoryService()
              └── metrics_server()
                    └── MetricsServer(port)
```
