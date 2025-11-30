#!/bin/bash
# Spec Kit Post-Edit Hook (Example)
# This script runs after Claude makes file edits
#
# NOTE: This is an EXAMPLE hook. Customize for your project's needs.
#
# To enable this hook, add to settings.json:
# {
#   "hooks": {
#     "PostToolUse": [{
#       "hooks": [{ "command": "./.claude/hooks/post-edit.sh \"$CLAUDE_FILE_PATH\"", "type": "command" }],
#       "matcher": "Edit|Write"
#     }]
#   }
# }

# Exit early if no file path provided
if [ -z "$1" ]; then
    exit 0
fi

FILE_PATH="$1"
EXTENSION="${FILE_PATH##*.}"

# Auto-format based on file type (customize for your project)
case "$EXTENSION" in
    py)
        # Python: Run black/ruff if available
        if command -v ruff &> /dev/null; then
            ruff format "$FILE_PATH" 2>/dev/null || true
        elif command -v black &> /dev/null; then
            black --quiet "$FILE_PATH" 2>/dev/null || true
        fi
        ;;

    js|ts|jsx|tsx)
        # JavaScript/TypeScript: Run prettier if available
        if command -v prettier &> /dev/null; then
            prettier --write "$FILE_PATH" 2>/dev/null || true
        fi
        ;;

    go)
        # Go: Run gofmt
        if command -v gofmt &> /dev/null; then
            gofmt -w "$FILE_PATH" 2>/dev/null || true
        fi
        ;;

    rs)
        # Rust: Run rustfmt
        if command -v rustfmt &> /dev/null; then
            rustfmt "$FILE_PATH" 2>/dev/null || true
        fi
        ;;

    md)
        # Markdown: Could run markdownlint or prettier
        # Disabled by default to avoid changing spec files unexpectedly
        # if command -v prettier &> /dev/null; then
        #     prettier --write "$FILE_PATH" 2>/dev/null || true
        # fi
        ;;
esac

exit 0
