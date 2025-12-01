#!/bin/bash
# Spec Kit Phase Gate Hook
# Enforces test gates at workflow phase transitions
#
# USAGE:
# ./.claude/hooks/phase-gate.sh <from_phase> <to_phase>
#
# PHASES: specify → clarify → plan → checklist → tasks → analyze → implement
#
# BEHAVIOR:
# - Runs full test suite before phase transitions
# - Requires 100% pass rate and coverage
# - Blocks phase transition if gates fail
#
# This script is called by workflow commands before transitioning phases.

set -e

FROM_PHASE="${1:-unknown}"
TO_PHASE="${2:-unknown}"

# Configuration
COVERAGE_THRESHOLD="${SPECKIT_COVERAGE_THRESHOLD:-100}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚦 PHASE GATE: ${FROM_PHASE} → ${TO_PHASE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Define which phases require test gates
requires_test_gate() {
    local phase="$1"
    case "$phase" in
        implement|analyze)
            return 0  # These phases require test gates
            ;;
        *)
            return 1  # Other phases don't require test gates
            ;;
    esac
}

# Define which phases require full test suite (not just affected tests)
requires_full_suite() {
    local from="$1"
    local to="$2"

    # Full suite required when entering or completing implementation
    case "$to" in
        implement)
            return 0
            ;;
    esac

    # Full suite required when completing implementation (tasks → done)
    if [ "$from" = "implement" ]; then
        return 0
    fi

    return 1
}

# Check if this transition requires a test gate
if ! requires_test_gate "$TO_PHASE"; then
    echo "✅ Phase transition ${FROM_PHASE} → ${TO_PHASE} does not require test gate"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
fi

# Check if we need full test suite
if requires_full_suite "$FROM_PHASE" "$TO_PHASE"; then
    echo "🔬 Running FULL test suite before phase transition..."
    echo ""

    # Delegate to test-gate.sh which handles all test types
    if ./.claude/hooks/test-gate.sh "force-run"; then
        echo ""
        echo "✅ PHASE GATE PASSED: Ready to transition to ${TO_PHASE}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 0
    else
        echo ""
        echo "❌ PHASE GATE FAILED: Cannot transition to ${TO_PHASE}"
        echo ""
        echo "Fix all failing tests and ensure 100% coverage before proceeding."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 1
    fi
else
    echo "✅ Phase transition ${FROM_PHASE} → ${TO_PHASE} passed (no full suite required)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
fi
