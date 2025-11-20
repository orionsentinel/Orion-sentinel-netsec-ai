# Device Inventory & Fingerprinting

## Overview

The inventory module tracks all devices on the network, classifies them, and maintains metadata for security analysis.

## Components

1. **Inventory Store** (`store.py`): SQLite database for device persistence
2. **Device Collector** (`collector.py`): Extracts device info from logs
3. **Device Fingerprinter** (`fingerprinting.py`): Classifies device types
4. **Inventory Service** (`service.py`): Continuous inventory updates

## Device Model

Each device has:

- **Identity**: IP, MAC, hostname
- **Classification**: Device type, tags, owner
- **Activity**: First/last seen, connection patterns
- **Risk**: Risk score, anomaly count, threat intel matches

## Device Types

The fingerprinter can identify:

- Smart TVs (Chromecast, Apple TV, Samsung, etc.)
- Printers
- NAS devices
- IP cameras
- Smart speakers
- Phones/tablets
- IoT devices
- Raspberry Pi
- Unknown

## Tagging System

Devices can have multiple tags:

- **Type tags**: `iot`, `media`, `security`, `office`, `storage`
- **Environment tags**: `lab`, `production`, `family`, `guest`
- **Risk tags**: `high-risk`, `medium-risk`, `anomalous`, `threat-indicator`
- **Custom tags**: Any user-defined tag

## Fingerprinting Heuristics

### Port-based

Devices are classified by open ports:

- Ports 8008, 8009 → Chromecast/Google TV
- Port 631 → Printer
- Ports 445, 139, 548 → NAS

### Destination-based

Devices are classified by domains they contact:

- `googleapis.com`, `googleusercontent.com` → Google device
- `apple.com`, `icloud.com` → Apple device
- `amazon.com`, `amazonaws.com` → Amazon device

### Vendor-based

MAC address OUI lookup identifies vendors.

## Data Collection

The collector extracts device information from:

1. **Suricata events**: Source/dest IPs, ports, protocols
2. **DNS queries**: Client IPs, queried domains
3. **Threat intel events**: Related IPs
4. **AI anomaly events**: Device behaviors

## Storage

Devices are stored in SQLite (`/data/inventory.db`) with indexes for:

- Last seen (for activity queries)
- Tags (for filtering)
- Risk score (for threat hunting)

## API Operations

```python
from orion_ai.inventory.store import InventoryStore

store = InventoryStore()

# Get device
device = store.get_device("192.168.1.50")

# Tag device
store.tag_device("192.168.1.50", "lab")

# List devices
devices = store.list_devices(limit=100)

# Get new devices
new = store.list_new_devices_since(datetime.utcnow() - timedelta(days=7))

# Get stats
stats = store.get_stats()
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `INVENTORY_POLL_INTERVAL` | `300` | Update interval (seconds) |
| `INVENTORY_DB_PATH` | `/data/inventory.db` | Database file path |
| `LOKI_URL` | `http://localhost:3100` | Loki instance URL |

## Running the Service

```bash
cd stacks/ai
docker-compose up inventory
```

## Integration with SOAR

SOAR playbooks can:

- Tag devices automatically
- Filter actions by device tags
- React to new device events

Example:

```yaml
- action_type: TAG_DEVICE
  parameters:
    device_ip: "{{fields.device_ip}}"
    tag: suspicious
```

## Grafana Dashboards

Recommended panels:

- Total devices over time
- New devices (last 7 days)
- Unknown/untagged devices
- Device type breakdown (pie chart)
- High-risk devices
- Device activity heatmap

## Loki Queries

```logql
# New device events
{service="inventory", stream="inventory_event"} | json | event_type="new_device"

# Devices by tag
{service="inventory"} | json | tags=~".*lab.*"
```

## Best Practices

1. **Tag devices promptly**: Helps with risk assessment
2. **Review unknown devices**: Investigate unclassified devices
3. **Set device owners**: Accountability for security
4. **Monitor new devices**: Alert on unexpected additions
5. **Periodic audits**: Review inventory for inactive devices

## Future Enhancements

- [ ] MAC vendor lookup (OUI database)
- [ ] Active fingerprinting (nmap integration)
- [ ] DHCP log integration
- [ ] Network segment awareness
- [ ] Device relationship mapping
- [ ] Automated type detection improvement via ML
# Device Inventory

## Overview

The device inventory module automatically discovers and tracks all devices on your network by analyzing NSM (Suricata) and DNS logs.

## Features

- **Automatic Discovery**: Devices are automatically discovered from Suricata flow records and DNS queries
- **Stable Identifiers**: Each device gets a stable ID based on MAC address (when available) or IP
- **Metadata Tracking**: Tracks IP, MAC, hostname, first/last seen timestamps
- **Tagging**: Support for custom tags (e.g., "iot", "trusted", "lab")
- **Type Guessing**: Attempts to guess device type from hostname patterns
- **SQLite Storage**: Lightweight persistence in `/var/lib/orion-ai/devices.db`

## Device Model

Each device has the following attributes:

- `device_id`: Unique stable identifier (hash of MAC/IP)
- `ip`: Current IP address
- `mac`: MAC address (optional)
- `hostname`: DNS hostname (optional)
- `first_seen`: Timestamp when first observed
- `last_seen`: Timestamp when last observed
- `tags`: List of user-defined tags
- `guess_type`: Guessed device type (TV, phone, laptop, etc.)
- `owner`: Device owner (optional)

## Services

### Inventory Service

The inventory service runs periodically (default: every 10 minutes) and:

1. Queries Suricata flows and DNS logs from Loki
2. Extracts device information (IP, MAC, hostname)
3. Updates or creates device records
4. Emits `new_device` events for newly discovered devices
5. Attempts to guess device type from hostname patterns

### Configuration

Set via environment variables:

```bash
# How often to run device discovery
INVENTORY_INTERVAL_MINUTES=10

# How far back to look for devices
INVENTORY_LOOKBACK_MINUTES=15
```

## Device Tagging

Devices can be tagged for organization and SOAR playbook targeting:

- Manually via UI (planned)
- Automatically via SOAR playbooks (e.g., tag devices with anomalies)
- Via API: `POST /api/device/{device_id}/tag`

Common tags:
- `trusted`: Known safe devices
- `iot`: IoT devices (sensors, cameras, smart home)
- `lab`: Lab/experimental devices
- `guest`: Guest devices
- `anomalous`: Devices with detected anomalies
- `threat-intel-match`: Devices that contacted known bad indicators

## Device Types

The inventory module attempts to guess device types based on hostname patterns:

- `phone`: iPhone, Android, mobile
- `TV`: Roku, Chromecast, AppleTV
- `NAS`: Synology, QNAP
- `laptop`: MacBook, ThinkPad
- `desktop`: iMac, PC
- `iot`: Cameras, sensors, doorbells
- `printer`: Printers, scanners
- `unknown`: Could not determine type

## Web UI

The device inventory is accessible via:

- `/devices` - List all devices with filtering and search
- `/device/{device_id}` - Detailed device profile with timeline and events

## API Endpoints

- `GET /api/devices` - List devices (supports `?tag=` and `?search=` filters)
- `GET /api/device/{device_id}` - Get device profile

## Future Enhancements

- [ ] Manual device classification via UI
- [ ] Device ownership assignment
- [ ] Network segmentation visualization
- [ ] Device behavior baselining
- [ ] Automatic device grouping
