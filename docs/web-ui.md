# Web UI Guide

Orion Sentinel provides a simple, focused web interface for SOC operations.

## Access

**Default URL**: `http://your-pi-ip:8080`

**Configuration**:

```bash
# .env
API_HOST=0.0.0.0
API_PORT=8080
```

## Pages

### 🏠 Dashboard

**URL**: `/`

**Overview**:
- Security Health Score (0-100)
- Recent security events (last 24h)
- Device statistics (total, unknown, recently active)
- Top suspicious devices

**Use Case**: Daily security posture check at a glance.

---

### 📱 Devices

**URL**: `/devices`

**Features**:
- Complete device inventory
- Filter by tags
- Search by IP, hostname, or MAC
- Risk level indicators
- Alert counts per device

**Actions**:
- Click device to view detailed profile
- Tag devices for classification
- Review device timeline

**Use Case**: Asset management, device classification, investigating specific hosts.

---

### 🚨 Events

**URL**: `/events`

**Features**:
- Searchable security event log
- Filter by severity (INFO, WARNING, CRITICAL)
- Filter by event type (threat intel match, anomaly, domain risk, etc.)
- Time range selection (1 hour to 1 week)
- Full event details with TI context

**Columns**:
- Timestamp
- Severity badge
- Event type
- Title
- Device IP
- Source (ai, threat_intel, soar)
- Description

**Use Case**: Incident investigation, trend analysis, alert review.

---

### 🤖 Playbooks

**URL**: `/playbooks`

**Features**:
- List all SOAR playbooks
- View playbook status (enabled/disabled)
- See dry-run vs production mode
- Enable/disable playbooks with one click
- Expand playbook details (conditions & actions)
- Statistics (enabled count, dry-run count)

**Playbook Details** (click row to expand):
- Matching conditions
- Configured actions
- Priority level
- Event type filter

**Actions**:
- Toggle playbook enabled/disabled
- View configuration

**Use Case**: SOAR management, playbook debugging, testing automation.

---

### ⚙️ Settings

**URL**: `/settings`

**Status**: Placeholder (future implementation)

**Planned Features**:
- Toggle features on/off
- Adjust detection thresholds
- Configure integrations
- Manage API keys
- System health checks

---

## API Endpoints

All pages have corresponding JSON API endpoints:

### Health Score

```bash
GET /api/health
```

**Response**:

```json
{
  "score": 85,
  "status": "Good",
  "metrics": {...}
}
```

---

### Events

```bash
GET /api/events?limit=50&hours=24&severity=CRITICAL
```

**Parameters**:
- `limit`: Max events (1-500, default: 50)
- `hours`: Look back window (1-168, default: 24)
- `severity`: Filter by severity (INFO/WARNING/CRITICAL)
- `type`: Filter by event type

**Response**:

```json
{
  "events": [...],
  "count": 42
}
```

---

### Devices

```bash
GET /api/devices?tag=lab&search=192.168
```

**Parameters**:
- `tag`: Filter by tag
- `search`: Search term (IP, hostname, MAC)

**Response**:

```json
{
  "devices": [
    {
      "device_id": "...",
      "ip": "192.168.1.50",
      "hostname": "server-01",
      "tags": ["lab", "monitored"],
      "alert_count": 3,
      "risk_level": "medium"
    }
  ],
  "count": 15
}
```

---

### Device Profile

```bash
GET /api/device/{device_id}
```

**Response**:

```json
{
  "device": {...},
  "events": [...],
  "event_counts": {
    "intel_match": 2,
    "device_anomaly": 1,
    "domain_risk": 4
  },
  "timeline": [...]
}
```

---

### Playbooks

```bash
GET /api/playbooks
```

**Response**:

```json
{
  "playbooks": [
    {
      "id": "alert-high-risk-domain",
      "name": "Alert on High-Risk Domain Detection",
      "enabled": true,
      "match_event_type": "domain_risk",
      "dry_run": false,
      "priority": 10,
      "conditions": [...],
      "actions": [...]
    }
  ],
  "count": 6,
  "enabled_count": 5,
  "disabled_count": 1,
  "dry_run_count": 1
}
```

---

### Toggle Playbook

