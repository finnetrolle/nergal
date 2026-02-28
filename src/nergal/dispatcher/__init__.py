"""Tool Dispatcher system for Nergal.

This module provides the dispatcher abstractions for bridging
LLM responses with tool execution.

Exported classes:
    - ToolDispatcher: Abstract base class for dispatchers
    - ParsedToolCall: Dataclass for parsed tool calls
    - NativeToolDispatcher: For providers with native tool support
    - XmlToolDispatcher: For text-only providers
"""

from nergal.dispatcher.base import (
    ParsedToolCall,
    ToolDispatcher,
    get_dispatcher,
)
from nergal.dispatcher.native import NativeToolDispatcher
from nergal.dispatcher.xml import XmlToolDispatcher

__all__ = [
    "ToolDispatcher",
    "ParsedToolCall",
    "NativeToolDispatcher",
    "XmlToolDispatcher",
    "get_dispatcher",
]
