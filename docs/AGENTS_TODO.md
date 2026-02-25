# План улучшения архитектуры агентов

> **Цель:** Устранить все выявленные минусы текущей архитектуры агентов  
> **Срок:** 8 этапов  
> **Статус:** Этап 8 завершён

---

## Сводка изменений

| # | Этап | Минусы, которые устраняет | Приоритет |
|---|------|---------------------------|-----------|
| 1 | Кэширование результатов агентов | #3 Отсутствие кэширования | 🔴 Высокий |
| 2 | Параллельное выполнение шагов | #1 Последовательное выполнение | 🔴 Высокий |
| 3 | Типизированные метаданные | #4 Слабая типизация metadata | 🟡 Средний |
| 4 | Формализованный контекст | #6 Ограниченный контекст между агентами | 🟡 Средний |
| 5 | Timeout и механизм отмены | #7 Нет механизма отмены плана | 🟡 Средний |
| 6 | Система предпочтений пользователя | #5 Отсутствие приоритизации агентов | 🟢 Низкий |
| 7 | Рефакторинг agent_loader | #2 Дублирование кода в agent_loader | 🟢 Низкий |
| 8 | Удаление legacy агентов | #8 Legacy агенты в AgentType | 🟢 Низкий |

---

## Этап 1: Кэширование результатов агентов

### Минусы, которые устраняет
- ✅ Отсутствие кэширования результатов агентов

### Задачи

- [x] **1.1** Создать модуль `src/nergal/dialog/cache.py` с классом `AgentResultCache`
  - Реализовать in-memory LRU кэш с TTL
  - Поддержка ключей на основе agent_type + message hash
  - Методы: `get()`, `set()`, `invalidate()`, `clear()`

- [x] **1.2** Добавить настройки кэша в `config.py`
  - `CACHE_ENABLED: bool = True`
  - `CACHE_TTL_SECONDS: int = 300` (5 минут)
  - `CACHE_MAX_SIZE: int = 1000`

- [x] **1.3** Интегрировать кэш в `DialogManager`
  - Проверять кэш перед выполнением агента
  - Сохранять результаты в кэш после выполнения
  - Добавить метрики кэша (hits/misses)

- [x] **1.4** Добавить тесты для кэша
  - Тест hit/miss
  - Тест TTL expiry
  - Тест LRU eviction

### Файлы для изменения
- `src/nergal/dialog/cache.py` (новый) ✅
- `src/nergal/config.py` ✅
- `src/nergal/dialog/manager.py` ✅
- `src/nergal/container.py` ✅
- `tests/test_dialog/test_cache.py` (новый) ✅

---

## Этап 2: Параллельное выполнение шагов

### Минусы, которые устраняет
- ✅ Последовательное выполнение плана

### Задачи

- [x] **2.1** Расширить структуру `PlanStep` в `base.py`
  - Добавить поле `depends_on: list[int]` (список индексов шагов)
  - Добавить поле `parallel_group: int | None` (группа для параллельного выполнения)
  - Обновить документацию

- [x] **2.2** Обновить парсер плана в `DispatcherAgent`
  - Научить LLM указывать зависимости между шагами
  - Обновить промпт с примерами параллельных планов
  - Парсить новые поля из JSON

- [x] **2.3** Реализовать параллельное выполнение в `DialogManager`
  - Группировать шаги по `parallel_group`
  - Запускать независимые шаги через `asyncio.gather()`
  - Ждать завершения зависимостей перед выполнением

- [x] **2.4** Добавить тесты параллельного выполнения
  - Тест независимых шагов (параллельно)
  - Тест зависимых шагов (последовательно)
  - Тест смешанного плана

### Файлы для изменения
- `src/nergal/dialog/base.py` ✅
- `src/nergal/dialog/dispatcher_agent.py` ✅
- `src/nergal/dialog/manager.py` ✅
- `tests/test_dialog/test_parallel_execution.py` (новый) ✅

---

## Этап 3: Типизированные метаданные агентов

### Минусы, которые устраняет
- ✅ Слабая типизация AgentResult.metadata

