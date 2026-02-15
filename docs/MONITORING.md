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

## Metrics Available

All metrics are defined in [`src/nergal/monitoring/metrics.py`](src/nergal/monitoring/metrics.py).

### Bot Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_messages_total` | Counter | Total messages processed (labels: `status`, `agent_type`) |
| `bot_message_duration_seconds` | Histogram | Message processing time |
| `bot_errors_total` | Counter | Total errors (labels: `error_type`, `component`) |
| `bot_active_users` | Gauge | Active users in last hour |

```promql
# Example queries
rate(bot_messages_total[5m])                           # Messages per second
histogram_quantile(0.95, bot_message_duration_seconds) # p95 latency
sum by (agent_type) (bot_messages_total)               # By agent
```

### LLM Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_llm_requests_total` | Counter | LLM API requests (labels: `provider`, `model`, `status`) |
| `bot_llm_request_duration_seconds` | Histogram | LLM request latency |
| `bot_llm_tokens_total` | Counter | Token usage (labels: `provider`, `model`, `type`) |

```promql
# Example queries
rate(bot_llm_requests_total[5m])                       # Requests per second
sum by (model) (bot_llm_tokens_total)                  # Tokens by model
histogram_quantile(0.95, bot_llm_request_duration_seconds) # p95 LLM latency
```

### Web Search Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_web_search_requests_total` | Counter | Web search requests (labels: `status`) |
| `bot_web_search_duration_seconds` | Histogram | Web search latency |

```promql
# Example queries
rate(bot_web_search_requests_total[5m])  # Searches per second
sum(bot_web_search_requests_total) by (status)  # By status
```

### STT Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_stt_requests_total` | Counter | Speech-to-text requests (labels: `provider`, `status`) |
| `bot_stt_duration_seconds` | Histogram | STT processing time |
| `bot_stt_audio_duration_seconds` | Histogram | Processed audio duration |

```promql
# Example queries
rate(bot_stt_requests_total[5m])           # STT requests per second
avg(bot_stt_audio_duration_seconds)        # Average audio length
```

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `system_cpu_percent` | Gauge | CPU usage percentage |
| `system_memory_percent` | Gauge | Memory usage percentage |
| `system_disk_percent` | Gauge | Disk usage percentage (label: `path`) |

```promql
# Example queries
system_cpu_percent          # Current CPU usage
system_memory_percent       # Current memory usage
system_disk_percent{path="/"}  # Root disk usage
```

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

## Alerting Rules

Alert rules are defined in [`monitoring/alerts.yml`](monitoring/alerts.yml).

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

## Structured Logging

The bot uses `structlog` for structured JSON logging when `MONITORING_JSON_LOGS=true`.

### Configuration

Logging is configured in [`src/nergal/monitoring/logging_config.py`](src/nergal/monitoring/logging_config.py):

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

## Health Check Endpoint

The bot provides health checks via [`src/nergal/monitoring/health.py`](src/nergal/monitoring/health.py):

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

## Grafana Dashboards

### Pre-built Dashboard

A pre-built dashboard is available at [`monitoring/grafana/dashboards/nergal-bot-overview.json`](monitoring/grafana/dashboards/nergal-bot-overview.json) with:

- Message rate and latency graphs
- LLM request metrics
- Token usage visualization
- Error tracking
- System resource usage
- Live error logs

### Dashboard Panels

1. **Message Overview**
   - Messages per minute
   - Processing latency (p50, p95, p99)
   - Active users gauge

2. **LLM Metrics**
   - Requests per minute by provider/model
   - Token usage over time
   - Request latency distribution

3. **Error Tracking**
   - Error rate over time
   - Errors by type and component
   - Recent error logs

4. **System Resources**
   - CPU usage
   - Memory usage
   - Disk usage

### Creating Custom Dashboards

1. Open Grafana → Dashboards → New Dashboard
2. Add Prometheus queries using the metrics above
3. Save and optionally export to `monitoring/grafana/dashboards/`

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

## Prometheus Configuration

The Prometheus configuration is in [`monitoring/prometheus.yml`](monitoring/prometheus.yml):

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

## Best Practices

1. **Set up alerting early** - Don't wait for issues to happen
2. **Use meaningful alert thresholds** - Adjust based on your usage patterns
3. **Monitor the monitors** - Set up alerts for Prometheus/Grafana downtime
4. **Review logs regularly** - Look for patterns before they become issues
5. **Keep dashboards updated** - Add new metrics as features are added
6. **Use labels consistently** - Makes querying easier
7. **Set appropriate retention** - Balance storage vs. history needs

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

## Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide with monitoring setup
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) - Agent system architecture
- [LLM_PROVIDERS.md](LLM_PROVIDERS.md) - LLM provider configuration
