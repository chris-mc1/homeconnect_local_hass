#!/usr/bin/env bash
# Run homeconnect_ws tests inside the Home Assistant container on Bowman Mtn.
set -euo pipefail
HOST="${HA_HOST:-ntableman@192.168.50.10}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

rsync -av --delete \
  "$REPO_ROOT/tests/" \
  "$HOST:/tmp/hcws-pytest/tests/"

rsync -av --delete \
  "$REPO_ROOT/custom_components/homeconnect_ws/" \
  "$HOST:/tmp/hcws-pytest/homeconnect_ws/"

ssh "$HOST" 'docker exec home-assistant rm -rf /config/hcws_tests \
  && docker cp /tmp/hcws-pytest/tests home-assistant:/config/hcws_tests \
  && docker cp /tmp/hcws-pytest/homeconnect_ws home-assistant:/config/custom_components/homeconnect_ws \
  && docker exec home-assistant bash -c "cd /config && python3 -m pytest hcws_tests/ -q --tb=line"'
