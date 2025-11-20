# Operations Guide

This guide covers backup, restore, upgrade procedures, and resource monitoring for Orion Sentinel NSM AI.

## Overview

Orion Sentinel provides three core operational scripts for safe management:

- **`scripts/backup-all.sh`**: Creates timestamped backups of configuration and state
- **`scripts/restore-all.sh`**: Restores from a backup with confirmation
- **`scripts/upgrade.sh`**: Safe upgrade workflow with automatic backup

## Backup

### What Gets Backed Up

The backup script creates a comprehensive snapshot including:

1. **Metadata**
   - Current git commit hash and branch
   - Timestamp and hostname
   - Git status (modified files)

2. **Configuration Files**
   - `config/` directory (playbooks, etc.)
   - `.env` files (NSM stack, AI stack, root)
   - Suricata, Loki, Promtail, Grafana configs
   - AI service configuration

3. **State and Inventory**
   - SQLite databases (`*.db`) - device inventory, etc.
   - JSON state files - intel cache, baselines, etc.
   - Threat intelligence cache

4. **AI Models Manifest**
   - File listing of models directory (not the models themselves)
   - Note: Models are too large to backup; download separately

### What Does NOT Get Backed Up

- **Loki data** (logs) - large volume, use Loki object storage or snapshots
- **AI model files** (`.onnx`, `.tflite`) - download separately, see docs
- **Grafana runtime data** - dashboards are provisioned from config
- **Suricata logs** (`.eve.json`) - archived separately if needed
- **Docker volumes data** - backup using Docker volume commands if needed

### Running a Backup

```bash
# From repository root
./scripts/backup-all.sh
```

Output:
```
==> Orion Sentinel Backup
Backup directory: /home/pi/orion-sentinel-nsm-ai/backups/backup_20250120_143022

[1/6] Backing up metadata...
   ✓ Created metadata.txt
[2/6] Backing up configuration files...
   ✓ Backed up config/
   ✓ Backed up NSM stack configs
   ✓ Backed up AI stack configs
...
==> Backup completed successfully!
Backup location: .../backups/backup_20250120_143022
```

### Backup Location

Backups are stored in:
```
backups/backup_YYYYMMDD_HHMMSS/
├── metadata.txt              # Backup metadata
├── BACKUP_SUMMARY.txt        # Human-readable summary
├── models_manifest.txt       # AI models listing
├── config/                   # Configuration files
├── stacks/
│   ├── nsm/                  # NSM stack configs
│   └── ai/                   # AI stack configs
├── data/                     # SQLite databases
└── var/                      # State files
```

### Backup Best Practices

1. **Before upgrades**: Always backup before running upgrades (automatic in `upgrade.sh`)
2. **Regular schedule**: Run weekly backups via cron:
   ```bash
   # Add to crontab (weekly on Sunday at 2 AM)
   0 2 * * 0 /home/pi/orion-sentinel-nsm-ai/scripts/backup-all.sh
   ```
3. **Retention**: Keep at least 3 recent backups, remove old ones manually
4. **Off-site**: Copy important backups to external storage or network share
5. **Test restores**: Periodically test restore process in dev environment

## Restore

### Usage

```bash
# Restore from a specific backup
./scripts/restore-all.sh backups/backup_20250120_143022
```

### Restore Process

1. **Validation**: Script checks for valid backup structure
2. **Information Display**: Shows backup metadata and summary
3. **Confirmation Prompt**: Asks for explicit confirmation (y/N)
4. **Restore Steps**:
   - Restores configuration files
   - Restores state and inventory databases
   - Sets proper permissions on `.env` files
   - Creates restore log

### Interactive Prompts

The script will ask for confirmation:
```
==> This will restore configuration and state files from the backup.
WARNING: This will overwrite existing files!

Continue with restore? (y/N)
```

Type `y` and press Enter to proceed.

### After Restore

1. **Review files**: Check that restored configs are appropriate
2. **Update environment-specific settings**: Adjust IPs, credentials if needed
3. **Restart services**:
   ```bash
   cd stacks/nsm && docker compose restart
   cd stacks/ai && docker compose restart
   ```

### Restore Limitations

- **Loki data**: Not restored (see manual Loki backup/restore procedures)
- **AI models**: Must be re-downloaded separately
- **Environment differences**: May need to adjust IPs, paths for different hosts

