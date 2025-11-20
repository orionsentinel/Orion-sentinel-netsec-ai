# Threat Model

This document describes the security assumptions, threat landscape, and recommended mitigations for the Orion Sentinel NSM+AI system.

## Overview

Orion Sentinel is designed for **home labs and small networks** with the assumption of a trusted local network. It is **not designed to be directly exposed to the public internet** without additional security controls.

## System Assets

### Primary Assets

1. **Network Monitoring Data**
   - Suricata IDS alerts and network flow metadata
   - DNS query logs from Pi-hole
   - Host logs from endpoints (if EDR-lite is enabled)
   - Aggregate view of network communications

2. **AI-Generated Intelligence**
   - Anomaly detection results
   - Domain risk assessments
   - Threat intelligence correlation outputs
   - Device fingerprinting and classification

3. **Device Inventory Database**
   - IP and MAC addresses of all network devices
   - Device types, tags, and metadata
   - Historical behavior baselines
   - Risk scores

4. **SOAR Playbooks and Automation**
   - Playbook configurations and rules
   - Response automation logic
   - Integration credentials (Pi-hole API key)
   - Execution history and audit logs

5. **Configuration and Credentials**
   - Grafana admin credentials
   - Pi-hole API keys
   - Loki access
   - `.env` files with sensitive settings

### Secondary Assets

- Grafana dashboards and visualizations
- Suricata rule sets
- Historical log data in Loki
- AI model files and parameters

## Key Components

### Pi #2 (Security Pi)

**Role:** Central security monitoring and analysis platform

**Runs:**
- Suricata (passive IDS)
- Loki (log aggregation)
- Grafana (dashboards)
- AI services (SOAR, inventory, anomaly detection, health score)
- Web UI/API

**Network position:** 
- Receives mirrored/SPAN traffic for IDS
- Communicates with Pi #1 (DNS Pi) via API
- Accessed by administrators via LAN

### Pi #1 (DNS Pi)

**Role:** DNS filtering and resolution (separate repo: `orion-sentinel-dns-ha`)

**Interaction with Pi #2:**
- Exposes Pi-hole API for SOAR automation (block domain actions)
- Provides DNS query logs for analysis

### Grafana Web UI

**Role:** Primary user interface for monitoring and dashboards

**Exposure:**
- Default port 3000
- Should be restricted to LAN or VPN only
- Contains sensitive network information

### Loki

**Role:** Central log repository

**Exposure:**
- Port 3100 for log ingestion and queries
- Should be restricted to trusted services only

## Deployment Assumptions

The threat model assumes the following deployment conditions:

### ✅ Assumed Secure

1. **Physical Security**
   - Raspberry Pi devices are in a physically secure location
   - No unauthorized physical access to devices

2. **Network Security**
   - Home/lab network is behind a NAT router/firewall
   - No port forwarding from WAN to Orion Sentinel services
   - Local network is trusted (no adversaries on LAN)

3. **Access Control**
   - Grafana and web UI are only accessible from LAN or VPN
   - Strong passwords are used for Grafana admin
   - Pi-hole API key is kept secret

4. **Platform Security**
   - Raspberry Pi OS is kept up to date
   - SSH access is secured (key-based auth, no root login)
   - Default passwords have been changed

5. **Container Security**
   - Docker daemon is not exposed to network
   - Containers run with minimal privileges (except where required)

### ⚠️ Out of Scope

These threats are **not** addressed by the current design:

1. **Physical Attacks**
   - Physical tampering with Raspberry Pi
   - SD card theft
   - Hardware keyloggers

2. **Advanced Persistent Threats (APTs)**
   - Nation-state actors
   - Zero-day exploits in Docker/Linux kernel
   - Supply chain attacks on base images

3. **Insider Threats**
   - Malicious administrators with legitimate access
   - Compromised admin credentials

4. **Performance DoS**
   - Overwhelming the Pi with excessive log volume
   - Resource exhaustion attacks

## Threat Scenarios

### High Severity Threats

#### 1. Pi #2 (Security Pi) Compromise

**Scenario:** Attacker gains root access to the Security Pi

**Impact:**
- **Critical**: Access to all network monitoring data
- **Critical**: Visibility into network topology, device inventory
- **High**: Ability to see DNS queries (privacy breach)
- **High**: Can disable monitoring/alerting (go undetected)
- **High**: Can modify SOAR playbooks (manipulate responses)
- **Medium**: Access to Pi-hole API key (tamper with DNS filtering)

**Likelihood:** Low (if deployment assumptions hold)

**Attack Vectors:**
- Vulnerable service exposed to network (SSH, Docker, etc.)
- Weak credentials on SSH or Grafana
- Exploited vulnerability in custom code
- Compromised through another device on LAN

