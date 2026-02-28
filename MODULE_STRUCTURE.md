# Module Organization Guide

This document explains how to organize reusable modules within the Nergal project.

## Philosophy

When a component grows large enough to be useful independently, consider extracting it as a separate module within the project. This provides:

1. **Clear boundaries** - Module has a well-defined API
2. **Reusability** - Can be used in other projects
3. **Maintainability** - Easier to test and reason about
4. **Evolution path** - Can be extracted to separate package/repo later

## Decision Criteria

When should a component be extracted as a separate module?

✅ **Extract when:**
- Component has >3 files
- Component has its own configuration
- Component could be useful in other contexts
- Component tests need to be isolated
- Component has a clear API

❌ **Keep integrated when:**
- Component is small (<3 files)
- Component is tightly coupled to main app
- Component is specific to this domain (e.g., telegram handlers)

## Directory Structure

```
src/
├── nergal/              # Main application
└── stt_lib/             # Reusable module
    ├── __init__.py        # Public API
    ├── config.py          # Module-specific config
    ├── base.py            # Abstract base classes
    ├── factory.py         # Factory pattern for instantiation
    ├── exceptions.py       # Module-specific exceptions
    ├── utils.py           # Utility functions (if any)
    └── providers/         # Implementations
        ├── __init__.py
        └── provider_1.py
```

## Module API Design

### Public API (`__init__.py`)

Export only what external consumers need:

```python
# Good: Clean, minimal API
from stt_lib import (
    create_stt_provider,    # Factory
    BaseSTTProvider,         # Abstract base
    STTConfig,               # Configuration
    convert_ogg_to_wav,      # Utility function
    STTError,                # Base exception
)

# Avoid: Internal implementation details
# Don't export: _internal_utils, _BaseInternalClass
```

### Configuration

Use `pydantic-settings` for configuration with environment variable support:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class ModuleConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MODULE_",  # Prefix for env vars
        env_file=".env",
    )

    field: str = "default_value"
```

### Exceptions

Define module-specific exceptions that inherit from a base module exception:

```python
class ModuleError(Exception):
    """Base exception for this module."""
    def __init__(self, message, cause=None):
        self.message = message
        self.cause = cause
        super().__init__(message)

class SpecificError(ModuleError):
    """Specific error type."""
    pass
```

## Integration with Main App

### Import Pattern

The main app imports from the module using clean imports:

```python
# src/nergal/container.py
from stt_lib import BaseSTTProvider  # Only import what's needed
from stt_lib import create_stt_provider

def _create_stt_provider(settings):
    return create_stt_provider(
        provider_type=settings.stt.provider,
        model=settings.stt.model,
    )
```

### DI Container Integration

Use dependency injection to create module instances:

```python
# src/nergal/container.py
class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(lambda: _load_settings())

    # Module provider - configured via settings
    module_provider = providers.Singleton(
        lambda settings: _create_module_provider(settings),
        settings=settings,
    )

def _create_module_provider(settings):
    from stt_lib import create_module
    return create_module(config=settings.module)
```

## Testing

### Test Structure

Create isolated tests for the module:

```
tests/
├── test_stt_lib/         # Module-specific tests
│   ├── conftest.py        # Shared fixtures
│   ├── test_base.py        # Base class tests
│   ├── test_factory.py     # Factory tests
│   ├── test_config.py      # Configuration tests
│   ├── test_audio.py       # Audio utilities tests
│   └── test_providers/    # Provider implementation tests
│       └── test_local_whisper.py
└── test_nergal/          # Main app tests
```

### Fixtures

Define fixtures in `conftest.py`:

```python
# tests/test_stt_lib/conftest.py
import pytest

@pytest.fixture
def module_config():
    from stt_lib import ModuleConfig
    return ModuleConfig(
        field1="value1",
        field2="value2",
    )

@pytest.fixture
def mock_audio_data():
    return b"fake audio data"
```

### Test Isolation

Module tests should NOT import from the main app:

```python
# Good: Tests only import from module under test
from stt_lib import create_stt_provider
from stt_lib.config import STTConfig

# Bad: Tests import from main app
from nergal.container import Container  # Don't do this!
```

## Pyproject.toml Configuration

Include both packages in the build:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/nergal", "src/stt_lib"]
```

## Migration Path: Extract to Separate Package

When the module grows larger or needs wider adoption:

### Phase 1: Separate Repository

```bash
# Clone or move module to separate repo
git remote add module-origin git@github.com:user/module.git
git subtree push --prefix=src/stt_lib module-origin main
```

### Phase 2: Add to Requirements

```bash
# In consuming projects
pip install https://github.com/user/module.git
```

### Phase 3: Publish to PyPI (Optional)

```bash
# In module repo
python -m build
twine upload dist/*
```

## Example: stt_lib

The STT library demonstrates this pattern:

**Before:**
```
src/nergal/
└── stt/
    ├── base.py
    ├── factory.py
    ├── audio_utils.py
    └── providers/
```

**After:**
```
src/
├── nergal/              # Main app
│   ├── container.py      # Imports: from stt_lib import BaseSTTProvider
│   └── handlers/
│       └── messages.py  # Imports: from stt_lib import convert_ogg_to_wav
└── stt_lib/             # Reusable module
    ├── __init__.py        # Clean public API
    ├── base.py
    ├── factory.py
    ├── audio.py
    ├── config.py
    ├── exceptions.py
    └── providers/
```

**Benefits achieved:**
- ✅ Clean imports (`from stt_lib import ...`)
- ✅ Independent configuration (`STTConfig`)
- ✅ Isolated exceptions (not in nergal.exceptions)
- ✅ Separate tests (`tests/test_stt_lib/`)
- ✅ Documentation ([README_STT.md](README_STT.md))
- ✅ Ready to extract to separate repo

## Checklist for Extracting a Module

Before extracting a component as a separate module:

- [ ] Has clean, minimal public API
- [ ] Has its own configuration class
- [ ] Has module-specific exceptions
- [ ] Has comprehensive tests
- [ ] Tests don't depend on main app
- [ ] Has documentation (README)
- [ ] Updated main app imports
- [ ] Updated pyproject.toml
- [ ] Removed old files from main app
- [ ] Verified tests still pass

## Future Modules to Consider

Potential candidates for extraction:

| Component | Status | Notes |
|-----------|---------|--------|
| LLM providers | Integrated | Already has base class + factory |
| Web search | Consider | Could be extracted like STT |
| Memory service | Evaluate | Potentially useful for other bots |
| Monitoring | Evaluate | Metrics collection could be reusable |
