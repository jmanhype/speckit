#!/bin/bash
#
# create-beads-issues.sh - Bulk create Beads issues from tasks.md
#
# DESCRIPTION:
#   Workaround for bd create --file segfault bug.
#   Extracts tasks from tasks.md and creates Beads issues individually.
#
# USAGE:
#   ./create-beads-issues.sh <path-to-tasks.md> <epic-id>
#
# EXAMPLE:
#   ./create-beads-issues.sh specs/001-my-feature/tasks.md speckit-abc123
#
# REQUIREMENTS:
#   - bd CLI installed and initialized
#   - tasks.md in standard format: - [ ] T001 Description...
#
# OUTPUT:
#   - Creates one Beads issue per task
#   - Prints Beads ID → Task ID mapping for update script
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1" >&2; }

# Check arguments
if [ $# -lt 2 ]; then
    log_error "Usage: $0 <path-to-tasks.md> <epic-id>"
    log_error "Example: $0 specs/001-my-feature/tasks.md speckit-abc123"
    exit 1
fi

TASKS_FILE="$1"
EPIC_ID="$2"

# Validate inputs
if [ ! -f "$TASKS_FILE" ]; then
    log_error "Tasks file not found: $TASKS_FILE"
    exit 1
fi

if ! command -v bd &> /dev/null; then
    log_error "bd CLI not found. Install Beads first: https://github.com/steveyegge/beads"
    exit 1
fi

# Check if epic exists
if ! bd show "$EPIC_ID" &> /dev/null; then
    log_error "Epic not found: $EPIC_ID"
    log_error "Create epic first: bd create \"Feature Name\" --type epic"
    exit 1
fi

log_info "Creating Beads issues from $TASKS_FILE for epic $EPIC_ID"
log_info "Extracting tasks without existing Beads IDs..."

# Count tasks to process
TASK_COUNT=$(grep "^- \[ \] T" "$TASKS_FILE" | grep -v "speckit-mw9\|bd-" | wc -l | tr -d ' ')

if [ "$TASK_COUNT" -eq 0 ]; then
    log_warning "No tasks found without Beads IDs"
    log_info "All tasks already have Beads IDs linked"
    exit 0
fi

log_info "Found $TASK_COUNT tasks to create"
echo ""

CREATED=0
FAILED=0

# Extract tasks without Beads IDs and create issues
grep "^- \[ \] T" "$TASKS_FILE" | \
  grep -v "speckit-mw9\|bd-" | \
  while IFS= read -r line; do
    # Extract task ID and description
    task_id=$(echo "$line" | sed 's/^- \[ \] \([^ ]*\).*/\1/')

    # Extract full description (everything after task ID)
    description=$(echo "$line" | sed 's/^- \[ \] [^ ]* //')

    # Determine priority based on markers or task number
    if echo "$line" | grep -q "\[P1\]"; then
      priority="P1"
    elif echo "$line" | grep -q "\[P2\]"; then
      priority="P2"
    elif echo "$line" | grep -q "\[P3\]"; then
      priority="P3"
    else
      # Default to P1 for MVP tasks (T001-T099), P2 for others
      task_num=$(echo "$task_id" | sed 's/T0*//')
      if [ "$task_num" -le 99 ] 2>/dev/null; then
        priority="P1"
      else
        priority="P2"
      fi
    fi

    # Determine labels from description
    labels="task"
    echo "$description" | grep -q "\[P\]" && labels="$labels,parallel"
    echo "$description" | grep -q "backend" && labels="$labels,backend"
    echo "$description" | grep -q "frontend" && labels="$labels,frontend"
    echo "$description" | grep -q "testing\|tests" && labels="$labels,testing"
    echo "$description" | grep -q "TDD\|must fail" && labels="$labels,tdd"
    echo "$description" | grep -qi "US1" && labels="$labels,us1"
    echo "$description" | grep -qi "US2" && labels="$labels,us2"
    echo "$description" | grep -qi "US3" && labels="$labels,us3"
    echo "$description" | grep -qi "US4" && labels="$labels,us4"
    echo "$description" | grep -qi "US5" && labels="$labels,us5"
    echo "$description" | grep -qi "US6" && labels="$labels,us6"

    # Create the Beads issue
    echo -n "Creating $task_id... "

    if beads_id=$(bd create "$task_id: $description" \
      --parent "$EPIC_ID" \
      --type task \
      --priority "$priority" \
      --labels "$labels" \
      --quiet 2>&1 | grep -o '[a-z0-9-]*\.[0-9]*$'); then

      echo -e "${GREEN}✓${NC} $beads_id"
      echo "$task_id → $beads_id" >> /tmp/beads-mapping.txt
      CREATED=$((CREATED + 1))

      # Small delay to avoid overwhelming the system
      sleep 0.1
    else
      echo -e "${RED}✗${NC} Failed"
      FAILED=$((FAILED + 1))
    fi
  done

# Wait for any background processes
wait

echo ""
log_success "Bulk import complete!"
log_info "Created: $CREATED issues"

if [ "$FAILED" -gt 0 ]; then
    log_warning "Failed: $FAILED issues"
fi

# Check if mapping file was created
if [ -f /tmp/beads-mapping.txt ]; then
    log_info "Mapping saved to /tmp/beads-mapping.txt"
    echo ""
    log_info "Next step: Update tasks.md with Beads IDs"
    log_info "Run: .specify/scripts/bash/update-tasks-with-beads-ids.sh $TASKS_FILE"
else
    log_warning "No mapping file created (no issues created)"
fi

exit 0
