# Migration Guide - NVMe-Backed NetSec Pi

This guide helps existing Orion Sentinel NetSec users migrate to the new NVMe-backed architecture.

## What Changed?

### Major Changes in v2.0

1. **NVMe Storage Required**
   - Logs and PCAPs now stored on NVMe instead of Docker volumes
   - Avoids microSD wear and provides better I/O performance
   - Required mount point: `/mnt/orion-nvme-netsec`

2. **Docker Compose Profile Changes**
   - Old profile `netsec-core` → New profile `netsec-minimal`
   - New profiles: `netsec-plus-evebox`, `netsec-debug`
   - Profile `ai` remains but is legacy (not recommended for production)

3. **Environment Variable Changes**
   - `MONITOR_IF` → `NETSEC_INTERFACE`
   - New: `NVME_BASE_PATH` (default: `/mnt/orion-nvme-netsec`)
   - New: `ORION_NODE_ROLE`, `ORION_NODE_NAME` (for Loki labels)

4. **Container Names Updated**
   - Old: `orion-suricata`, `orion-promtail`, `orion-node-exporter`
   - New: `orion-netsec-suricata`, `orion-netsec-promtail`, `orion-netsec-node-exporter`
   - Ensures clear naming for multi-node Orion deployments

5. **Configuration Directory Restructure**
   - Configs moved from `stacks/nsm/` to `config/`
   - `config/suricata/suricata.yaml`
   - `config/promtail/promtail-config.yml`

6. **AI Services Separated**
   - AI services remain available but are legacy
   - Future: AI services will run on separate AI Node (Pi 5 + AI HAT)
   - Production deployments should use `netsec-minimal` profile only

---

## Migration Steps

### Step 1: Backup Current Deployment

**Backup configuration:**

```bash
make backup-config
```

**Backup Docker volumes (optional but recommended):**

```bash
make backup-volumes
```

**Export current environment:**

```bash
cp .env .env.backup
```

### Step 2: Stop Current Services

```bash
make stop
# or
docker compose down
```

### Step 3: Pull Latest Changes

```bash
git fetch origin
git checkout main  # or your desired branch
git pull
```

### Step 4: Set Up NVMe Storage

**Format and mount NVMe (⚠️ THIS WILL ERASE NVMe DATA!):**

```bash
# Identify NVMe device
lsblk

# Format NVMe
sudo mkfs.ext4 /dev/nvme0n1p1

# Create mount point
sudo mkdir -p /mnt/orion-nvme-netsec

# Mount NVMe
sudo mount /dev/nvme0n1p1 /mnt/orion-nvme-netsec

# Add to /etc/fstab for persistent mount
echo "UUID=$(sudo blkid -s UUID -o value /dev/nvme0n1p1)  /mnt/orion-nvme-netsec  ext4  defaults,noatime  0  2" | sudo tee -a /etc/fstab

# Verify
sudo mount -a
df -h /mnt/orion-nvme-netsec
```

**Run NVMe health check:**

```bash
./scripts/check-nvme.sh
```

### Step 5: Update Environment Configuration

**Create new `.env` from template:**

```bash
mv .env .env.old
cp .env.example .env
```

**Migrate settings from old `.env` to new `.env`:**

| Old Variable | New Variable | Notes |
|--------------|--------------|-------|
| `MONITOR_IF` | `NETSEC_INTERFACE` | Rename only |
| `NODE_NAME` | `ORION_NODE_NAME` | Also set `ORION_NODE_ROLE=netsec` |
| `LOKI_URL` | `LOKI_URL` | No change |
| `LOCAL_OBSERVABILITY` | `LOCAL_OBSERVABILITY` | No change |
| - | `NVME_BASE_PATH` | New: `/mnt/orion-nvme-netsec` |

**Example migration:**

Old `.env`:
```bash
MONITOR_IF=eth0
NODE_NAME=netsec-pi-01
LOKI_URL=http://192.168.8.50:3100
LOCAL_OBSERVABILITY=false
```

New `.env`:
```bash
NETSEC_INTERFACE=eth0
ORION_NODE_ROLE=netsec
ORION_NODE_NAME=netsec-pi-01
LOKI_URL=http://192.168.8.50:3100
LOCAL_OBSERVABILITY=false
NVME_BASE_PATH=/mnt/orion-nvme-netsec
```

### Step 6: Migrate Existing Logs to NVMe (Optional)

If you want to preserve existing logs from Docker volumes:

```bash
# Create NVMe directories
sudo mkdir -p /mnt/orion-nvme-netsec/suricata/logs
sudo mkdir -p /mnt/orion-nvme-netsec/suricata/rules

# Copy logs from Docker volume
docker run --rm -v suricata-logs:/source -v /mnt/orion-nvme-netsec/suricata/logs:/dest busybox sh -c "cp -av /source/* /dest/"

# Copy rules
docker run --rm -v suricata-rules:/source -v /mnt/orion-nvme-netsec/suricata/rules:/dest busybox sh -c "cp -av /source/* /dest/"

# Set ownership
sudo chown -R 1000:1000 /mnt/orion-nvme-netsec/suricata
```

**Or start fresh (recommended):**

Suricata will automatically download latest rules on first start, and logs will start fresh.

### Step 7: Remove Old Docker Volumes (Optional)

After verifying new deployment works:

```bash
docker volume rm suricata-logs suricata-rules
```

### Step 8: Start New Deployment

**Production (recommended):**

```bash
make up-minimal
```

**With EveBox UI:**

```bash
make up-evebox
```

**Legacy (with AI services):**

