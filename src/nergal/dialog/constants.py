"""Constants for dialog processing.

This module contains keywords, patterns, and other constants used
for message classification and agent selection. All agent keywords
are centralized here for easy maintenance and consistency.
"""

# =============================================================================
# Web Search Agent Keywords
# =============================================================================

# Keywords that indicate a search request
SEARCH_KEYWORDS = [
    # Direct search commands
    "найди",
    "поиск",
    "find",
    "search",
    "look up",
    "google",
    # Definition questions
    "что такое",
    "what is",
    "who is",
    "кто такой",
    "кто такая",
    # Specification questions
    "какой",
    "какая",
    "какое",
    "какие",
    # Time/place questions
    "when did",
    "where is",
    "где находится",
    "когда было",
    # News and current events
    "последние новости",
    "latest news",
    "новости",
    "news",
    "current",
    # Time-related
    "сейчас",
    "сегодня",
    "today",
    # Weather
    "погода",
    "weather",
    # Financial
    "курс",
    "exchange rate",
    "цена",
    "price",
    "сколько стоит",
    "how much",
    # Trends
    "trending",
    "popular",
]

# Regex patterns that indicate search intent
SEARCH_PATTERNS = [
    r"(?:найди|поиск|find|search|look up)\s+(.+)",
    r"(?:что такое|what is|what's)\s+(.+)",
    r"(?:кто такой|кто такая|who is)\s+(.+)",
    r"(?:какой|какая|какое|какие)\s+(?:сейчас|сегодня|последние)\s+(.+)",
    r"(?:when did|where is|где находится|когда было)\s+(.+)",
    r"(?:новости|news)\s+(?:про|о|about|on)\s+(.+)",
    r"(?:последние|latest|current)\s+(.+)",
]

# Filler words to remove from search queries
FILLER_WORDS = [
    "пожалуйста",
    "пж",
    "pls",
    "please",
    "можешь",
    "can you",
    "хочу",
    "i want",
    "нужно",
    "need to",
]

# Time-related words that boost search confidence
TIME_RELATED_WORDS = [
    "сейчас",
    "сегодня",
    "недавно",
    "current",
    "today",
    "recent",
    "latest",
]


# =============================================================================
# News Agent Keywords
# =============================================================================

# Keywords that indicate news aggregation request
NEWS_KEYWORDS = [
    # Direct news requests
    "новости",
    "news",
    "пресса",
    "сми",
    "press",
    "media",
    # Source comparison
    "сравни источники",
    "compare sources",
    "что пишут",
    "what do they write",
    "сколько источников",
    "multiple sources",
    # News analysis
    "агрегация",
    "aggregation",
    "обзор прессы",
    "press review",
    "итоги дня",
    "daily summary",
    # Source verification
    "достоверность",
    "credibility",
    "проверь источник",
    "verify source",
    "предвзятость",
    "bias",
    # Additional news keywords from NewsAgent
    "газета",
    "журнал",
    "newspaper",
    "journal",
    "сообщается",
    "источники",
    "репортаж",
    "корреспондент",
    "reported",
    "sources",
    "coverage",
    "breaking",
    "заявил",
    "объявил",
    "опубликовал",
    "анонс",
    "announced",
    "stated",
    "published",
    "revealed",
    "скандал",
    "событие",
    "происшествие",
    "чрезвычайное",
    "scandal",
    "event",
    "incident",
    "emergency",
    "политика",
    "экономика",
    "финансы",
    "технологии",
    "politics",
    "economy",
    "finance",
    "technology",
]

# Patterns for news aggregation intent
NEWS_PATTERNS = [
    r"(?:новости|news)\s+(?:про|о|about|on)\s+(.+)",
    r"(?:что|what)\s+(?:пишут|do they write|говорят|do they say)\s+(?:про|о|about)?\s*(.+)",
    r"(?:сравни|compare)\s+(?:источники|sources)\s+(?:про|о|about)?\s*(.+)",
    r"(?:агрегация|aggregate)\s+(.+)",
    r"(?:сколько|how many)\s+(?:источников|sources)\s+(.+)",
]

