# Technical Review - Nergal Bot

This document tracks technical debt, code quality issues, and completed improvements.

## Completed Improvements

### ✅ main.py Refactoring - Handler Extraction (2026-02-24)

**Status**: Completed

**Problem**: The [`src/nergal/main.py`](src/nergal/main.py) file was 913 lines long and contained multiple concerns mixed together:
- Command handlers (`/start`, `/help`, `/status`, `/todoist_token`, `/todoist_disconnect`)
- Message handlers (text and voice)
- Group chat logic (`should_respond_in_group`, `clean_message_text`)
- Bot application lifecycle management
- Main entry point

This made the file difficult to maintain, test, and understand.

**Solution**: Extracted handlers into a dedicated module with clear separation of concerns.

**Changes Made**:

1. **Created [`src/nergal/handlers/__init__.py`](src/nergal/handlers/__init__.py)**
   - New module for all Telegram bot handlers
   - Clean exports for all handler functions

2. **Created [`src/nergal/handlers/commands.py`](src/nergal/handlers/commands.py)**
   - Extracted all command handlers:
     - `start_command` - Handles `/start`
     - `help_command` - Handles `/help`
     - `status_command` - Handles `/status` for health checks
     - `todoist_token_command` - Handles `/todoist_token` for Todoist integration
     - `todoist_disconnect_command` - Handles `/todoist_disconnect`

3. **Created [`src/nergal/handlers/messages.py`](src/nergal/handlers/messages.py)**
   - Extracted message handlers:
     - `handle_message` - Processes text messages
     - `handle_voice` - Processes voice messages with STT
   - Extracted utility functions:
     - `should_respond_in_group` - Group chat response logic
     - `clean_message_text` - Removes bot mentions from messages

4. **Refactored [`src/nergal/main.py`](src/nergal/main.py)**
   - Reduced from 913 lines to 371 lines (59% reduction)
   - Now imports handlers from `nergal.handlers`
   - Contains only:
     - `BotApplication` class (lifecycle management)
     - `HttpxLogFilter` class (logging utility)
     - `configure_logging` function
     - `main` entry point
   - Cleaner imports and better organization

**Benefits**:
- **Maintainability**: Each file has a single responsibility
- **Testability**: Handlers can be tested independently
- **Readability**: Smaller files are easier to understand
- **Reusability**: Handlers can be imported and reused

**File Structure After Refactoring**:
```
src/nergal/
├── main.py                    # BotApplication + entry point (371 lines)
├── handlers/
│   ├── __init__.py           # Module exports (27 lines)
│   ├── commands.py           # Command handlers (156 lines)
│   └── messages.py           # Message handlers + utilities (435 lines)
└── ...
```

---

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

### ✅ Database Connection Pool Management (2026-02-24)

**Status**: Completed

**Problem**: Database connection pool was managed with global variables in [`src/nergal/database/connection.py`](src/nergal/database/connection.py), making testing difficult and violating DI principles.

**Solution**: Integrated database pool lifecycle into DI container with async initialization.

**Changes Made**:

1. **Refactored [`src/nergal/database/connection.py`](src/nergal/database/connection.py)**
   - Removed global `_pool` and `_db_connection` singleton variables
   - `DatabaseConnection` class now manages its own pool internally
   - Added `is_connected` property to check pool status
   - Added safety checks in `connect()` and `disconnect()` for idempotency
   - Legacy functions (`create_pool`, `get_pool`, `close_pool`, `get_connection`, `get_database`) marked as deprecated with warnings
   - Clear separation between class-based DI approach and deprecated global functions

2. **Updated [`src/nergal/container.py`](src/nergal/container.py)**
   - Added async lifecycle management functions:
     - `init_database()` - Initialize connection pool at startup
     - `shutdown_database()` - Gracefully close connections at shutdown
   - Updated `_create_memory_service()` to accept `database` parameter for proper DI
   - Updated `memory_service` provider to inject database dependency

3. **Updated [`src/nergal/main.py`](src/nergal/main.py)**
   - `initialize_memory()` now uses `init_database()` from container
   - `shutdown_memory()` now uses `shutdown_database()` from container
   - `_run_database_migrations()` accepts database instance as parameter

**Benefits**:
- **Testability**: Database connections can be easily mocked in tests
- **Lifecycle management**: Clear control over connection pool initialization/shutdown
- **DI integration**: Database is now properly integrated with the DI container
- **Backward compatibility**: Legacy functions still work with deprecation warnings

**Usage Example**:
```python
# Production usage (through DI container)
from nergal.container import get_container, init_database, shutdown_database

# At startup
await init_database()

# Get database from container
container = get_container()
db = container.database()

# At shutdown
await shutdown_database()

# Testing with mocks
from nergal.container import override_container, reset_container
from unittest.mock import AsyncMock

container = Container()
mock_db = AsyncMock()
container.database.override(mock_db)
override_container(container)

# ... run tests ...

reset_container()
```

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
