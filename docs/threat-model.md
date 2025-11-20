# Threat Model & Security Hardening

This document describes the security architecture, threat model, and hardening recommendations for Orion Sentinel NSM AI deployments.

## System Overview

Orion Sentinel is a home/lab network security monitoring platform running on Raspberry Pi 5 (Pi #2) with the following key characteristics:

- **Passive monitoring**: Non-inline traffic monitoring via port mirroring
- **Local processing**: All AI and analytics run on-device (no cloud dependencies)
- **LAN-only interfaces**: Web UI and Grafana are designed for local network access
- **Limited attack surface**: Minimal exposed services, no inbound WAN connections by default

## Assets

### Critical Assets

1. **Network Monitoring Data**
   - Suricata IDS logs (`.eve.json` files)
   - DNS query logs from Pi-hole
   - Network flow metadata
   - **Risk**: Exposure reveals network topology and user behavior

2. **Device Inventory Database**
   - SQLite database (`data/inventory.db`)
   - Device IPs, MACs, hostnames, types
   - Behavioral baselines and anomaly scores
   - **Risk**: Reveals all devices on network and their characteristics

3. **AI Model Outputs**
   - Anomaly detection results
   - Domain risk scores
   - Threat intelligence matches
   - **Risk**: Could help attacker understand detection capabilities

4. **Configuration & Credentials**
   - `.env` files (Pi-hole API keys, Grafana passwords)
   - `playbooks.yml` (SOAR automation rules)
   - Grafana datasource configs
   - **Risk**: Credential theft enables lateral movement

5. **SOAR Playbooks**
   - Automated response rules
   - Blocking policies
   - Integration credentials
   - **Risk**: Attacker could manipulate or disable defenses

### Supporting Assets

- Loki log database
- Grafana dashboards and configurations
- Threat intelligence cache
- AI model files (`.onnx`, `.tflite`)
- Prometheus metrics
- Docker container runtime

## Key Components

### Pi #2 (Security Pi)

**Role**: Network Security Monitoring & AI Analysis

**Services**:
- Suricata IDS (passive mode)
- Loki (log aggregation)
- Grafana (visualization)
- AI service (anomaly detection, domain risk)
- Prometheus (metrics, optional)
- SOAR service (automated response)

**Network Interfaces**:
- Primary interface: LAN connectivity for management
- Mirrored interface: Receives duplicate traffic from switch (promiscuous mode)

**Exposure**:
- Web UI: `http://pi2-ip:8000` (LAN only, no authentication by default)
- Grafana: `http://pi2-ip:3000` (LAN only, password-protected)
- Loki API: `http://pi2-ip:3100` (LAN only, no authentication)
- Prometheus: `http://pi2-ip:9090` (LAN only, if enabled)

### Integration Points

**Pi #1 (DNS Pi)**:
- Pi-hole API: Receives block requests from Pi #2
- DNS log shipping: Sends logs to Pi #2's Loki via Promtail
- **Trust boundary**: Pi #2 must authenticate to Pi-hole API

**Network Switch/Router**:
- Port mirroring: Sends copy of LAN traffic to Pi #2
- **Trust assumption**: Switch configuration is trusted

## Threat Model

### Assumptions

#### Trusted Environment
- **Local network is semi-trusted**: Home/lab environment, not hostile datacenter
- **Physical security**: Raspberry Pis are in a physically secure location
- **No public internet exposure**: Services are NOT exposed to WAN by default
- **VPN for remote access**: If remote access is needed, use VPN (WireGuard, Tailscale)

#### Network Segmentation
- **LAN/VLAN isolation (optional)**: Pi #2 may be on dedicated management VLAN
- **Port mirroring is read-only**: Pi #2 cannot inject traffic via mirrored port
- **No inline blocking**: Pi #2 is NOT in network path (no IPS mode)

#### User Behavior
- **Authorized administrators only**: Only trusted users have SSH/console access
- **Secure credential management**: Passwords and API keys are stored securely
- **No shared credentials**: Each service has unique credentials

### Threats

#### T1: Compromise of Pi #2 Host

**Scenario**: Attacker gains shell access to Pi #2 via:
- Exploited vulnerability in Docker, Grafana, or other service
- Compromised SSH credentials
- Physical access to the device

**Impact**:
- **Critical**: Full access to network monitoring data
- Attacker sees all network traffic metadata (who talks to whom)
- Attacker can read DNS queries (revealing user browsing habits)
- Attacker can disable monitoring or SOAR responses
- Attacker may pivot to other devices via Pi-hole API credentials

**Likelihood**: Low (in typical home/lab with LAN-only access)

**Mitigations**:
- **M1.1**: Keep OS and packages updated (`apt update && apt upgrade`)
- **M1.2**: Use strong SSH keys (disable password auth)
- **M1.3**: Firewall rules to allow only necessary traffic
- **M1.4**: Enable UFW or nftables to restrict access
- **M1.5**: Regular security audits of running services
- **M1.6**: Use AppArmor or SELinux for container isolation (if available on Pi OS)
- **M1.7**: Disable unused services
- **M1.8**: Monitor for unauthorized access attempts

#### T2: Exposure of Web UI or Grafana to WAN

**Scenario**: Misconfiguration exposes Grafana or API server to public internet

**Impact**:
- **High**: Unauthorized access to dashboards and logs
- Information disclosure about network topology
- Potential credential brute-forcing
- Data exfiltration

**Likelihood**: Low (requires explicit misconfiguration)

**Mitigations**:
- **M2.1**: Never port-forward Pi #2 services to WAN
- **M2.2**: Use VPN (WireGuard, Tailscale) for remote access
- **M2.3**: Set strong Grafana admin password (`GRAFANA_ADMIN_PASSWORD`)
- **M2.4**: Enable Grafana authentication for all users
- **M2.5**: Configure firewall to drop WAN traffic to Pi #2
- **M2.6**: Use reverse proxy (Nginx) with mTLS if remote access is required
- **M2.7**: Regular port scans to verify no unintended exposure

#### T3: Theft of Pi-hole API Credentials

**Scenario**: Attacker obtains `PIHOLE_API_KEY` from `.env` file or memory

**Impact**:
- **Medium**: Attacker can modify Pi-hole blocklists
- Add/remove domains from allow/deny lists
- Potentially bypass DNS blocking for malicious domains
- Disrupt DNS filtering for entire network

**Likelihood**: Low (requires prior compromise of Pi #2)

**Mitigations**:
- **M3.1**: Restrict `.env` file permissions (`chmod 600`)
- **M3.2**: Use Docker secrets instead of environment variables
- **M3.3**: Rotate Pi-hole API key periodically
- **M3.4**: Monitor Pi-hole for unexpected configuration changes
- **M3.5**: Enable Pi-hole audit logging
- **M3.6**: Set up alerts for blocklist modifications
- **M3.7**: Use read-only API key if Pi-hole supports it

#### T4: Malicious Log Injection

**Scenario**: Attacker injects crafted logs into Loki via:
- Compromised Promtail on Pi #1
- Direct access to Loki API (if exposed)
- Malicious container on same Docker network

**Impact**:
- **Medium**: Pollutes log data with false information
- Triggers false positive alerts
- Hides real attack indicators (log poisoning)
- Exploits AI model with adversarial inputs

**Likelihood**: Low (requires network access or prior compromise)

**Mitigations**:
- **M4.1**: Loki API should only accept connections from trusted sources
- **M4.2**: Use Docker network isolation (separate bridge networks)
- **M4.3**: Enable Loki authentication (basic auth or OAuth)
- **M4.4**: Input validation on AI service (sanitize log inputs)
- **M4.5**: Anomaly detection on log volume/patterns
- **M4.6**: Immutable logging (write-once storage for critical logs)

#### T5: SOAR Playbook Manipulation

**Scenario**: Attacker modifies `playbooks.yml` to:
- Disable blocking rules
- Add malicious domains to allowlist
- Trigger denial-of-service by blocking legitimate domains

**Impact**:
- **High**: Compromise of automated defense system
- Legitimate traffic blocked (DoS)
- Malicious traffic allowed (evasion)

**Likelihood**: Low (requires write access to Pi #2 filesystem)

**Mitigations**:
- **M5.1**: Protect `config/playbooks.yml` with strict permissions
- **M5.2**: Use git to track playbook changes (commit all edits)
- **M5.3**: Enable playbook dry-run mode by default (`SOAR_DRY_RUN=1`)
- **M5.4**: Add integrity checks (hash verification of playbook file)
- **M5.5**: Alert on playbook modifications
- **M5.6**: Require multi-person approval for playbook changes (in team environments)

#### T6: Data Exfiltration via Logs

**Scenario**: Network monitoring data contains sensitive information:
- Browsing history (DNS queries)
- Internal hostnames and IPs
- Communication patterns

**Impact**:
- **Medium**: Privacy violation if data is exfiltrated
- Attacker learns network topology
- User behavior profiling

**Likelihood**: Low (requires prior compromise or misconfiguration)

**Mitigations**:
- **M6.1**: Encrypt backups (use encrypted filesystem or `gpg`)
- **M6.2**: Limit log retention period (Loki: 7 days default)
- **M6.3**: Do not expose Loki or logs to cloud services
- **M6.4**: Network segmentation (isolate Pi #2 on management VLAN)
- **M6.5**: Redact sensitive fields from logs if possible
- **M6.6**: Regular review of log retention policies

#### T7: Docker Container Escape

**Scenario**: Vulnerability in Docker allows container escape to host

**Impact**:
- **Critical**: Full host compromise (same as T1)
- Access to all container data and host filesystem

**Likelihood**: Very Low (requires 0-day in Docker runtime)

**Mitigations**:
- **M7.1**: Keep Docker updated to latest stable version
- **M7.2**: Use Docker user namespaces (remap root)
- **M7.3**: Run containers as non-root user where possible
- **M7.4**: Enable Docker seccomp and AppArmor profiles
- **M7.5**: Limit container capabilities (`--cap-drop ALL`)
- **M7.6**: Use read-only root filesystems where appropriate

#### T8: Supply Chain Attacks (Docker Images)

**Scenario**: Compromised Docker image contains backdoor or malware

**Impact**:
- **High**: Malicious code runs with container privileges
- Data exfiltration, cryptocurrency mining, or pivoting

**Likelihood**: Very Low (using official images from Docker Hub)

**Mitigations**:
- **M8.1**: Use official images only (grafana/grafana, grafana/loki, etc.)
- **M8.2**: Pin image versions (avoid `latest` tag)
- **M8.3**: Verify image signatures (Docker Content Trust)
- **M8.4**: Regular vulnerability scanning (`docker scan` or Trivy)
- **M8.5**: Build custom images from trusted base images
- **M8.6**: Review Dockerfiles before building

## Security Hardening Recommendations

### Essential (Must Do)

1. **Strong Passwords**
   - Set strong Grafana admin password: `GRAFANA_ADMIN_PASSWORD`
   - Generate strong Pi-hole API key
   - Use SSH keys only (disable password auth)

2. **OS Updates**
   - Keep Raspberry Pi OS updated:
     ```bash
     sudo apt update && sudo apt upgrade -y
     ```
   - Enable unattended security updates:
     ```bash
     sudo apt install unattended-upgrades
     sudo dpkg-reconfigure unattended-upgrades
     ```

3. **Docker Security**
   - Keep Docker up to date:
     ```bash
     sudo apt update && sudo apt install docker-ce docker-ce-cli
     ```
   - Remove unused images and containers:
     ```bash
     docker system prune -a
     ```

4. **Firewall Configuration**
   - Enable UFW (Uncomplicated Firewall):
     ```bash
     sudo ufw default deny incoming
     sudo ufw default allow outgoing
     sudo ufw allow from 192.168.1.0/24 to any port 22  # SSH from LAN only
     sudo ufw allow from 192.168.1.0/24 to any port 3000 # Grafana from LAN only
     sudo ufw enable
     ```

5. **File Permissions**
   - Protect sensitive files:
     ```bash
     chmod 600 stacks/*/.env
     chmod 600 config/playbooks.yml
     ```

6. **No WAN Exposure**
   - Verify no port forwarding to Pi #2
   - Use VPN (WireGuard, Tailscale) for remote access

### Recommended (Should Do)

7. **VLAN Segmentation**
   - Place Pi #2 on dedicated management VLAN
   - Restrict access to management VLAN via ACLs

8. **Enable Grafana Authentication**
   - Configure Grafana for all users (not just admin):
     ```yaml
     # grafana.ini
     [auth.anonymous]
     enabled = false
     ```

9. **Loki Authentication**
   - Enable basic auth on Loki API (advanced configuration)

10. **SSH Hardening**
    - Disable root login: `PermitRootLogin no`
    - Disable password auth: `PasswordAuthentication no`
    - Change default SSH port (optional): `Port 2222`

11. **Monitoring and Alerting**
    - Set up alerts for failed SSH attempts
    - Monitor Docker container restarts
    - Alert on high CPU/memory (potential cryptomining)

12. **Backup Encryption**
    - Encrypt backup archives:
      ```bash
      tar czf - backups/backup_20250120/ | gpg -c > backup_20250120.tar.gz.gpg
      ```

### Advanced (Nice to Have)

13. **Two-Factor Authentication**
    - Enable 2FA for Grafana (LDAP, OAuth, or plugin)

14. **Intrusion Detection on Pi #2 Itself**
    - Run AIDE (file integrity monitoring) on Pi #2
    - Monitor for unauthorized changes to configs

15. **Network Segmentation**
    - Isolate mirrored traffic interface (no IP assigned)
    - Use separate Docker networks for each stack

16. **Log Immutability**
    - Configure Loki to use object storage with versioning
    - Use write-once storage backend

17. **Security Scanning**
    - Run Trivy to scan Docker images:
      ```bash
      trivy image grafana/grafana:latest
      ```
    - Use Lynis for OS security audit:
      ```bash
      sudo lynis audit system
      ```

## Deployment Scenarios

### Scenario 1: Home Lab (Low Security Requirements)

**Setup**:
- Pi #2 on main LAN
- Grafana with strong password
- No VPN (LAN access only)
- Weekly manual backups

**Acceptable Risks**:
- Other devices on LAN can access Grafana
- No encryption at rest

**Recommended**:
- Essential hardening (1-6)
- Firewall to block WAN access

### Scenario 2: Home Network (Medium Security Requirements)

**Setup**:
- Pi #2 on management VLAN
- Grafana with 2FA
- VPN (Tailscale/WireGuard) for remote access
- Automated encrypted backups

**Mitigations**:
- Essential + Recommended (1-12)
- VLAN ACLs to restrict access
- Regular OS and Docker updates

### Scenario 3: Small Office/SOHO (High Security Requirements)

**Setup**:
- Pi #2 on isolated management VLAN
- All services behind reverse proxy with mTLS
- Centralized authentication (LDAP/OAuth)
- Encrypted backups to off-site storage
- Regular security audits

**Mitigations**:
- Essential + Recommended + Advanced (all)
- Formal change management for playbooks
- Intrusion detection on Pi #2 itself
- Regular penetration testing

## Incident Response

### If Pi #2 is Compromised

1. **Isolate**: Disconnect Pi #2 from network immediately
2. **Assess**: Review logs for signs of data exfiltration or lateral movement
3. **Contain**: Change all credentials (Pi-hole API, Grafana, SSH keys)
4. **Recover**: Restore from known-good backup
5. **Investigate**: Analyze how compromise occurred
6. **Harden**: Implement additional mitigations to prevent recurrence

### If Credentials are Leaked

1. **Rotate immediately**: Generate new Pi-hole API key, Grafana password
2. **Review logs**: Check Pi-hole audit log and Grafana access logs for unauthorized changes
3. **Revert unauthorized changes**: Restore blocklists, playbooks from backup
4. **Enable monitoring**: Set up alerts for future configuration changes

## Compliance Considerations

For users subject to compliance frameworks (e.g., small business, non-profit):

- **GDPR/Privacy**: Log retention policies, data minimization, encryption
- **PCI DSS**: Network segmentation, access controls, logging (if handling payment data nearby)
- **NIST Cybersecurity Framework**: Aligns with Identify, Protect, Detect, Respond, Recover

Orion Sentinel can support these frameworks with proper configuration (not compliant out-of-the-box).

## Security Contacts

If you discover a security vulnerability in Orion Sentinel:

- **Do not open a public issue**
- Contact the repository maintainer directly via GitHub private message
- Provide details of the vulnerability and steps to reproduce
- Allow reasonable time for a fix before public disclosure

## Related Documentation

- [Operations Guide](operations.md): Backup, restore, upgrade procedures
- [Architecture Overview](architecture.md): System design and data flows
- [Pi Setup Guide](pi2-setup.md): Initial installation and configuration

## Changelog

- **2025-01-20**: Initial threat model and hardening guide
