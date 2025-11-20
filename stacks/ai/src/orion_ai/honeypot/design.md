# Honeypot Design

## Overview

Honeypot services are decoy services designed to detect unauthorized access attempts
and potential lateral movement within the network.

## Proposed Services

1. **SSH Honeypot** - Fake SSH service on port 2222
2. **HTTP Honeypot** - Fake web server on port 8888
3. **SMB Honeypot** - Fake file share service

## Implementation TODO

- [ ] Deploy lightweight honeypot containers (e.g., cowrie, honeytrap)
- [ ] Configure logging to Loki with `service="honeypot"`
- [ ] Implement event parser to convert honeypot logs to Events
- [ ] Create SOAR playbook to tag devices accessing honeypots
- [ ] Add honeypot access events to device profiles

## Security Considerations

- Honeypots should be isolated and not contain any real data
- Access attempts should trigger immediate alerts
- Consider legal implications in your jurisdiction
