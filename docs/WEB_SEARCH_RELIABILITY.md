# Web Search Agent: Reliability and Telemetry Analysis

This document provides a detailed analysis of the web search agent architecture, identifies potential reliability issues, and proposes improvements for better observability and troubleshooting.

## Current Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Web Search Flow                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Message                                                                │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐      │
│  │ WebSearchAgent  │────▶│   LLM Provider   │────▶│ Search Queries  │      │
│  │ (can_handle)    │     │ (generate query) │     │ Generated       │      │
│  └─────────────────┘     └──────────────────┘     └─────────────────┘      │
│         │                                                                     │
│         ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │              ZaiMcpHttpSearchProvider                            │        │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │        │
│  │  │ MCP Init      │─▶│ Tools/List    │─▶│ Tools/Call        │   │        │
│  │  │ (session)     │  │ (discover)    │  │ (search)          │   │        │
│  │  └───────────────┘  └───────────────┘  └───────────────────┘   │        │
│  └─────────────────────────────────────────────────────────────────┘        │
│         │                                                                     │
│         ▼                                                                     │
│  ┌─────────────────┐     ┌──────────────────┐                              │
│  │ Parse Results   │────▶│ Generate Response│────▶ AgentResult             │
│  │ (SearchResult)  │     │ (LLM synthesis)  │                              │
│  └─────────────────┘     └──────────────────┘                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose |
|------|---------|
| [`web_search_agent.py`](../src/nergal/dialog/agents/web_search_agent.py) | Agent logic: query generation, search orchestration, response synthesis |
| [`zai_mcp_http.py`](../src/nergal/web_search/zai_mcp_http.py) | MCP protocol implementation over HTTP with SSE |
| [`base.py`](../src/nergal/web_search/base.py) | Base classes: `SearchRequest`, `SearchResult`, `SearchResults` |
| [`models.py`](../src/nergal/database/models.py) | `WebSearchTelemetry` model |
| [`repositories.py`](../src/nergal/database/repositories.py) | `WebSearchTelemetryRepository` for database operations |

---

## Current Telemetry

### What's Already Tracked

#### 1. Database Telemetry (`WebSearchTelemetry`)

| Field | Type | Description |
|-------|------|-------------|
| `query` | TEXT | Search query |
| `status` | VARCHAR | `success`, `error`, `timeout`, `empty` |
| `results_count` | INTEGER | Number of results returned |
| `error_type` | VARCHAR | Exception class name |
| `error_message` | TEXT | Error message |
| `error_stack_trace` | TEXT | Full stack trace |
| `http_status_code` | INTEGER | HTTP status from API |
| `api_response_time_ms` | INTEGER | API response time |
| `api_session_id` | VARCHAR | MCP session ID |
| `raw_response` | JSONB | Raw API response (truncated if large) |
| `total_duration_ms` | INTEGER | Total search operation time |
| `init_duration_ms` | INTEGER | MCP initialization time |
| `tools_list_duration_ms` | INTEGER | Tools list call time |
| `search_call_duration_ms` | INTEGER | Actual search call time |
| `provider_name` | VARCHAR | Search provider name |
| `tool_used` | VARCHAR | MCP tool name |

#### 2. Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `bot_web_search_requests_total` | Counter | `status` |
| `bot_web_search_duration_seconds` | Histogram | - |

#### 3. TelemetryContext (in-memory)

Tracks timing for each phase of the MCP protocol:
- Init duration
- Tools list duration
- Search call duration
- Total duration

---

## Identified Issues

### 1. No Retry Mechanism

**Problem**: If a search fails due to transient network issues, there's no automatic retry.

**Location**: [`zai_mcp_http.py:454-578`](../src/nergal/web_search/zai_mcp_http.py:454)

```python
# Current: Single attempt, no retry
async def search(self, request: SearchRequest, ...) -> SearchResults:
    try:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # ... search logic
    except httpx.TimeoutException as e:
        # No retry, just raise
        raise SearchError("Request timeout", ...)
```

