# Рекомендации по агентам для бота-консультанта

Этот документ описывает специализированные агенты для бота-консультанта, который:
1. Получает вопрос от пользователя
2. Составляет план формирования ответа
3. Проходит по плану с агентами-помощниками
4. Выдает структурированный ответ

## Текущие агенты

| Агент | Описание | Статус | Файл |
|-------|----------|--------|------|
| `default` | Общий агент, финальное формирование ответа | ✅ Реализован | [`default_agent.py`](src/nergal/dialog/default_agent.py) |
| `dispatcher` | Анализ запроса и составление плана | ✅ Реализован | [`dispatcher_agent.py`](src/nergal/dialog/dispatcher_agent.py) |
| `web_search` | Поиск информации в интернете | ✅ Реализован | [`agents/web_search_agent.py`](src/nergal/dialog/agents/web_search_agent.py) |
| `fact_check` | Проверка фактов на достоверность | ✅ Реализован | [`agents/fact_check_agent.py`](src/nergal/dialog/agents/fact_check_agent.py) |
| `analysis` | Анализ данных и сравнение информации | ✅ Реализован | [`agents/analysis_agent.py`](src/nergal/dialog/agents/analysis_agent.py) |
| `news` | Агрегация и обработка новостей | ✅ Реализован | [`agents/news_agent.py`](src/nergal/dialog/agents/news_agent.py) |
| `clarification` | Уточнение неоднозначных запросов | ✅ Реализован | [`agents/clarification_agent.py`](src/nergal/dialog/agents/clarification_agent.py) |
| `comparison` | Структурированное сравнение альтернатив | ✅ Реализован | [`agents/comparison_agent.py`](src/nergal/dialog/agents/comparison_agent.py) |
| `summary` | Резюмирование длинных текстов | ✅ Реализован | [`agents/summary_agent.py`](src/nergal/dialog/agents/summary_agent.py) |
| `tech_docs` | Поиск по технической документации | ✅ Реализован | [`agents/tech_docs_agent.py`](src/nergal/dialog/agents/tech_docs_agent.py) |
| `code_analysis` | Анализ кодовой базы | ✅ Реализован | [`agents/code_analysis_agent.py`](src/nergal/dialog/agents/code_analysis_agent.py) |
| `metrics` | Получение метрик и статистики | ✅ Реализован | [`agents/metrics_agent.py`](src/nergal/dialog/agents/metrics_agent.py) |
| `expertise` | Экспертные знания в специфических доменах | ✅ Реализован | [`agents/expertise_agent.py`](src/nergal/dialog/agents/expertise_agent.py) |

---

## Категории агентов

### 🔴 CORE - Основные агенты

#### DefaultAgent (`default`)

**Назначение:** Общий агент для обычных разговоров и финального формирования ответа

**Роль в плане ответа:** Всегда завершает цепочку агентов, формируя финальный ответ пользователю

**Ключевые функции:**
- Обработка приветствий и простых разговоров
- Синтез информации от предыдущих агентов
- Формирование ответа в заданном стиле
- Персонализация на основе контекста памяти

#### DispatcherAgent (`dispatcher`)

**Назначение:** Анализ запроса и составление плана выполнения

**Роль в системе:** Получает сообщение первым и решает какие агенты должны его обработать

**Ключевые функции:**
- Динамическое формирование списка доступных агентов
- Анализ смысла запроса
- Составление оптимального плана выполнения
- Указание недостающих агентов

---

### 🟡 INFORMATION - Агенты сбора информации

#### WebSearchAgent (`web_search`)

**Назначение:** Поиск актуальной информации в интернете

**Роль в плане ответа:** Получает свежие данные из веба

**Ключевые функции:**
- Поиск через MCP (Model Context Protocol)
- Интеграция с Z.ai Web Search API
- Возврат структурированных результатов с URL

**Интеграции:**
- Z.ai MCP HTTP endpoint
- Поддержка различных поисковых провайдеров

**Примеры использования в плане:**
```
Вопрос: "Какая погода в Москве?"
План: web_search -> default

Вопрос: "Какие новости о Kubernetes?"
План: web_search -> news -> default
```

---

#### TechDocsAgent (`tech_docs`)

**Назначение:** Поиск по технической документации библиотек и фреймворков

**Роль в плане ответа:** Предоставляет актуальную документацию по технологиям

**Ключевые функции:**
- Поиск по официальной документации
- Извлечение примеров кода
- Актуальные версии API
- Best practices

**Примеры использования в плане:**
```
Вопрос: "Как использовать async/await в Python 3.11?"
План: tech_docs -> default

Вопрос: "Какие есть паттерны для обработки ошибок в Go?"
План: tech_docs -> analysis -> default
```