# High-credibility source patterns
CREDIBLE_SOURCES = [
    "reuters", "associated press", "bbc", "the guardian",
    "the new york times", "washington post", "the economist",
    "bloomberg", "financial times", "the wall street journal",
    "nature", "science", "the lancet",
    "тасс", "риа новости", "интерфакс", "коммерсант",
    "ведомости", "рбк", "медуза", "дождь",
]

# Source categories by bias tendency
SOURCE_BIAS = {
    "left": ["the guardian", "the new york times", "cnn", "msnbc", "huffpost"],
    "center": ["reuters", "associated press", "bbc", "the economist", "bloomberg"],
    "right": ["fox news", "the wall street journal", "breitbart", "daily mail"],
    "russia_state": ["тасс", "риа новости", "россия сегодня"],
    "russia_independent": ["медуза", "дождь", "новая газета", "коммерсант"],
}


# =============================================================================
# Analysis Agent Keywords
# =============================================================================

ANALYSIS_KEYWORDS = [
    "сравни", "проанализируй", "в чем разница", "преимущества",
    "недостатки", "плюсы", "минусы", "за и против", "выводы",
    "какой вывод", "что лучше", "что выбрать", "оцени",
    "analyze", "analysis", "compare", "comparison",
    "pros and cons", "advantages", "disadvantages",
]


# =============================================================================
# Comparison Agent Keywords
# =============================================================================

COMPARISON_KEYWORDS = [
    "сравни", "разница", "отличия", "против", "vs", "или",
    "что лучше", "какой выбрать", "преимущества", "недостатки",
    "плюсы", "минусы", "за и против", "выбрать между",
    "compare", "difference", "versus", "which is better",
]


# =============================================================================
# Summary Agent Keywords
# =============================================================================

SUMMARY_KEYWORDS = [
    "кратко", "сократи", "резюме", "суть", "главное",
    "основное", "tldr", "tl;dr", "summary", "в двух словах",
    "выдели главное", "перечисли основные", "итог",
    "summarize", "brief", "essence", "key points",
]


# =============================================================================
# Clarification Agent Keywords
# =============================================================================

CLARIFICATION_KEYWORDS = [
    # Ambiguity indicators
    "настроить", "проблема", "ошибка", "не работает",
    "лучше", "оптимальный", "правильный", "нужно",
    "сделать", "изменить", "проверить", "понять",
    # Question patterns
    "как", "что", "почему", "зачем", "когда",
]


# =============================================================================
# Fact Check Agent Keywords
# =============================================================================

FACT_CHECK_KEYWORDS = [
    "правда", "ложь", "проверь", "достоверно", "верно",
    "факт", "миф", "подтверди", "опровергни",
    "fact check", "true", "false", "verify", "verification",
    "достоверность", "проверка фактов",
]


# =============================================================================
# Expertise Agent Keywords
# =============================================================================

EXPERTISE_KEYWORDS = [
    # Domain-specific triggers
    "безопасность", "security", "уязвимость", "vulnerability",
    "юридическ", "legal", "закон", "law",
    "финанс", "finance", "инвестици", "investment",
    "архитектур", "architecture", "проектировани", "design",
    "эксперт", "expert", "специалист", "specialist",
    "профессиональн", "professional",
]


# =============================================================================
# Tech Docs Agent Keywords
# =============================================================================

TECH_DOCS_KEYWORDS = [
    "документация", "documentation", "docs", "api",
    "справочник", "reference", "гайд", "guide",
    "tutorial", "туториал", "пример", "example",
    "как использовать", "how to use", "usage",
    "метод", "method", "функция", "function",
    "класс", "class", "параметр", "parameter",
]


# =============================================================================
# Code Analysis Agent Keywords
# =============================================================================

CODE_ANALYSIS_KEYWORDS = [
    "код", "code", "функция", "function", "класс", "class",
    "метод", "method", "модуль", "module", "библиотека", "library",
    "алгоритм", "algorithm", "реализация", "implementation",
    "отладка", "debug", "дебаг", "ошибка в коде", "bug",
    "рефакторинг", "refactor", "оптимизация", "optimization",
    "архитектура кода", "code architecture",
    "объясни код", "explain code", "как работает", "how it works",
]