### 2. No Circuit Breaker

**Problem**: Repeated failures to the search API will continue indefinitely, potentially worsening the situation.

**Impact**: 
- Wasted resources on repeated failing requests
- No automatic recovery detection
- Cascading failures

### 3. Limited Error Categorization

**Problem**: Errors are tracked but not well categorized for alerting.

**Current error types**:
- `SearchError` (generic)
- `SearchProviderError`
- `SearchRateLimitError`
- `SearchTimeoutError`
- `SearchConnectionError`

**Missing categorization**:
- Authentication failures
- Quota exceeded
- Service unavailable (503)
- Invalid response format

### 4. No Health Check Endpoint

**Problem**: No way to proactively check if the search provider is healthy.

**Impact**:
- Issues discovered only when users try to search
- No early warning system

### 5. Incomplete Agent-Level Telemetry

**Problem**: `WebSearchAgent` doesn't track its own telemetry separately from the search provider.

**Missing metrics**:
- Query generation time
- Query generation failures
- Response synthesis time
- Fallback query usage

### 6. No Alerting Rules for Search Failures

**Problem**: Prometheus alerts exist for general errors but not specifically for search reliability.

### 7. Limited Observability for Empty Results

**Problem**: Empty results are tracked but not analyzed for patterns.

**Questions that can't be answered**:
- Are empty results due to bad queries?
- Are empty results due to API issues?
- Which types of queries consistently return no results?

---

## Proposed Improvements

### 1. Implement Retry with Exponential Backoff

```python
# Proposed implementation
class RetryConfig:
    max_retries: int = 3
    base_delay_ms: int = 500
    max_delay_ms: int = 5000
    retryable_errors: set[str] = {
        "TimeoutError",
        "ConnectionError", 
        "SearchTimeoutError",
        "SearchConnectionError",
    }

async def search_with_retry(
    self, 
    request: SearchRequest,
    retry_config: RetryConfig = RetryConfig(),
) -> SearchResults:
    last_error = None
    for attempt in range(retry_config.max_retries):
        try:
            return await self._do_search(request)
        except Exception as e:
            error_name = type(e).__name__
            if error_name not in retry_config.retryable_errors:
                raise
            last_error = e
            delay = min(
                retry_config.base_delay_ms * (2 ** attempt),
                retry_config.max_delay_ms,
            )
            logger.warning(
                f"Search attempt {attempt + 1} failed: {e}. "
                f"Retrying in {delay}ms"
            )
            await asyncio.sleep(delay / 1000)
    
    raise last_error
```

**Telemetry additions**:
- `retry_count`: Number of retries attempted
- `retry_reasons`: List of error types that triggered retries

### 2. Add Circuit Breaker Pattern

```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    success_threshold: int = 3
    
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _success_count: int = 0
    _last_failure_time: datetime | None = None
    _lock: threading.Lock = threading.Lock()
    
    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._reset()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
    
    def should_allow_request(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if self._last_failure_time:
                    elapsed = datetime.now() - self._last_failure_time
                    if elapsed > timedelta(seconds=self.recovery_timeout_seconds):
                        self._state = CircuitState.HALF_OPEN
                        self._success_count = 0
                        return True
                return False
            return True  # HALF_OPEN allows limited requests
    
    def _reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
```

**Telemetry additions**:
- `circuit_breaker_state`: Current state
- `circuit_breaker_open_count`: Times circuit opened

### 3. Enhanced Error Classification