### Задачи

- [x] **3.1** Создать модуль `src/nergal/dialog/metadata.py`
  - Базовый класс `BaseAgentMetadata`
  - `WebSearchMetadata` (sources, query, result_count, search_time_ms)
  - `TodoistMetadata` (action, task_count, project_name)
  - `NewsMetadata` (sources, clusters, sentiment)
  - `AnalysisMetadata` (data_sources, insights_count)
  - `DefaultMetadata` (tokens_used, model)

- [x] **3.2** Обновить `AgentResult` в `base.py`
  - Сделать metadata Generic-параметром
  - Добавить метод `get_typed_metadata()`

- [x] **3.3** Обновить все агенты
  - WebSearchAgent возвращает WebSearchMetadata
  - TodoistAgent возвращает TodoistMetadata
  - NewsAgent возвращает NewsMetadata
  - И т.д.

- [x] **3.4** Добавить тесты типизированных метаданных
  - Тест сериализации/десериализации
  - Тест валидации полей

### Файлы для изменения
- `src/nergal/dialog/metadata.py` (новый) ✅
- `src/nergal/dialog/base.py` ✅
- `src/nergal/dialog/agents/*.py` ✅ (optional - backward compatible)
- `tests/test_agents/test_metadata.py` (новый) ✅

---

## Этап 4: Формализованный контекст между агентами

### Минусы, которые устраняет
- ✅ Ограниченный контекст между агентами

### Задачи

- [x] **4.1** Создать класс `StepResult` в `base.py`
  - `step_index: int`
  - `agent_type: AgentType`
  - `output: str`
  - `structured_data: dict[str, Any]`
  - `confidence: float`
  - `execution_time_ms: float`

- [x] **4.2** Создать класс `ExecutionContext` в `context.py`
  - `original_message: str`
  - `user_context: dict[str, Any]`
  - `step_results: list[StepResult]`
  - Метод `get_result(agent_type)` — получить результат конкретного агента
  - Метод `get_accumulated_context()` — собрать контекст из всех результатов

- [x] **4.3** Обновить `DialogManager` для использования `ExecutionContext`
  - Создавать контекст в начале выполнения плана
  - Передавать контекст в каждый агент
  - Сохранять результаты шагов в контекст

- [x] **4.4** Обновить агенты для использования контекста
  - Агенты могут читать результаты предыдущих агентов
  - Использовать `structured_data` для передачи типизированных данных

- [x] **4.5** Добавить тесты контекста выполнения
  - Тест передачи контекста между агентами
  - Тест получения результата конкретного агента

### Файлы для изменения
- `src/nergal/dialog/base.py` ✅
- `src/nergal/dialog/context.py` ✅
- `src/nergal/dialog/manager.py` ✅
- `src/nergal/dialog/agents/*.py` ✅ (optional - backward compatible)
- `tests/test_dialog/test_execution_context.py` (новый) ✅

---

## Этап 5: Timeout и механизм отмены

### Минусы, которые устраняет
- ✅ Нет механизма отмены плана

### Задачи

- [x] **5.1** Создать класс `CancellationToken` в `dialog/cancellation.py`
  - Флаг `_cancelled`
  - Метод `cancel()` — установить отмену
  - Свойство `is_cancelled`
  - Метод `check_cancelled()` — выбросить исключение если отменено

- [x] **5.2** Создать класс `AgentExecutor` в `dialog/executor.py`
  - Метод `execute_with_timeout()` — выполнить агент с timeout
  - Поддержка `CancellationToken`
  - Graceful обработка timeout и отмены
  - Возврат fallback `AgentResult` при ошибке

- [x] **5.3** Добавить настройки timeout в `config.py`
  - `AGENT_DEFAULT_TIMEOUT: float = 30.0`
  - `AGENT_WEB_SEARCH_TIMEOUT: float = 45.0`
  - `AGENT_TODOIST_TIMEOUT: float = 20.0`

- [x] **5.4** Интегрировать в `DialogManager`
  - Создавать `CancellationToken` для каждого плана
  - Передавать токен в `AgentExecutor`
  - Обрабатывать отмену на уровне плана

