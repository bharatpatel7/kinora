#!/usr/bin/env bash
# Give containers internet access when a host VPN (NordVPN, corporate VPNs, ...) blocks
# apple/container's NAT traffic. Runs tinyproxy on the container bridge only, so container
# traffic goes out through the Mac's own (VPN) connection.
#
#   scripts/container-proxy.sh start   # then build/run with the printed proxy settings
#   scripts/container-proxy.sh stop
set -euo pipefail

STATE_DIR="${TMPDIR:-/tmp}/kinora-proxy"
PORT="${KINORA_PROXY_PORT:-8888}"
BRIDGE_IP="$(ifconfig bridge100 2>/dev/null | awk '/inet /{print $2; exit}')"

case "${1:-}" in
start)
    command -v tinyproxy >/dev/null || { echo "Install tinyproxy first: brew install tinyproxy" >&2; exit 1; }
    [ -n "$BRIDGE_IP" ] || { echo "No container bridge found. Run 'container system start' and start any container once." >&2; exit 1; }
    mkdir -p "$STATE_DIR"
    if [ -f "$STATE_DIR/tinyproxy.pid" ] && kill -0 "$(cat "$STATE_DIR/tinyproxy.pid")" 2>/dev/null; then
        echo "Proxy already running."
    else
        cat >"$STATE_DIR/tinyproxy.conf" <<EOF
Port $PORT
Listen $BRIDGE_IP
Allow ${BRIDGE_IP%.*}.0/24
Timeout 600
ConnectPort 443
LogLevel Warning
LogFile "$STATE_DIR/tinyproxy.log"
PidFile "$STATE_DIR/tinyproxy.pid"
EOF
        tinyproxy -c "$STATE_DIR/tinyproxy.conf"
        echo "Proxy listening on $BRIDGE_IP:$PORT (container network only)."
    fi
    P="http://$BRIDGE_IP:$PORT"
    cat <<EOF

Build:
  container build --build-arg HTTP_PROXY=$P --build-arg HTTPS_PROXY=$P --tag kinora --file Containerfile .
Run (proxy only needed for cloud providers):
  container run --rm -p 127.0.0.1:8000:8000 -e HTTPS_PROXY=$P -e REPLICATE_API_TOKEN kinora
EOF
    ;;
stop)
    if [ -f "$STATE_DIR/tinyproxy.pid" ]; then
        kill "$(cat "$STATE_DIR/tinyproxy.pid")" 2>/dev/null || true
        rm -f "$STATE_DIR/tinyproxy.pid"
        echo "Proxy stopped."
    else
        echo "Proxy not running."
    fi
    ;;
*)
    echo "usage: $0 start|stop" >&2
    exit 2
    ;;
esac