---

#### CodeAnalysisAgent (`code_analysis`)

**Назначение:** Анализ кода и технических артефактов

**Роль в плане ответа:** Отвечает на вопросы по кодовой базе

**Ключевые функции:**
- Объяснение работы кода
- Поиск паттернов использования
- Анализ архитектуры
- Code review insights

**Примеры использования в плане:**
```
Вопрос: "Где используется функция authenticate_user?"
План: code_analysis -> default

Вопрос: "Какие есть проблемы в архитектуре модуля payments?"
План: code_analysis -> analysis -> default
```

---

#### MetricsAgent (`metrics`)

**Назначение:** Получение актуальных метрик и статистики

**Роль в плане ответа:** Предоставляет количественные данные

**Ключевые функции:**
- Метрики производительности
- Статистика использования
- KPI и бизнес-метрики
- Инфраструктурные метрики

**Примеры использования в плане:**
```
Вопрос: "Какая средняя latency у API авторизации?"
План: metrics -> default

Вопрос: "Как выросла нагрузка на сервис за последний месяц?"
План: metrics -> analysis -> default
```

---

#### NewsAgent (`news`)

**Назначение:** Агрегация и обработка новостей из нескольких источников

**Роль в плане ответа:** Собирает новости, сравнивает источники, выявляет консенсус и противоречия

**Ключевые функции:**
- Агрегация новостей из нескольких источников
- Сравнение информации из разных источников
- Выявление точек согласия (консенсуса)
- Определение противоречий и расхождений
- Отслеживание ссылок на источники
- Оценка достоверности и предвзятости источников
- Кластеризация связанных новостей

**Примеры использования в плане:**
```
Вопрос: "Что пишут о выборах в США?"
План: web_search -> news -> fact_check -> default

Вопрос: "Какие новости про Kubernetes?"
План: web_search -> news -> default

Вопрос: "Сравни источники о конфликте в Сирии"
План: web_search -> news -> analysis -> default
```

**Формат ответа:**
```
## 📰 Агрегация новостей: [Тема]

### 📌 Основное
[Ключевые факты из консенсуса]

### ✅ Подтверждённые факты
[Список фактов с источниками]

### ⚠️ Спорные моменты
[Где источники расходятся]

### 📊 Источники
| Источник | Позиция | Достоверность |
|----------|---------|---------------|

### 🔗 Ссылки
- [Название источника](URL)

### 💡 Выводы
[Итоговый анализ]
```

---

### 🟢 PROCESSING - Агенты обработки

#### AnalysisAgent (`analysis`)

**Назначение:** Глубокий анализ информации из разных источников

**Роль в плане ответа:** Анализирует и синтезирует информацию

**Ключевые функции:**
- Сравнение нескольких источников
- Выявление противоречий
- Структурирование информации
- Формирование выводов

**Примеры использования в плане:**
```
Вопрос: "Сравни React и Vue для нового проекта"
План: web_search -> knowledge_base -> analysis -> default

Вопрос: "В чем плюсы и минусы микросервисов для нас?"
План: knowledge_base -> analysis -> default
```

---

#### FactCheckAgent (`fact_check`)

**Назначение:** Проверка достоверности информации

**Роль в плане ответа:** Верификация фактов из веб-поиска или утверждений пользователя

**Ключевые функции:**
- Кросс-проверка по нескольким источникам
- Оценка надежности источников
- Выявление устаревшей информации
- Определение bias (предвзятости)

**Примеры использования в плане:**
```
Вопрос: "Правда ли что Kubernetes 1.29 убирает dockershim?"
План: web_search -> fact_check -> default

Вопрос: "Насколько актуальна информация о производительности Go vs Rust?"
План: web_search -> fact_check -> analysis -> default
```

---

#### ComparisonAgent (`comparison`)

**Назначение:** Структурированное сравнение вариантов

**Роль в плане ответа:** Создает сравнительные таблицы и анализы

**Ключевые функции:**
- Сравнение по заданным критериям
- Создание comparison matrix
- Взвешенная оценка альтернатив
- Рекомендации на основе критериев

**Примеры использования в плане:**
```
Вопрос: "Что выбрать: PostgreSQL или MongoDB для нового сервиса?"
План: knowledge_base -> web_search -> comparison -> default

Вопрос: "Сравни облачных провайдеров для Kubernetes"
План: web_search -> comparison -> analysis -> default
```

---

#### SummaryAgent (`summary`)

**Назначение:** Резюмирование длинной информации

**Роль в плане ответа:** Сокращает и структурирует длинные ответы

**Ключевые функции:**
- TL;DR для длинных текстов
- Выделение ключевых пунктов
- Структурирование по разделам
- Адаптация уровня детализации

