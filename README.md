# Nergal - Telegram AI Bot

Telegram бот с интеграцией LLM, системой агентов, веб-поиском и памятью пользователей для круглосуточной работы на VPS.

## Возможности

- 🤖 **AI-диалоги** - интеграция с различными LLM провайдерами (Zai, OpenAI, Anthropic, MiniMax)
- 🎯 **Система агентов** - 14 специализированных агентов для разных типов задач
- 🔍 **Веб-поиск** - поиск информации в интернете с использованием MCP (Model Context Protocol)
- 🧠 **Система памяти** - краткосрочная и долгосрочная память пользователей
- 👥 **Групповые чаты** - работа в группах с упоминаниями и ответами на сообщения
- 🎭 **Стили ответов** - настраиваемые стили ответов (default, silvio_dante)
- 🐳 **Docker** - готовая контейнеризация для простого деплоя
- 📊 **Мониторинг** - Prometheus, Grafana, Loki для наблюдаемости
- ⚡ **uv** - быстрый менеджер зависимостей

## Технологии

- **Python 3.12** - современная версия Python
- **python-telegram-bot** - библиотека для работы с Telegram API
- **pydantic-settings** - управление конфигурацией через переменные окружения
- **httpx** - асинхронный HTTP клиент
- **PostgreSQL** - хранение данных памяти пользователей
- **MCP** - Model Context Protocol для веб-поиска
- **Prometheus** - сбор метрик
- **Grafana** - визуализация и дашборды

## Система агентов

Бот использует систему специализированных агентов:

### Основные агенты
- `default` - общение и финальное формирование ответа
- `dispatcher` - анализ запроса и составление плана выполнения

### Агенты сбора информации
- `web_search` - поиск в интернете
- `knowledge_base` - поиск по корпоративной базе знаний
- `tech_docs` - техническая документация
- `code_analysis` - анализ кода
- `metrics` - получение метрик и статистики
- `news` - агрегация новостей

### Агенты обработки
- `analysis` - анализ данных
- `fact_check` - проверка фактов
- `comparison` - сравнение альтернатив
- `summary` - резюмирование
- `clarification` - уточнение запросов

### Специализированные
- `expertise` - экспертные знания в доменах

Подробнее в [docs/AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) и [docs/AGENT_RECOMMENDATIONS.md](docs/AGENT_RECOMMENDATIONS.md).

## Локальная разработка

### Требования

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) - современный менеджер пакетов
- PostgreSQL (опционально, для системы памяти)

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/finnetrolle/nergal.git
cd nergal
```

2. Установите зависимости:
```bash
uv sync
```

3. Создайте файл `.env` на основе примера:
```bash
cp .env.example .env
```

4. Отредактируйте `.env` и добавьте необходимые ключи:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
LLM_API_KEY=your_llm_api_key
```

### Получение токена бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в `.env`

### Запуск

```bash
uv run bot
```

## Конфигурация

### Основные переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | *обязательно* |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `STYLE` | Стиль ответов (`default`, `silvio_dante`) | `default` |

### LLM провайдер

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `LLM_PROVIDER` | Провайдер LLM (`zai`, `openai`, `anthropic`, `minimax`) | `zai` |
| `LLM_API_KEY` | API ключ LLM провайдера | *обязательно* |
| `LLM_MODEL` | Модель для использования | `glm-4-flash` |
| `LLM_BASE_URL` | Кастомный URL API (опционально) | - |
| `LLM_TEMPERATURE` | Температура генерации | `0.7` |
| `LLM_MAX_TOKENS` | Максимум токенов (опционально) | - |
| `LLM_TIMEOUT` | Таймаут запроса в секундах | `120.0` |

### База данных

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DB_HOST` | Хост базы данных | `localhost` |
| `DB_PORT` | Порт базы данных | `5432` |
| `DB_USER` | Пользователь БД | `nergal` |
| `DB_PASSWORD` | Пароль БД | `nergal_secret` |
| `DB_NAME` | Имя базы данных | `nergal` |

### Веб-поиск

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `WEB_SEARCH_ENABLED` | Включить веб-поиск | `false` |
| `WEB_SEARCH_API_KEY` | API ключ для поиска (по умолчанию `LLM_API_KEY`) | - |
| `WEB_SEARCH_MCP_URL` | URL MCP endpoint для поиска | `https://api.z.ai/api/mcp/web_search_prime/mcp` |
| `WEB_SEARCH_MAX_RESULTS` | Максимальное количество результатов | `5` |
| `WEB_SEARCH_TIMEOUT` | Таймаут запроса в секундах | `30.0` |

