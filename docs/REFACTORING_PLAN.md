# План рефакторинга Nergal

## Анализ текущего состояния

### Сильные стороны
- ✅ Хорошая модульная архитектура с разделением ответственности
- ✅ Использование паттернов Factory, Registry, Strategy
- ✅ Асинхронная архитектура на asyncio
- ✅ Типизация с помощью type hints
- ✅ Конфигурация через pydantic-settings
- ✅ Подробная документация архитектуры

### Проблемные области

#### 1. Дублирование кода в агентах
Все агенты в [`src/nergal/dialog/agents/`](src/nergal/dialog/agents/) имеют схожую структуру:
- Идентичные паттерны в методах `can_handle()` с keyword matching
- Дублирование логики проверки контекста
- Похожие структуры `system_prompt`

#### 2. Несогласованность констант
- [`constants.py`](src/nergal/dialog/constants.py) содержит search-related ключевые слова
- Каждый агент имеет собственный список ключевых слов (например, `NewsAgent.NEWS_KEYWORDS`)
- Это приводит к рассинхронизации и сложности поддержки

#### 3. Организация файлов
- [`web_search_agent.py`](src/nergal/dialog/web_search_agent.py) находится в корне `dialog/`, а не в `agents/`
- Несогласованное размещение файлов агентов

#### 4. Отсутствие тестов
- В проекте нет директории `tests/`
- Нет unit тестов для критических компонентов

#### 5. Жёсткая связанность
- Прямая зависимость от конкретных реализаций провайдеров
- Сложно подменять реализации для тестирования

---

## Предлагаемый план рефакторинга

### Фаза 1: Базовая консолидация (Приоритет: Высокий)

#### 1.1 Создать базовый класс для специализированных агентов

**Файл:** [`src/nergal/dialog/agents/base_specialized.py`](src/nergal/dialog/agents/base_specialized.py)

```python
"""Base class for specialized agents with common functionality."""

from abc import abstractmethod
from typing import Any
from nergal.dialog.base import BaseAgent, AgentResult, AgentType
from nergal.llm import BaseLLMProvider, LLMMessage
from nergal.dialog.styles import StyleType


class BaseSpecializedAgent(BaseAgent):
    """Base class for specialized agents with keyword-based can_handle."""
    
    # Subclasses should define their keywords
    _keywords: list[str] = []
    _context_keys: list[str] = []  # Context keys that boost confidence
    _base_confidence: float = 0.3
    _keyword_boost: float = 0.2
    _context_boost: float = 0.3
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        super().__init__(llm_provider, style_type)
    
    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        """Determine confidence based on keywords and context.
        
        Uses configurable keyword matching and context analysis.
        Subclasses can override for custom logic.
        """
        confidence = self._base_confidence
        message_lower = message.lower()
        
        # Keyword matching
        matched_keywords = sum(1 for kw in self._keywords if kw in message_lower)
        confidence += min(matched_keywords * self._keyword_boost, 0.4)
        
        # Context-based boost
        for key in self._context_keys:
            if key in context:
                confidence += self._context_boost
                break
        
        return min(confidence, 1.0)
    
    @property
    @abstractmethod
    def _agent_keywords(self) -> list[str]:
        """Return agent-specific keywords for can_handle."""
        pass
```

**Затронутые файлы:**
- [`src/nergal/dialog/agents/analysis_agent.py`](src/nergal/dialog/agents/analysis_agent.py)
- [`src/nergal/dialog/agents/comparison_agent.py`](src/nergal/dialog/agents/comparison_agent.py)
- [`src/nergal/dialog/agents/summary_agent.py`](src/nergal/dialog/agents/summary_agent.py)
- [`src/nergal/dialog/agents/news_agent.py`](src/nergal/dialog/agents/news_agent.py)
- Все остальные агенты в `agents/`

---

#### 1.2 Консолидация констант

**Файл:** [`src/nergal/dialog/constants.py`](src/nergal/dialog/constants.py) (расширить)

```python
"""Centralized constants for dialog processing."""

# =============================================================================
# Agent Keywords - Centralized keyword definitions for all agents
# =============================================================================

# Web Search Agent Keywords
SEARCH_KEYWORDS = [...]

# News Agent Keywords  
NEWS_KEYWORDS = [...]

# Analysis Agent Keywords
ANALYSIS_KEYWORDS = [
    "сравни", "проанализируй", "в чем разница", "преимущества",
    "недостатки", "плюсы", "минусы", "за и против", "выводы",
    "какой вывод", "что лучше", "что выбрать", "оцени",
]

# Comparison Agent Keywords
COMPARISON_KEYWORDS = [...]

# Summary Agent Keywords  
SUMMARY_KEYWORDS = [...]

# Clarification Agent Keywords
CLARIFICATION_KEYWORDS = [...]

# Expertise Agent Keywords
EXPERTISE_KEYWORDS = [...]

# Tech Docs Agent Keywords
TECH_DOCS_KEYWORDS = [...]

# Code Analysis Agent Keywords
CODE_ANALYSIS_KEYWORDS = [...]

# Metrics Agent Keywords
METRICS_KEYWORDS = [...]

# Knowledge Base Agent Keywords
KNOWLEDGE_BASE_KEYWORDS = [...]

# =============================================================================
# Agent Metadata
# =============================================================================

AGENT_DESCRIPTIONS: dict[str, str] = {
    "default": "общий агент для обычных разговоров...",
    "web_search": "агент для поиска информации в интернете...",
    "news": "агент для агрегации новостей...",
    # ... etc
}
```