# =============================================================================
# Metrics Agent Keywords
# =============================================================================

METRICS_KEYWORDS = [
    "метрики", "metrics", "статистика", "statistics",
    "показатели", "indicators", "kpi", "KPI",
    "производительность", "performance", "скорость", "speed",
    "количество", "count", "число", "number",
    "график", "chart", "диаграмма", "diagram",
    "мониторинг", "monitoring", "аналитика", "analytics",
]


# =============================================================================
# Knowledge Base Agent Keywords
# =============================================================================

KNOWLEDGE_BASE_KEYWORDS = [
    "база знаний", "knowledge base", "kb",
    "регламент", "regulation", "стандарт", "standard",
    "политика", "policy", "процедура", "procedure",
    "инструкция", "instruction", "руководство", "manual",
    "внутренн", "internal", "корпоративн", "corporate",
]


# =============================================================================
# Agent Descriptions (for dispatcher prompts)
# =============================================================================

AGENT_DESCRIPTIONS: dict[str, str] = {
    # Core agents
    "default": "общий агент для обычных разговоров, приветствий, простых вопросов, личных бесед, финального формирования ответа пользователю",
    "dispatcher": "агент-планировщик для маршрутизации сообщений и составления планов выполнения",
    
    # Information gathering agents
    "web_search": "агент для поиска информации в интернете, актуальных новостей, фактов, погоды, курсов валют",
    "knowledge_base": "агент для поиска по корпоративной базе знаний, внутренней документации, регламентам, стандартам компании",
    "tech_docs": "агент для поиска по технической документации библиотек и фреймворков, API справочники, примеры кода",
    "code_analysis": "агент для анализа кодовой базы, поиска использования функций, объяснения работы кода, архитектурного анализа",
    "metrics": "агент для получения метрик производительности, статистики, KPI, количественных данных из систем мониторинга",
    "news": "агент для агрегации новостей из нескольких источников, сравнения информации, выявления консенсуса и противоречий, отслеживания ссылок и оценки достоверности источников",
    
    # Processing agents
    "analysis": "агент для анализа данных, сравнения информации, выявления закономерностей, синтеза выводов",
    "fact_check": "агент для проверки фактов на достоверность, верификации информации из поиска, оценки надёжности источников",
    "comparison": "агент для структурированного сравнения альтернатив, создания сравнительных таблиц, взвешенной оценки",
    "summary": "агент для резюмирования длинных текстов, выделения ключевых пунктов, создания TL;DR",
    "clarification": "агент для уточнения неоднозначных запросов, генерации уточняющих вопросов, дисамбигуации",
    
    # Specialized agents
    "expertise": "агент для экспертных знаний в специфических доменах: безопасность, юридические вопросы, финансы, архитектура",
    
    # Legacy agents (kept for backward compatibility)
    "faq": "агент для ответов на часто задаваемые вопросы",
    "small_talk": "агент для легких разговоров и светской беседы",
    "task": "агент для выполнения конкретных задач",
}


# =============================================================================
# Agent Categories
# =============================================================================

# Agents organized by category for documentation and routing
AGENT_CATEGORIES = {
    "core": ["default", "dispatcher"],
    "information": ["web_search", "knowledge_base", "tech_docs", "code_analysis", "metrics", "news"],
    "processing": ["analysis", "fact_check", "comparison", "summary", "clarification"],
    "specialized": ["expertise"],
}


# =============================================================================
# Default Agent Prompts
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """Ты — полезный AI-ассистент. Отвечай на вопросы пользователей
помогай с решением задач и поддерживай диалог.

Будь дружелюбным, но профессиональным. Если не знаешь ответа — честно признай это."""

DEFAULT_FALLBACK_RESPONSE = "Извините, я не смог обработать ваш запрос. Попробуйте переформулировать вопрос."