### Система памяти

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `MEMORY_SHORT_TERM_MAX_MESSAGES` | Максимум сообщений в истории | `50` |
| `MEMORY_LONG_TERM_ENABLED` | Включить долгосрочную память | `true` |
| `MEMORY_LONG_TERM_EXTRACTION_ENABLED` | Включить извлечение фактов | `true` |
| `MEMORY_CLEANUP_DAYS` | Дней хранения старых сообщений | `30` |

### Speech-to-Text

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `STT_ENABLED` | Включить обработку голосовых | `true` |
| `STT_PROVIDER` | Провайдер STT (`local`, `openai`) | `local` |
| `STT_MODEL` | Модель Whisper | `base` |
| `STT_LANGUAGE` | Код языка | `ru` |
| `STT_MAX_DURATION_SECONDS` | Макс. длительность аудио | `60` |

### Мониторинг

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `MONITORING_ENABLED` | Включить мониторинг | `true` |
| `MONITORING_METRICS_PORT` | Порт для метрик Prometheus | `8000` |
| `MONITORING_JSON_LOGS` | JSON формат логов | `true` |
| `MONITORING_LOG_LEVEL` | Уровень логирования | `INFO` |

### Авторизация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `AUTH_ENABLED` | Включить авторизацию | `true` |
| `AUTH_ADMIN_USER_IDS` | Список Telegram ID администраторов | `[]` |
| `AUTH_ADMIN_ENABLED` | Включить админ-панель | `true` |
| `AUTH_ADMIN_PORT` | Порт админ-панели | `8001` |

### Групповые чаты

Бот может работать в групповых чатах и отвечать только при упоминании или ответе на сообщение.

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `GROUP_CHAT_ENABLED` | Включить работу в группах | `true` |
| `GROUP_CHAT_BOT_NAME` | Имя бота для обнаружения упоминаний | `Sil` |
| `GROUP_CHAT_BOT_USERNAME` | Username бота (без @) | автоопределение |
| `GROUP_CHAT_RESPOND_TO_REPLIES` | Отвечать на ответы на сообщения бота | `true` |
| `GROUP_CHAT_RESPOND_TO_MENTIONS` | Отвечать при упоминании имени/username | `true` |

**Поведение в групповых чатах:**
- В приватных чатах бот отвечает на все сообщения
- В групповых чатах бот отвечает только когда:
  - Кто-то упоминает имя бота (например, "Sil, привет!")
  - Кто-то упоминает @username бота
  - Кто-то отвечает на сообщение бота (reply)

### Агенты

Каждый агент можно включить/выключить отдельно:

| Переменная | По умолчанию |
|------------|--------------|
| `AGENTS_WEB_SEARCH_ENABLED` | `true` |
| `AGENTS_NEWS_ENABLED` | `false` |
| `AGENTS_ANALYSIS_ENABLED` | `false` |
| `AGENTS_FACT_CHECK_ENABLED` | `false` |
| `AGENTS_COMPARISON_ENABLED` | `false` |
| `AGENTS_SUMMARY_ENABLED` | `false` |
| `AGENTS_CODE_ANALYSIS_ENABLED` | `false` |
| `AGENTS_METRICS_ENABLED` | `false` |
| `AGENTS_EXPERTISE_ENABLED` | `false` |
| `AGENTS_CLARIFICATION_ENABLED` | `false` |
| `AGENTS_KNOWLEDGE_BASE_ENABLED` | `false` |
| `AGENTS_TECH_DOCS_ENABLED` | `false` |

Подробнее о настройке LLM провайдеров см. в [docs/LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md).

## Деплой на VPS

### С помощью Docker (рекомендуется)

1. Скопируйте проект на VPS:
```bash
scp -r /path/to/nergal user@your-vps:/path/to/nergal
```

2. На VPS создайте `.env` файл:
```bash
cd /path/to/nergal
cp .env.example .env
nano .env  # Добавьте необходимые ключи
```

3. Запустите с помощью Docker Compose:
```bash
docker compose up -d
```

4. Проверьте логи:
```bash
docker compose logs -f
```

### С мониторингом

```bash
docker compose --profile monitoring up -d
```

Доступы:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Метрики: http://localhost:8000/metrics

### Управление ботом

```bash
# Остановить
docker compose down

# Перезапустить
docker compose restart

# Обновить после изменений в коде
docker compose up -d --build

# Бэкап базы данных
docker compose exec postgres pg_dump -U nergal nergal > backup.sql
```

