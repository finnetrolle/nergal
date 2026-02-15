# Monitoring and Observability Guide

This guide explains how to set up and use the monitoring system for the Nergal Telegram bot. The monitoring stack includes:

- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visualization and dashboards
- **Loki** - Log aggregation
- **Promtail** - Log shipping
- **Alertmanager** - Alert routing and notifications

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Nergal Bot    │────▶│    Prometheus    │────▶│    Grafana      │
│  (metrics:8000) │     │     (9090)       │     │     (3000)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │
        │                        ▼
        │               ┌──────────────────┐
        │               │  Alertmanager    │
        │               │     (9093)       │
        │               └──────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│    Promtail     │────▶│      Loki        │
│   (log agent)   │     │     (3100)       │
└─────────────────┘     └──────────────────┘
```

## Quick Start

### 1. Configure Environment Variables

Add monitoring settings to your `.env` file:

```bash
# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_METRICS_PORT=8000
MONITORING_JSON_LOGS=true
MONITORING_LOG_LEVEL=INFO
```

### 2. Start the Monitoring Stack

```bash
# Start all services including monitoring
docker-compose --profile monitoring up -d

# Or start only monitoring services
docker-compose up -d prometheus grafana loki promtail alertmanager
```

### 3. Access Dashboards

- **Grafana**: http://localhost:3000 (default: admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Bot Metrics**: http://localhost:8000/metrics

---

## Complete Metrics Reference

All metrics are defined in [`src/nergal/monitoring/metrics.py`](../src/nergal/monitoring/metrics.py).

### 📊 Overview Dashboard Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `bot_messages_total` | Counter | Total messages processed | `status`, `agent_type` |
| `bot_active_users` | Gauge | Unique users active in last hour | - |
| `bot_errors_total` | Counter | Total errors encountered | `error_type`, `component` |
| `system_cpu_percent` | Gauge | System CPU usage percentage | - |
| `system_memory_percent` | Gauge | System memory usage percentage | - |
| `system_disk_percent` | Gauge | System disk usage percentage | `path` |

### 💬 Message Processing Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `bot_messages_total` | Counter | Total messages processed | `status` (`success`/`error`), `agent_type` |
| `bot_message_duration_seconds` | Histogram | Time spent processing messages | `agent_type` |

**Buckets**: `0.1s`, `0.25s`, `0.5s`, `1s`, `2.5s`, `5s`, `10s`, `30s`, `60s`, `120s`

```promql
# Example queries
rate(bot_messages_total[5m])                           # Messages per second
histogram_quantile(0.95, rate(bot_message_duration_seconds_bucket[5m])) # p95 latency
sum by (agent_type) (rate(bot_messages_total[5m]))     # By agent type
sum by (status) (increase(bot_messages_total[1h]))     # Success/error count per hour
```

### 🧠 LLM Provider Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `bot_llm_requests_total` | Counter | LLM API requests | `provider`, `model`, `status` |
| `bot_llm_request_duration_seconds` | Histogram | LLM request latency | `provider`, `model` |
| `bot_llm_tokens_total` | Counter | Token usage | `provider`, `model`, `type` |

**Duration Buckets**: `0.5s`, `1s`, `2s`, `5s`, `10s`, `20s`, `30s`, `60s`, `120s`

**Token Types**: `prompt` (input tokens), `completion` (output tokens)

```promql
# Example queries
rate(bot_llm_requests_total[5m])                       # Requests per second
sum by (model) (rate(bot_llm_tokens_total[5m]))        # Tokens by model
histogram_quantile(0.95, rate(bot_llm_request_duration_seconds_bucket[5m])) # p95 LLM latency
sum(increase(bot_llm_tokens_total{type="prompt"}[1h])) # Prompt tokens per hour
sum(increase(bot_llm_tokens_total{type="completion"}[1h])) # Completion tokens per hour
```

### 🔍 Web Search Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `bot_web_search_requests_total` | Counter | Web search requests | `status` |
| `bot_web_search_duration_seconds` | Histogram | Web search latency | - |

**Buckets**: `0.5s`, `1s`, `2s`, `5s`, `10s`, `20s`, `30s`

```promql
# Example queries
rate(bot_web_search_requests_total[5m])                # Searches per second
sum by (status) (bot_web_search_requests_total)        # By status
histogram_quantile(0.95, rate(bot_web_search_duration_seconds_bucket[5m])) # p95 search latency
```

### 🎤 Speech-to-Text (STT) Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `bot_stt_requests_total` | Counter | STT requests | `provider`, `status` |
| `bot_stt_duration_seconds` | Histogram | STT processing time | `provider` |
| `bot_stt_audio_duration_seconds` | Histogram | Duration of processed audio | `provider` |

**Processing Duration Buckets**: `0.5s`, `1s`, `2s`, `5s`, `10s`, `20s`, `30s`, `60s`

**Audio Duration Buckets**: `5s`, `10s`, `20s`, `30s`, `45s`, `60s`, `90s`, `120s`

```promql
# Example queries
rate(bot_stt_requests_total[5m])                       # STT requests per second
sum by (provider) (rate(bot_stt_requests_total[5m]))   # By provider
histogram_quantile(0.95, rate(bot_stt_duration_seconds_bucket[5m])) # p95 STT latency
avg(bot_stt_audio_duration_seconds)                    # Average audio length
sum by (status) (increase(bot_stt_requests_total[1h])) # Success/error per hour
```

### 💾 System Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `system_cpu_percent` | Gauge | CPU usage percentage | - |
| `system_memory_percent` | Gauge | Memory usage percentage | - |
| `system_disk_percent` | Gauge | Disk usage percentage | `path` |

```promql
# Example queries
system_cpu_percent                                     # Current CPU usage
system_memory_percent                                  # Current memory usage
system_disk_percent{path="/"}                          # Root disk usage
avg_over_time(system_cpu_percent[1h])                  # Average CPU over hour
```

---

## Using Metrics in Code

### Decorators

Use the `@track_message` decorator to automatically track message processing:

```python
from nergal.monitoring.metrics import track_message