**Примеры использования в плане:**
```
Вопрос: "Расскажи про архитектуру нашего монолита"
План: knowledge_base -> summary -> default

Вопрос: "Что нового в последнем релизе React?"
План: web_search -> tech_docs -> summary -> default
```

---

#### ClarificationAgent (`clarification`)

**Назначение:** Уточнение неоднозначных вопросов

**Роль в плане ответа:** Определяет, нужен ли уточняющий вопрос пользователю

**Ключевые функции:**
- Определение неоднозначности в запросе
- Генерация уточняющих вопросов
- Интерпретация ответов пользователя
- Контекстная дисамбигуация

**Примеры использования:**
```
Вопрос: "Как настроить деплой?"
Уточнение: "Какую среду вы имеете в виду: staging, preprod или prod?"

Вопрос: "Кто отвечает за авторизацию?"
Уточнение: "Вы имеете в виду команду разработки или конкретного ответственного?"
```

---

### 🔵 SPECIALIZED - Специализированные агенты

#### ExpertiseAgent (`expertise`)

**Назначение:** Ответы в специфических доменах

**Роль в плане ответа:** Предоставляет экспертные знания в узких областях

**Специализации:**
- `security_expertise` — безопасность
- `legal_expertise` — юридические вопросы
- `finance_expertise` — финансовые вопросы
- `hr_expertise` — HR-практики
- `architecture_expertise` — программная архитектура

**Примеры использования в плане:**
```
Вопрос: "Какие есть требования к обработке персональных данных?"
План: knowledge_base -> expertise:legal -> default

Вопрос: "Как защитить API от DDoS?"
План: expertise:security -> tech_docs -> default
```

---

## Примеры сложных планов выполнения

### Пример 1: Техническое исследование
```
Вопрос: "Стоит ли нам мигрировать на Kubernetes? Какие плюсы и минусы?"

План:
1. knowledge_base — найти текущую архитектуру и проблемы
2. web_search — найти актуальные статьи про K8s
3. tech_docs — документация по миграции
4. comparison — сравнить с текущим решением
5. analysis — синтезировать выводы
6. default — сформировать финальный ответ
```

### Пример 2: Вопрос по процессам
```
Вопрос: "Как у нас работает процесс релиза и какие есть проблемы?"

План:
1. knowledge_base — найти регламент релизов
2. metrics — получить статистику релизов
3. code_analysis — проверить CI/CD конфигурацию
4. analysis — выявить проблемные места
5. default — сформировать ответ с рекомендациями
```

### Пример 3: Сравнение технологий
```
Вопрос: "Что выбрать для нового микросервиса: Go или Rust?"

План:
1. clarification — уточнить требования к сервису
2. knowledge_base — найти наши стандарты и опыт
3. web_search — актуальные сравнения
4. tech_docs — документация по обоим языкам
5. comparison — структурированное сравнение
6. analysis — выводы для нашего контекста
7. default — финальная рекомендация
```

### Пример 4: Анализ проблемы
```
Вопрос: "Почему у нас выросла latency в API на прошлой неделе?"

План:
1. metrics — получить графики latency
2. code_analysis — найти изменения в коде за период
3. knowledge_base — найти архитектуру затронутых сервисов
4. analysis — выявить корреляции и возможные причины
5. default — сформировать гипотезы и рекомендации
```

---

## Структура AgentType

```python
class AgentType(str, Enum):
    # Core agents
    DEFAULT = "default"           # Финальное формирование ответа
    DISPATCHER = "dispatcher"     # Планирование и маршрутизация
    
    # Information gathering agents
    WEB_SEARCH = "web_search"     # Поиск в интернете
    KNOWLEDGE_BASE = "knowledge_base"  # Корпоративная база знаний
    TECH_DOCS = "tech_docs"       # Техническая документация
    CODE_ANALYSIS = "code_analysis"  # Анализ кода
    METRICS = "metrics"           # Метрики и статистика
    NEWS = "news"                 # Агрегация новостей
    
    # Processing agents
    ANALYSIS = "analysis"         # Анализ информации
    FACT_CHECK = "fact_check"     # Проверка фактов
    COMPARISON = "comparison"     # Сравнение вариантов
    SUMMARY = "summary"           # Резюмирование
    CLARIFICATION = "clarification"  # Уточнение вопросов
    
    # Specialized agents
    EXPERTISE = "expertise"       # Экспертные знания
```

---

## Архитектура взаимодействия агентов

### Поток обработки запроса

