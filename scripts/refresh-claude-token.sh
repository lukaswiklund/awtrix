#!/usr/bin/env bash
# Keep Claude Code's OAuth token fresh so the bridge never reads an expired one.
#
# Claude Code only rotates ~/.claude/.credentials.json while it is running, so a
# quiet evening leaves the file holding an expired accessToken and the claude
# apps stuck on "CC?" (401) until the next session. This runs a trivial
# `claude -p` when the token is expired or about to be, which makes Claude Code
# refresh and rewrite the file. Meant for a timer; see README.
set -euo pipefail

CREDS="${CLAUDE_DIR:-$HOME}/.claude/.credentials.json"
MARGIN="${TOKEN_MARGIN:-1800}"   # refresh when fewer seconds than this remain

remaining=$(python3 - "$CREDS" <<'PY'
import json, sys, time
try:
    d = json.load(open(sys.argv[1])).get("claudeAiOauth") or {}
    print(int(d.get("expiresAt", 0) / 1000 - time.time()))
except (OSError, ValueError):
    print(0)
PY
)

if (( remaining > MARGIN )); then
    echo "token ok, ${remaining}s left"
    exit 0
fi

echo "token has ${remaining}s left; running claude to refresh"
# Not from inside a Claude Code session; the guard would refuse to start.
unset CLAUDECODE
claude -p "reply with ok" --model haiku </dev/null >/dev/null
echo "refreshed, now $(python3 -c "import json,time;print(int(json.load(open('$CREDS'))['claudeAiOauth']['expiresAt']/1000-time.time()))")s left"
