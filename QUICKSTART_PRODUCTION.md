# Quick Start - Production Readiness Features

This guide helps you quickly leverage the new production-readiness features.

## 🚀 Quick Commands

### Backup & Restore

```bash
# Backup all volumes
sudo make backup-volumes

# Restore a specific volume
sudo make restore-volume BACKUP_FILE=/srv/backups/orion/2024-01-15/volume.tar.gz

# Backup just configuration
make backup-config
```

### Service Management

```bash
# Start services
make up-all          # Start everything (recommended)
make up-core         # Start core NSM only

# Monitor services
make ps              # Show status
make health          # Check health
make logs            # Tail logs

# Stop services
make down            # Stop all services
```

### Updates

```bash
# Check for updates
make update-images

# Apply updates
make down
docker compose pull
make up-all

# Rollback if needed
# See docs/update.md for procedures
```

## 📋 Production Checklist

Before deploying to production:

- [ ] **Set up automated backups**
  ```bash
  sudo mkdir -p /srv/backups/orion
  (crontab -l; echo "0 2 * * 0 $(pwd)/backup/backup-volumes.sh") | crontab -
  ```

- [ ] **Test backup and restore**
  ```bash
  sudo make backup-volumes
  ls -lh /srv/backups/orion/
  # Test restore in dev environment
  ```

- [ ] **Verify image versions are pinned**
  ```bash
  grep -E "image:.*latest" compose.yml stacks/*/docker-compose.yml
  # Should return no results
  ```

- [ ] **Configure monitoring**
  - Set up Grafana dashboards
  - Configure alerts
  - Set up notification channels

- [ ] **Document your setup**
  - Note your LOKI_URL
  - Document network interfaces (MONITOR_IF)
  - Keep .env backed up separately

- [ ] **Security review**
  - No services exposed to internet without auth
  - Traefik+Authelia configured (in SPoG mode)
  - Firewall rules in place

## 🔧 Troubleshooting

### Backup fails with permission denied
```bash
# Run with sudo
sudo ./backup/backup-volumes.sh
# or
sudo make backup-volumes
```

### Services won't start
```bash
# Check logs
make logs

# Verify configuration
docker compose config

# Check disk space
df -h
```

### CI failing
```bash
# Run validations locally
docker compose -f compose.yml config
yamllint .
shellcheck scripts/*.sh backup/*.sh
```

## 📚 Documentation

- **Backup**: `backup/README.md`
- **Updates**: `docs/update.md`
- **Full details**: `PRODUCTION_READINESS.md`
- **Main docs**: `README.md`

## 🎯 Next Steps

1. **Read the docs**: Check `PRODUCTION_READINESS.md` for complete details
2. **Set up backups**: Configure automated backups using cron
3. **Subscribe to updates**: Watch GitHub repo for releases
4. **Join the community**: Report issues and share feedback

## ⚡ Common Tasks

### Weekly maintenance
```bash
make health          # Check service health
make logs            # Review logs for errors
ls /srv/backups/orion/  # Verify backups completed
```

### Monthly maintenance
```bash
make update-images   # Check for updates
# Review docs/update.md
# Test updates in dev environment
# Apply to production
```

### Disaster recovery
```bash
# 1. Stop services
make down

# 2. Restore volumes
sudo ./backup/restore-volume.sh /srv/backups/orion/latest/VOLUME.tar.gz

# 3. Restore config
cp .env.backup .env

# 4. Restart
make up-all
```

---

**For detailed information, see `PRODUCTION_READINESS.md`**