```python
from enum import Enum
from dataclasses import dataclass

class SearchErrorCategory(Enum):
    TRANSIENT = "transient"        # Network issues, timeouts - retry
    AUTHENTICATION = "auth"        # API key issues - alert immediately
    QUOTA = "quota"               # Rate limits - back off
    INVALID_REQUEST = "bad_request"  # Bad query - don't retry
    SERVICE_ERROR = "service"     # 5xx errors - retry with backoff
    INVALID_RESPONSE = "response"  # Parse errors - log for debugging
    UNKNOWN = "unknown"

@dataclass
class ClassifiedError:
    category: SearchErrorCategory
    original_error: Exception
    should_retry: bool
    alert_severity: str  # "critical", "warning", "info"
    suggested_action: str

def classify_search_error(error: Exception) -> ClassifiedError:
    error_name = type(e).__name__
    error_str = str(error).lower()
    
    # Authentication errors
    if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.AUTHENTICATION,
            original_error=error,
            should_retry=False,
            alert_severity="critical",
            suggested_action="Check API key configuration",
        )
    
    # Rate limiting
    if "429" in error_str or "rate limit" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.QUOTA,
            original_error=error,
            should_retry=True,
            alert_severity="warning",
            suggested_action="Implement backoff or upgrade plan",
        )
    
    # Service errors
    if "503" in error_str or "502" in error_str or "service unavailable" in error_str:
        return ClassifiedError(
            category=SearchErrorCategory.SERVICE_ERROR,
            original_error=error,
            should_retry=True,
            alert_severity="warning",
            suggested_action="Provider issue, will auto-retry",
        )
    
    # Timeouts and connection errors
    if isinstance(error, (httpx.TimeoutException, SearchTimeoutError)):
        return ClassifiedError(
            category=SearchErrorCategory.TRANSIENT,
            original_error=error,
            should_retry=True,
            alert_severity="info",
            suggested_action="Network issue, will retry",
        )
    
    # Default
    return ClassifiedError(
        category=SearchErrorCategory.UNKNOWN,
        original_error=error,
        should_retry=False,
        alert_severity="warning",
        suggested_action="Investigate error details",
    )
```

**Database schema addition**:
```sql
ALTER TABLE web_search_telemetry 
ADD COLUMN error_category VARCHAR(50),
ADD COLUMN should_retry BOOLEAN,
ADD COLUMN retry_count INTEGER DEFAULT 0;
```

### 4. Health Check Endpoint

```python
# In admin/server.py or separate health module

@dataclass
class SearchProviderHealth:
    status: str  # "healthy", "degraded", "unhealthy"
    last_success: datetime | None
    last_failure: datetime | None
    consecutive_failures: int
    circuit_breaker_state: str
    avg_response_time_ms: float | None
    success_rate_1h: float  # Success rate in last hour

async def check_search_health() -> SearchProviderHealth:
    """Check the health of the search provider."""
    repo = WebSearchTelemetryRepository()
    
    # Get recent telemetry
    recent = await repo.get_recent(limit=100)
    
    # Calculate metrics
    successes = [r for r in recent if r.is_success()]
    failures = [r for r in recent if r.is_error()]
    
    success_rate = len(successes) / len(recent) if recent else 0
    
    # Determine status
    if success_rate >= 0.95:
        status = "healthy"
    elif success_rate >= 0.8:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return SearchProviderHealth(
        status=status,
        last_success=max((r.created_at for r in successes), default=None),
        last_failure=max((r.created_at for r in failures), default=None),
        consecutive_failures=await repo.get_consecutive_failures(),
        circuit_breaker_state=search_provider.circuit_breaker.state.value,
        avg_response_time_ms=statistics.mean(
            [r.api_response_time_ms for r in successes if r.api_response_time_ms]
        ) if successes else None,
        success_rate_1h=success_rate,
    )

# Admin endpoint
@admin_router.get("/health/search")
async def search_health_endpoint():
    health = await check_search_health()
    return {
        "status": health.status,
        "details": asdict(health),
        "timestamp": datetime.now().isoformat(),
    }
```

### 5. Enhanced Agent-Level Telemetry

Add to `WebSearchAgent`:

```python
@dataclass
class AgentTelemetry:
    # Query generation
    query_generation_start_ms: int | None = None
    query_generation_duration_ms: int | None = None
    query_generation_method: str = "llm"  # "llm" or "fallback"
    query_generation_error: str | None = None
    
    # Search execution
    search_start_ms: int | None = None
    search_duration_ms: int | None = None
    queries_executed: int = 0
    queries_failed: int = 0
    
    # Response synthesis
    synthesis_start_ms: int | None = None
    synthesis_duration_ms: int | None = None
    synthesis_error: str | None = None
    
    # Overall
    total_duration_ms: int | None = None
    fallback_used: bool = False
```

