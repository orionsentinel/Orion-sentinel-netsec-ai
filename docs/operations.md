# Operations Guide

This guide covers operational procedures for the Orion Sentinel NSM + AI platform, including backup, restore, upgrade, development mode, and monitoring.

## Table of Contents

- [Backup & Restore](#backup--restore)
- [Upgrade Procedure](#upgrade-procedure)
- [Development Mode](#development-mode)
- [Resource Monitoring](#resource-monitoring)
- [Troubleshooting](#troubleshooting)

## Backup & Restore

### Creating Backups

The `scripts/backup-all.sh` script creates timestamped backups of all critical system state and configuration.

**What is backed up:**

- Device inventory database (`data/inventory.db`)
- All state files in `data/` and `var/` directories
- Configuration files (`config/*.yml`, `.env` files)
- SOAR playbooks (`config/playbooks.yml`)
- Grafana dashboard configurations
- AI models manifest (list of model files, not the models themselves due to size)
- Current git commit hash and status

**Usage:**

```bash
cd /path/to/Orion-sentinel-netsec-ai
./scripts/backup-all.sh
```

**Output:**

Backups are stored in `backups/backup_YYYYMMDD_HHMMSS/` with a manifest file listing all backed-up files.

**Backup Location:**

```
backups/
├── backup_20250115_103045/
│   ├── backup_manifest.txt
│   ├── git_commit.txt
│   ├── git_status.txt
│   ├── ai_models_manifest.txt
│   ├── config/
│   │   └── playbooks.yml
│   ├── data/
│   │   └── inventory.db
│   └── stacks/
│       ├── nsm/
│       │   └── .env
│       └── ai/
│           └── .env
└── backup_20250116_140530/
    └── ...
```

**Best Practices:**

- Create backups before upgrades (automated by `upgrade.sh`)
- Create backups before major configuration changes
- Schedule periodic backups via cron (e.g., daily at 2 AM):
  ```bash
  0 2 * * * cd /home/pi/Orion-sentinel-netsec-ai && ./scripts/backup-all.sh >> /var/log/orion-backup.log 2>&1
  ```
- Keep at least 7 days of backups
- Store critical backups off-device (external drive, NAS, etc.)

### Restoring from Backup

The `scripts/restore-all.sh` script restores system state from a backup directory.

**Usage:**

```bash
# List available backups
ls -lt backups/

# Restore from a specific backup
./scripts/restore-all.sh backups/backup_20250115_103045
```

**Restore Process:**

1. Script displays backup information and files to be restored
2. Prompts for confirmation (type `y` to proceed)
3. Restores configuration files and state data
4. Displays git state information (for reference only)
5. Provides next steps for manual components

**What is restored automatically:**

- Device inventory database
- Configuration files
- Environment variables (`.env` files)
- Grafana configurations

**Manual restore required for:**

- **Loki data volumes**: Time-series log data stored in Docker volumes
  ```bash
  # Stop Loki
  docker compose -f stacks/nsm/docker-compose.yml stop loki
  
  # Manually copy volume data if you have volume backups
  # (This is advanced - see Docker volume backup strategies)
  
  # Restart Loki
  docker compose -f stacks/nsm/docker-compose.yml start loki
  ```

- **AI model files**: Large binary files not included in standard backups
  - Copy models from your model storage to `stacks/ai/models/`

**After Restore:**

1. Review and update environment-specific settings in `.env` files
2. Restart services:
   ```bash
   cd stacks/nsm && docker compose up -d
   cd stacks/ai && docker compose up -d
   ```
3. Verify services are running:
   ```bash
   docker compose ps
   ```

## Upgrade Procedure

The `scripts/upgrade.sh` script performs a safe, automated upgrade.

### Upgrade Steps

**Automated Process:**

```bash
./scripts/upgrade.sh
```

The script performs these steps:

1. **Environment checks**: Verifies git, docker, and docker compose are installed
2. **Displays current state**: Shows current branch and commit
3. **Creates backup**: Runs `backup-all.sh` automatically
4. **Pulls changes**: Fetches and pulls latest code from git
5. **Updates Docker images**: Pulls latest container images for NSM and AI stacks
6. **Restarts services**: Brings up updated containers
7. **Verification**: Shows service status

### Recommended Upgrade Workflow

1. **Review release notes** (if available in repository)
2. **Test in development mode** first (see [Development Mode](#development-mode))
3. **Run upgrade during maintenance window**:
   ```bash
   ./scripts/upgrade.sh
   ```
4. **Monitor logs** after upgrade:
   ```bash
   # NSM stack
   docker compose -f stacks/nsm/docker-compose.yml logs -f
   
   # AI stack
   docker compose -f stacks/ai/docker-compose.yml logs -f
   ```
5. **Verify dashboards**: Check Grafana at `http://<pi-ip>:3000`
6. **Test API endpoints**: Check API docs at `http://<pi-ip>:8000/docs`

### Rollback Procedure

If issues occur after upgrade:

1. **Restore from backup**:
   ```bash
   ./scripts/restore-all.sh backups/backup_<timestamp>
   ```

2. **Revert to previous git commit** (if needed):
   ```bash
   # Check commit from backup
   cat backups/backup_<timestamp>/git_commit.txt
   
   # Revert to that commit
   git checkout <commit-hash>
   ```

3. **Restart services**:
   ```bash
   cd stacks/nsm && docker compose up -d
   cd stacks/ai && docker compose up -d
   ```

## Development Mode

Development mode allows you to test and develop dashboards and AI services using synthetic sample data without affecting production.

### Dev Environment Setup

**1. Sample Data**

Sample data files are provided in the `samples/` directory:

- `samples/suricata-eve.json`: Synthetic Suricata IDS alerts
- `samples/pihole-dns.log`: Dummy DNS queries
- `samples/intel_matches.json`: Sample threat intelligence matches

**2. Start Dev Stack**

```bash
cd stacks/nsm
docker compose -f docker-compose.dev.yml up -d
```

The dev stack includes:

- Loki (log storage)
- Grafana (dashboards)
- Log injector service (reads samples and pushes to Loki)

**3. Development Workflow**

```bash
# Edit dashboard configurations
vi config/grafana/dashboards/*.json

# Restart Grafana to reload
docker compose -f stacks/nsm/docker-compose.dev.yml restart grafana

# View logs
docker compose -f stacks/nsm/docker-compose.dev.yml logs -f log-injector
```

**4. Testing AI Services**

```bash
cd stacks/ai

# Set dev mode environment
export LOKI_URL=http://localhost:3100
export SOAR_DRY_RUN=1

# Run service locally
python -m orion_ai.soar.service

# Or in container
docker compose -f docker-compose.dev.yml up -d
```

**5. Accessing Dev Environment**

- Grafana: `http://localhost:3000` (admin/admin)
- Loki API: `http://localhost:3100`
- API Server: `http://localhost:8000` (if running)

### Sample Data Generation

To add your own sample data:

1. Copy real log samples (sanitized/anonymized):
   ```bash
   # Example: Export Suricata logs
   cat /var/log/suricata/eve.json | head -100 > samples/suricata-eve.json
   ```

2. Manually create synthetic events matching the expected schema

3. Update `samples/README.md` with data format documentation

## Resource Monitoring

### Container Resource Usage

Monitor CPU, memory, and disk usage of containers:

**Option 1: Docker stats (built-in)**

```bash
# Real-time stats for all containers
docker stats

# Stats for specific stack
docker compose -f stacks/nsm/docker-compose.yml ps -q | xargs docker stats
```

**Option 2: Metrics Stack (Optional)**

For historical metrics and alerting, use the metrics compose file:

```bash
cd stacks/nsm
docker compose -f docker-compose.metrics.yml up -d
```

This adds:

- **node-exporter**: System metrics (CPU, RAM, disk, network)
- **cAdvisor**: Container metrics
- Prometheus (optional): Metrics storage and querying
- Grafana dashboard: Resource usage visualization

**Access metrics:**

- Node exporter metrics: `http://<pi-ip>:9100/metrics`
- cAdvisor UI: `http://<pi-ip>:8080`
- Grafana dashboard: Add Prometheus datasource and import dashboard

### Pi Resource Monitoring

**Check system resources:**

```bash
# CPU and memory
htop

# Disk usage
df -h

# Temperature (Raspberry Pi)
vcgencmd measure_temp

# Container disk usage
docker system df
```

**View container logs:**

```bash
# Follow logs for a service
docker compose -f stacks/nsm/docker-compose.yml logs -f loki

# Last 100 lines
docker compose -f stacks/nsm/docker-compose.yml logs --tail=100 suricata

# Logs since timestamp
docker compose -f stacks/nsm/docker-compose.yml logs --since 2024-01-15T10:00:00
```

**Check container restarts:**

```bash
# Show restart count
docker compose -f stacks/nsm/docker-compose.yml ps

# Inspect restart history
docker inspect orion-loki | grep -A 10 RestartCount
```

### Performance Tuning

**For Raspberry Pi 5:**

1. **Ensure adequate cooling** - AI Hat generates heat
2. **Use quality SD card** - A2 rated recommended
3. **Monitor swap usage** - Avoid excessive swapping:
   ```bash
   free -h
   ```
4. **Adjust log retention** in `stacks/nsm/loki/loki-config.yaml`:
   ```yaml
   limits_config:
     retention_period: 168h  # 7 days (adjust as needed)
   ```

## Troubleshooting

### Common Issues

**Services not starting:**

```bash
# Check logs
docker compose logs <service-name>

# Check disk space
df -h

# Check memory
free -h

# Restart specific service
docker compose restart <service-name>
```

**Loki not receiving logs:**

```bash
# Verify Promtail is running
docker compose ps promtail

# Check Promtail logs
docker compose logs promtail

# Test Loki API
curl http://localhost:3100/ready
```

**Grafana dashboards empty:**

1. Check Loki datasource connection in Grafana
2. Verify logs are in Loki:
   ```bash
   curl -G -s "http://localhost:3100/loki/api/v1/query" \
     --data-urlencode 'query={job="suricata"}' | jq
   ```
3. Check dashboard time range

**High CPU/Memory usage:**

```bash
# Identify resource-heavy container
docker stats

# Review service logs for errors
docker compose logs <service-name>

# Adjust resource limits in docker-compose.yml if needed
```

**AI service errors:**

```bash
# Check AI service logs
docker compose -f stacks/ai/docker-compose.yml logs -f

# Verify AI Hat is detected (on Pi)
ls /dev/hailo*

# Check model files exist
ls -lh stacks/ai/models/
```

### Getting Help

1. Check service logs first
2. Review documentation in `docs/`
3. Search existing GitHub issues
4. Open a new issue with:
   - Description of problem
   - Steps to reproduce
   - Relevant log excerpts
   - Environment info (Pi model, OS version, Docker version)

## Maintenance Tasks

### Regular Maintenance Checklist

**Weekly:**
- [ ] Check container status: `docker compose ps`
- [ ] Review logs for errors
- [ ] Verify disk space: `df -h`

**Monthly:**
- [ ] Create backup: `./scripts/backup-all.sh`
- [ ] Update system packages: `sudo apt update && sudo apt upgrade`
- [ ] Clean old Docker images: `docker image prune -a`
- [ ] Review Grafana dashboards for anomalies

**Quarterly:**
- [ ] Test restore procedure
- [ ] Review and update SOAR playbooks
- [ ] Update threat intelligence feeds
- [ ] Review security configurations (see [Threat Model](threat-model.md))

### Log Rotation

Docker handles log rotation for containers (configured in docker-compose.yml):

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

To adjust, edit docker-compose.yml and restart services.

### Cleaning Up

**Remove old backups:**

```bash
# Keep only last 10 backups
cd backups
ls -t | tail -n +11 | xargs rm -rf
```

**Clean Docker resources:**

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (CAREFUL - this removes data!)
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

## See Also

- [Threat Model & Security](threat-model.md)
- [Architecture Documentation](architecture.md)
- [SOAR Playbooks](soar.md)
- [Development Setup](../README.md#development-setup)