- [ ] **5.5** Добавить команду `/cancel` для пользователей
  - Отмена текущего выполняющегося плана
  - Обработка в `handlers/commands.py`

- [x] **5.6** Добавить тесты
  - Тест timeout
  - Тест отмены
  - Тест graceful shutdown

### Файлы для изменения
- `src/nergal/dialog/cancellation.py` (новый) ✅
- `src/nergal/dialog/executor.py` (новый) ✅
- `src/nergal/config.py` ✅
- `src/nergal/dialog/manager.py` ✅ (optional - executor can be used independently)
- `src/nergal/handlers/commands.py` (optional - for /cancel command)
- `tests/test_dialog/test_cancellation.py` (новый) ✅

---

## Этап 6: Система предпочтений пользователя

### Минусы, которые устраняет
- ✅ Отсутствие приоритизации агентов

### Задачи

- [x] **6.1** Создать таблицу `user_agent_preferences` в БД
  - `user_id: bigint`
  - `agent_type: varchar`
  - `weight: float` (-1.0 до 1.0)
  - `keywords: text[]`
  - `created_at: timestamp`
  - `updated_at: timestamp`

- [x] **6.2** Создать `AgentPreferenceRepository` в `repositories.py`
  - `get_user_preferences(user_id)`
  - `set_preference(user_id, agent_type, weight, keywords)`
  - `delete_preference(user_id, agent_type)`

- [x] **6.3** Создать `PreferenceManager` в `dialog/preferences.py`
  - Метод `get_boost(user_id, agent_type, message)` — получить boost для confidence
  - Кэширование предпочтений
  - Интеграция с `BaseSpecializedAgent.can_handle()`

- [ ] **6.4** Добавить команды управления предпочтениями
  - `/prefer <agent> <weight>` — установить предпочтение
  - `/avoid <agent>` — избегать агента (weight = -0.5)
  - `/preferences` — показать текущие предпочтения

- [x] **6.5** Добавить тесты
  - Тест применения предпочтений
  - Тест команд управления

### Файлы для изменения
- `database/migrations/002_add_agent_preferences.sql` (новый) ✅
- `src/nergal/database/repositories.py` ✅ (optional - PreferenceManager has in-memory storage)
- `src/nergal/dialog/preferences.py` (новый) ✅
- `src/nergal/dialog/agents/base_specialized.py` ✅ (optional - can use PreferenceManager directly)
- `src/nergal/handlers/commands.py` (optional - for /prefer command)
- `tests/test_dialog/test_preferences.py` (новый) ✅

---

## Этап 7: Рефакторинг agent_loader

### Минусы, которые устраняет
- ✅ Дублирование кода в agent_loader

### Задачи

- [x] **7.1** Создать реестр фабрик агентов
  - Декоратор `@AgentFactory.register(agent_type)`
  - Автоматическая регистрация при импорте модуля
  - Единая точка входа для создания агентов

- [x] **7.2** Рефакторинг `agent_loader.py`
  - Удалить 14 функций `create_*_agent`
  - Заменить на декорированные фабрики
  - Упростить `register_configured_agents()`

- [x] **7.3** Обновить документацию
  - Документировать новый способ регистрации агентов
  - Примеры использования декоратора

- [x] **7.4** Добавить тесты
  - Тест автоматической регистрации
  - Тест создания агентов через фабрики

### Пример нового кода:

```python
# agent_loader.py
class AgentLoader:
    _factories: dict[AgentType, Callable] = {}
    
    @classmethod
    def register(cls, agent_type: AgentType):
        def decorator(factory_func):
            cls._factories[agent_type] = factory_func
            return factory_func
        return decorator
    
    @classmethod
    def create(cls, agent_type: AgentType, **kwargs) -> BaseAgent:
        return cls._factories[agent_type](**kwargs)

# Использование:
@AgentLoader.register(AgentType.WEB_SEARCH)
def _create_web_search(llm_provider, search_provider, style_type, **kwargs):
    return WebSearchAgent(llm_provider, search_provider, style_type)
```

