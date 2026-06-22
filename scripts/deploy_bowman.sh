#!/usr/bin/env bash
# Deploy homeconnect_ws fork to Bowman Mtn HA and verify Thermador hood.
set -euo pipefail
HOST="${HA_HOST:-ntableman@192.168.50.10}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
REMOTE="/home/ntableman/docker/ha/config/custom_components/homeconnect_ws"
HOOD_ENTRY="01KVPTGKWXRGW5RAFXGA8KDB2Z"

ssh "$HOST" "cp -a $REMOTE ${REMOTE}.bak-${STAMP}"

rsync -av --delete \
  --exclude='__pycache__' --exclude='*.pyc' \
  "$REPO_ROOT/custom_components/homeconnect_ws/" \
  "$HOST:$REMOTE/"

rsync -av "$REPO_ROOT/scripts/verify_thermador_hood.py" \
  "$HOST:/home/ntableman/docker/ha/config/scripts/verify_thermador_hood.py"

ssh "$HOST" "docker cp /home/ntableman/docker/ha/config/scripts/verify_thermador_hood.py home-assistant:/config/scripts/verify_thermador_hood.py \
  && docker restart home-assistant"

echo "Waiting for HA..."
sleep 55

ssh "$HOST" "docker exec home-assistant python3 -c \"
import json, urllib.request, urllib.error
from pathlib import Path

entry_id = '${HOOD_ENTRY}'
with open('/config/.storage/auth') as f:
    auth = json.load(f)['data']
tokens = [t['token'] for t in auth.get('refresh_tokens', [])
          if t.get('token_type') == 'long_lived_access_token' and t.get('token')]

for token in tokens:
    req = urllib.request.Request(
        'http://127.0.0.1:8123/api/services/homeassistant/reload_config_entry',
        data=json.dumps({'entry_id': entry_id}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        urllib.request.urlopen(req, timeout=30)
        print('reloaded homeconnect hood entry')
        break
    except urllib.error.HTTPError:
        continue
\""

sleep 10
ssh "$HOST" 'docker exec home-assistant python3 /config/scripts/verify_thermador_hood.py'
