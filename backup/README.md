# Orion Sentinel - Backup & Restore

This directory contains scripts for backing up and restoring critical Docker volumes.

## Quick Start

### Backup All Volumes
```bash
sudo ./backup-volumes.sh
```

Default backup location: `/srv/backups/orion/YYYY-MM-DD_HH-MM-SS`

### Restore a Volume
```bash
sudo ./restore-volume.sh /srv/backups/orion/2024-01-15_10-30-00/VOLUME_NAME.tar.gz
```

## Critical Volumes

The following volumes are backed up:

| Volume | Description | Priority |
|--------|-------------|----------|
| `suricata-logs` | Suricata IDS logs and alerts | High |
| `suricata-rules` | Suricata rules and configuration | High |
| `soar-data` | SOAR playbook execution history | Medium |
| `inventory-data` | Device inventory database | High |
| `change-data` | Network change monitoring data | Medium |
| `health-data` | Security health score data | Low |

## Backup Schedule Recommendations

### Weekly Backups
Add to crontab for automatic weekly backups:
```bash
# Run backups every Sunday at 2 AM
0 2 * * 0 /path/to/Orion-sentinel-netsec-ai/backup/backup-volumes.sh
```

### Retention Policy
- **Daily backups**: Keep for 7 days
- **Weekly backups**: Keep for 4 weeks
- **Monthly backups**: Keep for 6 months

## Detailed Usage

### Backup Script

**Basic usage:**
```bash
sudo ./backup-volumes.sh
```

**Custom backup location:**
```bash
sudo ./backup-volumes.sh /mnt/external-drive/orion-backups
```

The script will:
1. Create a timestamped backup directory
2. Backup all critical volumes to `.tar.gz` files
3. Generate a manifest file with backup details
4. Display a summary of the backup operation

### Restore Script

**Auto-detect volume name:**
```bash
sudo ./restore-volume.sh /srv/backups/orion/2024-01-15/orion-sentinel-netsec-ai_inventory-data.tar.gz
```

**Specify custom volume name:**
```bash
sudo ./restore-volume.sh backup.tar.gz my-custom-volume
```

⚠️ **Important:** Stop all containers before restoring:
```bash
make down
```

The script will:
1. Warn if the volume already exists
2. Check for containers using the volume
3. Clear existing volume data
4. Extract and restore the backup
5. Display restore summary

## Service-Specific Restore Procedures

### Restore Suricata Configuration
```bash
# 1. Stop services
make down

# 2. Restore the volume
sudo ./restore-volume.sh /srv/backups/orion/latest/orion-sentinel-netsec-ai_suricata-rules.tar.gz

# 3. Restart services
make up-core
```

### Restore Device Inventory
```bash
# 1. Stop services
make down

# 2. Restore the volume
sudo ./restore-volume.sh /srv/backups/orion/latest/orion-sentinel-netsec-ai_inventory-data.tar.gz

# 3. Restart services
make up-all

# 4. Verify inventory data
curl http://localhost:8000/api/inventory
```

### Restore SOAR Playbook History
```bash
# 1. Stop services
make down

# 2. Restore the volume
sudo ./restore-volume.sh /srv/backups/orion/latest/orion-sentinel-netsec-ai_soar-data.tar.gz

# 3. Restart services
make up-all
```

## Automated Backup Setup

### 1. Create Backup Location
```bash
sudo mkdir -p /srv/backups/orion
sudo chown $(whoami):$(whoami) /srv/backups/orion
```

### 2. Add to Crontab
```bash
crontab -e
```

Add this line:
```
# Orion Sentinel weekly backups (Sunday 2 AM)
0 2 * * 0 /home/pi/Orion-sentinel-netsec-ai/backup/backup-volumes.sh /srv/backups/orion
```

### 3. Setup Log Rotation
Create `/etc/logrotate.d/orion-backups`:
```
/srv/backups/orion/*/*.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
}
```

### 4. Cleanup Old Backups
Add cleanup script to crontab:
```bash
# Clean up backups older than 30 days (keep monthly)
0 3 1 * * find /srv/backups/orion -type d -mtime +30 -exec rm -rf {} \;
```

## Testing Your Backups

**IMPORTANT:** Regularly test your backups to ensure they work!

```bash
# 1. Create a test backup
sudo ./backup-volumes.sh /tmp/test-backup

# 2. Create a test volume
docker volume create test-restore

# 3. Test restore
sudo ./restore-volume.sh /tmp/test-backup/latest/VOLUME_NAME.tar.gz test-restore

# 4. Verify data
docker run --rm -v test-restore:/data alpine ls -la /data

# 5. Cleanup
docker volume rm test-restore
rm -rf /tmp/test-backup
```

## Troubleshooting

### Permission Denied
**Problem:** Script fails with permission denied

**Solution:** Run with sudo:
```bash
sudo ./backup-volumes.sh
```

### Volume Not Found
**Problem:** Volume doesn't exist during backup

**Solution:** This is normal if services aren't running. The script will skip non-existent volumes.

### Disk Space Issues
**Problem:** Insufficient space for backups

**Solution:** 
1. Check available space: `df -h /srv/backups`
2. Clean up old backups: `rm -rf /srv/backups/orion/OLD_DATE`
3. Consider external storage or network mount

### Container Still Running
**Problem:** Cannot restore while containers are running

**Solution:**
```bash
# Stop all services
make down

# Then retry restore
sudo ./restore-volume.sh BACKUP_FILE.tar.gz
```

## Security Considerations

- Backups contain sensitive network data - store securely
- Consider encrypting backup archives for offsite storage
- Restrict access to backup directory:
  ```bash
  sudo chmod 700 /srv/backups/orion
  ```
- Use encrypted remote storage (e.g., encrypted S3, encrypted NFS)

## Offsite Backup Options

### Option 1: rsync to Remote Server
```bash
rsync -avz --delete /srv/backups/orion/ user@backup-server:/backups/orion/
```

### Option 2: Cloud Storage
```bash
# Using rclone (configure first)
rclone sync /srv/backups/orion remote:orion-backups
```

### Option 3: Encrypted USB Drive
```bash
# Mount encrypted drive
sudo cryptsetup open /dev/sdX orion-backup
sudo mount /dev/mapper/orion-backup /mnt/backup

# Copy backups
sudo rsync -av /srv/backups/orion/ /mnt/backup/

# Unmount
sudo umount /mnt/backup
sudo cryptsetup close orion-backup
```