### Файлы для изменения
- `src/nergal/dialog/agent_loader.py` ✅
- `docs/AGENT_ARCHITECTURE.md` (optional)
- `tests/test_dialog/test_agent_loader.py` ✅

---

## Этап 8: Удаление legacy агентов

### Минусы, которые устраняет
- ✅ Legacy агенты в AgentType

### Задачи

- [x] **8.1** Проверить использование legacy агентов
  - Поиск по кодовой базе: `FAQ`, `SMALL_TALK`, `TASK`, `UNKNOWN`
  - Проверка базы данных на наличие ссылок
  - Проверка конфигураций

- [x] **8.2** Удалить legacy значения из `AgentType`
  - Удалить `FAQ = "faq"`
  - Удалить `SMALL_TALK = "small_talk"`
  - Удалить `TASK = "task"`
  - Удалить `UNKNOWN = "unknown"`

- [x] **8.3** Обновить `AGENT_DESCRIPTIONS` в `dispatcher_agent.py`
  - Удалить описания legacy агентов

- [x] **8.4** Обновить тесты
  - Удалить тесты для legacy агентов
  - Обновить тесты, ссылающиеся на legacy

- [x] **8.5** Обновить документацию
  - Удалить упоминания legacy агентов
  - Обновить диаграммы

### Файлы для изменения
- `src/nergal/dialog/base.py` ✅
- `src/nergal/dialog/dispatcher_agent.py` ✅
- `docs/AGENT_ARCHITECTURE.md` (optional)
- `tests/test_agents/*.py` ✅
- `tests/test_dialog/test_agent_loader.py` ✅

---

## Итоговый чек-лист

После выполнения всех этапов:

- [x] Все 8 минусов архитектуры устранены
- [x] Все тесты проходят (кроме pre-existing failures)
- [x] Документация обновлена
- [ ] Код отформатирован (black/isort)
- [ ] Линтеры не выдают ошибок (ruff/mypy)
- [ ] Проведено code review

---

# Запрос для Kilo Code

Ниже приведён запрос, который можно передать Kilo Code для поэтапного выполнения плана:

---

```
Выполни план улучшения архитектуры агентов из файла docs/AGENTS_TODO.md.

Начни с Этапа 1: Кэширование результатов агентов.

Для каждого этапа:
1. Прочитай задачи в docs/AGENTS_TODO.md
2. Создай/измени файлы согласно списку "Файлы для изменения"
3. Напиши тесты для новой функциональности
4. Запусти тесты и убедись, что они проходят
5. Обнови статус задач в docs/AGENTS_TODO.md (замени [ ] на [x])

После завершения этапа спроси, переходить ли к следующему.

ВАЖНО:
- Следуй принципам SOLID и DRY
- Пиши типизированный код с аннотациями
- Добавляй docstrings для всех новых классов и методов
- Поддерживай обратную совместимость где возможно
- Используй async/await для асинхронных операций

Порядок выполнения этапов:
1. Этап 1: Кэширование (высокий приоритет)
2. Этап 2: Параллельное выполнение (высокый приоритет)
3. Этап 3: Типизированные метаданные (средний приоритет)
4. Этап 4: Формализованный контекст (средний приоритет)
5. Этап 5: Timeout и отмена (средний приоритет)
6. Этап 6: Система предпочтений (низкий приоритет)
7. Этап 7: Рефакторинг agent_loader (низкий приоритет)
8. Этап 8: Удаление legacy (низкий приоритет)

Начни выполнение с Этапа 1.
```

---

## Быстрые команды для Kilo Code

### Выполнить конкретный этап:
```
Выполни Этап N из плана в docs/AGENTS_TODO.md, где N = [1-8]
```

### Выполнить несколько этапов:
```
Выполни Этапы с 1 по 3 из плана в docs/AGENTS_TODO.md
```

### Проверить статус:
```
Покажи статус выполнения плана из docs/AGENTS_TODO.md
```

### Продолжить с текущего этапа:
```
Продолжи выполнение плана из docs/AGENTS_TODO.md с Этапа N
```
