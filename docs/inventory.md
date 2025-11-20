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