## Upgrade

### Safe Upgrade Procedure

The upgrade script automates the recommended workflow:

```bash
./scripts/upgrade.sh
```

### Upgrade Steps

1. **Pre-flight checks**
   - Verifies git repository status
   - Checks for uncommitted changes (with prompt)
   - Verifies Docker availability

2. **Automatic backup**
   - Runs `backup-all.sh` before any changes
   - Saves current state for rollback

3. **Git pull**
   - Shows incoming changes
   - Asks for confirmation
   - Pulls latest code from current branch

4. **Docker image updates**
   - Pulls latest images for NSM stack (Suricata, Loki, Grafana, etc.)
   - Pulls latest images for AI stack
   - Rebuilds custom images (AI service)

5. **Service restart**
   - Restarts NSM stack containers
   - Restarts AI stack containers
   - Uses `docker compose up -d` (non-disruptive)

6. **Verification**
   - Shows commit before/after
   - Lists running containers
   - Displays next steps

### Example Output

```
==> Orion Sentinel Upgrade
Repository: /home/pi/orion-sentinel-nsm-ai

[0/6] Pre-flight checks...
   ✓ Pre-flight checks passed

[1/6] Creating backup...
==> Orion Sentinel Backup
...
[2/6] Pulling latest changes from git...
Changes to be pulled:
  abc1234 Add new threat intel feed
  def5678 Update Grafana dashboards

Pull these changes? (y/N) y
   ✓ Updated to abc1234

[3/6] Pulling latest Docker images...
   ✓ Docker images updated

[4/6] Rebuilding custom images...
   ✓ Custom images rebuilt

[5/6] Restarting services...
   ✓ Services restarted

[6/6] Verifying upgrade...
   Previous: def5678
   Current:  abc1234

==> Upgrade completed successfully!
```

### Rollback After Failed Upgrade

If an upgrade causes issues:

```bash
# Rollback git changes
git reset --hard <previous-commit-hash>

# Restore from backup
./scripts/restore-all.sh backups/backup_<timestamp>

# Restart services
cd stacks/nsm && docker compose restart
cd stacks/ai && docker compose restart
```

The previous commit hash is shown in the upgrade output.

## Development Mode

### Using Sample Data

For development and testing, use the provided sample data and dev compose stack:

```bash
cd stacks/nsm
docker compose -f docker-compose.dev.yml up
```

This starts:
- Loki (log storage)
- Grafana (visualization)
- Log injector service (reads from `samples/` and pushes to Loki)

Sample files provided:
- `samples/suricata-eve.json`: Dummy Suricata IDS alerts
- `samples/pihole-dns.log`: Dummy DNS queries from Pi-hole
- `samples/intel_matches.json`: Sample threat intel matches

### Dev Workflow

1. **Start dev environment**:
   ```bash
   cd stacks/nsm
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Verify data ingestion**:
   ```bash
   # Check Loki has received logs
   curl -G http://localhost:3100/loki/api/v1/query \
     --data-urlencode 'query={job="suricata"}'
   ```

3. **Develop dashboards**:
   - Access Grafana: http://localhost:3000
   - Develop and test queries against sample data
   - Export dashboards to `config/grafana/`

4. **Test AI pipelines**:
   - AI services read from Loki
   - Use sample data to test anomaly detection
   - Verify outputs without affecting production

## Resource Monitoring

### Lightweight Monitoring Stack

Optional: Add resource monitoring with node-exporter and Prometheus:

```bash
cd stacks/nsm
docker compose -f docker-compose.yml -f docker-compose.metrics.yml up -d
```

This adds:
- **node-exporter**: Host metrics (CPU, RAM, disk, network)
- **cAdvisor**: Container metrics
- **Prometheus**: Metrics storage (optional, can use Grafana Cloud)

### Viewing Resource Usage

#### Docker Stats
```bash
# Real-time container resource usage
docker stats

# Specific containers
docker stats suricata loki grafana ai-service
```

#### Container Logs
```bash
# Follow logs for all services
cd stacks/nsm
docker compose logs -f

# Specific service
docker compose logs -f suricata

# Last 100 lines
docker compose logs --tail=100 loki
```

#### Service Health
```bash
# Check running containers
docker compose ps

# Check for restarts (indicates crashes)
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.RestartCount}}"
```

#### Disk Usage
```bash
# Docker disk usage
docker system df

