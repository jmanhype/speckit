#!/bin/bash
# Spec Kit Session Start Hook
# This script runs when a Claude Code session begins
#
# To use this hook instead of the inline command, update settings.json:
# {
#   "hooks": {
#     "SessionStart": [{
#       "hooks": [{ "command": "./.claude/hooks/session-start.sh", "type": "command" }],
#       "matcher": ""
#     }]
#   }
# }

set -e

# Colors for output (will show in Claude Code logs)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Prime Beads if available
if command -v bd &> /dev/null; then
    bd prime 2>/dev/null || true
    echo -e "${GREEN}[Spec Kit]${NC} Beads context loaded"
else
    echo -e "${YELLOW}[Spec Kit]${NC} Beads not installed (optional)"
fi

# 2. Show current feature status if in a Spec Kit project
if [ -d ".specify" ]; then
    # Find the most recent feature directory
    if [ -d "specs" ]; then
        current_feature=$(ls -td specs/*/ 2>/dev/null | head -1)

        if [ -n "$current_feature" ] && [ -d "$current_feature" ]; then
            feature_name=$(basename "$current_feature")
            echo -e "${BLUE}[Spec Kit]${NC} Current feature: $feature_name"

            # Check which artifacts exist
            artifacts=""
            [ -f "${current_feature}spec.md" ] && artifacts="${artifacts}spec "
            [ -f "${current_feature}plan.md" ] && artifacts="${artifacts}plan "
            [ -f "${current_feature}tasks.md" ] && artifacts="${artifacts}tasks "

            if [ -n "$artifacts" ]; then
                echo -e "${BLUE}[Spec Kit]${NC} Artifacts: $artifacts"
            fi

            # Show task progress if tasks.md exists
            if [ -f "${current_feature}tasks.md" ]; then
                total=$(grep -c "^\s*- \[" "${current_feature}tasks.md" 2>/dev/null || echo "0")
                done=$(grep -c "^\s*- \[x\]" "${current_feature}tasks.md" 2>/dev/null || echo "0")

                if [ "$total" -gt 0 ]; then
                    percent=$((done * 100 / total))
                    echo -e "${BLUE}[Spec Kit]${NC} Progress: $done/$total tasks ($percent%)"
                fi
            fi
        fi
    else
        echo -e "${YELLOW}[Spec Kit]${NC} No features yet. Run /speckit.specify to start"
    fi
fi

exit 0
