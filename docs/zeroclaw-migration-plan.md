# План миграции архитектуры Nergal к ZeroClaw

> **Версия**: 1.0
> **Дата создания**: 2026-02-28
> **Язык реализации**: Python 3.12
> **Ориентировочная длительность**: 10-14 дней

---

## Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Этапы миграции](#этапы-миграции)
3. [Детальные шаги по фазам](#детальные-шаги-по-фазам)
4. [Порядок реализации](#порядок-реализации)
5. [Тестирование](#тестирование)
6. [Стратегия обратной совместимости](#стратегия-обратной-совместимости)

---

## Обзор архитектуры

### Текущая архитектура Nergal

```
┌─────────────────────────────────────────────────────────────────┐
│                    TelegramBotEntry                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DialogManager                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         DispatcherAgent (создаёт ExecutionPlan)          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         AgentRegistry (BaseAgent наследники)             │  │
│  │  - DefaultAgent                                        │  │
│  │  - WebSearchAgent                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Целевая архитектура ZeroClaw

```
┌─────────────────────────────────────────────────────────────────┐
│                    ChannelFactory                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Channel (Telegram, Discord, Slack, CLI)         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Central Orchestration Loop                       │  │
│  │         - MemoryLoader                                  │  │
│  │         - ToolDispatcher                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                 │
│        ┌───────────┬───────────┬───────────┬───────────┐    │
│        ▼           ▼           ▼           ▼           ▼    │
│   Provider    Tool(N)     Memory    Observer  SecurityPolicy│
└─────────────────────────────────────────────────────────────────┘
```

---

## Этапы миграции

| Фаза | Название | Длительность | Зависимости |
|------|----------|---------------|-------------|
| Фаза 1 | Базовая инфраструктура (traits) | 1 день | - |
| Фаза 2 | Provider Trait (унфикация LLM) | 1-2 дня | Фаза 1 |
| Фаза 3 | Tool Trait + ToolDispatcher | 2 дня | Фаза 1, 2 |
| Фаза 4 | Channel Trait (абстракция мессенджеров) | 2 дня | Фаза 1 |
| Фаза 5 | Memory Trait (множественные бэкенды) | 1-2 дня | Фаза 1 |
| Фаза 6 | SecurityPolicy (автономность) | 1 день | Фаза 1, 3 |
| Фаза 7 | Observer Trait (метрики) | 1 день | Фаза 1 |
| Фаза 8 | Skills (расширения) | 2 дня | Фаза 1, 3 |
| Фаза 9 | Central Agent Orchestration Loop | 2-3 дня | Все фазы |
| Фаза 10 | Конфигурация TOML | 1 день | Все фазы |

---

## Детальные шаги по фазам

### Фаза 1: Базовая инфраструктура (Traits)

**Цель**: Создать базовые абстракции (traits) для всей системы.

#### Шаг 1.1: Создать базовый пакет `src/nergal/core/`

**Задачи**:
- Создать директорию `src/nergal/core/`
- Создать `__init__.py`

**Команды**:
```bash
mkdir -p src/nergal/core
touch src/nergal/core/__init__.py
```

---

#### Шаг 1.2: Создать базовые модели данных

**Файл**: `src/nergal/core/models.py`

**Классы для создания**:
```python
# Базовые модели для всех компонентов
@dataclass
class ProviderCapabilities:
    """Возможности LLM провайдера."""
    native_tool_calling: bool
    vision: bool
    streaming: bool

@dataclass
class ChatMessage:
    """Сообщение чата для LLM."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list["ToolCall"] | None = None

@dataclass
class ToolCall:
    """Вызов инструмента."""
    id: str
    name: str
    arguments: str  # JSON string

@dataclass
class ChatResponse:
    """Ответ от LLM провайдера."""
    text: str | None
    tool_calls: list[ToolCall]
    model: str
    tokens_used: int | None = None

@dataclass
class ToolSpec:
    """Спецификация инструмента для LLM."""
    name: str
    description: str
    parameters: dict  # JSON Schema

@dataclass
class ToolResult:
    """Результат выполнения инструмента."""
    success: bool
    output: str
    error: str | None = None

@dataclass
class ChannelMessage:
    """Сообщение из канала (мессенджера)."""
    id: str
    sender: str
    reply_target: str
    content: str
    channel: str
    timestamp: int
    thread_ts: str | None = None

@dataclass
class SendMessage:
    """Сообщение для отправки в канал."""
    content: str
    recipient: str
    subject: str | None = None
    thread_ts: str | None = None

@dataclass
class ObserverEvent:
    """Событие для наблюдателя."""
    event_type: str
    timestamp: float
    data: dict[str, Any]

@dataclass
class ObserverMetric:
    """Метрика для наблюдателя."""
    name: str
    value: float
    tags: dict[str, str]
```

---

#### Шаг 1.3: Создать базовые исключения

**Файл**: `src/nergal/core/exceptions.py`

```python
class NergalError(Exception):
    """Базовое исключение Nergal."""
    pass

class ProviderError(NergalError):
    """Ошибка провайдера LLM."""
    pass

class ToolExecutionError(NergalError):
    """Ошибка выполнения инструмента."""
    pass

class ChannelError(NergalError):
    """Ошибка канала."""
    pass

class MemoryError(NergalError):
    """Ошибка памяти."""
    pass

class SecurityViolationError(NergalError):
    """Нарушение безопасности."""
    pass

class AutonomyDeniedError(NergalError):
    """Отказ в автономности."""
    pass
```

---

### Фаза 2: Provider Trait (Унификация LLM)

**Цель**: Создать унифицированный интерфейс для всех LLM провайдеров.

#### Шаг 2.1: Создать Provider trait

**Файл**: `src/nergal/providers/base.py`

**Интерфейс для создания**:
```python
class BaseProvider(ABC):
    """Базовый интерфейс для LLM провайдеров."""

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Вернуть возможности провайдера."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResponse:
        """Основной метод чата с поддержкой инструментов."""
        pass

    @abstractmethod
    async def chat_with_system(
        self,
        system: str,
        message: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResponse:
        """Чат с системным промптом без инструментов."""
        pass

    @abstractmethod
    async def simple_chat(
        self,
        message: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> ChatResponse:
        """Простой чат без истории и инструментов."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Имя провайдера."""
        pass
```

---

#### Шаг 2.2: Адаптировать текущий ZAI провайдер

**Файл**: `src/nergal/providers/zai.py` (переместить из `llm/providers/zai.py`)

**Задачи**:
1. Переместить `llm/providers/zai.py` → `providers/zai.py`
2. Реализовать интерфейс `BaseProvider`
3. Добавить метод `capabilities()`
4. Обновить методы для работы с новыми моделями данных

---

#### Шаг 2.3: Создать ProviderFactory

**Файл**: `src/nergal/providers/factory.py`

```python
class ProviderFactory:
    """Фабрика для создания провайдеров из конфигурации."""

    _providers: dict[str, type[BaseProvider]] = {}

    @classmethod
    def register(cls, key: str, provider_class: type[BaseProvider]):
        """Зарегистрировать провайдер."""
        cls._providers[key] = provider_class

    @classmethod
    def create(cls, config: ProviderConfig) -> BaseProvider:
        """Создать провайдер из конфигурации."""
        provider_class = cls._providers.get(config.provider_type)
        if provider_class is None:
            raise ProviderError(f"Unknown provider: {config.provider_type}")
        return provider_class.from_config(config)
```

---

### Фаза 3: Tool Trait + ToolDispatcher

**Цель**: Создать систему инструментов вместо агентов.

#### Шаг 3.1: Создать Tool trait

**Файл**: `src/nergal/tools/base.py`

**Интерфейс для создания**:
```python
class BaseTool(ABC):
    """Базовый интерфейс для инструментов."""

    @abstractmethod
    def name(self) -> str:
        """Уникальное имя инструмента."""
        pass

    @abstractmethod
    def description(self) -> str:
        """Описание для LLM."""
        pass

    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema параметров."""
        pass

    @abstractmethod
    async def execute(self, args: dict) -> ToolResult:
        """Выполнить инструмент."""
        pass

    def spec(self) -> ToolSpec:
        """Полная спецификация."""
        return ToolSpec(
            name=self.name(),
            description=self.description(),
            parameters=self.parameters_schema(),
        )
```

---

#### Шаг 3.2: Создать стандартные инструменты

**Файл**: `src/nergal/tools/shell.py` - выполнение shell команд
**Файл**: `src/nergal/tools/file.py` - операции с файлами
**Файл**: `src/nergal/tools/http.py` - HTTP запросы
**Файл**: `src/nergal/tools/memory.py` - инструменты для памяти
**Файл**: `src/nergal/tools/search.py` - веб-поиск (перенос из WebSearchAgent)

---

#### Шаг 3.3: Создать ToolDispatcher

**Файл**: `src/nergal/core/tool_dispatcher.py`

```python
class BaseToolDispatcher(ABC):
    """Базовый интерфейс для диспетчера инструментов."""

    @abstractmethod
    def parse_response(
        self, response: ChatResponse
    ) -> tuple[str | None, list[ParsedToolCall]]:
        """Парсить ответ от LLM для извлечения вызовов инструментов."""
        pass

    @abstractmethod
    def format_results(self, results: list[ToolExecutionResult]) -> ChatMessage:
        """Форматировать результаты для отправки в LLM."""
        pass

    @abstractmethod
    def prompt_instructions(self, tools: list[BaseTool]) -> str:
        """Генерировать инструкции для системного промпта."""
        pass

    @abstractmethod
    def should_send_tool_specs(self) -> bool:
        """Отправлять ли спецификации инструментов в API."""
        pass


class NativeToolDispatcher(BaseToolDispatcher):
    """Диспетчер для native function calling."""


class XmlToolDispatcher(BaseToolDispatcher):
    """Диспетчер для XML-based tool calling (fallback)."""
```

---

#### Шаг 3.4: Создать ToolRegistry

**Файл**: `src/nergal/tools/registry.py`

```python
class ToolRegistry:
    """Реестр инструментов."""

    _tools: dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool):
        """Зарегистрировать инструмент."""
        cls._tools[tool.name()] = tool

    @classmethod
    def get(cls, name: str) -> BaseTool | None:
        """Получить инструмент по имени."""
        return cls._tools.get(name)

    @classmethod
    def get_all(cls) -> list[BaseTool]:
        """Получить все инструменты."""
        return list(cls._tools.values())

    @classmethod
    def get_specs(cls) -> list[ToolSpec]:
        """Получить спецификации всех инструментов."""
        return [tool.spec() for tool in cls._tools.values()]
```

---

### Фаза 4: Channel Trait (Абстракция мессенджеров)

**Цель**: Создать абстракцию для работы с разными мессенджерами.

#### Шаг 4.1: Создать Channel trait

**Файл**: `src/nergal/channels/base.py`

**Интерфейс для создания**:
```python
class BaseChannel(ABC):
    """Базовый интерфейс для каналов (мессенджеров)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя канала."""
        pass

    @abstractmethod
    async def send(self, message: SendMessage) -> str:
        """Отправить сообщение, вернуть message ID."""
        pass

    @abstractmethod
    async def listen(self, tx: asyncio.Queue[ChannelMessage]):
        """Начать слушать сообщения (long-running)."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверить здоровье соединения."""
        pass

    @abstractmethod
    async def start_typing(self, recipient: str):
        """Показать индикатор набора текста."""
        pass

    @abstractmethod
    async def stop_typing(self, recipient: str):
        """Скрыть индикатор набора текста."""
        pass

    @property
    @abstractmethod
    def supports_draft_updates(self) -> bool:
        """Поддерживает ли обновление сообщений."""
        pass

    async def send_draft(
        self, message: SendMessage
    ) -> str | None:
        """Отправить черновик для потоковой отправки."""
        return None

    async def update_draft(
        self, message_id: str, content: str
    ) -> bool:
        """Обновить черновик."""
        return False

    async def finalize_draft(self, message_id: str) -> bool:
        """Финализировать черновик."""
        return False

    async def cancel_draft(self, message_id: str) -> bool:
        """Отменить черновик."""
        return False
```

---

#### Шаг 4.2: Адаптировать Telegram как Channel

**Файл**: `src/nergal/channels/telegram.py`

**Задачи**:
1. Реализовать интерфейс `BaseChannel` для Telegram
2. Интегрировать с существующим `python-telegram-bot`
3. Перенести логику из `handlers/` в класс канала

---

#### Шаг 4.3: Создать ChannelFactory

**Файл**: `src/nergal/channels/factory.py`

```python
class ChannelFactory:
    """Фабрика для создания каналов."""

    _channels: dict[str, type[BaseChannel]] = {}

    @classmethod
    def register(cls, key: str, channel_class: type[BaseChannel]):
        """Зарегистрировать канал."""
        cls._channels[key] = channel_class

    @classmethod
    def create(cls, config: ChannelConfig) -> BaseChannel:
        """Создать канал из конфигурации."""
        channel_class = cls._channels.get(config.channel_type)
        if channel_class is None:
            raise ChannelError(f"Unknown channel: {config.channel_type}")
        return channel_class.from_config(config)
```

---

### Фаза 5: Memory Trait (Множественные бэкенды)

**Цель**: Создать абстракцию памяти с разными бэкендами.

#### Шаг 5.1: Создать Memory trait

**Файл**: `src/nergal/memory/base.py`

**Интерфейс для создания**:
```python
class MemoryCategory(str, Enum):
    """Категории памяти."""
    CORE = "core"
    DAILY = "daily"
    CONVERSATION = "conversation"
    CUSTOM = "custom"

@dataclass
class MemoryEntry:
    """Запись памяти."""
    id: str
    key: str
    content: str
    category: MemoryCategory
    timestamp: datetime
    session_id: str | None = None
    score: float | None = None

class BaseMemory(ABC):
    """Базовый интерфейс для памяти."""

    @abstractmethod
    async def store(
        self,
        key: str,
        content: str,
        category: MemoryCategory,
        session_id: str | None = None,
    ) -> MemoryEntry:
        """Сохранить память."""
        pass

    @abstractmethod
    async def recall(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[MemoryEntry]:
        """Найти память по запросу."""
        pass

    @abstractmethod
    async def get(self, key: str) -> MemoryEntry | None:
        """Получить память по ключу."""
        pass

    @abstractmethod
    async def list(
        self,
        category: MemoryCategory | None = None,
        session_id: str | None = None,
    ) -> list[MemoryEntry]:
        """Получить список памяти."""
        pass

    @abstractmethod
    async def forget(self, key: str) -> bool:
        """Удалить память."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Количество записей."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверить здоровье."""
        pass
```

---

#### Шаг 5.2: Адаптировать PostgreSQL Memory

**Файл**: `src/nergal/memory/postgresql.py`

**Задачи**:
1. Адаптировать существующий `MemoryService` к интерфейсу `BaseMemory`
2. Добавить поддержку категорий

---

#### Шаг 5.3: Создать дополнительные бэкенды

**Файл**: `src/nergal/memory/sqlite.py` - SQLite бэкенд
**Файл**: `src/nergal/memory/markdown.py` - Markdown файлы
**Файл**: `src/nergal/memory/none.py` - Stateless (без памяти)

---

#### Шаг 5.4: Создать MemoryLoader

**Файл**: `src/nergal/memory/loader.py`

```python
class BaseMemoryLoader(ABC):
    """Загрузчик контекста из памяти."""

    @abstractmethod
    async def load_context(
        self,
        memory: BaseMemory,
        query: str,
        max_entries: int = 5,
        min_score: float = 0.6,
    ) -> str:
        """Загрузить контекст из памяти."""
        pass


class KeywordMemoryLoader(BaseMemoryLoader):
    """Загрузчик по ключевым словам."""


class VectorMemoryLoader(BaseMemoryLoader):
    """Загрузчик по векторному сходству (с embeddings)."""
```

---

### Фаза 6: SecurityPolicy (Автономность)

**Цель**: Создать систему безопасности с уровнями автономности.

#### Шаг 6.1: Создать SecurityPolicy

**Файл**: `src/nergal/security/base.py`

```python
class AutonomyLevel(str, Enum):
    """Уровни автономности."""
    DENY_ALL = "deny_all"           # Ручное подтверждение всего
    READ_ONLY = "read_only"           # Только чтение
    ALLOW_LIST = "allow_list"        # Только allowlist
    RESTRICTED = "restricted"         # Подтверждение опасных операций
    FULL_AUTONOMY = "full_autonomy"  # Без ограничений

@dataclass
class SecurityPolicy:
    """Политика безопасности."""

    autonomy_level: AutonomyLevel
    allowlist_shell: list[str] = field(default_factory=list)
    denylist_patterns: list[str] = field(default_factory=list)
    allowlist_file_read: list[str] = field(default_factory=list)
    allowlist_file_write: list[str] = field(default_factory=list)
    allowlist_urls: list[str] = field(default_factory=list)

    def check_tool_execution(
        self, tool_name: str, args: dict
    ) -> tuple[bool, str | None]:
        """Проверить можно ли выполнить инструмент."""
        pass

    def check_shell_command(self, command: str) -> tuple[bool, str | None]:
        """Проверить shell команду."""
        pass

    def check_file_operation(
        self, path: str, operation: str
    ) -> tuple[bool, str | None]:
        """Проверить операцию с файлом."""
        pass
```

---

#### Шаг 6.2: Создать Sandbox

**Файл**: `src/nergal/security/sandbox.py`

```python
class BaseSandbox(ABC):
    """Базовый интерфейс для изоляции."""

    @abstractmethod
    def wrap_command(self, cmd: list[str]) -> list[str]:
        """Обернуть команду в sandbox."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Доступен ли sandbox."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя sandbox."""
        pass


class FirejailSandbox(BaseSandbox):
    """Firejail sandbox."""


class BubblewrapSandbox(BaseSandbox):
    """Bubblewrap sandbox."""


class NoSandbox(BaseSandbox):
    """Без изоляции."""
```

---

### Фаза 7: Observer Trait (Метрики)

**Цель**: Создать систему наблюдения за агентом.

#### Шаг 7.1: Создать Observer trait

**Файл**: `src/nergal/observer/base.py`

```python
class EventType(str, Enum):
    """Типы событий."""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TOOL_CALL = "tool_call"
    TOOL_ERROR = "tool_error"
    MEMORY_STORE = "memory_store"
    MEMORY_RECALL = "memory_recall"
    CHANNEL_MESSAGE = "channel_message"
    SECURITY_DENIAL = "security_denial"

class BaseObserver(ABC):
    """Базовый интерфейс для наблюдателя."""

    @abstractmethod
    async def record_event(self, event: ObserverEvent):
        """Записать событие."""
        pass

    @abstractmethod
    async def record_metric(self, metric: ObserverMetric):
        """Записать метрику."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Имя наблюдателя."""
        pass
```

---

#### Шаг 7.2: Создать реализации Observer

**Файл**: `src/nergal/observer/console.py` - вывод в консоль
**Файл**: `src/nergal/observer/file.py` - запись в файл
**Файл**: `src/nergal/observer/prometheus.py` - Prometheus экспорт

---

### Фаза 8: Skills (Расширения)

**Цель**: Создать систему пользовательских расширений.

#### Шаг 8.1: Создать модели Skills

**Файл**: `src/nergal/skills/models.py`

```python
from dataclasses import dataclass
from typing import Any
from enum import Enum

class SkillKind(str, Enum):
    """Тип инструмента в скилле."""
    SHELL = "shell"
    HTTP = "http"
    SCRIPT = "script"

@dataclass
class SkillTool:
    """Инструмент в скилле."""
    name: str
    description: str
    kind: SkillKind
    command: str  # shell command, URL, или script path
    args: list["SkillArg"]

@dataclass
class SkillArg:
    """Аргумент инструмента."""
    name: str
    description: str
    required: bool = False
    type: str = "string"
    enum: list[str] | None = None

@dataclass
class SkillManifest:
    """Манифест скилла."""
    name: str
    description: str
    version: str
    author: str
    tools: list[SkillTool]
```

---

#### Шаг 8.2: Создать парсер TOML для Skills

**Файл**: `src/nergal/skills/parser.py`

**Задачи**:
1. Парсинг `SKILL.toml` файлов
2. Валидация манифеста
3. Создание `SkillManifest`

---

#### Шаг 8.3: Создать SkillRegistry и загрузчик

**Файл**: `src/nergal/skills/registry.py`

```python
class SkillRegistry:
    """Реестр скиллов."""

    def __init__(self, skills_dir: str):
        self._skills_dir = skills_dir
        self._skills: dict[str, SkillManifest] = {}

    async def load_all(self):
        """Загрузить все скиллы из директории."""
        pass

    def get(self, name: str) -> SkillManifest | None:
        """Получить скилл по имени."""
        pass

    def get_all_tools(self) -> list[BaseTool]:
        """Получить инструменты всех скиллов."""
        pass
```

---

#### Шаг 8.4: Создать директорию для Skills

**Команды**:
```bash
mkdir -p ~/.nergal/skills
```

---

### Фаза 9: Central Agent Orchestration Loop

**Цель**: Создать главный оркестратор замещающий DialogManager.

#### Шаг 9.1: Создать Agent билдер

**Файл**: `src/nergal/agent/builder.py`

```python
class AgentBuilder:
    """Билдер для создания Agent."""

    def __init__(self):
        self._provider: BaseProvider | None = None
        self._tools: list[BaseTool] = []
        self._memory: BaseMemory | None = None
        self._memory_loader: BaseMemoryLoader | None = None
        self._channel: BaseChannel | None = None
        self._security: SecurityPolicy | None = None
        self._observer: BaseObserver | None = None
        self._max_iterations: int = 10
        self._temperature: float = 0.7

    def with_provider(self, provider: BaseProvider) -> "AgentBuilder":
        self._provider = provider
        return self

    def with_tools(self, tools: list[BaseTool]) -> "AgentBuilder":
        self._tools.extend(tools)
        return self

    def with_memory(
        self, memory: BaseMemory, loader: BaseMemoryLoader
    ) -> "AgentBuilder":
        self._memory = memory
        self._memory_loader = loader
        return self

    def with_channel(self, channel: BaseChannel) -> "AgentBuilder":
        self._channel = channel
        return self

    def with_security(self, security: SecurityPolicy) -> "AgentBuilder":
        self._security = security
        return self

    def with_observer(self, observer: BaseObserver) -> "AgentBuilder":
        self._observer = observer
        return self

    def with_max_iterations(self, max: int) -> "AgentBuilder":
        self._max_iterations = max
        return self

    def with_temperature(self, temp: float) -> "AgentBuilder":
        self._temperature = temp
        return self

    def build(self) -> "Agent":
        """Создать экземпляр Agent."""
        if self._provider is None:
            raise NergalError("Provider is required")
        if not self._tools:
            raise NergalError("At least one tool is required")

        return Agent(
            provider=self._provider,
            tools=self._tools,
            memory=self._memory,
            memory_loader=self._memory_loader,
            channel=self._channel,
            security=self._security,
            observer=self._observer,
            max_iterations=self._max_iterations,
            temperature=self._temperature,
        )
```

---

#### Шаг 9.2: Создать главный класс Agent

**Файл**: `src/nergal/agent/agent.py`

**Основной класс для создания**:

```python
class Agent:
    """Главный агент с централизованным оркестрационным циклом."""

    def __init__(
        self,
        provider: BaseProvider,
        tools: list[BaseTool],
        memory: BaseMemory | None = None,
        memory_loader: BaseMemoryLoader | None = None,
        channel: BaseChannel | None = None,
        security: SecurityPolicy | None = None,
        observer: BaseObserver | None = None,
        max_iterations: int = 10,
        temperature: float = 0.7,
    ):
        self._provider = provider
        self._tools = {t.name(): t for t in tools}
        self._memory = memory
        self._memory_loader = memory_loader
        self._channel = channel
        self._security = security
        self._observer = observer
        self._max_iterations = max_iterations
        self._temperature = temperature
        self._history: list[ChatMessage] = []

        # Инициализация tool dispatcher
        self._tool_dispatcher = self._create_tool_dispatcher()
        self._system_prompt = self._build_system_prompt()

    async def turn(self, user_message: str, sender: str) -> str:
        """Основной цикл обработки сообщения."""
        pass

    async def _turn_iteration(
        self, user_message: str, sender: str
    ) -> tuple[str | None, bool]:
        """Одна итерация цикла."""
        pass

    async def _load_memory_context(self, query: str) -> str:
        """Загрузить контекст из памяти."""
        pass

    def _build_system_prompt(self) -> str:
        """Построить системный промпт."""
        pass

    def _create_tool_dispatcher(self) -> BaseToolDispatcher:
        """Создать диспетчер инструментов."""
        if self._provider.capabilities().native_tool_calling:
            return NativeToolDispatcher()
        else:
            return XmlToolDispatcher()

    async def _execute_tools(
        self, tool_calls: list[ParsedToolCall]
    ) -> list[ToolExecutionResult]:
        """Выполнить инструменты."""
        pass

    async def _execute_single_tool(
        self, call: ParsedToolCall
    ) -> ToolExecutionResult:
        """Выполнить один инструмент."""
        pass

    async def _record_event(self, event_type: str, data: dict):
        """Записать событие."""
        if self._observer:
            await self._observer.record_event(ObserverEvent(...))

    async def _record_metric(self, name: str, value: float, tags: dict):
        """Записать метрику."""
        if self._observer:
            await self._observer.record_metric(ObserverMetric(...))
```

---

#### Шаг 9.3: Создать новую конфигурацию

**Файл**: `src/nergal/config_new.py` (заменить старый `config.py`)

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ProviderConfig:
    """Конфигурация провайдера."""
    provider_type: str  # "zai", "openai", "anthropic"
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None

@dataclass
class ChannelConfig:
    """Конфигурация канала."""
    channel_type: str  # "telegram", "discord", "cli"
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

@dataclass
class MemoryConfig:
    """Конфигурация памяти."""
    backend: str  # "postgresql", "sqlite", "markdown", "none"
    auto_save: bool = True
    min_relevance_score: float = 0.6
    config: dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityConfig:
    """Конфигурация безопасности."""
    level: str  # AutonomyLevel
    allowlist_shell: list[str] = field(default_factory=list)
    denylist_patterns: list[str] = field(default_factory=list)
    sandbox: str = "none"  # "firejail", "bubblewrap", "none"

@dataclass
class SkillsConfig:
    """Конфигурация скиллов."""
    enabled: bool = True
    skills_dir: str = "~/.nergal/skills"
    prompt_injection_mode: str = "default"

@dataclass
class AgentConfig:
    """Конфигурация агента."""
    provider: ProviderConfig
    channels: list[ChannelConfig]
    memory: MemoryConfig
    security: SecurityConfig
    skills: SkillsConfig
    max_tool_iterations: int = 10
    max_history_messages: int = 50
    parallel_tools: bool = True
    temperature: float = 0.7
```

---

### Фаза 10: Конфигурация TOML

**Цель**: Перейти от env vars к TOML конфигурации.

#### Шаг 10.1: Создать парсер TOML

**Файл**: `src/nergal/config/toml.py`

```python
import tomli
from pathlib import Path

class TomlConfigLoader:
    """Загрузчик конфигурации из TOML."""

    CONFIG_PATHS = [
        Path.cwd() / "nergal.toml",
        Path.home() / ".nergal" / "config.toml",
    ]

    def load(self, path: str | None = None) -> AgentConfig:
        """Загрузить конфигурацию."""
        pass

    def _resolve_path(self) -> Path | None:
        """Найти конфигурационный файл."""
        pass
```

---

#### Шаг 10.2: Создать пример конфигурации

**Файл**: `nergal.toml.example`

```toml
# Nergal Configuration File

[agent]
max_tool_iterations = 10
max_history_messages = 50
parallel_tools = true
temperature = 0.7

[provider]
type = "zai"
api_key = "${ZAI_API_KEY}"
model = "glm-4"
temperature = 0.7

[[channels_config]]
type = "telegram"
enabled = true
bot_token = "${TELEGRAM_BOT_TOKEN}"

[memory]
backend = "postgresql"
auto_save = true
min_relevance_score = 0.6

[memory.config]
connection_string = "${DATABASE_URL}"

[security]
level = "restricted"
allowlist_shell = ["ls", "cat", "grep", "echo"]
denylist_patterns = ["rm -rf", "format", "mkfs"]
sandbox = "none"

[skills]
enabled = true
skills_dir = "~/.nergal/skills"
prompt_injection_mode = "default"

[observer]
type = "prometheus"  # or "console", "file"
```

---

#### Шаг 10.3: Обновить main.py

**Файл**: `src/nergal/main.py`

**Задачи**:
1. Заменить DI контейнер на Builder Pattern
2. Загружать конфигурацию из TOML
3. Создавать Agent через AgentBuilder
4. Запускать каналы через ChannelFactory

---

## Порядок реализации

### Рекомендуемый порядок:

1. **Создать ветку для миграции**:
   ```bash
   git checkout -b feature/zeroclaw-architecture
   ```

2. **Реализовать по фазам** (каждая фаза как отдельный PR):
   - Фаза 1 → PR #1
   - Фаза 2 → PR #2
   - Фаза 3 → PR #3
   - ...

3. **Тестировать каждую фазу** перед слиянием.

4. **Обновлять документацию** по мере продвижения.

---

## Тестирование

### Единичные тесты для каждой фазы

| Фаза | Тестовый файл | Что тестировать |
|------|---------------|----------------|
| Фаза 1 | `tests/core/test_models.py` | Модели данных |
| Фаза 2 | `tests/providers/test_base.py` | Provider интерфейс |
| Фаза 3 | `tests/tools/test_base.py` | Tool интерфейс |
| Фаза 3 | `tests/tools/test_dispatcher.py` | ToolDispatcher |
| Фаза 4 | `tests/channels/test_base.py` | Channel интерфейс |
| Фаза 5 | `tests/memory/test_base.py` | Memory интерфейс |
| Фаза 6 | `tests/security/test_policy.py` | SecurityPolicy |
| Фаза 7 | `tests/observer/test_base.py` | Observer интерфейс |
| Фаза 8 | `tests/skills/test_parser.py` | Skills парсер |
| Фаза 9 | `tests/agent/test_agent.py` | Agent оркестрация |
| Фаза 10 | `tests/config/test_toml.py` | TOML конфигурация |

### Интеграционные тесты

- Создать `tests/integration/test_agent_integration.py`
- Тестировать полный цикл: User → Channel → Agent → Tools → Response

---

## Стратегия обратной совместимости

### Шаг 1: Сохранить старую систему как "legacy"

- Переименовать `DialogManager` → `LegacyDialogManager`
- Сохранить в `src/nergal/legacy/dialog/`
- Оставить работу через флаг `use_legacy = True`

### Шаг 2: Постепенная миграция

1. Начать с новых каналов (добавить CLI канал)
2. Перевести WebSearch на Tool
3. Перевести память на новый интерфейс
4. Перевести Telegram на Channel

### Шаг 3: Удаление legacy

- После полной миграции удалить legacy код
- Очистить зависимость от старых компонентов

---

## Запуск миграции с помощью Claude

Чтобы запустить реализацию конкретного шага:

1. **Открыть этот файл** в редакторе
2. **Выбрать фазу и шаг** для реализации
3. **Запросить у Claude**:
   ```
   Реализуй Фазу X, Шаг Y из файла docs/zeroclaw-migration-plan.md
   ```
4. **Код будет создан** согласно описанию
5. **Протестировать** созданный код
6. **Перейти к следующему шагу**

---

## Контрольный список завершения

### Фаза 1: Базовая инфраструктура
- [x] Создан пакет `src/nergal/core/`
- [x] Созданы базовые модели (`models.py`)
- [x] Созданы исключения (`exceptions.py`)
- [x] Написаны тесты для моделей
- [x] Документация обновлена

### Фаза 2: Provider Trait
- [ ] Создан интерфейс `BaseProvider`
- [ ] Адаптирован ZAI провайдер
- [ ] Создан `ProviderFactory`
- [ ] Написаны тесты

### Фаза 3: Tool Trait + ToolDispatcher
- [ ] Создан интерфейс `BaseTool`
- [ ] Созданы стандартные инструменты
- [ ] Создан `ToolDispatcher`
- [ ] Создан `ToolRegistry`
- [ ] Написаны тесты

### Фаза 4: Channel Trait
- [ ] Создан интерфейс `BaseChannel`
- [ ] Адаптирован Telegram как Channel
- [ ] Создан `ChannelFactory`
- [ ] Написаны тесты

### Фаза 5: Memory Trait
- [ ] Создан интерфейс `BaseMemory`
- [ ] Адаптирован PostgreSQL Memory
- [ ] Созданы дополнительные бэкенды
- [ ] Создан `MemoryLoader`
- [ ] Написаны тесты

### Фаза 6: SecurityPolicy
- [ ] Создан `SecurityPolicy`
- [ ] Создан `Sandbox`
- [ ] Написаны тесты

### Фаза 7: Observer Trait
- [ ] Создан интерфейс `BaseObserver`
- [ ] Созданы реализации (console, file, prometheus)
- [ ] Написаны тесты

### Фаза 8: Skills
- [ ] Созданы модели Skills
- [ ] Создан парсер TOML
- [ ] Создан `SkillRegistry`
- [ ] Создана директория для Skills
- [ ] Написаны тесты

### Фаза 9: Central Agent Orchestration Loop
- [ ] Создан `AgentBuilder`
- [ ] Создан главный класс `Agent`
- [ ] Создана новая конфигурация
- [ ] Написаны тесты

### Фаза 10: Конфигурация TOML
- [ ] Создан парсер TOML
- [ ] Создан пример конфигурации
- [ ] Обновлен `main.py`
- [ ] Написаны тесты

---

## Дополнительные ресурсы

- [ZeroClaw Architecture Guide](docs/architecture-guide.md)
- [Nergal Documentation](README.md)
- [Python ABC Documentation](https://docs.python.org/3/library/abc.html)
- [TOML Specification](https://toml.io/en/)

---

## Примечания

1. **Параллельная разработка**: Фазы 2-7 можно разрабатывать параллельно разными разработчиками
2. **Инкрементальная миграция**: Каждая фаза должна быть работоспособной самостоятельно
3. **Документирование**: Каждый интерфейс должен иметь docstrings с примерами
4. **Типизация**: Использовать type hints везде (mypy strict mode)
5. **Логирование**: Использовать structlog для логирования

---

**Версия плана**: 1.0
**Последнее обновление**: 2026-02-28
**Статус**: Готов к реализации
