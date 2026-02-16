# Анализ приложения Nergal и план рефакторинга

## Обзор проекта

**Nergal** — Telegram AI-бот с интеграцией LLM, системой специализированных агентов, веб-поиском и памятью пользователей.

### Технологический стек
- Python 3.12
- python-telegram-bot 22.0+
- pydantic-settings для конфигурации
- PostgreSQL + asyncpg
- Prometheus + Grafana для мониторинга
- Docker контейнеризация

---

## ✅ Выполненные изменения (Sprint 1 & 2)

### Sprint 1: Очистка мёртвого код ✅

1. **Удалён `src/nergal/protocols.py`** (220 строк)
   - Файл не использовался нигде в проекте

2. **Интегрирован `src/nergal/exceptions.py`** в кодовую базу
   - Добавлены импорты в LLM, WebSearch, STT модули
   - Добавлен недостающий класс `SearchRateLimitError`

3. **Добавлены тесты**:
   - `tests/test_database/test_repositories.py` — 28 тестов для репозиториев
   - `tests/test_memory/test_service.py` — 20 тестов для MemoryService

### Sprint 2: Конфигурируемая регистрация агентов ✅

1. **Добавлен `AgentSettings`** в [`src/nergal/config.py`](src/nergal/config.py)
   - Каждый агент можно включить/выключить через переменные окружения
   - Пример: `AGENTS_NEWS_ENABLED=true`, `AGENTS_FACT_CHECK_ENABLED=true`

2. **Создан [`src/nergal/dialog/agent_loader.py`](src/nergal/dialog/agent_loader.py)**
   - Функция `register_configured_agents()` для регистрации агентов по конфигурации
   - Фабричные функции для создания каждого агента

3. **Обновлён [`src/nergal/main.py`](src/nergal/main.py)**
   - Использует `register_configured_agents()` вместо хардкода
   - Удалён неиспользуемый импорт `WebSearchAgent`

---

## 1. Неиспользуемые файлы и мёртвый код

### Статус после рефакторинга

#### 1.1 ~~Полностью неиспользуемые файлы~~ ✅ ИСПРАВЛЕНО

| Файл | Строк | Статус |
|------|-------|--------|
| ~~`src/nergal/protocols.py`~~ | ~~220~~ | ✅ Удалён |
| `src/nergal/exceptions.py` | 384 | ✅ Интегрирован в кодовую базу |

#### 1.2 Специализированные агенты — теперь конфигурируемые ✅

Все агенты теперь можно включить через переменные окружения:

| Агент | Переменная окружения | По умолчанию |
|-------|---------------------|--------------|
| `WebSearchAgent` | `AGENTS_WEB_SEARCH_ENABLED` | `true` |
| `NewsAgent` | `AGENTS_NEWS_ENABLED` | `false` |
| `AnalysisAgent` | `AGENTS_ANALYSIS_ENABLED` | `false` |
| `FactCheckAgent` | `AGENTS_FACT_CHECK_ENABLED` | `false` |
| `ComparisonAgent` | `AGENTS_COMPARISON_ENABLED` | `false` |
| `SummaryAgent` | `AGENTS_SUMMARY_ENABLED` | `false` |
| `CodeAnalysisAgent` | `AGENTS_CODE_ANALYSIS_ENABLED` | `false` |
| `MetricsAgent` | `AGENTS_METRICS_ENABLED` | `false` |
| `ExpertiseAgent` | `AGENTS_EXPERTISE_ENABLED` | `false` |
| `ClarificationAgent` | `AGENTS_CLARIFICATION_ENABLED` | `false` |
| `KnowledgeBaseAgent` | `AGENTS_KNOWLEDGE_BASE_ENABLED` | `false` |
| `TechDocsAgent` | `AGENTS_TECH_DOCS_ENABLED` | `false` |

#### 1.3 Дублирование констант

Константы `AGENT_DESCRIPTIONS` дублируются:
- [`src/nergal/dialog/constants.py:339-366`](src/nergal/dialog/constants.py:339)
- [`src/nergal/dialog/dispatcher_agent.py:25-51`](src/nergal/dialog/dispatcher_agent.py:25)