```
┌─────────────────────────────────────────────────────────────────┐
│                         Пользователь                             │
│                    "Сравни React и Vue"                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DispatcherAgent                             │
│  Анализирует запрос, составляет план:                           │
│  web_search -> knowledge_base -> comparison -> default          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WebSearchAgent                              │
│  Ищет актуальные статьи, сравнения, benchmarks                  │
│  Результат: список URL и summary                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KnowledgeBaseAgent                            │
│  Ищет в корпоративной базе: наши стандарты, опыт, решения       │
│  Результат: релевантные документы                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ComparisonAgent                              │
│  Структурирует сравнение по критериям:                          │
│  производительность, экосистема, кривая обучения, наш опыт      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DefaultAgent                               │
│  Формирует финальный ответ в нужном стиле:                      │
│  "Исходя из наших стандартов и требований..."                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Пользователь                             │
│                    Получает ответ                                │
└─────────────────────────────────────────────────────────────────┘
```

### Контекст между агентами

```python
@dataclass
class AgentContext:
    """Контекст, передаваемый между агентами в рамках одного плана."""
    
    # Оригинальный запрос
    original_query: str
    
    # Уточненный запрос (если был clarification)
    clarified_query: str | None = None
    
    # Результаты предыдущих агентов
    agent_results: dict[AgentType, AgentResult] = field(default_factory=dict)
    
    # Накопленный контекст (документы, факты, метрики)
    accumulated_context: dict[str, Any] = field(default_factory=dict)
    
    # Метаданные плана
    plan_id: str = ""
    current_step: int = 0
    total_steps: int = 0
```

---

## Базовые классы для агентов

### BaseSpecializedAgent

Все специализированные агенты наследуются от [`BaseSpecializedAgent`](src/nergal/dialog/agents/base_specialized.py):

```python
class BaseSpecializedAgent(BaseAgent):
    """Базовый класс для специализированных агентов."""
    
    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        style_type: StyleType = StyleType.DEFAULT,
    ) -> None:
        super().__init__(llm_provider, style_type)
    
    @property
    def category(self) -> AgentCategory:
        """Категория агента."""
        return AgentType.get_category(self.agent_type)
    
    async def process(
        self,
        message: str,
        context: dict[str, Any],
        history: list[LLMMessage],
    ) -> AgentResult:
        """Обработка сообщения с использованием accumulated_context."""
        # Базовая реализация...
```

### ContextAwareAgent

Для агентов, которым нужен доступ к памяти пользователя:

```python
class ContextAwareAgent(BaseSpecializedAgent):
    """Агент с доступом к контексту памяти пользователя."""
    
    async def get_memory_context(
        self, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Получить контекст памяти из context."""
        return context.get("memory", {})
```

---

## Регистрация агентов

```python
# В DialogManager
from nergal.dialog.agents import (
    WebSearchAgent,
    KnowledgeBaseAgent,
    TechDocsAgent,
    CodeAnalysisAgent,
    MetricsAgent,
    NewsAgent,
    AnalysisAgent,
    FactCheckAgent,
    ComparisonAgent,
    SummaryAgent,
    ClarificationAgent,
    ExpertiseAgent,
)

# Регистрация агентов
dialog_manager.register_agent(WebSearchAgent(llm_provider, style_type))
dialog_manager.register_agent(KnowledgeBaseAgent(llm_provider, style_type))
dialog_manager.register_agent(TechDocsAgent(llm_provider, style_type))
dialog_manager.register_agent(CodeAnalysisAgent(llm_provider, style_type))
dialog_manager.register_agent(MetricsAgent(llm_provider, style_type))
dialog_manager.register_agent(NewsAgent(llm_provider, style_type))
dialog_manager.register_agent(AnalysisAgent(llm_provider, style_type))
dialog_manager.register_agent(FactCheckAgent(llm_provider, style_type))
dialog_manager.register_agent(ComparisonAgent(llm_provider, style_type))
dialog_manager.register_agent(SummaryAgent(llm_provider, style_type))
dialog_manager.register_agent(ClarificationAgent(llm_provider, style_type))
dialog_manager.register_agent(ExpertiseAgent(llm_provider, style_type))
```

---

## Заключение

Все запланированные агенты реализованы и доступны для использования. Система агентов обеспечивает:

1. **Модульность** — каждый агент отвечает за свою область
2. **Гибкость** — динамическое формирование планов через DispatcherAgent
3. **Расширяемость** — легко добавлять новых агентов через BaseSpecializedAgent
4. **Персонализацию** — интеграция с системой памяти для учета контекста пользователя
5. **Качество** — многоэтапная обработка с проверкой фактов и анализом

Для добавления нового агента:
1. Создать класс, наследующий от `BaseSpecializedAgent`
2. Определить `agent_type` и `system_prompt`
3. Реализовать методы `can_handle()` и `process()`
4. Зарегистрировать агент в `DialogManager`
