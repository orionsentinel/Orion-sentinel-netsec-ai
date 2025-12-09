# Orion Sentinel - Update & Maintenance Guide

This guide covers how to keep your Orion Sentinel NetSec node updated and secure.

## Table of Contents

1. [Update Strategy](#update-strategy)
2. [Updating Docker Images](#updating-docker-images)
3. [Updating Configuration](#updating-configuration)
4. [Security Updates](#security-updates)
5. [Rollback Procedures](#rollback-procedures)
6. [Automated Updates](#automated-updates)
7. [Monitoring for Updates](#monitoring-for-updates)

## Update Strategy

Orion Sentinel uses a **manual update approach** by default to ensure stability and control over production environments.

### Update Frequency Recommendations

- **Security patches**: Apply immediately when available
- **Minor updates**: Monthly review and update cycle
- **Major updates**: Quarterly, with testing in dev environment first

## Updating Docker Images

### 1. Check for Updates

```bash
# Pull latest images (doesn't restart services)
make update-images

# Or manually:
docker compose pull
```

### 2. Review Changes

Before updating, check the changelog:
- [Orion Sentinel Releases](https://github.com/orionsentinel/Orion-sentinel-netsec-ai/releases)
- [Suricata Changelog](https://suricata.io/category/releases/)
- [Grafana Releases](https://grafana.com/docs/grafana/latest/release-notes/)

### 3. Backup Before Update

**CRITICAL:** Always backup before major updates:

```bash
# Backup all volumes
sudo ./backup/backup-volumes.sh

# Backup configuration
make backup-config
```

### 4. Apply Updates

```bash
# Pull latest images
docker compose pull

# Stop services
make down

# Start with updated images
make up-all

# Or restart in one command
make restart
```

### 5. Verify Update

```bash
# Check service status
make status

# View logs for errors
make logs

# Test functionality
make test
```

## Updating Configuration

### Update from Git Repository

```bash
# Pull latest code and configs
git pull origin main

# Review changes
git log -5

# Backup current config
cp .env .env.backup

# Merge any new .env variables
diff .env.example .env

# Restart to apply config changes
make restart
```

### Update Individual Service Configs

#### Suricata Rules
```bash
# Update Suricata rules
docker exec orion-suricata suricata-update

# Or update the configuration file
vim stacks/nsm/suricata/suricata.yaml

# Restart Suricata
docker compose restart suricata
```

#### SOAR Playbooks
```bash
# Edit playbooks
vim config/playbooks.yml

# Validate YAML syntax
yamllint config/playbooks.yml

# Restart SOAR service
docker compose restart soar
```

## Security Updates

### Immediate Security Patch Procedure

When a critical security vulnerability is announced:

1. **Assess Impact**
   ```bash
   # Check current image versions
   docker compose images
   ```

2. **Backup**
   ```bash
   sudo ./backup/backup-volumes.sh /srv/backups/orion/security-update-$(date +%Y%m%d)
   ```

3. **Update Affected Service**
   ```bash
   # Pull specific service
   docker compose pull <service-name>
   
   # Restart only that service
   docker compose up -d <service-name>
   ```

4. **Verify**
   ```bash
   # Check service health
   docker compose ps
   
   # Verify no vulnerabilities
   docker scan <image-name> || true
   ```

### Security Checklist

- [ ] All services running with non-root users where possible
- [ ] No services exposed directly to internet (use Traefik + Authelia)
- [ ] Regular security updates applied
- [ ] Audit logs enabled and monitored
- [ ] Backups tested and verified
- [ ] Secrets stored in `.env`, never in git

## Rollback Procedures

### Quick Rollback - Restore Previous Images

```bash
# List previous images
docker images | grep orion

# Tag current version before update
docker tag orion-ai:latest orion-ai:backup-$(date +%Y%m%d)

# To rollback, use the backup tag
docker tag orion-ai:backup-20240115 orion-ai:latest
make restart
```

### Full Rollback - Restore from Backup

```bash
# 1. Stop services
make down

# 2. Restore volumes
sudo ./backup/restore-volume.sh /srv/backups/orion/2024-01-15/orion-sentinel-netsec-ai_inventory-data.tar.gz

# 3. Restore config
cp .env.backup .env

# 4. Revert code
git reset --hard COMMIT_HASH

# 5. Rebuild and restart
docker compose build
make up-all
```

## Automated Updates

### Option 1: Watchtower (Container Auto-Update)

**Not recommended for production** - but useful for dev/lab environments.

Add to `compose.yml`:
```yaml
  watchtower:
    image: containrrr/watchtower:latest
    container_name: orion-watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_SCHEDULE=0 0 2 * * SUN  # Sunday 2 AM
      - WATCHTOWER_INCLUDE_STOPPED=false
      - WATCHTOWER_NOTIFICATIONS=email
      - WATCHTOWER_NOTIFICATION_EMAIL_TO=admin@example.com
    restart: unless-stopped
```

### Option 2: Diun (Update Notifications)

**Recommended approach** - notifies you of updates without auto-applying them.

Add to `compose.yml`:
```yaml
  diun:
    image: crazymax/diun:latest
    container_name: orion-diun
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/diun.yml:/etc/diun/diun.yml:ro
    environment:
      - LOG_LEVEL=info
      - DIUN_WATCH_SCHEDULE=0 0 3 * * *  # Daily 3 AM
    restart: unless-stopped
```

Create `config/diun.yml`:
```yaml
watch:
  workers: 10
  schedule: "0 0 3 * * *"
  
notif:
  mail:
    host: smtp.gmail.com
    port: 587
    username: your-email@gmail.com
    password: your-app-password
    from: orion@example.com
    to: admin@example.com

providers:
  docker:
    watchByDefault: true
```

### Option 3: Manual Reminder Script

Add to crontab:
```bash
# Check for updates monthly (1st of month, 9 AM)
0 9 1 * * echo "Reminder: Check for Orion Sentinel updates - run 'make update-images'" | mail -s "Orion Update Reminder" admin@example.com
```

## Monitoring for Updates

### Check Current Versions

```bash
# Show running versions
docker compose images

# Show available updates (requires internet)
docker compose pull --dry-run 2>&1 | grep -i "pull"
```

### Subscribe to Release Notifications

1. **GitHub Watch**: Watch the repository for releases
   - Go to https://github.com/orionsentinel/Orion-sentinel-netsec-ai
   - Click "Watch" → "Custom" → "Releases"

2. **RSS Feed**: Subscribe to release feed
   - `https://github.com/orionsentinel/Orion-sentinel-netsec-ai/releases.atom`

3. **Email Notifications**: Configure GitHub notification settings

### Security Advisories

Monitor these sources for security updates:

- **Suricata**: https://suricata.io/category/security/
- **Docker**: https://www.docker.com/blog/category/docker-security/
- **Grafana**: https://grafana.com/blog/category/security/
- **GitHub Security Advisories**: Check repository security tab

## Update Testing Procedure

Before applying updates to production:

### 1. Test in Lab Environment

```bash
# On a separate test system
git clone https://github.com/orionsentinel/Orion-sentinel-netsec-ai.git test-orion
cd test-orion

# Apply update
docker compose pull
make up-all

# Run tests
make test

# Verify functionality
curl http://localhost:8000/api/health
```

### 2. Smoke Test Checklist

After any update, verify:

- [ ] All containers started successfully: `make status`
- [ ] No errors in logs: `make logs`
- [ ] Suricata capturing traffic: `docker exec orion-suricata suricatasc -c "capture-mode"`
- [ ] Web UI accessible: `curl http://localhost:8000`
- [ ] Logs flowing to Loki: Check Grafana dashboards
- [ ] SOAR playbooks executing: Check SOAR logs

### 3. Performance Baseline

Compare before/after metrics:

```bash
# Check resource usage
docker stats --no-stream

# Check disk usage
docker system df

# Check network performance
docker exec orion-suricata suricatasc -c "dump-counters"
```

## Version Pinning

### Current Practice

The project uses specific version tags where critical, and allows controlled `latest` for others.

To pin all versions, update `compose.yml`:

```yaml
services:
  suricata:
    image: jasonish/suricata:7.0.2  # Pinned version
    
  promtail:
    image: grafana/promtail:2.9.3  # Already pinned
```

### Recommended Pinning Strategy

- **Production**: Pin all images to specific versions
- **Development**: Use `latest` for faster iteration
- **CI/CD**: Pin to specific versions for reproducible builds

### Image Digest Pinning (Most Secure)

For maximum security and reproducibility:

```bash
# Get image digest
docker inspect --format='{{index .RepoDigests 0}}' grafana/promtail:2.9.3

# Use digest in compose file
image: grafana/promtail@sha256:abc123...
```

## Troubleshooting Updates

### Update Fails - Containers Won't Start

```bash
# Check logs
make logs

# Verify config
docker compose config

# Try rebuilding
docker compose build --no-cache
make up-all
```

### Incompatible Configuration

```bash
# Compare configs
diff .env.example .env

# Reset to defaults (backup first!)
cp .env .env.old
cp .env.example .env
# Edit .env with your values
```

### Performance Degradation After Update

```bash
# Check resource usage
docker stats

# Check for config changes
git diff HEAD~1 stacks/

# Rollback if needed
git checkout HEAD~1 -- stacks/
make restart
```

## Maintenance Schedule

### Weekly
- [ ] Check service health: `make health`
- [ ] Review logs for errors: `make logs | grep -i error`
- [ ] Verify backups completed: `ls -lh /srv/backups/orion/`

### Monthly
- [ ] Check for available updates: `docker compose pull --dry-run`
- [ ] Review and update Suricata rules
- [ ] Test backup restoration procedure
- [ ] Review security advisories

### Quarterly
- [ ] Plan major version updates
- [ ] Full system backup and verification
- [ ] Update documentation
- [ ] Review and update SOAR playbooks

## Getting Help

If you encounter issues during updates:

1. **Check Documentation**: Review docs in `/docs` directory
2. **GitHub Issues**: Search existing issues or create new one
3. **Rollback**: Use backup/rollback procedures above
4. **Community**: Join discussions on GitHub

## Emergency Contacts

Keep this information handy:

- **Backup Location**: `/srv/backups/orion/`
- **Config Backup**: `.env.backup`, `config.tar.gz`
- **Last Known Good Version**: (tag in git)
- **Emergency Rollback**: `git reset --hard <commit>` + restore backups