```bash
POST /api/playbooks/{playbook_id}/toggle
Content-Type: application/json

{
  "enabled": false
}
```

**Response**:

```json
{
  "success": true,
  "playbook": {...}
}
```

---

### Configuration

```bash
GET /api/config
```

**Response**:

```json
{
  "detection": {
    "device_window_minutes": 60,
    "domain_window_minutes": 30,
    "enable_blocking": false
  },
  "model": {
    "device_anomaly_threshold": 0.8,
    "domain_risk_threshold": 0.85
  },
  "threat_intel": {
    "enabled": true,
    "refresh_interval_hours": 4
  }
}
```

---

## Design Philosophy

The web UI follows a "SOC wallboard" approach:

- **Minimal, Not Overwhelming**: Focus on actionable information
- **Read-Mostly**: Most pages are view-only (playbook toggle is the exception)
- **No Authentication**: Designed for internal/trusted networks
- **Fast & Lightweight**: No heavy JavaScript frameworks
- **Auto-Refresh Ready**: Pages can be set to auto-refresh for monitoring

## Development

### Running Locally

```bash
cd stacks/ai/src
python -m orion_ai.ui.api
```

**Access**: `http://localhost:8080`

### Custom Styling

Templates use inline CSS for simplicity. To customize:

1. Edit `src/orion_ai/ui/templates/base.html`
2. Modify the `<style>` block
3. Changes apply to all pages

### Adding New Pages

1. Create template in `src/orion_ai/ui/templates/`
2. Add view function in `src/orion_ai/ui/views.py`
3. Add route in `src/orion_ai/ui/api.py`
4. Update navigation in `base.html`

**Example**:

```python
# views.py
def get_my_view() -> Dict[str, Any]:
    return {"data": "..."}

# api.py
@app.get("/my-page", response_class=HTMLResponse)
async def my_page(request: Request):
    data = views.get_my_view()
    return templates.TemplateResponse("my_page.html", {"request": request, **data})
```

## Security Considerations

- **No Built-In Auth**: Use reverse proxy (nginx, traefik) for authentication
- **Internal Use Only**: Not designed for public exposure
- **API Access**: All endpoints accessible without credentials
- **HTTPS**: Use reverse proxy for TLS termination
- **Rate Limiting**: Not implemented (use reverse proxy)

**Recommended nginx config**:

```nginx
server {
    listen 443 ssl;
    server_name orion.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Basic auth for additional security
    auth_basic "Orion Sentinel SOC";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    location / {
        proxy_pass http://192.168.1.5:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Page Not Loading

```bash
# Check if service is running
docker ps | grep ai-service

# Check logs
docker logs ai-service | grep uvicorn

# Verify port mapping
docker-compose ps
```

### Events Not Showing

- Check Loki connectivity: `curl http://loki:3100/ready`
- Verify events are being written to Loki
- Check time range filter (default: 24 hours)

### Playbooks Not Loading

- Check `config/playbooks.yml` exists
- Verify YAML syntax: `yamllint config/playbooks.yml`
- Check file permissions
- Review logs for parsing errors

### Slow Performance

- Check database size: `du -h data/*.db`
- Run cleanup: `python -m orion_ai.threat_intel.sync --stats`
- Reduce time windows on queries
- Consider adding indexes to Loki queries

## Roadmap

Planned enhancements:

- [ ] **Authentication**: OAuth2/OIDC integration
- [ ] **User Preferences**: Dark mode, custom refresh intervals
- [ ] **Export**: CSV/JSON export for events and devices
- [ ] **Grafana Integration**: Embed Grafana panels in dashboard
- [ ] **Live Updates**: WebSocket for real-time event stream
- [ ] **Advanced Filters**: Save filter presets
- [ ] **Device Actions**: Bulk tagging, manual event creation
- [ ] **Playbook Editor**: Visual playbook builder (currently YAML-only)

## Comparison with Grafana

**Web UI**:
- Quick device/event lookup
- SOAR playbook management
- Simplified security operations
- Focused on actionable data

**Grafana** (keep using for):
- Time-series dashboards
- Custom visualizations
- Long-term trend analysis
- Drill-down analytics

**Use Both**: Web UI for daily ops, Grafana for analysis and dashboards.
