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
# Comparison Agent Keywords
# =============================================================================

COMPARISON_KEYWORDS = [
    "сравни", "разница", "отличия", "против", "vs", "или",
    "что лучше", "какой выбрать", "преимущества", "недостатки",
    "плюсы", "минусы", "за и против", "выбрать между",
    "compare", "difference", "versus", "which is better",
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
# Agent Descriptions (for dispatcher prompts)
# =============================================================================

AGENT_DESCRIPTIONS: dict[str, str] = {
    # Core agents
    "default": "общий агент для обычных разговоров, приветствий, простых вопросов, личных бесед, финального формирования ответа пользователю",
    "dispatcher": "агент-планировщик для маршрутизации сообщений и составления планов выполнения",

    # Information gathering agents
    "web_search": "агент для поиска информации в интернете, актуальных новостей, фактов, погоды, курсов валют",

    # Processing agents
    "fact_check": "агент для проверки фактов на достоверность, верификации информации из поиска, оценки надёжности источников",
    "comparison": "агент для структурированного сравнения альтернатив, создания сравнительных таблиц, взвешенной оценки",

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
    "information": ["web_search"],
    "processing": ["fact_check", "comparison"],
    "specialized": ["expertise"],
}


# =============================================================================
# Default Agent Prompts
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """Ты — полезный AI-ассистент. Отвечай на вопросы пользователей
помогай с решением задач и поддерживай диалог.

Будь дружелюбным, но профессиональным. Если не знаешь ответа — честно признай это."""

DEFAULT_FALLBACK_RESPONSE = "Извините, я не смог обработать ваш запрос. Попробуйте переформулировать вопрос."