@track_message(agent_type="web_search")
async def process_search_query(query: str):
    # Your code here
    pass
```

### Context Managers

Track LLM requests:

```python
from nergal.monitoring.metrics import track_llm_request

async with track_llm_request(provider="zai", model="glm-4-flash"):
    response = await llm_provider.generate(messages)
```

Track web searches:

```python
from nergal.monitoring.metrics import track_web_search

async with track_web_search():
    results = await web_search.search(query)
```

Track STT requests:

```python
from nergal.monitoring.metrics import track_stt_request

async with track_stt_request(provider="local", audio_duration=30.0):
    text = await stt_provider.transcribe(audio_data)
```

### Manual Tracking

Track errors:

```python
from nergal.monitoring.metrics import track_error

try:
    # Your code
except Exception as e:
    track_error(type(e).__name__, "component_name")
    raise
```

Track token usage:

```python
from nergal.monitoring.metrics import track_tokens

track_tokens(
    provider="zai",
    model="glm-4-flash",
    prompt_tokens=100,
    completion_tokens=50
)
```

Track user activity:

```python
from nergal.monitoring.metrics import track_user_activity

track_user_activity(user_id=123456789)
```

---

## Grafana Dashboard

### Pre-built Dashboard

A comprehensive dashboard is available at [`monitoring/grafana/dashboards/nergal-bot-overview.json`](../monitoring/grafana/dashboards/nergal-bot-overview.json).

### Dashboard Sections

#### 📊 Overview
- **Messages (1h)** - Total messages processed in the last hour
- **Active Users** - Unique users with activity in the last hour
- **Web Searches (1h)** - Web search requests in the last hour
- **Errors (1h)** - Total errors in the last hour (color-coded by severity)
- **Memory** - Current memory usage with thresholds
- **Bot Status** - Bot health status indicator

#### 💬 Message Processing
- **Message Rate** - Messages per second by status and agent type
- **Message Processing Latency** - p50, p95, p99 latency percentiles

#### 🧠 LLM Provider
- **LLM Request Rate** - Requests per second by provider/model/status
- **LLM Request Latency** - p50, p95 latency percentiles
- **Token Usage Rate** - Tokens per second (prompt vs completion)

#### 🔍 Web Search
- **Web Search Request Rate** - Searches per second by status
- **Web Search Latency** - p50, p95 latency percentiles

#### 🎤 Speech-to-Text (STT)
- **STT Requests (1h)** - Total STT requests in the last hour
- **STT Success (1h)** - Successful STT requests
- **STT Request Rate** - Requests per second by provider and status
- **STT Processing Latency** - p50, p95 latency percentiles
- **Audio Duration Processed** - Duration of audio being processed
- **STT by Provider** - Breakdown by provider

#### ❌ Errors
- **Errors by Type** - Bar chart of errors by type/component (1h buckets)
- **Error Logs** - Live error logs from Loki

#### 📊 Token Usage & System Resources
- **Tokens per Hour** - Bar chart of hourly token usage
- **Token Usage (Last Hour)** - Stat panel with prompt/completion/total tokens
- **CPU & Memory Usage** - Time series of system resources
- **Disk Usage** - Disk usage by path with threshold lines

### Dashboard Features

- **Auto-refresh**: Every 30 seconds
- **Time range**: Last 6 hours (adjustable)
- **Smooth graphs**: Line interpolation for better visualization
- **Color coding**: Consistent colors across all panels
  - Green: Success/healthy
  - Yellow: Warning/moderate
  - Orange: Elevated concern
  - Red: Error/critical
  - Blue: Information/prompt tokens
  - Purple: Completion tokens/memory

---

## Alerting Rules

Alert rules are defined in [`monitoring/alerts.yml`](../monitoring/alerts.yml).

### Critical Alerts

| Alert | Condition | Description |
|-------|-----------|-------------|
| `BotDown` | Bot unreachable for 1m | Bot is not responding |
| `CriticalErrorRate` | >1 error/sec for 1m | Critical error rate detected |
| `LLMProviderDown` | >50% LLM errors for 2m | LLM provider appears down |
| `CriticalMemoryUsage` | Memory >95% for 2m | Memory exhaustion imminent |

### Warning Alerts

| Alert | Condition | Description |
|-------|-----------|-------------|
| `HighErrorRate` | >0.1 errors/sec for 2m | Elevated error rate |
| `SlowMessageProcessing` | p95 latency >60s for 5m | Slow message processing |
| `LLMRequestLatencyHigh` | p95 latency >30s for 5m | High LLM latency |
| `HighCPUUsage` | CPU >80% for 5m | High CPU usage |
| `HighMemoryUsage` | Memory >85% for 5m | High memory usage |

---

## Configuring Alert Notifications

### Telegram Alerts (Recommended)

Create a separate Telegram bot for alerts and configure Alertmanager:

1. Create a new bot via @BotFather
2. Get your chat ID by messaging @userinfobot
3. Edit `monitoring/alertmanager.yml`:

```yaml
receivers:
  - name: 'critical-alerts'
    telegram_configs:
      - bot_token: 'YOUR_ALERT_BOT_TOKEN'
        api_url: 'https://api.telegram.org'
        chat_id: YOUR_CHAT_ID
        parse_mode: 'HTML'