**Преимущества:**
- Единое место для всех ключевых слов
- Легко добавлять новые агенты
- Упрощает тестирование

---

#### 1.3 Переместить web_search_agent.py

**Действие:** Переместить [`src/nergal/dialog/web_search_agent.py`](src/nergal/dialog/web_search_agent.py) → [`src/nergal/dialog/agents/web_search_agent.py`](src/nergal/dialog/agents/web_search_agent.py)

**Обновить импорты в:**
- [`src/nergal/dialog/__init__.py`](src/nergal/dialog/__init__.py)
- [`src/nergal/main.py`](src/nergal/main.py)
- [`src/nergal/dialog/agents/__init__.py`](src/nergal/dialog/agents/__init__.py)

---

### Фаза 2: Улучшение архитектуры (Приоритет: Средний)

#### 2.1 Добавить протоколы для dependency injection

**Файл:** [`src/nergal/protocols.py`](src/nergal/protocols.py)

```python
"""Protocol definitions for dependency injection."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """Protocol for LLM providers."""
    
    @property
    def provider_name(self) -> str:
        ...
    
    async def generate(
        self,
        messages: list["LLMMessage"],
        **kwargs,
    ) -> "LLMResponse":
        ...


@runtime_checkable  
class SearchProviderProtocol(Protocol):
    """Protocol for search providers."""
    
    async def search(self, request: "SearchRequest") -> "SearchResponse":
        ...


@runtime_checkable
class STTProviderProtocol(Protocol):
    """Protocol for STT providers."""
    
    @property
    def provider_name(self) -> str:
        ...
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
    ) -> str:
        ...
```

**Преимущества:**
- Возможность использовать mock-объекты в тестах
- Слабая связанность между компонентами
- Лучшая документация интерфейсов

---

#### 2.2 Улучшить обработку ошибок

**Файл:** [`src/nergal/exceptions.py`](src/nergal/exceptions.py)

```python
"""Custom exceptions for the application."""


class NergalError(Exception):
    """Base exception for all Nergal errors."""
    pass


class AgentError(NergalError):
    """Error during agent processing."""
    
    def __init__(self, agent_type: str, message: str, cause: Exception | None = None):
        self.agent_type = agent_type
        self.cause = cause
        super().__init__(f"Agent {agent_type} error: {message}")


class LLMError(NergalError):
    """Error from LLM provider."""
    pass


class SearchError(NergalError):
    """Error during web search."""
    pass


class STTError(NergalError):
    """Error during speech-to-text processing."""
    pass


class ConfigurationError(NergalError):
    """Error in configuration."""
    pass
```

---

#### 2.3 Добавить структурированное логирование

**Файл:** [`src/nergal/logging_utils.py`](src/nergal/logging_utils.py)

```python
"""Structured logging utilities."""

import logging
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any


class StructuredLogger:
    """Logger that outputs structured JSON logs."""
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    def log_agent_execution(
        self,
        agent_type: str,
        message_preview: str,
        execution_time_ms: float,
        success: bool,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log agent execution with structured data."""
        self._logger.info(
            json.dumps({
                "event": "agent_execution",
                "agent_type": agent_type,
                "message_preview": message_preview[:50],
                "execution_time_ms": execution_time_ms,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            })
        )
```

---

### Фаза 3: Тестирование (Приоритет: Высокий)

#### 3.1 Создать структуру тестов

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_agents/
│   ├── __init__.py
│   ├── test_base.py
│   ├── test_default_agent.py
│   ├── test_web_search_agent.py
│   ├── test_news_agent.py
│   └── test_dispatcher.py
├── test_dialog/
│   ├── __init__.py
│   ├── test_manager.py
│   ├── test_context.py
│   └── test_registry.py
├── test_llm/
│   ├── __init__.py
│   └── test_providers.py
├── test_web_search/
│   ├── __init__.py
│   └── test_providers.py
└── test_stt/
    ├── __init__.py
    └── test_providers.py
```

#### 3.2 Добавить pytest конфигурацию

**Файл:** [`pyproject.toml`](pyproject.toml) (дополнить)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
filterwarnings = [
    "ignore::DeprecationWarning",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
]
```

#### 3.3 Пример теста для BaseAgent

**Файл:** [`tests/test_agents/test_base.py`](tests/test_agents/test_base.py)

