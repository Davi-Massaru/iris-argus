#!/bin/sh
set -eu
rm -f /tmp/agentic-ready /tmp/agentic-worker-heartbeat

output=$(iris session IRIS -U AGENTIC <<'EOF'
set installer=##class(%SYS.Python).Import("app.install")
do installer.setup()
halt
EOF
)
printf '%s\n' "$output"
printf '%s\n' "$output" | grep -q '^AGENTIC_INSTALL_OK'

rm -f /tmp/agentic-worker-stop
nohup python3 /opt/agentic/worker/supervisor.py >/tmp/agentic-worker.log 2>&1 &
attempt=0
until test -f /tmp/agentic-worker-heartbeat; do
    attempt=$((attempt + 1))
    if test "$attempt" -ge 20; then
        echo 'Worker failed its SQL readiness check; inspect /tmp/agentic-worker.log'
        exit 1
    fi
    sleep 1
done
touch /tmp/agentic-ready
