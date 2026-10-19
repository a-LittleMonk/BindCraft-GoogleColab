#!/usr/bin/env bash
# Pull a campaign's results off the rented box onto this machine.
# Run this from YOUR computer, not from the instance.
#
#   bash fetch_results.sh root@ssh5.vast.ai:12345 ./results
#
# The host:port pair is on the vast.ai instance card ("Direct ssh connect").
# Always fetch before destroying an instance - destroying deletes everything.
set -euo pipefail

TARGET="${1:-}"
DEST="${2:-./results}"
REMOTE_PATH="${BC_ROOT:-/workspace}/designs/"

if [ -z "$TARGET" ]; then
  echo "usage: bash fetch_results.sh user@host:port [dest_dir]" >&2
  exit 1
fi

HOST="${TARGET%%:*}"
PORT="${TARGET##*:}"
[ "$PORT" = "$HOST" ] && PORT=22

mkdir -p "$DEST"
rsync -avh --progress -e "ssh -p $PORT" "$HOST:$REMOTE_PATH" "$DEST/"
echo
echo "Fetched to $DEST"