```bash
make up-full
```

### Step 9: Verify New Deployment

```bash
# Check services
make status

# Run validation
make test

# Check NVMe usage
./scripts/check-nvme.sh

# Check logs
make logs
```

---

## Profile Mapping

| Old Command | New Command | Profile Used |
|-------------|-------------|--------------|
| `make up-core` | `make up-minimal` | `netsec-minimal` |
| `make up-all` | `make up-full` | `netsec-minimal` + `ai` (legacy) |
| `make start-spog` | `make up-minimal` | `netsec-minimal` (recommended) |
| - | `make up-evebox` | `netsec-plus-evebox` (new) |
| - | `make up-debug` | `netsec-minimal` + `netsec-debug` (new) |

---

## Troubleshooting Migration Issues

### Issue: NVMe not mounted

**Symptoms:**
- `check-nvme.sh` fails
- Docker containers fail to start with "mount point does not exist"

**Solution:**
```bash
# Check if NVMe is mounted
df -h | grep nvme

# If not mounted, check /etc/fstab entry
cat /etc/fstab | grep nvme

# Mount manually
sudo mount /dev/nvme0n1p1 /mnt/orion-nvme-netsec

# Or remount all
sudo mount -a
```

### Issue: Permission denied errors in Suricata logs

**Symptoms:**
- Suricata fails to write to `/var/log/suricata`
- Permission errors in `docker logs orion-netsec-suricata`

**Solution:**
```bash
# Set ownership to Suricata container user (UID 1000)
sudo chown -R 1000:1000 /mnt/orion-nvme-netsec/suricata

# Verify permissions
ls -la /mnt/orion-nvme-netsec/suricata/logs
```

### Issue: Container name conflicts

**Symptoms:**
- Docker compose fails with "container name already in use"

**Solution:**
```bash
# Stop and remove old containers
docker compose down
docker ps -a | grep orion- | awk '{print $1}' | xargs docker rm -f

# Start with new names
make up-minimal
```

### Issue: Promtail not shipping logs to Loki

**Symptoms:**
- No logs appearing in CoreSrv Grafana
- Promtail shows connection errors

**Solution:**
```bash
# Check Loki URL in .env
grep LOKI_URL .env

# Test Loki connectivity
curl http://192.168.x.x:3100/ready

# Check Promtail logs
docker logs orion-netsec-promtail | grep -i error

# Verify Promtail config has environment variables expanded
docker exec orion-netsec-promtail cat /etc/promtail/config.yml | grep LOKI_URL
```

### Issue: Missing Loki labels in Grafana

**Symptoms:**
- Can't filter logs by `orion_node_role` or `orion_node_name` in Grafana

**Solution:**
```bash
# Verify environment variables are set
docker exec orion-netsec-promtail env | grep ORION

# If missing, ensure they're set in .env
echo "ORION_NODE_ROLE=netsec" >> .env
echo "ORION_NODE_NAME=netsec-pi-01" >> .env

# Restart Promtail
docker compose restart promtail
```

---

## Rollback to Previous Version

If migration fails and you need to rollback:

### Step 1: Stop New Deployment

```bash
make stop
```

### Step 2: Restore Old Code

```bash
git checkout <previous-commit-or-tag>
```

### Step 3: Restore Configuration

```bash
cp .env.old .env
```

### Step 4: Start Old Deployment

```bash
docker compose --profile netsec-core up -d
# or
make start-spog
```

### Step 5: Restore Volumes (if needed)

```bash
# If you backed up volumes
make restore-volume BACKUP_FILE=/path/to/backup.tar.gz
```

---

## Post-Migration Tasks

### Update CoreSrv Prometheus

Update CoreSrv's `prometheus.yml` to use new container names:

```yaml
scrape_configs:
  - job_name: 'netsec-pi-01'
    static_configs:
      - targets: ['192.168.x.x:9100']
        labels:
          orion_node_role: 'netsec'
          orion_node_name: 'netsec-pi-01'
```

### Update Grafana Dashboards

Import new dashboards from `docs/grafana-dashboards.md`:
- NetSec Pi Overview
- Suricata Alerts
- Network Traffic Analysis
- NetSec Node Health

### Set Up Automated Backups

```bash
# Add to crontab for weekly backups
crontab -e

# Add line (runs every Sunday at 2 AM):
0 2 * * 0 cd /path/to/Orion-sentinel-netsec-ai && make backup-config
```

### Monitor NVMe Health

Add NVMe health monitoring to cron:

```bash
# Check NVMe daily
crontab -e

# Add line (runs daily at 6 AM):
0 6 * * * /path/to/Orion-sentinel-netsec-ai/scripts/check-nvme.sh
```

---

## Getting Help

If you encounter issues during migration:

1. **Check logs:** `make logs`
2. **Run validation:** `make test`
3. **Check NVMe:** `./scripts/check-nvme.sh`
4. **Review documentation:** `docs/architecture-netsec.md`
5. **Open an issue:** [GitHub Issues](https://github.com/orionsentinel/Orion-sentinel-netsec-ai/issues)

---

## Summary

**Key takeaways:**

✅ **NVMe storage is now required** - Improves reliability and performance  
✅ **Profile names updated** - `netsec-minimal` is production default  
✅ **Container names updated** - Better naming for multi-node setups  
✅ **Config location moved** - From `stacks/nsm/` to `config/`  
✅ **AI services are legacy** - Future AI capabilities on separate node  

**Next steps:**
1. Test deployment with `make test`
2. Verify logs in CoreSrv Grafana
3. Update Grafana dashboards
4. Set up automated backups
