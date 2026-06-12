#!/usr/bin/env bash
# Guard: when backend/requirements.txt is staged, pylock.toml must be staged too.
# Deterministic + offline — does NOT regenerate the lock (pip lock is non-deterministic
# across runs due to index drift / safe-chain min-age, which would cause false failures).
# It only enforces that the dev regenerated and staged the lock alongside the manifest.
set -euo pipefail

REQ="backend/requirements.txt"
LOCK="pylock.toml"

staged="$(git diff --cached --name-only)"

# Only fires when requirements.txt is part of this commit.
echo "$staged" | grep -qx "$REQ" || exit 0

if echo "$staged" | grep -qx "$LOCK"; then
  echo "✓ $LOCK staged alongside $REQ"
  exit 0
fi

echo "❌ $REQ changed but $LOCK is not staged."
echo "   Regenerate the lock and stage it:"
echo "     pip lock -r $REQ -o $LOCK && git add $LOCK"
exit 1