---

## 2. Сильные стороны решения

### 2.1 Архитектура
- **Модульная структура** — чёткое разделение ответственности между модулями
- **Агентная система** — гибкая диспетчеризация запросов через `DispatcherAgent`
- **Провайдер-паттерн** — абстракции для LLM, STT, WebSearch с возможностью расширения
- **Repository pattern** — разделение логики доступа к данным

### 2.2 Технические решения
- **Современный Python** — type hints, dataclasses, async/await, Pydantic v2
- **Конфигурация через env** — pydantic-settings с валидацией
- **Мониторинг из коробки** — Prometheus metrics, health checks, structured logging
- **Docker-ready** — docker-compose с опциональным стеком мониторинга

### 2.3 Качество кода
- **Документация** — docstrings, README, детальные docs/
- **Тесты** — pytest с fixtures, покрытие основных компонентов
- **Линтинг** — Ruff для проверки кода

### 2.4 Функциональность
- **Система памяти** — краткосрочная (контекст) и долгосрочная (профиль пользователя)
- **Speech-to-Text** — локальный Whisper
- **Веб-поиск** — интеграция с MCP
- **Admin interface** — веб-панель для управления пользователями

---

## 3. Слабые стороны и области улучшения

### 3.1 Мёртвый код (критично)

| Проблема | Влияние |
|----------|---------|
| `protocols.py` не используется | 220 строк мёртвого кода |
| `exceptions.py` не используется | 384 строк мёртвого кода |
| 11 агентов не регистрируются | ~4000 строк неиспользуемого кода |

### 3.2 Покрытие тестами (средний приоритет)

| Модуль | Строк кода | Тесты |
|--------|------------|-------|
| `src/nergal/` | ~14,473 | 1,580 |
| `database/repositories.py` | 818 | 0 |
| `memory/service.py` | 453 | 0 |
| `web_search/zai_mcp_http.py` | 403 | 0 |
| `admin/server.py` | 449 | 0 |

**Покрытие**: ~11% (очень низкое)

### 3.3 Организация кода

| Файл | Строк | Проблема |
|------|-------|----------|
| `main.py` | 707 | Слишком много ответственности |
| `repositories.py` | 818 | Монолитный файл |
| `dispatcher_agent.py` | 468 | Сложная логика планирования |

### 3.4 Ограниченная расширяемость

- Только один LLM провайдер (Zai) реализован
- Только один STT провайдер (local Whisper)
- Только один WebSearch провайдер (Zai MCP)

### 3.5 Безопасность

- Хардкод секретов в примерах (`nergal_secret`)
- Нет rate limiting
- Нет валидации входных данных

### 3.6 Типизация

- Использование `Any` в критичных местах
- Нет настроенного mypy
- Protocols определены, но не используются

---

## 4. План рефакторинга

### Фаза 1: Очистка мёртвого кода (Приоритет: Высокий)

#### 1.1 Удаление неиспользуемых файлов
```bash
# Удалить или переместить в архив
rm src/nergal/protocols.py
rm src/nergal/exceptions.py
```

**Альтернатива**: Интегрировать `exceptions.py` в кодовую базу для улучшения обработки ошибок.

#### 1.2 Решение по специализированным агентам

**Вариант A**: Удалить неиспользуемые агенты
- Удалить файлы из `src/nergal/dialog/agents/`
- Обновить `__init__.py`

**Вариант B**: Создать механизм регистрации
```python
# В config.py добавить
class AgentSettings(BaseSettings):
    enabled_agents: list[str] = ["default", "web_search"]

# В main.py
for agent_name in settings.agents.enabled_agents:
    if agent_name == "web_search" and web_search_provider:
        manager.register_agent(web_search_agent)
```

**Рекомендация**: Вариант B — сохраняет инвестиции в разработку агентов.

### Фаза 2: Улучшение тестируемости (Приоритет: Высокий)

#### 2.1 Добавить тесты для критичных модулей

