#!/bin/sh
set -eu
output=$(iris session IRIS -U ARGUS <<'EOF'
set installer=##class(%SYS.Python).Import("argus.install")
do installer.setup()
halt
EOF
)
printf '%s\n' "$output"
printf '%s\n' "$output" | grep -q '^ARGUS_INSTALL_OK'
touch /tmp/argus-ready