# Loki data directory
du -sh stacks/nsm/loki/data/

# Backup size
du -sh backups/
```

### Grafana Dashboard for Pi Resources

The NSM stack includes a pre-configured dashboard for Raspberry Pi monitoring:

- **CPU usage** (per core and total)
- **Memory usage** (used vs available)
- **Disk space** (all mounted filesystems)
- **Network traffic** (bytes in/out)
- **Container stats** (if using metrics stack)

Access at: http://localhost:3000/d/pi-resources

### Alerts and Notifications

To set up alerts for resource exhaustion:

1. Edit `stacks/nsm/prometheus/rules/system-alerts.yml`
2. Add alert rules for high CPU, low disk, high memory
3. Configure notification channels in Grafana (email, Slack, etc.)

Example alert rule:
```yaml
groups:
  - name: system
    interval: 30s
    rules:
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        annotations:
          summary: "Memory usage above 90%"
```

## Maintenance Tasks

### Log Rotation

Loki automatically manages log retention based on `loki-config.yaml`:
```yaml
limits_config:
  retention_period: 168h  # 7 days
```

### Cleanup Old Backups

```bash
# List backups by size and age
ls -lht backups/

# Remove backups older than 30 days
find backups/ -type d -name "backup_*" -mtime +30 -exec rm -rf {} \;
```

### Update Threat Intel Feeds

Threat intel is updated automatically by the AI service. To manually refresh:

```bash
cd stacks/ai
docker compose restart ai-service

# Check logs
docker compose logs -f ai-service | grep "threat_intel"
```

### Database Maintenance

SQLite databases (inventory) are automatically managed. For manual optimization:

```bash
# Vacuum to reclaim space
sqlite3 /path/to/inventory.db "VACUUM;"
```

## Troubleshooting

### Backup Fails

**Issue**: Backup script exits with errors

**Solution**:
- Check disk space: `df -h`
- Verify write permissions: `ls -la backups/`
- Review script output for specific errors

### Restore Doesn't Apply Changes

**Issue**: Files not restored after running script

**Solution**:
- Check restore log in `backups/restore_<timestamp>.log`
- Verify backup directory structure
- Ensure target directories exist and are writable

### Upgrade Pulls Wrong Branch

**Issue**: Upgrade pulls unexpected changes

**Solution**:
- Check current branch: `git branch`
- Switch to desired branch: `git checkout main`
- Re-run upgrade script

### Services Don't Start After Upgrade

**Issue**: Docker containers fail to start

**Solution**:
```bash
# Check for errors
docker compose ps
docker compose logs

# Try rebuilding
docker compose build --no-cache
docker compose up -d

# If all else fails, rollback
git reset --hard <previous-commit>
./scripts/restore-all.sh backups/backup_<timestamp>
```

## Security Considerations

### Backup Security

- **Sensitive data**: Backups contain `.env` files with credentials
- **Permissions**: Scripts set `chmod 600` on `.env` files
- **Storage**: Keep backups on encrypted storage
- **Retention**: Don't keep unnecessary old backups with outdated credentials

### Upgrade Safety

- **Review changes**: Always review git log before pulling
- **Test first**: Test upgrades in dev environment when possible
- **Rollback ready**: Know how to rollback (documented above)
- **Avoid automation**: Don't automate upgrades without human review

## Integration with External Systems

### Loki Backup (Advanced)

For production deployments, configure Loki to use object storage:

```yaml
# loki-config.yaml
storage_config:
  aws:
    s3: s3://access_key:secret_key@region/bucket
    sse_encryption: true
```

Or use volume snapshots:
```bash
# Stop Loki
docker compose stop loki

# Backup volume
docker run --rm -v nsm_loki-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/loki-data.tar.gz -C /data .

# Restart Loki
docker compose start loki
```

### Off-site Backup

Use `rsync` to copy backups to remote storage:

```bash
# Add to backup script or cron job
rsync -avz --delete \
  /home/pi/orion-sentinel-nsm-ai/backups/ \
  user@backup-server:/backups/orion-sentinel/
```

## Related Documentation

- [Architecture Overview](architecture.md)
- [Threat Model & Security](threat-model.md)
- [Pi Setup Guide](pi2-setup.md)
- [Logging & Dashboards](logging-and-dashboards.md)