```
tests/
├── test_database/
│   ├── test_repositories.py    # UserRepository, ProfileRepository
│   └── test_connection.py
├── test_memory/
│   ├── test_service.py
│   └── test_extraction.py
├── test_web_search/
│   └── test_zai_mcp_http.py
└── test_admin/
    └── test_server.py
```

#### 2.2 Настроить pytest-cov
```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "-v --tb=short --cov=nergal --cov-report=term-missing"
```

### Фаза 3: Рефакторинг main.py (Приоритет: Средний)

#### 3.1 Вынести компоненты

```
src/nergal/
├── bot/
│   ├── __init__.py
│   ├── application.py    # BotApplication class
│   ├── handlers.py       # Command handlers
│   └── middleware.py     # Auth, logging middleware
├── main.py               # Только entry point
```

#### 3.2 Упростить main.py
```python
# main.py должен быть ~50 строк
async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    
    app = BotApplication.create()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Фаза 4: Улучшение обработки ошибок (Приоритет: Средний)

#### 4.1 Интегрировать исключения
```python
# Заменить generic exceptions на кастомные
from nergal.exceptions import LLMError, AgentError, ConfigurationError

async def process_message(...):
    try:
        result = await agent.process(message, context)
    except LLMError as e:
        logger.error("LLM failed", error=e)
        raise AgentError(f"Agent failed: {e}", agent_type=agent.agent_type)
```

#### 4.2 Добавить retry логику
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def generate_response(...):
    ...
```

### Фаза 5: Типизация (Приоритет: Низкий)

#### 5.1 Настроить mypy
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
```

#### 5.2 Заменить Any на конкретные типы
```python
# Было
def process(self, context: dict[str, Any]) -> Any:

# Стало
from typing import TypedDict

class AgentContext(TypedDict):
    user_id: int
    history: list[LLMMessage]
    metadata: dict[str, str]

def process(self, context: AgentContext) -> AgentResult:
```

### Фаза 6: Документация (Приоритет: Низкий)

#### 6.1 Добавить архитектурные диаграммы
- Mermaid диаграммы в README
- ADR (Architecture Decision Records)

#### 6.2 API документация
- OpenAPI схему для admin server
- Документацию для интеграции

---

## 5. Метрики успеха

| Метрика | Текущее | Цель |
|---------|---------|------|
| Покрытие тестами | ~11% | >70% |
| Строк мёртвого кода | ~4,600 | 0 |
| Cyclomatic complexity main.py | Высокая | <10 |
| Время загрузки | - | <5s |
| mypy strict | ❌ | ✅ |

---

## 6. Приоритизированный список задач

### Sprint 1 (Неделя 1-2) ✅ ЗАВЕРШЁН
- [x] Удалить `protocols.py`
- [x] Решить судьбу `exceptions.py` (интегрировать или удалить) — интегрирован
- [x] Добавить тесты для `database/repositories.py`
- [x] Добавить тесты для `memory/service.py`

### Sprint 2 (Неделя 3-4) ✅ ЗАВЕРШЁН
- [x] Создать механизм регистрации агентов — создан `agent_loader.py`
- [ ] Рефакторинг `main.py` — вынести BotApplication
- [ ] Добавить тесты для `web_search/`

### Sprint 3 (Неделя 5-6)
- [ ] Настроить mypy strict
- [ ] Добавить retry логику
- [ ] Интегрировать кастомные исключения

### Backlog
- [ ] Добавить OpenAI провайдер для LLM
- [ ] Добавить OpenAI провайдер для STT
- [ ] API документация для admin server
- [ ] Архитектурные диаграммы

---

## 7. Заключение

Nergal — хорошо спроектированный Telegram бот с современной архитектурой. Основные проблемы связаны с накопившимся мёртвым кодом и низким покрытием тестами. Рефакторинг следует начинать с очистки кодовой базы и добавления тестов для критичных модулей.

**Оценка качества кода**: 7/10
- Архитектура: 8/10
- Тестируемость: 4/10
- Документация: 8/10
- Поддерживаемость: 6/10
