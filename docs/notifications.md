# Notifications & Alerts

Orion Sentinel supports multiple notification channels to alert you of security events in real-time.

## Supported Channels

### 📧 Email (SMTP)

Send email notifications via any SMTP server (Gmail, Office 365, SendGrid, etc.).

**Configuration:**

```bash
# .env
NOTIFY_SMTP_HOST=smtp.gmail.com
NOTIFY_SMTP_PORT=587
NOTIFY_SMTP_USER=your-email@gmail.com
NOTIFY_SMTP_PASS=your-app-password  # Use app-specific password for Gmail
NOTIFY_EMAIL_FROM=orion-sentinel@yourdomain.com
NOTIFY_EMAIL_TO=security-team@yourdomain.com,admin@yourdomain.com
NOTIFY_SMTP_USE_TLS=true
```

**Notes:**
- For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833)
- Multiple recipients: comma-separated email addresses
- Emails include HTML formatting with severity-based colors

### 📱 Signal

Send encrypted messages via Signal Messenger using signal-cli.

**Requirements:**
- [signal-cli](https://github.com/AsamK/signal-cli) with REST API enabled

**Configuration:**

```bash
# .env
NOTIFY_SIGNAL_ENABLED=true
NOTIFY_SIGNAL_API_URL=http://signal-cli:8080
NOTIFY_SIGNAL_NUMBER=+31612345678  # Your Signal number
NOTIFY_SIGNAL_RECIPIENTS=+31687654321,+31698765432  # Recipients
```

**Setup signal-cli:**

```bash
# Via Docker
docker run -d --name signal-cli \
  -p 8080:8080 \
  -v signal-cli-config:/home/.local/share/signal-cli \
  bbernhard/signal-cli-rest-api:latest

# Register/verify your number (one-time setup)
curl -X POST "http://localhost:8080/v1/register/+31612345678"
curl -X POST "http://localhost:8080/v1/register/+31612345678/verify/123456"
```

### 💬 Telegram

Send messages via Telegram Bot API.

**Setup:**

1. Create a bot with [@BotFather](https://t.me/botfather) on Telegram
2. Get your Chat ID: Message your bot and visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
3. Configure environment:

```bash
# .env
NOTIFY_TELEGRAM_ENABLED=true
NOTIFY_TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
NOTIFY_TELEGRAM_CHAT_ID=123456789  # Or multiple: 123456789,-987654321
```

**Notes:**
- Chat ID is your user ID or group ID (groups start with `-`)
- Messages use Markdown formatting
- Multiple chats: comma-separated IDs

### 🔗 Webhook

Send JSON POST requests to custom endpoints.

**Configuration:**

```bash
# .env
NOTIFY_WEBHOOK_URL=https://your-webhook.example.com/alerts
NOTIFY_WEBHOOK_TOKEN=your-bearer-token  # Optional
```

**Payload Format:**

```json
{
  "subject": "High-Risk Domain Detected",
  "message": "A high-risk domain has been detected...",
  "severity": "WARNING",
  "tags": ["domain_risk", "ai"],
  "metadata": {...},
  "timestamp": "2024-11-21T20:00:00Z"
}
```

## Notification Flow

1. **Event Detection**: AI, threat intel, or SOAR detects a security event
2. **Playbook Trigger**: SOAR playbook matches event conditions
3. **Action Execution**: Playbook's `SEND_NOTIFICATION` action fires
4. **Channel Dispatch**: Notification sent to all enabled channels
5. **Delivery**: Users receive alerts via Email, Signal, Telegram, and/or Webhook

## SOAR Integration

Notifications are triggered by SOAR playbooks via the `SEND_NOTIFICATION` action:

```yaml
# config/playbooks.yml
playbooks:
  - id: alert-high-risk-domain
    name: "Alert on High-Risk Domain Detection"
    enabled: true
    match_event_type: "domain_risk"
    conditions:
      - field: "metadata.risk_score"
        operator: ">="
        value: 0.85
    actions:
      - type: "SEND_NOTIFICATION"
        params:
          subject: "High-Risk Domain Detected"
          message: "Review and consider blocking this domain"
          severity: "WARNING"
```

## Notification Content

Notifications automatically include:

- **Event Details**: Type, severity, title, description
- **Device Information**: IP, device ID, tags
- **Threat Intelligence**: IOC matches, sources, confidence scores
- **Risk Context**: Risk score, reasons for alert
- **Actionable Info**: What was detected and why it matters

## Testing Notifications

Test your notification setup:

```python
from orion_ai.notifications import send_notification, Notification, NotificationSeverity

# Send test notification
notification = Notification(
    subject="Orion Sentinel Test Alert",
    message="This is a test notification. Your alert channels are working!",
    severity=NotificationSeverity.INFO,
    tags=["test"]
)

send_notification(notification)
```

## Troubleshooting

### Email Not Sending

- Check SMTP credentials and port
- Verify TLS settings match your provider
- Check firewall rules for outbound SMTP
- Review logs: `docker logs ai-service | grep NOTIFY`

### Signal Not Working

- Verify signal-cli is running: `curl http://localhost:8080/v1/about`
- Check number registration: Must be verified
- Ensure recipients are Signal users
- Check API URL accessibility from container

### Telegram Not Delivering

- Verify bot token with: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Ensure chat has received at least one message from user
- Check chat ID format (groups need `-` prefix)
- Test with Telegram's [API test tool](https://core.telegram.org/bots/api#making-requests)

## Best Practices

1. **Start with Email**: Easiest to set up, reliable delivery
2. **Use Signal for Critical Alerts**: End-to-end encrypted, push notifications
3. **Telegram for Team Coordination**: Good for group chats, easy setup
4. **Webhooks for Integration**: Connect to existing alerting/ticketing systems
5. **Configure Multiple Channels**: Redundancy ensures alerts are received
6. **Test Regularly**: Verify all channels weekly
7. **Severity Mapping**: Use appropriate severity levels (INFO, WARNING, CRITICAL)
8. **Rate Limiting**: Be mindful of notification frequency to avoid alert fatigue

## Advanced Configuration

### Custom Notification Templates

Create custom notifications in your code:

```python
from orion_ai.notifications import event_to_notification, send_notification
from orion_ai.core.models import Event, EventType, EventSeverity

# Convert event to notification with full context
event = Event(...)
notification = event_to_notification(
    event,
    include_device_info=True,
    include_ti_context=True
)

send_notification(notification)
```

### SOAR-Specific Notifications

For SOAR playbook execution alerts:

```python
from orion_ai.notifications import build_soar_notification

notification = build_soar_notification(
    event=triggering_event,
    playbook_name="Block High-Risk Domain",
    actions_taken=["Blocked domain via Pi-hole", "Tagged device"],
    dry_run=False
)

send_notification(notification)
```
