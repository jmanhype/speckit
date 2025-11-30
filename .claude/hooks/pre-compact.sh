#!/bin/bash
# Spec Kit Pre-Compact Hook
# This script runs before Claude Code compacts context
#
# Purpose: Preserve important context in Beads before it's lost
#
# To use this hook instead of the inline command, update settings.json:
# {
#   "hooks": {
#     "PreCompact": [{
#       "hooks": [{ "command": "./.claude/hooks/pre-compact.sh", "type": "command" }],
#       "matcher": ""
#     }]
#   }
# }

set -e

# Prime Beads to ensure context is persisted
if command -v bd &> /dev/null; then
    bd prime 2>/dev/null || true
    echo "[Spec Kit] Beads context preserved before compaction"
fi

exit 0