Подробнее в [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Структура проекта

```
nergal/
├── src/nergal/
│   ├── __init__.py              # Пакет
│   ├── config.py                # Конфигурация (pydantic-settings)
│   ├── main.py                  # Точка входа, логика бота
│   ├── exceptions.py            # Исключения
│   ├── auth.py                  # Авторизация пользователей
│   ├── database/                # Работа с БД
│   │   ├── connection.py        # Подключение
│   │   ├── models.py            # SQLAlchemy модели
│   │   └── repositories.py      # Репозитории
│   ├── dialog/                  # Управление диалогами
│   │   ├── base.py              # Базовые классы агентов
│   │   ├── constants.py         # Константы и промпты
│   │   ├── context.py           # Контекст диалога
│   │   ├── default_agent.py     # DefaultAgent
│   │   ├── dispatcher_agent.py  # DispatcherAgent
│   │   ├── manager.py           # DialogManager
│   │   ├── styles.py            # Стили ответов
│   │   ├── agent_loader.py      # Загрузка агентов по конфигурации
│   │   └── agents/              # Специализированные агенты
│   │       ├── base_specialized.py
│   │       ├── web_search_agent.py
│   │       ├── knowledge_base_agent.py
│   │       ├── tech_docs_agent.py
│   │       ├── code_analysis_agent.py
│   │       ├── metrics_agent.py
│   │       ├── news_agent.py
│   │       ├── analysis_agent.py
│   │       ├── fact_check_agent.py
│   │       ├── comparison_agent.py
│   │       ├── summary_agent.py
│   │       ├── clarification_agent.py
│   │       └── expertise_agent.py
│   ├── llm/                     # LLM провайдеры
│   │   ├── base.py              # Базовый класс
│   │   ├── factory.py           # Фабрика провайдеров
│   │   └── providers/           # Реализации провайдеров
│   │       └── zai.py           # Z.ai реализация
│   ├── memory/                  # Система памяти
│   │   ├── service.py           # MemoryService
│   │   └── extraction.py        # Извлечение фактов
│   ├── monitoring/              # Мониторинг
│   │   ├── health.py            # Health checks
│   │   ├── logging_config.py    # Конфигурация логирования
│   │   └── metrics.py           # Prometheus метрики
│   ├── admin/                   # Admin веб-панель
│   │   └── server.py            # Flask сервер управления
│   ├── stt/                     # Speech-to-Text
│   │   ├── base.py
│   │   ├── factory.py
│   │   ├── audio_utils.py       # Конвертация аудио
│   │   └── providers/
│   │       └── local_whisper.py
│   ├── utils/
│   │   └── markdown_to_telegram.py
│   └── web_search/              # Веб-поиск
│       ├── base.py
│       └── zai_mcp_http.py      # MCP HTTP провайдер
├── database/
│   └── init.sql                 # Инициализация БД
├── docs/
│   ├── AGENT_ARCHITECTURE.md    # Архитектура агентов
│   ├── AGENT_RECOMMENDATIONS.md # Рекомендации по агентам
│   ├── DEPLOYMENT.md            # Гайд по деплою
│   ├── LLM_PROVIDERS.md         # LLM провайдеры
│   └── MONITORING.md            # Мониторинг
├── monitoring/
│   ├── alerts.yml               # Правила алертов
│   ├── alertmanager.yml         # Конфигурация Alertmanager
│   ├── prometheus.yml           # Конфигурация Prometheus
│   ├── loki-config.yml          # Конфигурация Loki
│   ├── promtail-config.yml      # Конфигурация Promtail
│   └── grafana/                 # Grafana дашборды
├── tests/                       # Тесты
├── Dockerfile                   # Docker-образ
├── docker-compose.yml           # Docker Compose конфигурация
├── pyproject.toml               # Зависимости и настройки проекта
├── .python-version              # Версия Python
├── .env.example                 # Пример конфигурации
└── README.md                    # Документация
```

## Команды бота

- `/start` - начать работу с ботом
- `/help` - получить справку
- `/status` - проверить статус системы
- `/clear` - очистить историю диалога

## Разработка

### Форматирование и линтинг

Проект использует [Ruff](https://docs.astral.sh/ruff/) для линтинга и форматирования.

```bash
# Проверка
uv run ruff check .

# Форматирование
uv run ruff format .
```

### Тесты

```bash
# Запуск тестов
uv run pytest

# С покрытием
uv run pytest --cov=nergal
```

### Типизация

```bash
# Проверка типов
uv run mypy src/
```

## Документация

- [AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md) - Архитектура системы агентов
- [AGENT_RECOMMENDATIONS.md](docs/AGENT_RECOMMENDATIONS.md) - Рекомендации по использованию агентов
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Подробный гайд по деплою
- [LLM_PROVIDERS.md](docs/LLM_PROVIDERS.md) - Настройка LLM провайдеров
- [MONITORING.md](docs/MONITORING.md) - Настройка мониторинга

## Лицензия

MIT License. См. файл [LICENSE](LICENSE) для подробностей.