Update `process()` method to track:

```python
async def process(self, message: str, context: dict, history: list) -> AgentResult:
    agent_telemetry = AgentTelemetry()
    start_time = time.time()
    
    try:
        # Step 1: Generate queries
        agent_telemetry.query_generation_start_ms = time.time() * 1000
        try:
            search_queries = await self._generate_search_queries(message)
            agent_telemetry.query_generation_method = "llm"
        except Exception as e:
            search_queries = [self._fallback_extract_query(message)]
            agent_telemetry.query_generation_method = "fallback"
            agent_telemetry.query_generation_error = str(e)
        agent_telemetry.query_generation_duration_ms = (
            time.time() * 1000 - agent_telemetry.query_generation_start_ms
        )
        
        # Step 2: Execute searches (with telemetry)
        agent_telemetry.search_start_ms = time.time() * 1000
        all_results = await self._execute_multiple_searches(search_queries)
        agent_telemetry.search_duration_ms = (
            time.time() * 1000 - agent_telemetry.search_start_ms
        )
        agent_telemetry.queries_executed = len(search_queries)
        
        # Step 3: Synthesize response
        agent_telemetry.synthesis_start_ms = time.time() * 1000
        response, tokens = await self._generate_response_with_results(...)
        agent_telemetry.synthesis_duration_ms = (
            time.time() * 1000 - agent_telemetry.synthesis_start_ms
        )
        
        agent_telemetry.total_duration_ms = time.time() * 1000 - start_time * 1000
        
        return AgentResult(
            response=response,
            agent_type=self.agent_type,
            confidence=0.9,
            metadata={
                "agent_telemetry": asdict(agent_telemetry),
                # ... other metadata
            },
            tokens_used=tokens,
        )
    except Exception as e:
        # Track error in telemetry
        agent_telemetry.total_duration_ms = time.time() * 1000 - start_time * 1000
        # ... error handling
```

### 6. Prometheus Alerting Rules for Search

Add to [`monitoring/alerts.yml`](../monitoring/alerts.yml):

```yaml
groups:
  - name: web_search_alerts
    rules:
      # High failure rate
      - alert: WebSearchHighFailureRate
        expr: |
          (
            rate(bot_web_search_requests_total{status="error"}[5m])
            /
            rate(bot_web_search_requests_total[5m])
          ) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High web search failure rate"
          description: "{{ $value | humanizePercentage }} of web searches are failing"
      
      # Complete search outage
      - alert: WebSearchOutage
        expr: |
          (
            rate(bot_web_search_requests_total{status="error"}[5m])
            /
            rate(bot_web_search_requests_total[5m])
          ) > 0.5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Web search service outage"
          description: "More than 50% of web searches are failing"
      
      # Slow searches
      - alert: WebSearchSlowResponses
        expr: |
          histogram_quantile(0.95, 
            rate(bot_web_search_duration_seconds_bucket[5m])
          ) > 20
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Web search responses are slow"
          description: "P95 latency is {{ $value | humanizeDuration }}"
      
      # No searches (possible circuit breaker open)
      - alert: WebSearchNoTraffic
        expr: |
          rate(bot_web_search_requests_total[5m]) == 0
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "No web search traffic"
          description: "No web searches in the last 10 minutes"
      
      # Authentication errors
      - alert: WebSearchAuthError
        expr: |
          increase(bot_web_search_requests_total{status="error"}[1m]) > 0
          and on() 
          bot_web_search_requests_total{status="error"} offset 1m
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Web search authentication error"
          description: "Check API key configuration"
```

### 7. Empty Results Analysis

Add database view and API endpoint:

```sql
-- View for analyzing empty result patterns
CREATE OR REPLACE VIEW web_search_empty_analysis AS
SELECT 
    query,
    COUNT(*) as occurrence_count,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(api_response_time_ms) as avg_response_time,
    MAX(created_at) as last_occurrence,
    MIN(created_at) as first_occurrence,
    array_agg(DISTINCT error_type) as error_types
FROM web_search_telemetry
WHERE status = 'empty' OR (status = 'success' AND results_count = 0)
GROUP BY query
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC;
```

```python
# Admin endpoint for empty results analysis
@admin_router.get("/admin/search/empty-results")
async def get_empty_results_analysis():
    """Analyze patterns in empty search results."""
    repo = WebSearchTelemetryRepository()
    
    # Get recent empty results
    empty = await repo.get_empty_results(limit=100)
    
    # Group by query pattern
    patterns = analyze_query_patterns([e.query for e in empty])
    
    return {
        "total_empty_searches": len(empty),
        "patterns": patterns,
        "recent": [
            {
                "query": e.query,
                "created_at": e.created_at.isoformat(),
                "response_time_ms": e.api_response_time_ms,
            }
            for e in empty[:10]
        ],
    }
```

---

## Enhanced Metrics

### New Prometheus Metrics

Add to [`metrics.py`](../src/nergal/monitoring/metrics.py):

```python
# Web Search Enhanced Metrics

bot_web_search_retries_total = Counter(
    "bot_web_search_retries_total",
    "Total number of search retries",
    ["reason"],
)

bot_web_search_circuit_breaker_state = Gauge(
    "bot_web_search_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
)

bot_web_search_query_generation_duration_seconds = Histogram(
    "bot_web_search_query_generation_duration_seconds",
    "Time spent generating search queries",
    ["method"],  # llm or fallback
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

bot_web_search_synthesis_duration_seconds = Histogram(
    "bot_web_search_synthesis_duration_seconds",
    "Time spent synthesizing search results into response",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
)

bot_web_search_results_per_query = Histogram(
    "bot_web_search_results_per_query",
    "Number of results returned per search query",
    buckets=[0, 1, 2, 3, 5, 10, 20, 50],
)

bot_web_search_queries_per_request = Histogram(
    "bot_web_search_queries_per_request",
    "Number of search queries generated per user request",
    buckets=[1, 2, 3, 4, 5],
)
```

---

## Admin Dashboard Enhancements

### New Admin Endpoints

```python
# In admin/server.py

@admin_router.get("/admin/search/telemetry/recent")
async def get_recent_telemetry(
    limit: int = 50,
    status: str | None = None,
):
    """Get recent search telemetry records."""
    repo = WebSearchTelemetryRepository()
    records = await repo.get_recent(limit=limit, status=status)
    return {
        "records": [asdict(r) for r in records],
        "total": len(records),
    }

@admin_router.get("/admin/search/telemetry/{telemetry_id}")
async def get_telemetry_detail(telemetry_id: UUID):
    """Get detailed telemetry for a specific search."""
    repo = WebSearchTelemetryRepository()
    record = await repo.get_by_id(telemetry_id)
    if not record:
        raise HTTPException(status_code=404, detail="Telemetry not found")
    return asdict(record)

@admin_router.get("/admin/search/stats")
async def get_search_stats():
    """Get aggregated search statistics."""
    repo = WebSearchTelemetryRepository()
    
    # Get stats from database view
    stats = await repo.get_stats_summary()
    
    return {
        "24h": {
            "total": stats["total_24h"],
            "success_rate": stats["success_rate_24h"],
            "avg_response_time_ms": stats["avg_response_time_24h"],
            "error_types": stats["error_types_24h"],
        },
        "7d": {
            "total": stats["total_7d"],
            "success_rate": stats["success_rate_7d"],
            "avg_response_time_ms": stats["avg_response_time_7d"],
        },
    }

@admin_router.get("/admin/search/health")
async def get_search_health():
    """Get current health status of search provider."""
    return await check_search_health()

@admin_router.post("/admin/search/circuit-breaker/reset")
async def reset_circuit_breaker():
    """Manually reset the circuit breaker."""
    search_provider.circuit_breaker.reset()
    return {"status": "reset", "timestamp": datetime.now().isoformat()}
```

