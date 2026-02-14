"""Constants for dialog processing.

This module contains keywords, patterns, and other constants used
for message classification and agent selection.
"""

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
]

# Patterns for news aggregation intent
NEWS_PATTERNS = [
    r"(?:новости|news)\s+(?:про|о|about|on)\s+(.+)",
    r"(?:что|what)\s+(?:пишут|do they write|говорят|do they say)\s+(?:про|о|about)?\s*(.+)",
    r"(?:сравни|compare)\s+(?:источники|sources)\s+(?:про|о|about)?\s*(.+)",
    r"(?:агрегация|aggregate)\s+(.+)",
    r"(?:сколько|how many)\s+(?:источников|sources)\s+(.+)",
]