**Mitigations:**
- Keep OS and packages updated (`apt update && apt upgrade`)
- Use SSH key-based authentication only
- Firewall rules restricting access to management ports
- Strong passwords on all services
- Regular security monitoring and log review
- Consider dedicated management VLAN for Pi devices

#### 2. Grafana Unauthorized Access

**Scenario:** Attacker accesses Grafana without authentication or with stolen credentials

**Impact:**
- **High**: Read access to all network monitoring data
- **Medium**: Information disclosure about network topology
- **Medium**: Can see device inventory and behavior
- **Low**: Cannot modify system (read-only in Grafana)

**Likelihood:** Medium (if exposed to internet or weak password used)

**Attack Vectors:**
- Weak admin password (default: admin/admin)
- Grafana exposed to WAN
- Credential stuffing/brute force
- Vulnerability in Grafana software

**Mitigations:**
- **Critical**: Change default Grafana admin password
- **Critical**: Restrict Grafana to LAN/VPN only (no WAN exposure)
- Enable Grafana authentication
- Consider SSO/OAuth integration for enterprise deployments
- Regular updates to Grafana container image
- Monitor Grafana access logs

#### 3. Pi-hole API Key Theft

**Scenario:** Attacker obtains the Pi-hole API key

**Impact:**
- **High**: Can modify Pi-hole blocklists (add/remove domains)
- **Medium**: Can allow malicious domains through filter
- **Medium**: Can block legitimate domains (DoS on users)
- **Low**: Limited to DNS filtering control

**Likelihood:** Low (key stored in `.env` file, not in version control)

**Attack Vectors:**
- Pi #2 compromise (see threat #1)
- `.env` file accidentally committed to public repo
- Log files containing API key (if logged)
- Backup files with weak permissions

**Mitigations:**
- Never commit `.env` files to version control (in `.gitignore`)
- Restrict file permissions on `.env` files (`chmod 600`)
- Rotate API key periodically
- Use read-only API key if Pi-hole supports it
- Consider network segmentation between Pi #1 and Pi #2
- Audit Pi-hole change logs regularly

### Medium Severity Threats

#### 4. Loki Data Exposure

**Scenario:** Unauthorized access to Loki data repository

**Impact:**
- **High**: Access to historical network monitoring data
- **Medium**: Information about past security incidents
- **Low**: Cannot modify data (append-only log store)

**Likelihood:** Low (Loki not exposed to WAN)

**Attack Vectors:**
- Loki port 3100 exposed to network
- Compromised container with access to Loki volume

**Mitigations:**
- Restrict Loki access to Docker network only
- Set retention policy to limit historical data (7-30 days)
- Encrypt Loki data at rest if possible
- Regular backup rotation (delete old backups)

#### 5. SOAR Automation Abuse

**Scenario:** Attacker triggers SOAR playbooks maliciously

**Impact:**
- **Medium**: Unintended blocking of legitimate domains/IPs
- **Medium**: Alert fatigue from false positives
- **Low**: Actions are logged and reversible

**Likelihood:** Low (requires ability to inject events into Loki)

**Attack Vectors:**
- Crafted events injected into Loki
- Compromised AI service container
- Playbook logic bugs leading to unintended triggers

**Mitigations:**
- Run SOAR in dry-run mode initially (`SOAR_DRY_RUN=1`)
- Set conservative thresholds in playbooks
- Implement rate limiting on SOAR actions
- Review SOAR logs regularly
- Test playbooks in dev environment before production
- Require manual approval for high-impact actions

#### 6. Container Escape

**Scenario:** Attacker escapes from Docker container to host