---

## Implementation Priority

### Phase 1: Critical ✅ COMPLETED
1. ✅ Add retry mechanism with exponential backoff → [`reliability.py`](../src/nergal/web_search/reliability.py)
2. ✅ Add enhanced error classification → [`reliability.py`](../src/nergal/web_search/reliability.py)
3. ✅ Add Prometheus alerting rules for search → [`alerts.yml`](../monitoring/alerts.yml)

### Phase 2: Important ✅ COMPLETED
4. ✅ Add circuit breaker pattern → [`reliability.py`](../src/nergal/web_search/reliability.py)
5. ✅ Add health check endpoint → [`health.py`](../src/nergal/monitoring/health.py)
6. ✅ Add agent-level telemetry → [`web_search_agent.py`](../src/nergal/dialog/agents/web_search_agent.py)

### Phase 3: Enhancement ✅ COMPLETED
7. ✅ Add empty results analysis → [`init.sql`](../database/init.sql) (view `web_search_empty_results`)
8. ✅ Add admin dashboard endpoints → [`server.py`](../src/nergal/admin/server.py)
9. ✅ Add enhanced Prometheus metrics → [`metrics.py`](../src/nergal/monitoring/metrics.py)

---

## Implementation Details

### New Files Created

#### [`src/nergal/web_search/reliability.py`](../src/nergal/web_search/reliability.py)

Contains reliability components:
- `CircuitBreaker` - Circuit breaker pattern implementation with CLOSED/OPEN/HALF_OPEN states
- `RetryConfig` - Configuration for retry behavior
- `SearchErrorCategory` - Error classification enum (TRANSIENT, AUTHENTICATION, QUOTA, etc.)
- `ClassifiedError` - Classified error with category and suggested action
- `classify_search_error()` - Error classification function
- `execute_with_retry()` - Retry wrapper with exponential backoff and jitter

### Modified Files

#### [`src/nergal/web_search/zai_mcp_http.py`](../src/nergal/web_search/zai_mcp_http.py)
- Added `retry_config` and `circuit_breaker` parameters to `__init__`
- Added retry telemetry fields to `TelemetryContext`
- Refactored `search()` to use `_do_search()` with retry logic via `execute_with_retry()`

#### [`src/nergal/database/models.py`](../src/nergal/database/models.py)
- Added to `WebSearchTelemetry`: `retry_count`, `retry_reasons`, `total_retry_delay_ms`, `error_category`

#### [`src/nergal/database/repositories.py`](../src/nergal/database/repositories.py)
- Updated `record_to_web_search_telemetry()` and `record_search()` with new fields

#### [`database/init.sql`](../database/init.sql)
- Added columns: `retry_count`, `retry_reasons`, `total_retry_delay_ms`, `error_category`
- Added migration block for existing databases
- Added `web_search_error_categories` view for error analysis

#### [`monitoring/alerts.yml`](../monitoring/alerts.yml)
- Added alerts: `WebSearchHighFailureRate`, `WebSearchOutage`, `WebSearchSlowResponses`, `WebSearchNoTraffic`, `WebSearchCircuitBreakerOpen`, `WebSearchHighRetryRate`

#### [`src/nergal/monitoring/metrics.py`](../src/nergal/monitoring/metrics.py)
- Added metrics: `bot_web_search_retries_total`, `bot_web_search_circuit_breaker_state`, `bot_web_search_query_generation_duration_seconds`, `bot_web_search_synthesis_duration_seconds`, `bot_web_search_results_per_query`, `bot_web_search_queries_per_request`, `bot_web_search_errors_by_category`

#### [`src/nergal/monitoring/health.py`](../src/nergal/monitoring/health.py)
- Enhanced `check_web_search_health()` with circuit breaker status and success rate checking
- Added `check_web_search_health_detailed()` for admin endpoints

