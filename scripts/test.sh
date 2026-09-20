#!/bin/sh
set -eu
output=$(iris session IRIS <<'EOF'
zn "ARGUS"
set runner=##class(%SYS.Python).Import("runpy")
do runner."run_path"("/opt/argus/scripts/embedded_tests.py")
halt
EOF
)
printf '%s\n' "$output"
printf '%s\n' "$output" | grep -q '^ARGUS_EMBEDDED_TESTS_OK'
python3 /opt/argus/scripts/http_smoke.py
