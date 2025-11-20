#!/usr/bin/env bash
#
# log-injector.sh - Inject sample logs into Loki for development/testing
#
# This script reads sample log files and pushes them to Loki with appropriate labels
# simulating a production environment.
#

set -euo pipefail

# Configuration
LOKI_URL="${LOKI_URL:-http://loki:3100}"
INJECT_INTERVAL="${INJECT_INTERVAL:-30}"
SAMPLES_DIR="/samples"

echo "==================================================="
echo "Orion Sentinel Log Injector - Development Mode"
echo "==================================================="
echo "Loki URL: ${LOKI_URL}"
echo "Injection interval: ${INJECT_INTERVAL} seconds"
echo "Samples directory: ${SAMPLES_DIR}"
echo ""

# Install required tools
echo "Installing dependencies..."
apk add --no-cache curl jq coreutils

# Wait for Loki to be ready
echo "Waiting for Loki to be ready..."
for i in $(seq 1 30); do
    if curl -s "${LOKI_URL}/ready" >/dev/null 2>&1; then
        echo "✓ Loki is ready"
        break
    fi
    echo "  Waiting for Loki... ($i/30)"
    sleep 2
done

# Function to send logs to Loki
send_to_loki() {
    local job="$1"
    local log_file="$2"
    local extra_labels="$3"
    
    if [ ! -f "$log_file" ]; then
        echo "  ⚠ File not found: $log_file"
        return
    fi
    
    # Current timestamp in nanoseconds
    timestamp=$(date +%s%N)
    
    # Build labels
    labels="{job=\"${job}\",environment=\"dev\""
    if [ -n "$extra_labels" ]; then
        labels="${labels},${extra_labels}"
    fi
    labels="${labels}}"
    
    # Read file and prepare Loki push payload
    # For JSON files (suricata, intel_matches), send each line as a separate entry
    # For text files (pihole), send each line as is
    
    if [ "${log_file##*.}" = "json" ]; then
        # JSON format - send each line
        count=0
        while IFS= read -r line; do
            # Skip comments and empty lines
            echo "$line" | grep -q '^#' && continue
            [ -z "$line" ] && continue
            
            # Escape quotes in the log line
            escaped_line=$(echo "$line" | sed 's/"/\\"/g')
            
            # Create Loki push payload
            payload=$(cat <<EOF
{
  "streams": [
    {
      "stream": ${labels},
      "values": [
        ["${timestamp}", "${escaped_line}"]
      ]
    }
  ]
}
EOF
)
            
            # Send to Loki
            if curl -s -X POST "${LOKI_URL}/loki/api/v1/push" \
                -H "Content-Type: application/json" \
                -d "$payload" >/dev/null 2>&1; then
                count=$((count + 1))
            fi
            
            # Increment timestamp slightly to maintain order
            timestamp=$((timestamp + 1000000))
        done < "$log_file"
        echo "  ✓ Sent ${count} events from $(basename "$log_file")"
    else
        # Text format - send each line
        count=0
        while IFS= read -r line; do
            # Skip comments and empty lines
            echo "$line" | grep -q '^#' && continue
            [ -z "$line" ] && continue
            
            # Escape quotes in the log line
            escaped_line=$(echo "$line" | sed 's/"/\\"/g')
            
            # Create Loki push payload
            payload=$(cat <<EOF
{
  "streams": [
    {
      "stream": ${labels},
      "values": [
        ["${timestamp}", "${escaped_line}"]
      ]
    }
  ]
}
EOF
)
            
            # Send to Loki
            if curl -s -X POST "${LOKI_URL}/loki/api/v1/push" \
                -H "Content-Type: application/json" \
                -d "$payload" >/dev/null 2>&1; then
                count=$((count + 1))
            fi
            
            # Increment timestamp slightly to maintain order
            timestamp=$((timestamp + 1000000))
        done < "$log_file"
        echo "  ✓ Sent ${count} events from $(basename "$log_file")"
    fi
}

echo ""
echo "Starting log injection loop..."
echo "Press Ctrl+C to stop"
echo ""

# Main injection loop
cycle=1
while true; do
    echo "[Cycle ${cycle}] $(date)"
    echo "---------------------------------------------------"
    
    # Inject Suricata EVE logs
    if [ -f "${SAMPLES_DIR}/suricata-eve.json" ]; then
        send_to_loki "suricata" "${SAMPLES_DIR}/suricata-eve.json" "source=\"suricata\",host=\"dev-pi\""
    fi
    
    # Inject Pi-hole DNS logs
    if [ -f "${SAMPLES_DIR}/pihole-dns.log" ]; then
        send_to_loki "pihole" "${SAMPLES_DIR}/pihole-dns.log" "source=\"pihole\",host=\"dev-pi\""
    fi
    
    # Inject threat intelligence matches
    if [ -f "${SAMPLES_DIR}/intel_matches.json" ]; then
        send_to_loki "intel" "${SAMPLES_DIR}/intel_matches.json" "source=\"threat_intel\",host=\"dev-pi\""
    fi
    
    echo ""
    echo "Next injection in ${INJECT_INTERVAL} seconds..."
    echo ""
    
    sleep "${INJECT_INTERVAL}"
    cycle=$((cycle + 1))
done