```

### Email Alerts

Configure SMTP in `monitoring/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alerts@your-domain.com'
  smtp_auth_username: 'alerts@your-domain.com'
  smtp_auth_password: 'your-password'

receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'admin@your-domain.com'
        send_resolved: true
```

### Slack Alerts

Configure Slack webhook in `monitoring/alertmanager.yml`:

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

receivers:
  - name: 'critical-alerts'
    slack_configs:
      - channel: '#alerts-critical'
        send_resolved: true
```

---

## Structured Logging

The bot uses `structlog` for structured JSON logging when `MONITORING_JSON_LOGS=true`.

### Configuration

Logging is configured in [`src/nergal/monitoring/logging_config.py`](../src/nergal/monitoring/logging_config.py):

```python
from nergal.monitoring.logging_config import setup_logging

setup_logging(
    json_format=True,  # JSON logs for production
    log_level="INFO"
)
```

### Log Format

```json
{
  "event": "Message processed successfully",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "info",
  "logger": "nergal.main",
  "service": "nergal-bot",
  "user_id": 123456789,
  "duration_seconds": 2.5,
  "agent_used": "default"
}
```

### Querying Logs in Grafana

1. Open Grafana → Explore
2. Select Loki datasource
3. Use LogQL queries:

```logql
# All error logs
{service="nergal-bot"} |= "error"

# Logs for specific user
{service="nergal-bot"} | json | user_id="123456789"

# Slow requests (>5s)
{service="nergal-bot"} | json | duration_seconds > 5

# Logs by level
{service="nergal-bot"} | json | level="error"

# Logs containing specific text
{service="nergal-bot"} |= "LLM request"
```

---

## Health Check Endpoint

The bot provides health checks via [`src/nergal/monitoring/health.py`](../src/nergal/monitoring/health.py).

### Components Checked

| Component | Description |
|-----------|-------------|
| `telegram` | Telegram API connectivity |
| `llm` | LLM provider availability |
| `database` | PostgreSQL connection |
| `web_search` | Web search API (if enabled) |
| `stt` | Speech-to-text service (if enabled) |

### Usage

