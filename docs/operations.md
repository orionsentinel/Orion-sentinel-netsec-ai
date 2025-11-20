# Operations Guide

This guide covers operational procedures for the Orion Sentinel NSM+AI system, including backups, restores, upgrades, and development workflows.

## Table of Contents

- [Backup and Restore](#backup-and-restore)
- [Upgrades](#upgrades)
- [Development Mode](#development-mode)
- [Resource Monitoring](#resource-monitoring)
- [Troubleshooting](#troubleshooting)

## Backup and Restore

### Creating a Backup

The `backup-all.sh` script creates a timestamped backup of your system state and configuration:

```bash
./scripts/backup-all.sh
```

**What gets backed up:**
- Configuration files (`config/*.yml`, environment examples)
- SQLite databases and JSON state files (inventory, SOAR state, etc.)
- Git commit information (for version tracking)
- AI models manifest (list of models, not the files themselves)
- Docker Compose configurations

**What is NOT backed up:**
- AI model files (too large - tracked in manifest instead)
- Loki log data (regenerates from live sources)
- Grafana dashboards (auto-provisioned from code)
- Suricata rule files (downloaded on startup)
- Docker volumes (requires separate backup procedure)
- `.env` files (contain secrets - not safe to backup)

**Backup location:** `backups/backup-YYYYMMDD-HHMMSS/`

Each backup includes:
- `BACKUP-SUMMARY.txt` - Overview of backup contents
- `backup-manifest.txt` - Detailed list of backed up files
- `git-commit.txt` - Git commit information at backup time
- `ai-models-manifest.txt` - List of AI models (not the models themselves)

### Restoring from Backup

To restore from a backup:

```bash
./scripts/restore-all.sh backups/backup-20241120-143022
```

The script will:
1. Display a summary of the backup contents
2. Show which files will be restored
3. Ask for confirmation
4. Restore configuration and data files

**Important notes:**
- You must recreate `.env` files manually (they're not backed up for security)
- Services may need to be restarted after restore
- Loki data and Docker volumes require manual restoration

### Advanced: Docker Volume Backup

For complete disaster recovery, also backup Docker volumes:

```bash
# Backup Loki data volume
docker run --rm \
  -v orion-loki-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/loki-data-$(date +%Y%m%d).tar.gz -C /data .

# Backup Grafana data volume  
docker run --rm \
  -v orion-grafana-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/grafana-data-$(date +%Y%m%d).tar.gz -C /data .
```

To restore a volume:

```bash
# Stop services first
cd stacks/nsm && docker compose down

# Restore Loki data
docker run --rm \
  -v orion-loki-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/loki-data-20241120.tar.gz -C /data

# Restart services
docker compose up -d
```

## Upgrades

### Recommended Upgrade Procedure

The `upgrade.sh` script automates the upgrade process:

```bash
./scripts/upgrade.sh
```

**Upgrade steps:**
1. **Pre-flight checks** - Verifies git and docker are available
2. **Automatic backup** - Creates backup of current state
3. **Git pull** - Pulls latest code from repository
4. **Docker image pull** - Pulls latest container images
5. **Service restart** - Restarts all services with new code/images

**Options:**
- `--skip-backup` - Skip backup step (not recommended)
- `--skip-docker` - Skip docker operations (for code-only updates)

### Manual Upgrade Steps

If you prefer to upgrade manually:

```bash
# 1. Create backup
./scripts/backup-all.sh

# 2. Pull latest code
git fetch origin
git pull origin main

# 3. Update dependencies (if needed)
pip install -r requirements.txt --upgrade

# 4. Pull and restart NSM stack
cd stacks/nsm
docker compose pull
docker compose up -d
cd ../..

# 5. Pull and restart AI stack
cd stacks/ai
docker compose pull
docker compose up -d
cd ../..

# 6. Verify services are running
cd stacks/nsm && docker compose ps
cd ../ai && docker compose ps
```

### Rollback Procedure

If an upgrade fails:

```bash
# 1. Revert to previous git commit
git log --oneline -10  # Find the commit hash
git checkout <previous-commit-hash>

# 2. Restore from backup
./scripts/restore-all.sh backups/backup-<timestamp>

# 3. Restart services
cd stacks/nsm && docker compose restart
cd ../ai && docker compose restart
```

## Development Mode

Development mode allows you to test the system with sample data without requiring a real network setup.

### Starting Dev Environment

```bash
cd stacks/nsm
docker compose -f docker-compose.dev.yml up -d
```

This starts:
- Loki (log aggregation)
- Grafana (dashboards)
- Log injector service (pushes sample data to Loki)

### Sample Data

Sample data is provided in the `samples/` directory:
- `suricata-eve.json` - Synthetic Suricata IDS alerts
- `pihole-dns.log` - Sample DNS query logs
- `intel_matches.json` - Sample threat intelligence matches

The dev environment's log injector service reads these files and pushes them to Loki with appropriate labels, simulating a production environment.

### Developing Dashboards

With dev mode running:

1. Access Grafana at `http://localhost:3000`
2. Default credentials: admin/admin
3. Dashboards auto-provision from `stacks/nsm/grafana/dashboards/`
4. Query sample data using Loki data source
5. Edit dashboards and export as JSON
6. Save exported JSON to `stacks/nsm/grafana/dashboards/` for version control

### Testing SOAR Playbooks

Test playbooks in dry-run mode:

```bash
# Edit playbooks
nano config/playbooks.yml

# Set dry-run mode in AI stack
cd stacks/ai
# In docker-compose.yml, ensure SOAR_DRY_RUN=1

# Restart SOAR service
docker compose restart soar

# Watch logs
docker compose logs -f soar
```

## Resource Monitoring

### Monitoring Pi Resource Usage

Check CPU, memory, and disk usage:

```bash
# Overall system resources
htop

# Docker container resource usage
docker stats

# Disk usage
df -h
du -sh stacks/*/
```

### Optional: Metrics Stack

For detailed monitoring, deploy the metrics stack:

```bash
cd stacks/nsm
docker compose -f docker-compose.metrics.yml up -d
```

This adds:
- **node-exporter** - Host metrics (CPU, RAM, disk, network)
- **cAdvisor** - Container metrics
- Prometheus dashboard in Grafana

Access metrics dashboard at: `http://localhost:3000/d/node-exporter`

### Container Health Checks

View container status and restarts:

```bash
# NSM stack
cd stacks/nsm
docker compose ps

# AI stack  
cd stacks/ai
docker compose ps

# View logs for a specific service
docker compose logs -f loki
docker compose logs -f soar

# Check for restart loops
docker ps -a --filter "status=restarting"
```

### Log Management

Logs are automatically rotated by Docker (configured in compose files):
- Max size: 10MB per file
- Max files: 3

To view logs:

```bash
# Recent logs
docker compose logs --tail=100 service-name

# Follow logs in real-time
docker compose logs -f service-name

# Logs with timestamps
docker compose logs -t service-name
```

### Disk Space Management

Loki and Suricata can consume significant disk space. Monitor and clean up:

```bash
# Check Loki data size
du -sh stacks/nsm/loki/data/

# Check Suricata logs
du -sh /var/log/suricata/

# Clean old Docker images
docker image prune -a

# Clean old Docker volumes (CAUTION: data loss)
docker volume prune
```

Set Loki retention policy in `stacks/nsm/loki/loki-config.yaml`:

```yaml
limits_config:
  retention_period: 168h  # 7 days
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs service-name

# Common issues:
# 1. Port already in use
sudo netstat -tlnp | grep :3100  # Loki
sudo netstat -tlnp | grep :3000  # Grafana

# 2. Permission issues
ls -la stacks/nsm/loki/data/
# Fix: sudo chown -R 10001:10001 stacks/nsm/loki/data/

# 3. Config file errors
docker compose config  # Validates compose file
```

### Grafana Dashboard Not Loading

```bash
# 1. Check Grafana is running
docker compose ps grafana

# 2. Check Loki connection
docker compose exec grafana wget -O- http://loki:3100/ready

# 3. Re-provision dashboards
docker compose restart grafana
docker compose logs -f grafana
```

### High CPU/Memory Usage

```bash
# Identify resource-heavy containers
docker stats --no-stream

# Common culprits:
# - Suricata (packet processing)
# - AI services (model inference)
# - Loki (indexing/querying)

# Reduce Suricata resource usage:
# Edit stacks/nsm/suricata/suricata.yaml
# Reduce worker threads

# Reduce AI service frequency:
# Edit stacks/ai/docker-compose.yml
# Increase INVENTORY_POLL_INTERVAL, SOAR_POLL_INTERVAL
```

### Network Connectivity Issues

```bash
# Check Docker networks
docker network ls
docker network inspect orion-network

# Test connectivity between containers
docker compose exec soar ping loki
docker compose exec promtail wget -O- http://loki:3100/ready

# Restart network
docker compose down
docker compose up -d
```

### Database/State Corruption

```bash
# 1. Stop services
docker compose down

# 2. Restore from backup
./scripts/restore-all.sh backups/backup-<timestamp>

# 3. Restart services
docker compose up -d

# If no backup available, reset state:
rm data/*.db
docker compose up -d
# Services will recreate databases
```

## Maintenance Schedule

Recommended maintenance tasks:

### Daily
- Check container health: `docker compose ps`
- Review critical alerts in Grafana

### Weekly
- Create backup: `./scripts/backup-all.sh`
- Review disk usage: `df -h`
- Check for service restarts

### Monthly
- System upgrade: `./scripts/upgrade.sh`
- Clean old backups (keep last 4 weeks)
- Update Suricata rules: `docker compose exec suricata suricata-update`
- Review and tune playbooks

### Quarterly
- Full system backup including Docker volumes
- Review threat model and security posture
- Update documentation for any configuration changes

## See Also

- [Threat Model](threat-model.md) - Security considerations
- [Architecture](architecture.md) - System design and components
- [SOAR Guide](soar.md) - Playbook configuration
- [README](../README.md) - Getting started