#### [`src/nergal/dialog/agents/web_search_agent.py`](../src/nergal/dialog/agents/web_search_agent.py)
- Added `AgentTelemetry` dataclass for tracking query generation, search execution, and synthesis timing
- Updated `process()` to track and record telemetry to Prometheus metrics

#### [`src/nergal/admin/server.py`](../src/nergal/admin/server.py)
- Updated HTML templates to display error_category and retry info
- Added retry section template for detailed telemetry view
- Updated `_format_telemetry_row()` to show error category and retry count

---

## Testing Recommendations

### Unit Tests

```python
# tests/test_web_search/test_reliability.py

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_retry_on_timeout():
    """Test that search retries on timeout."""
    provider = ZaiMcpHttpSearchProvider(api_key="test")
    
    with patch.object(provider, '_do_search') as mock_search:
        # First two attempts timeout, third succeeds
        mock_search.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            SearchResults(results=[], query="test"),
        ]
        
        result = await provider.search_with_retry(
            SearchRequest(query="test")
        )
        
        assert mock_search.call_count == 3
        assert result is not None

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    """Test that circuit breaker opens after threshold failures."""
    provider = ZaiMcpHttpSearchProvider(api_key="test")
    provider.circuit_breaker.failure_threshold = 3
    
    for _ in range(3):
        provider.circuit_breaker.record_failure()
    
    assert provider.circuit_breaker.state == CircuitState.OPEN
    assert not provider.circuit_breaker.should_allow_request()

@pytest.mark.asyncio
async def test_error_classification():
    """Test error classification logic."""
    # Auth error
    error = SearchProviderError("401 Unauthorized")
    classified = classify_search_error(error)
    assert classified.category == SearchErrorCategory.AUTHENTICATION
    assert not classified.should_retry
    
    # Rate limit
    error = SearchProviderError("429 Rate limit exceeded")
    classified = classify_search_error(error)
    assert classified.category == SearchErrorCategory.QUOTA
    assert classified.should_retry
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_search_flow_with_telemetry():
    """Test complete search flow with telemetry recording."""
    agent = WebSearchAgent(
        llm_provider=mock_llm,
        search_provider=mock_search,
    )
    
    result = await agent.process(
        message="What's the weather in Moscow?",
        context={},
        history=[],
    )
    
    # Verify telemetry was recorded
    repo = WebSearchTelemetryRepository()
    recent = await repo.get_recent(limit=1)
    
    assert len(recent) == 1
    assert recent[0].query == "weather Moscow"
    assert recent[0].status == "success"
    assert recent[0].total_duration_ms is not None
```

---

## Monitoring Dashboard Queries

### Grafana Panel Queries

```promql
# Success Rate (last hour)
sum(rate(bot_web_search_requests_total{status="success"}[1h])) 
/ 
sum(rate(bot_web_search_requests_total[1h]))

# P95 Latency
histogram_quantile(0.95, 
  rate(bot_web_search_duration_seconds_bucket[5m])
)

# Error Rate by Type
sum by (error_type) (
  rate(bot_web_search_requests_total{status="error"}[5m])
)

# Circuit Breaker State
bot_web_search_circuit_breaker_state

# Query Generation Method Distribution
sum by (method) (
  rate(bot_web_search_query_generation_duration_seconds_count[5m])
)

# Average Results Per Query
rate(bot_web_search_results_per_query_sum[5m]) 
/ 
rate(bot_web_search_results_per_query_count[5m])
```

---

## Summary

This document outlines comprehensive improvements to make the web search agent more reliable and observable:

1. **Retry Mechanism**: Handle transient failures automatically
2. **Circuit Breaker**: Prevent cascading failures
3. **Error Classification**: Better categorization for alerting
4. **Health Checks**: Proactive monitoring
5. **Enhanced Telemetry**: Track all phases of search operation
6. **Alerting Rules**: Early warning for issues
7. **Empty Results Analysis**: Identify problematic query patterns

Implementing these improvements will significantly enhance the reliability of the web search feature and provide the observability needed to quickly diagnose and resolve issues.
