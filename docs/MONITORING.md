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

# Grafana Configuration
GRAFANA_PASSWORD=your_secure_password
GRAFANA_URL=http://localhost:3000
```

### 2. Start the Monitoring Stack

```bash
# Start all services including monitoring
docker-compose up -d

# Or start only monitoring services
docker-compose up -d prometheus grafana loki promtail alertmanager node-exporter
```

### 3. Access Dashboards

- **Grafana**: http://localhost:3000 (default: admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Bot Metrics**: http://localhost:8000/metrics

## Metrics Available

### Bot Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_messages_total` | Counter | Total messages processed (labels: status, agent_type) |
| `bot_message_duration_seconds` | Histogram | Message processing time |
| `bot_errors_total` | Counter | Total errors (labels: error_type, component) |
| `bot_active_users` | Gauge | Active users in last hour |

### LLM Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_llm_requests_total` | Counter | LLM API requests (labels: provider, model, status) |
| `bot_llm_request_duration_seconds` | Histogram | LLM request latency |
| `bot_llm_tokens_total` | Counter | Token usage (labels: provider, model, type) |

### Web Search Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_web_search_requests_total` | Counter | Web search requests (labels: status) |
| `bot_web_search_duration_seconds` | Histogram | Web search latency |

### STT Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `bot_stt_requests_total` | Counter | Speech-to-text requests (labels: provider, status) |
| `bot_stt_duration_seconds` | Histogram | STT processing time |
| `bot_stt_audio_duration_seconds` | Histogram | Processed audio duration |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `system_cpu_percent` | Gauge | CPU usage percentage |
| `system_memory_percent` | Gauge | Memory usage percentage |
| `system_disk_percent` | Gauge | Disk usage percentage (label: path) |

## Alerting Rules

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
```

## Health Check Endpoint

The bot provides a `/status` command in Telegram that shows:
- Overall health status
- Component health (LLM, Telegram, Web Search, STT)
- Uptime

## Grafana Dashboards

### Pre-built Dashboard

A pre-built dashboard is available at `monitoring/grafana/dashboards/nergal-bot-overview.json` with:

- Message rate and latency graphs
- LLM request metrics
- Token usage visualization
- Error tracking
- System resource usage
- Live error logs

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

## Troubleshooting

### Metrics Not Available

1. Check if monitoring is enabled: `MONITORING_ENABLED=true`
2. Verify metrics server is running: `curl http://localhost:8000/metrics`
3. Check logs for errors

### Logs Not Appearing in Loki

1. Verify Loki is running: `curl http://localhost:3100/ready`
2. Check Promtail logs: `docker logs nergal-promtail`
3. Verify Docker logging driver is configured

### Alerts Not Firing

1. Check Prometheus UI → Alerts page
2. Verify alert rules are loaded
3. Check Alertmanager UI for silences or inhibitions

### High Memory Usage

If monitoring stack uses too much memory:

1. Reduce Prometheus retention: add `--storage.tsdb.retention.time=7d`
2. Reduce Loki retention in `loki-config.yml`
3. Increase scrape intervals in `prometheus.yml`

## Best Practices

1. **Set up alerting early** - Don't wait for issues to happen
2. **Use meaningful alert thresholds** - Adjust based on your usage patterns
3. **Monitor the monitors** - Set up alerts for Prometheus/Grafana downtime
4. **Review logs regularly** - Look for patterns before they become issues
5. **Keep dashboards updated** - Add new metrics as features are added

## Security Considerations

1. **Change default passwords** - Especially Grafana admin password
2. **Restrict port access** - Don't expose monitoring ports publicly
3. **Use HTTPS** - Put Grafana behind a reverse proxy with TLS
4. **Secure Alertmanager** - Don't expose web UI publicly
5. **Rotate credentials** - Regularly update API keys and passwords