```python
from nergal.monitoring.health import HealthChecker

health = HealthChecker(
    llm_provider=llm_provider,
    db_connection=db,
    web_search_provider=web_search,
)

# Check all components
result = await health.check_all()
# Returns: {"telegram": True, "llm": True, "database": True, ...}

# Get overall status
is_healthy = result.is_healthy  # All components healthy
```

### Telegram /status Command

Users can check bot status via `/status` command in Telegram:

```
Bot Status: ✅ Healthy

Components:
• Telegram: ✅ Connected
• LLM (zai/glm-4-flash): ✅ Available
• Database: ✅ Connected
• Web Search: ✅ Enabled

Uptime: 3d 14h 22m
```

---

## Monitoring Without Docker

If running the bot without Docker:

1. Install dependencies:
```bash
pip install prometheus-client structlog psutil
```

2. Run the bot:
```bash
python -m nergal.main
```

3. Metrics will be available at `http://localhost:8000/metrics`

4. Configure external Prometheus to scrape this endpoint

---

## Prometheus Configuration

The Prometheus configuration is in [`monitoring/prometheus.yml`](../monitoring/prometheus.yml):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'nergal-bot'
    static_configs:
      - targets: ['nergal-bot:8000']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

rule_files:
  - '/etc/prometheus/alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

---

## Troubleshooting

### Metrics Not Available

1. Check if monitoring is enabled: `MONITORING_ENABLED=true`
2. Verify metrics server is running: `curl http://localhost:8000/metrics`
3. Check logs for errors:
   ```bash
   docker compose logs nergal-bot | grep -i metrics
   ```

### Logs Not Appearing in Loki

1. Verify Loki is running: `curl http://localhost:3100/ready`
2. Check Promtail logs: `docker logs nergal-promtail`
3. Verify Docker logging driver is configured in `docker-compose.yml`

### Alerts Not Firing

1. Check Prometheus UI → Alerts page
2. Verify alert rules are loaded:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```
3. Check Alertmanager UI for silences or inhibitions

### High Memory Usage

If monitoring stack uses too much memory:

1. Reduce Prometheus retention:
   ```yaml
   # docker-compose.yml
   prometheus:
     command:
       - '--storage.tsdb.retention.time=7d'
   ```

2. Reduce Loki retention in `monitoring/loki-config.yml`

3. Increase scrape intervals in `monitoring/prometheus.yml`:
   ```yaml
   global:
     scrape_interval: 30s  # Instead of 15s
   ```

### Grafana Dashboard Not Loading

1. Check if datasource is configured:
   ```bash
   curl http://localhost:3000/api/datasources
   ```
2. Verify Prometheus is accessible from Grafana
3. Check provisioning in `monitoring/grafana/provisioning/`

---

## Best Practices

1. **Set up alerting early** - Don't wait for issues to happen
2. **Use meaningful alert thresholds** - Adjust based on your usage patterns
3. **Monitor the monitors** - Set up alerts for Prometheus/Grafana downtime
4. **Review logs regularly** - Look for patterns before they become issues
5. **Keep dashboards updated** - Add new metrics as features are added
6. **Use labels consistently** - Makes querying easier
7. **Set appropriate retention** - Balance storage vs. history needs

---

## Security Considerations

1. **Change default passwords** - Especially Grafana admin password
2. **Restrict port access** - Don't expose monitoring ports publicly
   ```bash
   # Only allow local access
   sudo ufw deny 8000
   sudo ufw deny 3000
   sudo ufw deny 9090
   ```
3. **Use HTTPS** - Put Grafana behind a reverse proxy with TLS
4. **Secure Alertmanager** - Don't expose web UI publicly
5. **Rotate credentials** - Regularly update API keys and passwords
6. **Limit log access** - Logs may contain sensitive information

---

## Metrics Server API

The metrics server exposes a simple HTTP API:

### GET /metrics

Returns Prometheus-formatted metrics:

```
# HELP bot_messages_total Total number of messages processed
# TYPE bot_messages_total counter
bot_messages_total{agent_type="default",status="success"} 1234

# HELP bot_message_duration_seconds Time spent processing messages
# TYPE bot_message_duration_seconds histogram
bot_message_duration_seconds_bucket{agent_type="default",le="0.1"} 100
bot_message_duration_seconds_bucket{agent_type="default",le="0.25"} 200
...
```

---

## Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide with monitoring setup
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) - Agent system architecture
- [LLM_PROVIDERS.md](LLM_PROVIDERS.md) - LLM provider configuration
- [STT.md](STT.md) - Speech-to-text configuration