**Impact:**
- **Critical**: Full host compromise (same as threat #1)

**Likelihood:** Very Low (requires Docker vulnerability)

**Attack Vectors:**
- Exploited vulnerability in Docker runtime
- Misconfigured container capabilities
- Privileged container exploitation

**Mitigations:**
- Keep Docker engine updated
- Avoid running containers in privileged mode (except Suricata, which requires it for packet capture)
- Use Docker security scanning
- Regularly update base images
- Consider AppArmor/SELinux profiles for containers

### Low Severity Threats

#### 7. Log Injection

**Scenario:** Attacker injects false data into logs

**Impact:**
- **Medium**: False alerts and wasted investigation time
- **Low**: Can be detected by correlation with other sources
- **Low**: Does not grant system access

**Likelihood:** Low (requires network access or compromised endpoint)

**Mitigations:**
- Validate log sources (signed/authenticated log shipping)
- Correlation with multiple data sources
- Anomaly detection on log patterns
- Regular baseline reviews

#### 8. Resource Exhaustion

**Scenario:** High log volume overwhelms Pi resources

**Impact:**
- **Medium**: Monitoring gaps due to dropped logs
- **Low**: Services may restart automatically
- **Low**: Does not compromise data confidentiality

**Likelihood:** Medium (especially on high-traffic networks)

**Mitigations:**
- Set log retention policies
- Configure log sampling for high-volume sources
- Monitor resource usage (see operations.md)
- Use log filtering in Promtail
- Consider deploying on more powerful hardware for large networks

## Security Recommendations

### Deployment Best Practices

1. **Network Segmentation**
   ```
   Recommended VLAN structure:
   - VLAN 10: Management (Pi devices, admin access)
   - VLAN 20: Trusted devices
   - VLAN 30: IoT devices (monitored)
   - VLAN 40: Guest network
   
   Pi #2 should be on Management VLAN with access to mirror traffic
   ```

2. **Access Control**
   - Access Grafana only via VPN or from trusted management network
   - Use strong, unique passwords for all services
   - Enable two-factor authentication where supported
   - Consider SSO integration for team environments

3. **Monitoring and Alerting**
   - Set up alerts for Pi resource exhaustion
   - Monitor for unexpected container restarts
   - Alert on SOAR playbook executions
   - Review logs weekly for anomalies

4. **Regular Maintenance**
   - Weekly: Review Grafana dashboards for anomalies
   - Monthly: Update system packages and Docker images
   - Quarterly: Review and test backup/restore procedures
   - Annually: Full security review and threat model update

### Secure Configuration Checklist

- [ ] Change Grafana default password
- [ ] Restrict Grafana to LAN/VPN (no WAN exposure)
- [ ] Set strong Pi-hole API key
- [ ] Configure `.env` file permissions to 600
- [ ] Enable UFW or iptables firewall
- [ ] Disable SSH password authentication (use keys only)
- [ ] Change default SSH port (optional defense-in-depth)
- [ ] Keep OS packages updated (`apt update && apt upgrade`)
- [ ] Set Loki retention policy (avoid filling disk)
- [ ] Test SOAR playbooks in dry-run mode first
- [ ] Configure regular automated backups
- [ ] Review Docker container logs weekly
- [ ] Monitor disk space usage
- [ ] Set up alerting for critical events

### Incident Response

If you suspect a compromise:

1. **Contain**
   - Disconnect affected Pi from network
   - Stop all Docker containers: `docker compose down`
   - Capture memory dump if forensics needed

2. **Assess**
   - Review Grafana logs for unusual activity
   - Check system logs: `journalctl -xe`
   - Review Docker logs: `docker compose logs`
   - Check for modified files: `debsums -c`

3. **Recover**
   - Restore from known-good backup
   - Rebuild Pi from scratch if needed
   - Rotate all credentials (Grafana, Pi-hole API key, SSH keys)
   - Review playbooks for tampering

4. **Learn**
   - Document incident timeline
   - Identify root cause
   - Update threat model
   - Improve detection/prevention controls

## Compliance Considerations

While Orion Sentinel is designed for home/lab use, users in regulated environments should consider:

- **Data Privacy**: Network monitoring data may include PII (IP addresses, DNS queries)
- **Data Retention**: Implement retention policies compliant with local regulations
- **Access Logging**: Audit all administrative actions
- **Encryption**: Consider encrypting backups and data at rest
- **Segregation of Duties**: Use separate accounts for admin vs. viewer access

Orion Sentinel is **not certified** for:
- HIPAA (healthcare data)
- PCI DSS (payment card data)
- SOC 2 compliance
- Government/military use cases

## Future Security Enhancements

Potential improvements for increased security:

1. **Authentication & Authorization**
   - OAuth/SSO integration for Grafana
   - API key authentication for Loki
   - Role-based access control (RBAC)

2. **Encryption**
   - TLS for Grafana (HTTPS)
   - Encrypted backups
   - Encrypted Docker volumes

3. **Auditing**
   - Centralized audit log for all admin actions
   - File integrity monitoring (AIDE/Tripwire)
   - Security event correlation

4. **Hardening**
   - AppArmor/SELinux profiles for containers
   - Read-only root filesystems where possible
   - Network policies restricting inter-container communication

5. **Monitoring**
   - Honeytokens for breach detection
   - SIEM integration for enterprise deployments
   - Automated security scanning (Trivy, Clair)

## References

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Raspberry Pi Benchmark](https://www.cisecurity.org/)
- [Grafana Security Best Practices](https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## See Also

- [Operations Guide](operations.md) - Backup, restore, and maintenance procedures
- [Architecture](architecture.md) - System design and components
- [SOAR Guide](soar.md) - Playbook security considerations