```python
"""Tests for base agent functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from nergal.dialog.base import BaseAgent, AgentRegistry, AgentType
from nergal.dialog.styles import StyleType


class TestAgentRegistry:
    """Tests for AgentRegistry."""
    
    def test_register_agent(self):
        """Test agent registration."""
        registry = AgentRegistry()
        agent = MagicMock(spec=BaseAgent)
        agent.agent_type = AgentType.DEFAULT
        
        registry.register(agent)
        
        assert registry.get(AgentType.DEFAULT) == agent
    
    def test_get_all_returns_all_agents(self):
        """Test getting all registered agents."""
        registry = AgentRegistry()
        agent1 = MagicMock(spec=BaseAgent, agent_type=AgentType.DEFAULT)
        agent2 = MagicMock(spec=BaseAgent, agent_type=AgentType.WEB_SEARCH)
        
        registry.register(agent1)
        registry.register(agent2)
        
        all_agents = registry.get_all()
        
        assert len(all_agents) == 2
```

---

### Фаза 4: Оптимизация производительности (Приоритет: Низкий)

#### 4.1 Добавить кэширование для can_handle

```python
from functools import lru_cache


class BaseSpecializedAgent(BaseAgent):
    """Base class with cached can_handle."""
    
    @lru_cache(maxsize=1000)
    def _get_keyword_matches(self, message_hash: int, message: str) -> int:
        """Cache keyword matching results."""
        return sum(1 for kw in self._keywords if kw in message.lower())
    
    async def can_handle(self, message: str, context: dict[str, Any]) -> float:
        confidence = self._base_confidence
        matches = self._get_keyword_matches(hash(message), message)
        confidence += min(matches * self._keyword_boost, 0.4)
        return min(confidence, 1.0)
```

#### 4.2 Оптимизировать выполнение плана

**Текущая проблема:** Последовательное выполнение агентов

**Решение:** Параллельное выполнение независимых агентов

```python
# В DialogManager._execute_plan
import asyncio


async def _execute_plan(self, plan, message, context, history):
    # Identify independent steps that can run in parallel
    independent_steps = self._identify_parallel_steps(plan)
    
    # Execute independent steps concurrently
    tasks = [
        self._execute_step(step, message, context, history)
        for step in independent_steps
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Continue with dependent steps...
```

---

### Фаза 5: Улучшение DX (Developer Experience)

#### 5.1 Добавить make-команды

**Файл:** [`Makefile`](Makefile)

```makefile
.PHONY: test lint format clean docker-build docker-up

test:
	uv run pytest tests/ -v --cov=src/nergal

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-logs:
	docker compose logs -f
```

#### 5.2 Добавить pre-commit hooks

**Файл:** [`.pre-commit-config.yaml`](.pre-commit-config.yaml)

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## Приоритеты реализации

| Фаза | Задача | Приоритет | Оценка времени |
|------|--------|-----------|----------------|
| 1.1 | Базовый класс для агентов | Высокий | 4 часа |
| 1.2 | Консолидация констант | Высокий | 2 часа |
| 1.3 | Перемещение web_search_agent | Низкий | 30 мин |
| 2.1 | Протоколы для DI | Средний | 3 часа |
| 2.2 | Обработка ошибок | Средний | 2 часа |
| 2.3 | Структурированное логирование | Низкий | 2 часа |
| 3.x | Тестирование | Высокий | 8-12 часов |
| 4.x | Оптимизация | Низкий | 4-6 часов |
| 5.x | DX улучшения | Средний | 1-2 часа |

---

## Рекомендуемый порядок выполнения

1. **Спринт 1 (Неделя 1):**
   - [ ] 1.2 Консолидация констант
   - [ ] 1.3 Перемещение web_search_agent
   - [ ] 3.1-3.3 Базовая структура тестов

2. **Спринт 2 (Неделя 2):**
   - [ ] 1.1 Базовый класс для агентов
   - [ ] Рефакторинг существующих агентов
   - [ ] 2.2 Улучшенная обработка ошибок

3. **Спринт 3 (Неделя 3):**
   - [ ] 2.1 Протоколы для DI
   - [ ] Покрытие тестами основных компонентов
   - [ ] 5.1-5.2 DX улучшения

4. **Спринт 4 (опционально):**
   - [ ] 4.1-4.2 Оптимизация производительности
   - [ ] 2.3 Структурированное логирование
   - [ ] Дополнительные тесты

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Регрессия функциональности | Средняя | Высокое | Комплексные тесты перед рефакторингом |
| Увеличение времени выполнения | Низкая | Среднее | Бенчмарки до/после |
| Сложность миграции | Средняя | Среднее | Поэтапный подход, backward compatibility |

---

## Метрики успеха

- ✅ Покрытие тестами > 80%
- ✅ Уменьшение дублирования кода на 30%+
- ✅ Время выполнения тестов < 30 секунд
- ✅ Все агенты используют общий базовый класс
- ✅ Единая точка конфигурации ключевых слов
