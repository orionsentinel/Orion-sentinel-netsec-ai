# Threat Model & Security

This document describes the threat model, security assumptions, and hardening recommendations for the Orion Sentinel NSM + AI platform.

## Table of Contents

- [Overview](#overview)
- [Assets](#assets)
- [Key Components](#key-components)
- [Trust Boundaries](#trust-boundaries)
- [Threat Analysis](#threat-analysis)
- [Security Assumptions](#security-assumptions)
- [Attack Scenarios](#attack-scenarios)
- [Mitigations & Hardening](#mitigations--hardening)
- [Security Checklist](#security-checklist)

## Overview

Orion Sentinel is a **passive network security monitoring** platform designed for home and lab environments. It monitors network traffic and DNS activity to detect threats and anomalies, but does **not** sit inline with network traffic.

**Security Posture:** Defense-in-depth with least privilege

**Deployment Model:** Internal LAN or isolated management VLAN

## Assets

### High-Value Assets

| Asset | Description | Sensitivity | Impact if Compromised |
|-------|-------------|-------------|----------------------|
| **NSM Logs** | Suricata IDS alerts, flow data | Medium | Network visibility exposed, attack patterns revealed |
| **DNS Logs** | Pi-hole DNS query logs | Medium | Browsing history, device behavior patterns revealed |
| **AI Outputs** | Anomaly detection results, risk scores | Medium | Security posture and weaknesses exposed |
| **Device Inventory** | Device fingerprints, metadata, tags | Low-Medium | Device enumeration, network mapping |
| **SOAR Playbooks** | Automated response rules | Medium | Automated defenses exposed |
| **Pi-hole API Key** | Credentials for DNS blocking | High | Ability to manipulate DNS blocking/allowlisting |
| **Grafana Credentials** | Admin access to dashboards | Medium | Dashboard tampering, data visibility |

### Data Retention

- **Loki logs**: Default 7 days (configurable)
- **Inventory database**: Persistent (SQLite)
- **AI model outputs**: Logged to Loki (7 day retention)

**Privacy Note:** All data remains on-device. No cloud dependencies or external data transmission except for:
- Threat intelligence feed downloads (optional)
- Software/image updates

## Key Components

### Pi #2 (Security Pi)

**Role:** Passive network security sensor

**Services:**
- Suricata IDS (passive monitoring on mirrored traffic)
- Loki (log aggregation)
- Grafana (visualization)
- AI detection services (anomaly detection, domain risk scoring)
- SOAR automation (response playbooks)
- Device inventory service
- REST API server

**Network Interfaces:**
- Primary interface: Management access (SSH, Grafana, API)
- Mirror interface: Passive traffic capture (no IP address)

### Pi #1 (DNS Pi)

**Role:** DNS resolver with ad/malware blocking

**Services:**
- Pi-hole (DNS filtering)
- Unbound (recursive resolver)

**Integration:**
- Ships DNS logs to Pi #2 (Loki)
- Exposes API for automated blocking (called by Pi #2 SOAR)

### External Dependencies

- **Threat Intelligence Feeds:**
  - AlienVault OTX
  - abuse.ch URLhaus
  - abuse.ch Feodo Tracker
  - PhishTank

- **Docker Registries:**
  - Docker Hub (for container images)
  - GitHub Container Registry (if applicable)

## Trust Boundaries

```
                                    Internet
                                       |
                                    [Firewall]
                                       |
    ┌──────────────────────────────────┴──────────────────────────────────┐
    |                          LAN / Home Network                         |
    |                        (Trusted Boundary)                           |
    |                                                                     |
    |  ┌──────────────┐         ┌─────────────┐        ┌──────────────┐ |
    |  │   Clients    │────────▶│   Pi #1     │───────▶│   Pi #2      │ |
    |  │  (Devices)   │         │  DNS + HA   │        │  NSM + AI    │ |
    |  │              │         │             │   API  │              │ |
    |  │              │         │ - Pi-hole ◄─┼────────┤ - SOAR       │ |
    |  └──────────────┘         │ - Unbound   │        │ - Grafana    │ |
    |                           └─────────────┘        └──────────────┘ |
    |                                 │                        │         |
    |                              DNS Logs                Mirrored      |
    |                                 ▼                    Traffic       |
    |                           Sent to Loki◄───────────Via Switch      |
    |                             on Pi #2                               |
    └─────────────────────────────────────────────────────────────────────┘

    Trust Levels:
    - Internet: UNTRUSTED
    - LAN: TRUSTED (assumes physical access control)
    - Management VLAN: HIGHLY TRUSTED (if using separate VLAN)
```

## Threat Analysis

### Threat Actors

**In-Scope Threat Actors:**

1. **External Attackers (Internet-based)**
   - Attempting to exploit devices on LAN
   - Malware infections on LAN devices
   - C2 communication attempts

2. **Malicious Insiders**
   - Compromised LAN device
   - Rogue device on network
   - Malicious guest/user

3. **Physical Access**
   - Unauthorized physical access to Pi devices
   - SD card theft

**Out-of-Scope (for home/lab):**

- Nation-state APTs
- Sophisticated supply chain attacks
- Insider threats with root access to Pis

### STRIDE Analysis

| Threat | Scenario | Impact | Likelihood |
|--------|----------|--------|-----------|
| **Spoofing** | Attacker spoofs Pi-hole API calls | Unauthorized DNS blocking | Low (requires LAN access) |
| **Tampering** | Modify playbooks or inventory DB | Disable defenses, hide devices | Medium (if Pi compromised) |
| **Repudiation** | Delete SOAR action logs | Hide malicious activity | Low (logs in Loki) |
| **Information Disclosure** | Access Grafana dashboards | Network visibility exposed | Medium (weak creds) |
| **Information Disclosure** | Steal inventory database | Device enumeration | Medium (if Pi compromised) |
| **Denial of Service** | Flood Loki with logs | Service degradation | Low-Medium |
| **Elevation of Privilege** | Container escape | Full Pi compromise | Low (with updated Docker) |

## Security Assumptions

### Deployment Assumptions

✅ **Assumed Safe:**

1. **Local Area Network (LAN) is trusted**
   - Physical access to LAN is controlled
   - Network switch/router is not compromised
   - No rogue devices on LAN (or monitored)

2. **Pi devices are physically secured**
   - Located in secure area (home, locked server rack)
   - No unauthorized physical access

3. **Administrative access is controlled**
   - SSH keys used (no password auth)
   - Strong sudo passwords
   - Admin access from trusted devices only

4. **Management interfaces not exposed to Internet**
   - Grafana, API, SSH only accessible from LAN or VPN
   - No port forwarding to Pi #2 from WAN

⚠️ **Do NOT assume:**

- LAN devices are not compromised
- Docker containers cannot be exploited
- Threat intel feeds are always trustworthy

### Design Assumptions

1. **Passive monitoring:** Pi #2 is NOT in the network path (no inline routing)
2. **No direct DNS:** Pi #2 does not resolve DNS; it only monitors DNS logs
3. **API-based enforcement:** Blocking happens via Pi-hole API, not locally
4. **All actions logged:** Every SOAR action is logged to Loki for audit

## Attack Scenarios

### Scenario 1: Compromised LAN Device

**Attack:** Malware infects a laptop on the LAN. Attacker pivots to target Pi #2.

**Steps:**
1. Attacker scans LAN from infected laptop
2. Discovers Pi #2 Grafana (port 3000) or API (port 8000)
3. Attempts credential brute force or exploits unpatched vulnerability
4. Gains access to Grafana or API

**Impact:**
- View NSM logs and dashboards (information disclosure)
- Tamper with device tags or playbooks (if API is exploited)
- Potentially access Pi-hole API key from environment variables

**Mitigations:**
- Use strong Grafana admin password
- Restrict API access with authentication (see hardening)
- Firewall rules: Only allow management access from specific IPs
- Monitor for brute force attempts in logs

### Scenario 2: Pi-hole API Key Theft

**Attack:** Attacker compromises Pi #2 and extracts `PIHOLE_API_KEY` from environment.

**Steps:**
1. Attacker gains shell access on Pi #2 (via container escape or SSH compromise)
2. Reads environment variable or config files
3. Uses API key to call Pi-hole API

**Impact:**
- Add malicious domains to allowlist (bypass filtering)
- Block legitimate domains (DoS)
- Disable Pi-hole entirely

**Mitigations:**
- Use environment variable secrets (not committed to git)
- Restrict Pi-hole API to specific IPs (Pi #2 only)
- Monitor Pi-hole API logs for unexpected changes
- Use read-only API key if possible (future enhancement)

### Scenario 3: Suricata/AI Service Manipulation

**Attack:** Attacker with access to Pi #2 disables Suricata or tampers with AI service.

**Steps:**
1. Attacker gains access to Pi #2
2. Stops Suricata container or modifies AI detection thresholds
3. Performs malicious activity on network (undetected)

**Impact:**
- Blind spots in security monitoring
- Malicious activity goes unnoticed

**Mitigations:**
- File integrity monitoring on critical configs (future enhancement)
- Health checks: Alert if Suricata stops
- Immutable containers (read-only root filesystems where possible)

### Scenario 4: Grafana Dashboard Defacement

**Attack:** Weak Grafana credentials allow unauthorized access.

**Steps:**
1. Attacker brute forces or guesses Grafana password (e.g., admin/admin)
2. Logs into Grafana
3. Deletes dashboards or modifies queries

**Impact:**
- Loss of visibility
- Misleading security data

**Mitigations:**
- Change default Grafana password immediately
- Enable Grafana auth via LDAP or OAuth (for multi-user setups)
- Backup Grafana dashboards (included in `backup-all.sh`)

## Mitigations & Hardening

### Network Hardening

**1. Firewall Rules (iptables/ufw on Pi #2)**

```bash
# Allow SSH from LAN only
sudo ufw allow from 192.168.1.0/24 to any port 22

# Allow Grafana from LAN only
sudo ufw allow from 192.168.1.0/24 to any port 3000

# Allow API from LAN only
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Allow Loki from Pi #1 only (for DNS log shipping)
sudo ufw allow from 192.168.1.2 to any port 3100

# Deny all other incoming
sudo ufw default deny incoming
sudo ufw enable
```

**2. Isolate on Management VLAN (Optional but Recommended)**

- Place Pi #2 on a separate VLAN (e.g., VLAN 10 - Management)
- Configure switch to mirror traffic to VLAN 10
- Restrict inter-VLAN routing (only allow specific services)

**3. VPN Access for Remote Management**

- Use Wireguard or OpenVPN for remote access
- Never expose Grafana/API directly to Internet

### Application Hardening

**1. Change Default Passwords**

```bash
# Grafana (set via environment variable)
export GRAFANA_ADMIN_PASSWORD="<strong-password>"
docker compose up -d
```

**2. Enable SOAR Dry-Run Mode Initially**

```bash
# In stacks/ai/.env
SOAR_DRY_RUN=1  # Test playbooks first!
```

**3. Use Secrets Management**

```bash
# Do NOT commit .env files to git
echo "*.env" >> .gitignore

# Use environment variables for sensitive data
# Example: .env file
PIHOLE_API_KEY=your-secret-key-here
GRAFANA_ADMIN_PASSWORD=your-password-here
```

**4. Restrict Pi-hole API Access**

On Pi #1, configure firewall to only accept API calls from Pi #2:

```bash
# Pi #1 firewall rule
sudo ufw allow from <pi2-ip> to any port 80
```

**5. Docker Security**

```yaml
# In docker-compose.yml files
services:
  service-name:
    # Run as non-root user
    user: "1000:1000"
    
    # Read-only root filesystem
    read_only: true
    
    # Drop unnecessary capabilities
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only add what's needed
    
    # No privileged mode (except Suricata which needs packet capture)
    privileged: false
```

### System Hardening

**1. Keep OS and Packages Updated**

```bash
# Weekly updates
sudo apt update && sudo apt upgrade -y

# Automatic security updates (optional)
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

**2. Secure SSH**

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers pi  # Only specific user
```

**3. Disable Unnecessary Services**

```bash
# Check running services
systemctl list-unit-files --state=enabled

# Disable unused services
sudo systemctl disable bluetooth
```

**4. Enable Fail2Ban**

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### Monitoring & Detection

**1. Enable Container Logging**

All docker-compose files include log rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**2. Monitor Unusual Activity**

- Set up Grafana alerts for:
  - Container restarts
  - High CPU/memory usage
  - Failed login attempts (Grafana, SSH)
  - Unusual API call patterns

**3. Audit SOAR Actions**

Review SOAR logs regularly:

```bash
docker compose -f stacks/ai/docker-compose.yml logs soar | grep "ACTION"
```

**4. File Integrity Monitoring (Future)**

Consider tools like AIDE or Tripwire for critical files:
- `/config/playbooks.yml`
- `stacks/*/docker-compose.yml`
- Scripts in `scripts/`

## Security Checklist

### Initial Deployment

- [ ] Change Grafana admin password
- [ ] Set strong Pi-hole API key
- [ ] Configure firewall rules (ufw)
- [ ] Disable SSH password authentication
- [ ] Enable SOAR dry-run mode
- [ ] Test backup and restore procedures
- [ ] Verify Grafana/API not accessible from WAN
- [ ] Review and customize SOAR playbooks
- [ ] Enable automatic security updates
- [ ] Document credentials in password manager

### Ongoing Maintenance

- [ ] Review SOAR action logs weekly
- [ ] Update OS packages monthly
- [ ] Rotate Pi-hole API key quarterly
- [ ] Test restore from backup quarterly
- [ ] Review firewall rules after network changes
- [ ] Monitor Docker image CVEs (Snyk, Trivy)
- [ ] Update threat intel feeds (automated in AI service)
- [ ] Review Grafana user access (if multi-user)

### Incident Response Readiness

- [ ] Document Pi #2 IP and access methods
- [ ] Backup inventory and configs (automated via cron)
- [ ] Know how to disable SOAR: `docker compose stop soar`
- [ ] Know how to check logs: `docker compose logs -f`
- [ ] Have rollback plan (restore script tested)
- [ ] Contact method for escalation (if team environment)

## Compliance & Privacy

### Data Privacy

**Home/Lab Use:**
- All monitoring data stays on-device
- No cloud uploads (except Docker image pulls, threat intel updates)
- DNS logs contain browsing history - treat as sensitive

**If Monitoring Others:**
- Inform users of monitoring (family members, guests)
- Comply with local privacy laws (GDPR, etc.)
- Avoid monitoring encrypted traffic (HTTPS content)

### Regulatory Considerations

For **non-home/business** use:

- **GDPR (EU):** DNS logs may be personal data
- **CCPA (California):** Notice requirements for monitoring
- **Industry Standards:** Consider CIS Benchmarks for Docker/Linux

Orion Sentinel is designed for **home/lab** use where the administrator owns the network. Consult legal counsel for business deployments.

## Limitations & Disclaimer

### Known Limitations

1. **Passive Monitoring Only**
   - Cannot block traffic inline (relies on Pi-hole API)
   - Limited visibility into encrypted traffic (HTTPS content not visible)

2. **Home-Lab Scope**
   - Not designed for enterprise-scale networks
   - Limited high-availability (single Pi)
   - No SOC integration (SIEM, ticketing)

3. **AI Detection Accuracy**
   - False positives possible
   - Requires tuning for your network
   - Models may not detect zero-day attacks

4. **Resource Constraints**
   - Raspberry Pi has limited CPU/RAM
   - Log retention constrained by SD card size

### Disclaimer

⚠️ **This project is for educational and home/lab use.**

- No warranties or guarantees of security effectiveness
- Use at your own risk
- Always test in non-production environment first
- Supplement with other security controls (antivirus, patching, backups)

## See Also

- [Operations Guide](operations.md) - Backup, restore, upgrade procedures
- [Architecture Documentation](architecture.md) - System design
- [SOAR Playbooks](soar.md) - Automated response configuration
- [Lab Mode](lab-mode.md) - Safe testing environment

## References

- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Raspberry Pi Security Guide](https://www.raspberrypi.com/documentation/computers/configuration.html#securing-your-raspberry-pi)
