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

### ✅ Repository Pattern Enhancement (2026-02-24)

**Status**: Completed

**Problem**: Repositories in [`src/nergal/database/repositories.py`](src/nergal/database/repositories.py) created database connections internally using `get_database()` singleton, making testing difficult and violating DI principles.

**Solution**: Integrated repositories with DI container using constructor injection pattern.

**Changes Made**:

1. **Updated [`src/nergal/container.py`](src/nergal/container.py)**
   - Added repository providers as Factory providers:
     - `user_repository` - Factory for `UserRepository`
     - `profile_repository` - Factory for `ProfileRepository`
     - `conversation_repository` - Factory for `ConversationRepository`
     - `web_search_telemetry_repository` - Factory for `WebSearchTelemetryRepository`
     - `user_integration_repository` - Factory for `UserIntegrationRepository`
   - Each repository receives `DatabaseConnection` via constructor injection
   - Added factory functions for each repository type

2. **Updated [`src/nergal/handlers/commands.py`](src/nergal/handlers/commands.py)**
   - `todoist_token_command()` now uses `container.user_integration_repository()`
   - `todoist_disconnect_command()` now uses `container.user_integration_repository()`

3. **Updated [`src/nergal/monitoring/health.py`](src/nergal/monitoring/health.py)**
   - `check_web_search_health()` now uses `container.web_search_telemetry_repository()`
   - `check_web_search_health_detailed()` now uses `container.web_search_telemetry_repository()`

4. **Updated [`src/nergal/dialog/agents/todoist_agent.py`](src/nergal/dialog/agents/todoist_agent.py)**
   - `_get_integration_repo()` now uses `container.user_integration_repository()`
   - Removed direct import of `UserIntegrationRepository`

5. **Updated [`src/nergal/auth.py`](src/nergal/auth.py)**
   - `AuthorizationService.__init__()` now uses `container.user_repository()`
   - Removed direct imports of `get_database` and `UserRepository`

6. **Updated [`src/nergal/admin/server.py`](src/nergal/admin/server.py)**
   - All handlers now use DI container for repositories:
     - `handle_users_dashboard()` uses `container.conversation_repository()`
     - `handle_telemetry_dashboard()` uses `container.web_search_telemetry_repository()`
     - `handle_telemetry_failures()` uses `container.web_search_telemetry_repository()`
     - `handle_telemetry_empty()` uses `container.web_search_telemetry_repository()`
     - `handle_telemetry_stats()` uses `container.web_search_telemetry_repository()`
     - `handle_telemetry_detail()` uses `container.web_search_telemetry_repository()`
     - `handle_user_allow()` uses `container.user_repository()`
   - Removed direct imports of repository classes

7. **Updated [`src/nergal/web_search/zai_mcp_http.py`](src/nergal/web_search/zai_mcp_http.py)**
   - `_get_telemetry_repo()` now uses `container.web_search_telemetry_repository()`

**Benefits**:
- **Testability**: Repositories can be easily mocked by overriding the container
- **Consistency**: All dependencies are managed through the same DI container
- **Loose coupling**: Components depend on abstractions through container, not concrete implementations
- **Single source of truth**: All repository creation logic in one place

**Usage Example**:
```python
# Production usage
from nergal.container import get_container

container = get_container()
user_repo = container.user_repository()
user = await user_repo.get_by_id(123)

# Testing with mocks
from nergal.container import override_container, reset_container
from unittest.mock import AsyncMock

container = Container()
mock_repo = AsyncMock()
container.user_repository.override(lambda: mock_repo)
override_container(container)

# ... run tests ...

reset_container()
```

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
├── Repositories (Factory)                 │
│   ├── user_repository                    │
│   ├── profile_repository                 │
│   ├── conversation_repository            │
│   ├── web_search_telemetry_repository    │
│   └── user_integration_repository        │
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
              │     └── MemoryService(db=database)
              ├── Repositories
              │     ├── user_repository()
              │     │     └── UserRepository(db=database)
              │     ├── profile_repository()
              │     │     └── ProfileRepository(db=database)
              │     ├── conversation_repository()
              │     │     └── ConversationRepository(db=database)
              │     ├── web_search_telemetry_repository()
              │     │     └── WebSearchTelemetryRepository(db=database)
              │     └── user_integration_repository()
              │           └── UserIntegrationRepository(db=database)
              └── metrics_server()
                    └── MetricsServer(port)
```
