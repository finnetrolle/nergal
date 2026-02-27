# Agent Architecture Design Guide

This guide describes ZeroClaw's modular, trait-based agent architecture. The design is intentionally language-agnostic—you can implement these patterns in any programming language to create a capable autonomous agent system.

ZEROCLAW IS NOT NERGAL. THIS IS AN ARCHITECTURE OF ANOTHER APPLICATION

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Design Principles](#core-design-principles)
3. [Component Architecture](#component-architecture)
   - [Provider](#provider---llm-backends)
   - [Channel](#channel---messaging-platforms)
   - [Tool](#tool---agent-capabilities)
   - [Memory](#memory---persistence-and-context)
   - [Security Policy](#security-policy---autonomy-and-sandboxing)
   - [Skills](#skills---user-defined-capabilities)
   - [Peripherals](#peripherals---hardware-integration)
   - [Observer](#observer---metrics-and-logging)
4. [Agent Orchestration Loop](#agent-orchestration-loop)
5. [Tool Calling Strategies](#tool-calling-strategies)
6. [Configuration System](#configuration-system)
7. [Implementing the Architecture](#implementing-the-architecture)
   - [Minimum Viable Implementation](#minimum-viable-implementation)
   - [Production-Ready Implementation](#production-ready-implementation)
8. [Examples by Language](#examples-by-language)

---

## Architecture Overview

ZeroClaw's architecture is built around **traits/interfaces** and a **central orchestration loop**. Every major capability is abstracted behind an interface, making the system:

- **Pluggable**: Swap implementations without changing core logic
- **Extensible**: Add new capabilities by implementing traits
- **Testable**: Mock any component for unit testing
- **Maintainable**: Clear boundaries between subsystems

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Orchestration                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Tool Calling & Memory Loading              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Provider    │   │    Memory    │   │  Observer    │
│  (LLM)      │   │  (Context)   │   │  (Metrics)   │
└──────────────┘   └──────────────┘   └──────────────┘
        │
        ├───────────────────┬───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Channel     │   │  Tool (×N)  │   │  Peripherals │
│  (Messaging) │   │  (Actions)   │   │  (Hardware)  │
└──────────────┘   └──────────────┘   └──────────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │ Security     │
                  │ Policy       │
                  └──────────────┘
```

---

## Core Design Principles

### 1. Trait-Based Abstraction

Every major capability is defined as an interface (trait). Core logic depends only on these interfaces, not concrete implementations.

**Benefits:**
- Swap implementations (e.g., change from SQLite to PostgreSQL memory)
- Mock for testing (e.g., fake provider for unit tests)
- Extend by adding new implementations (e.g., new channel)

### 2. Factory Pattern

Each subsystem has a factory that creates instances from configuration keys.

**Example:**
```python
# Factory creates provider from config string
provider = ProviderFactory.create(
    key="anthropic",
    api_key="sk-..."
)
```

### 3. Builder Pattern

Complex objects (especially the Agent) are built using a builder for clean configuration.

### 4. Dependency Injection

Components receive their dependencies (memory, tools, etc.) rather than creating them. This enables swapping and testing.

### 5. Fail-Fast with Explicit Errors

Unsupported operations return clear errors rather than silent fallbacks.

---

## Component Architecture

### Provider — LLM Backends

The **Provider** trait abstracts LLM API interactions.

**Purpose:** Enable swapping between OpenAI, Anthropic, Ollama, and other models without changing agent logic.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `capabilities()` | Declare supported features (native tools, vision, streaming) |
| `chat(request, model, temperature)` | Main chat entry with tools and history |
| `chat_with_system(system, message, model, temperature)` | Simple one-shot with optional system prompt |
| `simple_chat(message, model, temperature)` | Direct interaction without tools |
| `supports_native_tools()` | Does provider support function calling API? |
| `supports_streaming()` | Does provider support streaming responses? |
| `convert_tools(tools)` | Convert unified tool specs to provider format |

**Capabilities Declaration:**

```rust
struct ProviderCapabilities {
    native_tool_calling: bool,  // Can use function calling API
    vision: bool,                  // Can process images
}
```

**Tool Payload Variants:**

Different providers require different formats. Provider converts unified specs:

```rust
enum ToolsPayload {
    Gemini { function_declarations: Vec<JsonValue> },
    Anthropic { tools: Vec<JsonValue> },
    OpenAI { tools: Vec<JsonValue> },
    PromptGuided { instructions: String },  // Fallback: inject as text
}
```

**Implementing a Provider:**

1. Implement all chat methods
2. Declare capabilities
3. Convert tool specs to native format if supported
4. Handle streaming if supported
5. Implement retries/resilience wrapper

**Data Structures:**

```rust
struct ChatMessage {
    role: String,        // "system", "user", "assistant", "tool"
    content: String,
}

struct ToolCall {
    id: String,           // Unique ID for result matching
    name: String,          // Tool name to call
    arguments: String,      // JSON string of arguments
}

struct ChatResponse {
    text: Option<String>,           // Assistant text response
    tool_calls: Vec<ToolCall>,     // Tools to execute
}
```

---

### Channel — Messaging Platforms

The **Channel** trait abstracts user interactions across platforms.

**Purpose:** Enable the agent to receive messages and send responses via Telegram, Discord, Slack, CLI, etc.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `name()` | Channel identifier |
| `send(message, recipient)` | Send a message |
| `listen(tx)` | Start receiving messages (long-running) |
| `health_check()` | Connection health probe |
| `start_typing(recipient)` | Show "typing" indicator |
| `stop_typing(recipient)` | Hide "typing" indicator |
| `supports_draft_updates()` | Can we update messages in-place? |
| `send_draft()` / `update_draft()` / `finalize_draft()` | Progressive streaming responses |
| `cancel_draft()` | Abort a draft message |

**Data Structures:**

```rust
struct ChannelMessage {
    id: String,              // Unique message ID
    sender: String,          // User ID
    reply_target: String,    // Where to reply (channel/user)
    content: String,         // Message text
    channel: String,         // Channel identifier
    timestamp: u64,
    thread_ts: Option<String>, // Thread ID for threaded replies
}

struct SendMessage {
    content: String,
    recipient: String,
    subject: Option<String>,   // Email-style subject
    thread_ts: Option<String>, // Reply to thread
}
```

**Implementing a Channel:**

1. Implement platform-specific API calls
2. Map platform events to `ChannelMessage`
3. Convert `SendMessage` to platform format
4. Support streaming drafts if platform allows
5. Handle auth, rate limits, reconnects

---

### Tool — Agent Capabilities

The **Tool** trait defines agent actions.

**Purpose:** Give the LLM ability to execute code, read files, browse web, control hardware, etc.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `name()` | Unique tool identifier (for LLM function calling) |
| `description()` | Human-readable description for LLM |
| `parameters_schema()` | JSON Schema for validation |
| `execute(args)` | Run the tool with validated arguments |
| `spec()` | Complete spec for LLM registration |

**Data Structures:**

```rust
struct ToolSpec {
    name: String,
    description: String,
    parameters: JsonValue,  // JSON Schema
}

struct ToolResult {
    success: bool,
    output: String,
    error: Option<String>,
}
```

**Parameter Schema:**

JSON Schema describes expected inputs:

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "File path to read"
    },
    "encoding": {
      "type": "string",
      "enum": ["utf-8", "ascii"]
    }
  },
  "required": ["path"]
}
```

**Implementing a Tool:**

1. Define parameter schema
2. Validate inputs in `execute()`
3. Return structured result
4. Use security policy for dangerous operations
5. Never panic; always return errors

**Tool Categories:**

| Category | Examples |
|----------|-----------|
| **Shell** | Execute commands |
| **File** | Read, write, list files |
| **Memory** | Store, recall information |
| **HTTP** | Make web requests |
| **Browser** | Web automation |
| **Search** | Web search queries |
| **Notification** | Send alerts |

---

### Memory — Persistence and Context

The **Memory** trait stores and retrieves agent context.

**Purpose:** Enable long-term retention, conversation history, and semantic search.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `store(key, content, category, session_id)` | Save a memory |
| `recall(query, limit, session_id)` | Keyword search |
| `get(key)` | Get specific memory |
| `list(category, session_id)` | List all in category |
| `forget(key)` | Delete a memory |
| `count()` | Total memories |
| `health_check()` | Backend health |

**Data Structures:**

```rust
enum MemoryCategory {
    Core,              // Long-term facts, preferences
    Daily,             // Session logs
    Conversation,       // Conversation context
    Custom(String),     // User-defined categories
}

struct MemoryEntry {
    id: String,
    key: String,
    content: String,
    category: MemoryCategory,
    timestamp: String,
    session_id: Option<String>,
    score: Option<f64>,  // Relevance score (for embeddings)
}
```

**Memory Backends:**

| Backend | Use Case |
|---------|-----------|
| **SQLite** | Production, structured queries |
| **Markdown** | Human-editable, Git-friendly |
| **Embeddings + Vector** | Semantic search, RAG |
| **None** | Temporary, stateless mode |

**Implementing a Memory:**

1. Choose storage (file, database, cloud)
2. Implement CRUD operations
3. Support session scoping
4. Add optional embeddings for semantic search
5. Handle concurrency safely

---

### Security Policy — Autonomy and Sandboxing

The **Security Policy** defines what the agent can and cannot do.

**Purpose:** Provide guardrails for autonomous execution.

**Autonomy Levels:**

```rust
enum AutonomyLevel {
    DenyAll,           // Manual approval for everything
    ReadOnly,           // Can read, not write/execute
    AllowList,          // Only allowlisted commands
    Restricted,         // Ask for confirmation on dangerous ops
    FullAutonomy,       // No restrictions
}
```

**Policy Checks:**

| Operation | Check |
|-----------|--------|
| Shell command | Allowlist check, sandbox wrap |
| File write | Path allowlist, workspace constraint |
| File read | Path allowlist |
| HTTP request | URL allowlist |
| Tool execution | Autonomy level check |

**Sandboxing:**

```rust
trait Sandbox {
    fn wrap_command(&mut self, cmd: &Command) -> Result<()>;
    fn is_available(&self) -> bool;
    fn name(&self) -> &str;  // "firejail", "bubblewrap", "none"
}
```

**Implementing Security:**

1. Define allowlists in config
2. Check autonomy level before tool calls
3. Wrap shell commands with sandbox
4. Log all denied operations
5. Provide rollback/undo where possible

---

### Skills — User-Defined Capabilities

**Skills** are user or community-defined extensions.

**Purpose:** Let users share capabilities without modifying core code.

**Skill Structure:**

```
~/.zeroclaw/workspace/skills/<skill-name>/
├── SKILL.md          # Human-readable documentation
└── SKILL.toml        # Structured manifest
```

**Skill Manifest:**

```toml
[skill]
name = "weather"
description = "Fetch weather data"
version = "1.0.0"
author = "example"

[[skill.tools]]
name = "get_weather"
description = "Get current weather for a location"
kind = "http"  # "shell" or "script"
command = "https://api.weather.com/current"

[[skill.tools.args]]
name = "location"
description = "City name"
```

**Skill Tool Kinds:**

| Kind | Description |
|------|-------------|
| `shell` | Execute a shell command |
| `http` | Make HTTP request |
| `script` | Run a local script file |

**Implementing Skills:**

1. Define `SKILL.toml` manifest
2. Document in `SKILL.md`
3. Place in workspace `skills/` directory
4. Agent discovers and loads on startup

---

### Peripherals — Hardware Integration

The **Peripheral** trait enables hardware control.

**Purpose:** Connect physical devices (GPIO, sensors, actuators) as agent tools.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `name()` | Device instance name |
| `board_type()` | Board type identifier |
| `connect()` | Open transport (serial, GPIO) |
| `disconnect()` | Cleanup and close |
| `health_check()` | Probe responsiveness |
| `tools()` | Return available tools |

**Hardware Examples:**

- **STM32 boards** (Nucleo, Discovery) via serial
- **Raspberry Pi** GPIO via sysfs/libgpiod
- **Sensors** (I²C, SPI)
- **Actuators** (motors, relays)

**Peripheral Protocol:**

Firmware exposes a simple JSON-based protocol:

```json
// Request
{
  "action": "gpio_read",
  "pin": 5
}

// Response
{
  "status": "ok",
  "result": 1
}
```

**Implementing a Peripheral:**

1. Implement `tools()` to expose capabilities
2. Handle connection logic in `connect()`
3. Clean up resources in `disconnect()`
4. Keep firmware protocol simple and JSON-based

---

### Observer — Metrics and Logging

The **Observer** trait provides observability.

**Purpose:** Track agent behavior, costs, errors.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `record_event(event)` | Log a structured event |
| `record_metric(metric)` | Record a measurement |

**Event Types:**

```rust
enum ObserverEvent {
    AgentStart { provider, model },
    AgentEnd { provider, model, duration, tokens, cost },
    ToolCall { tool, duration, success },
    ToolError { tool, error },
    MemoryStore { key, category },
    MemoryRecall { query, count },
    ChannelMessage { channel, sender },
    SecurityDenial { operation, reason },
}
```

**Metric Types:**

```rust
struct ObserverMetric {
    name: String,       // "tokens_used", "response_time_ms"
    value: f64,
    tags: HashMap<String, String>,  // "model: claude-sonnet-4"
}
```

**Observer Backends:**

- **Console**: Print to stdout
- **File**: Write to log file
- **Prometheus**: Expose metrics endpoint
- **Custom**: Send to your system

---

## Agent Orchestration Loop

The agent's core loop coordinates all components:

### High-Level Flow

```
1. Receive User Message
   └─► Classify (optional: route to specific model)
   └─► Load memory context

2. Build Prompt
   └─► Add system prompt with tool instructions
   └─► Inject retrieved memory
   └─► Add conversation history

3. Call LLM Provider
   └─► Send messages + tool specs
   └─► Get response (text + tool calls)

4. Tool Execution Loop
   ├─► If response has text: Stream to user
   ├─► If response has tool calls:
   │   └─► Execute tools (parallel or sequential)
   │   └─► Format results for LLM
   │   └─► Add to history
   │   └─► Loop back to step 3
   └─► If no tool calls: Return final answer

5. Update Memory (optional)
   └─► Store user message
   └─► Store key learnings
```

### Turn-Level Pseudocode

```python
async def turn(agent, user_message):
    # First turn: add system prompt
    if agent.history.empty():
        system_prompt = build_system_prompt(
            tools=agent.tools,
            skills=agent.skills,
            identity=agent.identity
        )
        agent.history.add(system("system", system_prompt))

    # Load relevant memory
    context = agent.memory_loader.load_context(
        user_message,
        max_entries=5,
        min_score=0.6
    )

    # Enrich user message with context
    enriched_message = user_message
    if context:
        enriched_message = f"{context}\n\n{user_message}"

    # Add user message to history
    agent.history.add(user(enriched_message))

    # Select model (with optional classification)
    model = classify_model(user_message, agent.config)

    # Tool execution loop
    for iteration in range(agent.max_iterations):
        # Convert history for provider
        provider_messages = agent.tool_dispatcher.to_provider_messages(
            agent.history
        )

        # Call LLM
        response = await agent.provider.chat(
            messages=provider_messages,
            tools=agent.tool_specs if uses_native_tools else None,
            model=model,
            temperature=agent.temperature
        )

        # Parse response
        text, tool_calls = agent.tool_dispatcher.parse_response(response)

        # No tools: return final answer
        if not tool_calls:
            final_answer = text or response.text
            agent.history.add(assistant(final_answer))
            agent.trim_history()
            return final_answer

        # Stream partial text to user
        if text:
            print(text)
            agent.history.add(assistant(text))

        # Record tool calls in history
        agent.history.add(assistant_tool_calls(
            text=response.text,
            tool_calls=response.tool_calls
        ))

        # Execute tools
        results = await execute_tools(agent, tool_calls)

        # Format results and add to history
        formatted = agent.tool_dispatcher.format_results(results)
        agent.history.add(formatted)

        agent.trim_history()

    # Exceeded iterations
    raise AgentError("Max tool iterations exceeded")
```

### Memory Loading

The `MemoryLoader` retrieves relevant context:

```rust
trait MemoryLoader {
    fn load_context(&self, memory: &Memory, query: &str)
        -> impl Future<Output = String>;
}
```

**Strategies:**

1. **Keyword match**: Query memory by terms
2. **Vector similarity**: Use embeddings for semantic search
3. **Recent**: Last N conversations
4. **Category**: Filter by type (core, daily, conversation)

---

## Tool Calling Strategies

### Native Tool Calling

**Provider supports function calling API:**

1. Agent sends tool definitions in API request
2. LLM returns structured tool calls with IDs
3. Agent executes tools and returns results with IDs
4. LLM processes results and continues

**Flow:**

```
User: "Read hello.txt"

Provider Request:
  messages: [...]
  tools: [{
    name: "file_read",
    description: "Read a file",
    parameters: {type: "object", properties: {...}}
  }]

Provider Response:
  content: ""
  tool_calls: [{
    id: "call_abc123",
    name: "file_read",
    arguments: "{\"path\":\"hello.txt\"}"
  }]

Agent Execution:
  Execute file_read(path="hello.txt")

Provider Request:
  messages: [..., tool_results: [{
    tool_call_id: "call_abc123",
    content: "Hello, World!"
  }]

Provider Response:
  content: "The file contains: Hello, World!"
  tool_calls: []
```

### XML-Based Tool Calling

**Fallback for providers without function calling:**

1. Inject tool instructions into system prompt
2. LLM outputs tool calls as XML: `<invoke>{"name":"tool","args":{}}</invoke>`
3. Agent parses XML and executes
4. Results formatted as: `<result name="tool">output</result>`

**System Prompt Addition:**

```
## Tool Use Protocol

To use a tool, wrap a JSON object in <invoke> tags:

<invoke>
{"name": "file_read", "arguments": {"path": "hello.txt"}}
</invoke>

You may use multiple tools in a single response.
```

### Tool Dispatcher

The `ToolDispatcher` trait abstracts tool calling strategies:

```rust
trait ToolDispatcher {
    fn parse_response(&self, response: &ChatResponse)
        -> (String, Vec<ParsedToolCall>);

    fn format_results(&self, results: &[ToolExecutionResult])
        -> ConversationMessage;

    fn prompt_instructions(&self, tools: &[Tool])
        -> String;

    fn to_provider_messages(&self, history: &[ConversationMessage])
        -> Vec<ChatMessage>;

    fn should_send_tool_specs(&self) -> bool;
}
```

**Implementations:**

- `NativeToolDispatcher`: Use provider's function calling API
- `XmlToolDispatcher`: Parse/generate XML-based tool calls

---

## Configuration System

A hierarchical configuration system supports:

### Config Resolution Order

1. Environment variables (`ZEROCLAW_*`)
2. Active workspace marker
3. `~/.zeroclaw/config.toml`

### Config Sections

```toml
[agent]
max_tool_iterations = 10
max_history_messages = 50
parallel_tools = true
temperature = 0.7
tool_dispatcher = "native"  # or "xml"

[autonomy]
level = "restricted"  # deny_all, read_only, allow_list, restricted, full
allowlist_shell = ["ls", "cat", "grep"]
denylist_patterns = ["rm -rf", "format"]

[memory]
backend = "sqlite"  # or "markdown", "none"
auto_save = true
min_relevance_score = 0.6

[skills]
prompt_injection_mode = "default"  # default, minimal, off
enabled = true

[provider]
default = "openrouter"
model = "anthropic/claude-sonnet-4-20250514"

[model_routes]
hint = "fast"
provider = "openai"
model = "gpt-4o-mini"

[channels_config.telegram]
enabled = true
bot_token = "..."
```

### Runtime Proxy Configuration

Services can be proxied through a runtime:

```toml
[proxy]
enabled = true
host = "127.0.0.1"
port = 8080
allowed_services = ["provider.anthropic", "channel.telegram"]
```

---

## Implementing the Architecture

### Minimum Viable Implementation

A minimal agent needs only:

1. **Provider** — At least one LLM backend
2. **Tool** — At least shell execution
3. **Agent Loop** — Basic message → LLM → tool execution flow

**Pseudocode:**

```python
class MinimalAgent:
    def __init__(self, provider, tools):
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.history = []

    async def process(self, message):
        self.history.append({"role": "user", "content": message})

        for _ in range(10):  # Max iterations
            # Get LLM response
            response = await self.provider.chat(
                messages=self.history,
                tools=[t.spec() for t in self.tools.values()]
            )

            # Check for tool calls
            if not response.tool_calls:
                self.history.append({
                    "role": "assistant",
                    "content": response.text
                })
                return response.text

            # Execute tools
            for call in response.tool_calls:
                tool = self.tools[call.name]
                result = await tool.execute(call.arguments)
                self.history.append({
                    "role": "tool",
                    "content": json.dumps(result)
                })

    async def run_interactive(self):
        while True:
            user_input = input("User: ")
            if user_input == "/quit":
                break
            response = await self.process(user_input)
            print(f"Agent: {response}")
```

### Production-Ready Implementation

Add these components:

1. **Memory** — SQLite or similar for persistence
2. **Channel** — Multiple messaging platforms
3. **Security Policy** — Allowlists and sandboxing
4. **Observer** — Metrics and logging
5. **Skills** — User-defined extensions
6. **Configuration** — TOML/YAML with env overrides
7. **Factory Pattern** — Dynamic component creation
8. **Builder Pattern** — Clean agent construction
9. **Error Handling** — Resilience and retries
10. **Streaming** — Progressive responses

---

## Examples by Language

### Python Implementation Skeleton

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json
import asyncio

# === Provider Trait ===

class Provider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict], tools: Optional[List[Dict]],
                 model: str, temperature: float) -> Dict:
        pass

    @abstractmethod
    def supports_native_tools(self) -> bool:
        pass

class OpenAIProvider(Provider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def chat(self, messages, tools, model, temperature):
        # Implementation using OpenAI API
        import openai
        client = openai.AsyncOpenAI(api_key=self.api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or None,
            temperature=temperature
        )
        return {
            "text": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls or []
        }

    def supports_native_tools(self):
        return True

# === Tool Trait ===

@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str]

class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def parameters_schema(self) -> Dict:
        pass

    @abstractmethod
    async def execute(self, args: Dict) -> ToolResult:
        pass

class ShellTool(Tool):
    def name(self):
        return "shell"

    def description(self):
        return "Execute a shell command"

    def parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        }

    async def execute(self, args):
        command = args["command"]
        # TODO: Security check here
        process = await asyncio.create_subprocess_shell(command)
        stdout, _ = await process.communicate()
        return ToolResult(True, stdout, None)

# === Memory Trait ===

class Memory(ABC):
    @abstractmethod
    async def store(self, key: str, content: str, category: str,
                  session_id: Optional[str]):
        pass

    @abstractmethod
    async def recall(self, query: str, limit: int,
                    session_id: Optional[str]) -> List[Dict]:
        pass

class SqliteMemory(Memory):
    def __init__(self, db_path: str):
        import sqlite3
        self.conn = sqlite3.connect(db_path)

    async def store(self, key, content, category, session_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO memories (key, content, category, session_id) VALUES (?, ?, ?, ?)",
            (key, content, category, session_id)
        )
        self.conn.commit()

    async def recall(self, query, limit, session_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memories WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        )
        return cursor.fetchall()

# === Agent ===

class Agent:
    def __init__(self, provider: Provider, tools: List[Tool],
                 memory: Memory):
        self.provider = provider
        self.tools = {t.name(): t for t in tools}
        self.memory = memory
        self.history: List[Dict] = []
        self.max_iterations = 10

    async def turn(self, user_message: str) -> str:
        # Add user message to history
        self.history.append({"role": "user", "content": user_message})

        for _ in range(self.max_iterations):
            # Prepare tools specs
            tool_specs = [self._tool_spec(t) for t in self.tools.values()]

            # Call provider
            response = await self.provider.chat(
                messages=self.history,
                tools=tool_specs if self.provider.supports_native_tools() else None,
                model="gpt-4",
                temperature=0.7
            )

            tool_calls = response.get("tool_calls", [])

            # No tools: return final answer
            if not tool_calls:
                self.history.append({"role": "assistant", "content": response["text"]})
                return response["text"]

            # Stream partial text
            if response["text"]:
                print(response["text"], end="", flush=True)
                self.history.append({"role": "assistant", "content": response["text"]})

            # Execute tools
            for call in tool_calls:
                tool = self.tools.get(call["function"]["name"])
                if tool:
                    args = json.loads(call["function"]["arguments"])
                    result = await tool.execute(args)
                    self.history.append({
                        "role": "tool",
                        "content": json.dumps({
                            "tool_call_id": call["id"],
                            "content": result.output
                        })
                    })

        raise Exception("Max iterations exceeded")

    def _tool_spec(self, tool: Tool) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name(),
                "description": tool.description(),
                "parameters": tool.parameters_schema()
            }
        }

# === Usage ===

async def main():
    provider = OpenAIProvider(api_key="sk-...")
    tools = [ShellTool()]
    memory = SqliteMemory("agent.db")

    agent = Agent(provider, tools, memory)

    while True:
        user_input = input("User: ")
        if user_input == "/quit":
            break
        response = await agent.turn(user_input)
        print(f"\nAgent: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript/TypeScript Implementation Skeleton

```typescript
// === Provider Interface ===

interface ChatMessage {
  role: string;
  content: string;
}

interface ToolCall {
  id: string;
  name: string;
  arguments: string;
}

interface ChatResponse {
  text?: string;
  toolCalls: ToolCall[];
}

interface Provider {
  chat(messages: ChatMessage[], tools?: any[], model: string, temperature: number):
    Promise<ChatResponse>;
  supportsNativeTools(): boolean;
}

class OpenAIProvider implements Provider {
  constructor(private apiKey: string) {}

  async chat(messages, tools, model, temperature) {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages,
        tools,
        temperature,
      }),
    });

    const data = await response.json();
    return {
      text: data.choices[0].message.content,
      toolCalls: data.choices[0].message.tool_calls || [],
    };
  }

  supportsNativeTools(): boolean {
    return true;
  }
}

// === Tool Interface ===

interface ToolResult {
  success: boolean;
  output: string;
  error?: string;
}

interface Tool {
  name(): string;
  description(): string;
  parametersSchema(): object;
  execute(args: any): Promise<ToolResult>;
}

class ShellTool implements Tool {
  name(): string {
    return 'shell';
  }

  description(): string {
    return 'Execute a shell command';
  }

  parametersSchema(): object {
    return {
      type: 'object',
      properties: {
        command: { type: 'string' },
      },
      required: ['command'],
    };
  }

  async execute(args: any): Promise<ToolResult> {
    // Execute shell command
    const { exec } = require('child_process');
    return new Promise((resolve) => {
      exec(args.command, (error, stdout) => {
        resolve({
          success: !error,
          output: stdout || '',
          error: error?.message,
        });
      });
    });
  }
}

// === Agent ===

class Agent {
  constructor(
    private provider: Provider,
    private tools: Map<string, Tool>,
    private maxIterations: number = 10,
  ) {}

  private history: ChatMessage[] = [];

  async turn(userMessage: string): Promise<string> {
    this.history.push({ role: 'user', content: userMessage });

    for (let i = 0; i < this.maxIterations; i++) {
      const toolSpecs = Array.from(this.tools.values()).map(t => ({
        type: 'function',
        function: {
          name: t.name(),
          description: t.description(),
          parameters: t.parametersSchema(),
        },
      }));

      const response = await this.provider.chat(
        this.history,
        this.provider.supportsNativeTools() ? toolSpecs : undefined,
        'gpt-4',
        0.7,
      );

      if (response.toolCalls.length === 0) {
        this.history.push({ role: 'assistant', content: response.text || '' });
        return response.text || '';
      }

      if (response.text) {
        process.stdout.write(response.text);
        this.history.push({ role: 'assistant', content: response.text });
      }

      // Execute tools
      for (const call of response.toolCalls) {
        const tool = this.tools.get(call.name);
        if (tool) {
          const args = JSON.parse(call.arguments);
          const result = await tool.execute(args);
          this.history.push({
            role: 'tool',
            content: JSON.stringify({
              toolCallId: call.id,
              content: result.output,
            }),
          });
        }
      }
    }

    throw new Error('Max iterations exceeded');
  }
}

// === Usage ===

async function main() {
  const provider = new OpenAIProvider('sk-...');
  const tools = new Map([['shell', new ShellTool()]]);
  const agent = new Agent(provider, tools);

  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  for await (const line of readline) {
    if (line === '/quit') break;
    const response = await agent.turn(line);
    console.log(`Agent: ${response}`);
  }

  readline.close();
}

main().catch(console.error);
```

---

## Summary

ZeroClaw's architecture is built on:

1. **Traits/Interfaces** — Abstract all major capabilities
2. **Factory Pattern** — Dynamic component creation
3. **Builder Pattern** — Clean configuration
4. **Orchestration Loop** — Tool execution with LLM coordination
5. **Pluggable Components** — Swap implementations without core changes
6. **Security-First** — Guardrails and sandboxing
7. **Observable** — Metrics and logging throughout
8. **Extensible** — Skills and peripherals for custom capabilities

To recreate this architecture:

1. Define core traits (Provider, Tool, Channel, Memory, Observer)
2. Implement concrete versions for your needs
3. Build the agent orchestration loop
4. Add configuration and factory patterns
5. Implement security policies
6. Add observability
7. (Optional) Add skills and peripherals

The result is a modular, testable, and extensible agent system.
