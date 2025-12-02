# AGENTS.md - Instructions for AI Coding Agents

This file contains workflow rules and guidelines for AI agents (Claude Code, GitHub Copilot, Cursor, Amp, etc.) working in repositories that use **Spec Kit** + **Beads**.

## Core Philosophy

**Spec Kit** provides structure (WHAT/WHY/HOW).
**Beads** provides memory (persistent task graph that survives context limits).

Together they solve:
- ✅ Structured specification-driven development
- ✅ Long-term memory across sessions
- ✅ Dependency tracking that doesn't disappear
- ✅ Work discovery and prioritization

## Pivotal Methodology Alignment

Spec Kit + Beads implements practices from **Pivotal Labs** (now VMware Tanzu Labs):

| Pivotal Practice | Spec Kit + Beads Implementation |
|-----------------|--------------------------------|
| **TDD** | `test-gate.sh` enforces 100% test pass after every edit |
| **User Stories** | spec.md with P1/P2/P3 priorities, `[US#]` references |
| **Story Types** | Beads: `--type epic/task/bug`, labels for chores |
| **Story States** | Beads: `--status todo/in-progress/done/blocked` |
| **Acceptance Criteria** | spec.md `## Acceptance Criteria` → Beads epic description |
| **IPM (Planning)** | `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` |
| **Velocity** | Beads tracks task completion; `bd ready` shows unblocked work |
| **Dependencies** | `bd dep add` creates blocking relationships (P0 → P1 → P2) |

### Pivotal-Style Epic Format

Beads epics created by Spec Kit include:

```
PROBLEM STATEMENT:
[From spec.md ## Problem Statement]

BUSINESS VALUE:
[From spec.md ## Business Value]

ARCHITECTURAL VISION:
[From plan.md ## Architectural Vision]

INTEGRATION TESTS:
[From spec.md ## Integration Tests]

Acceptance Criteria:
[From spec.md ## Acceptance Criteria]

Blocks (N):
  ← TASK-1: P0 task description
  ← TASK-2: P1 task description
  ...
```

### Priority Levels (Pivotal-Aligned)

| Priority | Pivotal Equivalent | Description |
|----------|-------------------|-------------|
| **P0** | Urgent/Blocker | Critical path, blocks everything else |
| **P1** | High | MVP features, must-have |
| **P2** | Medium | Should-have, important but not blocking |
| **P3** | Low | Nice-to-have, future enhancements |

## Beads + Spec Kit Workflow

### General Rules

You **MUST** treat Beads (`bd` CLI) as the source of truth for all work items.

**DO:**
- ✅ Use Spec Kit for specs, plans, and high-level task structure
- ✅ Use Beads for ALL work items, dependencies, notes, and discoveries
- ✅ Check `bd ready` to find the next task to work on
- ✅ Update both `tasks.md` (checkboxes) AND Beads issues (close/update) when done
- ✅ Search Beads for prior work before creating new features

**DON'T:**
- ❌ Never invent your own TODO markdown files for work tracking
- ❌ Never expand `tasks.md` into a massive backlog (it's an index, not a database)
- ❌ Never lose track of discoveries or blockers (put them in Beads)
- ❌ Never forget context from previous sessions (Beads remembers)

### Before Starting Any Feature

1. **Check if Beads is initialized:**
   ```bash
   if [ ! -d .beads ]; then bd init; fi
   ```

2. **Search for prior work:**
   ```bash
   bd list --status open --json
   bd search <keywords> --json
   ```

3. **Summarize findings** in the spec under "Prior Work from Beads" section:
   ```markdown
   ## Prior Work from Beads

   - (bd-a1b2) OAuth2 integration - 70% complete, blocked by API keys
   - (bd-c9d3) User model tests - completed, ready for review
   ```

### During `/speckit.specify` Phase

After generating `spec.md`:

1. **Pull in Beads context:**
   ```bash
   bd list --label spec:<feature-slug> --json
   ```

2. **Link relevant issues** in the spec:
   ```markdown
   ## Related Beads Issues

   - (bd-a1b2) Previous attempt at this feature
   - (bd-x7y8) Dependency: requires auth system
   ```

### During `/speckit.plan` Phase

After generating `plan.md`:

1. **Create a Pivotal-style epic** using the automated script:
   ```bash
   ./.specify/scripts/bash/create-beads-epic.sh specs/###-feature-name P0
   ```

   This extracts from spec.md and plan.md:
   - Problem Statement
   - Business Value
   - Architectural Vision
   - Integration Tests
   - Acceptance Criteria

   And creates a rich Beads epic with full description.

2. **Epic ID is saved** to `specs/###-feature-name/.beads-epic-id`

3. **Store epic ID in `plan.md`** header:
   ```markdown
   **Beads Epic**: HEX-abc123
   ```

### During `/speckit.tasks` Phase

**CRITICAL:** `tasks.md` is an **INDEX**, not a backlog database.

After `/speckit.tasks` generates `tasks.md`:

1. **Bulk create Beads issues with dependencies:**
   ```bash
   # Get epic ID from plan phase
   EPIC_ID=$(cat specs/###-feature-name/.beads-epic-id)

   # Create all tasks with automatic priority detection and dependencies
   ./.specify/scripts/bash/create-beads-issues.sh specs/###-feature-name/tasks.md $EPIC_ID
   ```

   This script automatically:
   - Detects priority (P0/P1/P2/P3) from task markers or context
   - Creates Beads issues under the epic
   - Sets up dependencies (P0 → P1 → P2 → P3)
   - Labels tasks by user story, backend/frontend, etc.

2. **Link Beads IDs back to tasks.md:**
   ```bash
   ./.specify/scripts/bash/update-tasks-with-beads-ids.sh specs/###-feature-name/tasks.md
   ```

   Transforms:
   ```markdown
   - [ ] T001 [P] [P0] Verify header template contains Team link
   - [ ] T002 [P] [P1] Add GET /api/teams endpoint
   ```

   Into:
   ```markdown
   - [ ] (HEX-x1y2) T001 [P] [P0] Verify header template contains Team link
   - [ ] (HEX-x3y4) T002 [P] [P1] Add GET /api/teams endpoint
   ```

3. **Verify dependencies:**
   ```bash
   bd show $EPIC_ID  # Shows "Blocks (N):" with all child tasks
   bd ready          # Shows only P0 tasks initially (P1/P2/P3 are blocked)
   ```

4. **Keep `tasks.md` lightweight:**
   - Each bullet = one line with Beads ID + title
   - Full details, notes, blockers → live in Beads
   - Safe to load into agent context (small)

### During `/speckit.implement` Phase

**Always drive implementation from Beads:**

1. **Ask Beads what's ready:**
   ```bash
   bd ready --label feat-001 --json
   ```

2. **Pick one issue** (manually or agent-suggested):
   ```
   Next task: (bd-x1y2) T001 Verify header contains Team link
   ```

3. **Implement ONLY that Beads issue:**
   - Read the issue: `bd show bd-x1y2`
   - Implement the code
   - Run tests
   - Update the Beads issue with findings

4. **When done:**

   a. **Update `tasks.md`:**
   ```markdown
   - [X] (bd-x1y2) T001 [P] Verify header template contains Team link
   ```

   b. **Close or update Beads:**
   ```bash
   bd close bd-x1y2

   # OR if you discovered something:
   bd update bd-x1y2 --note "Completed. Found that nav styles need updating too. Created bd-z9z9 to track."
   bd close bd-x1y2
   ```

5. **Repeat** until `bd ready` returns empty.

### Handling Discoveries and Blockers

When you discover new work or blockers during implementation:

**DON'T** expand `tasks.md` with 50 new bullets.

**DO** create Beads issues:

```bash
# Discovery: found a bug
bd create "Fix nav styles conflicting with new header" \
  -t bug \
  -l speckit,feat-001 \
  -d "Discovered while implementing bd-x1y2. Nav z-index conflicts."

# Blocker: missing API key
bd create "Get production API keys for OAuth" \
  -t task \
  -l speckit,feat-001,blocked \
  -d "Blocking bd-c9d3. Need keys from DevOps."

# Link the blocker
bd dep add bd-c9d3 bd-new-blocker --type blocks
```

Then note in the original issue:
```bash
bd update bd-c9d3 --note "Blocked by bd-new-blocker (missing API keys)"
```

### End of Session

Before finishing a work session:

1. **Ensure all work is in Beads:**
   - Discoveries → Beads issues
   - Blockers → Beads issues with `blocked` label
   - Notes → Beads issue updates

2. **Sync `tasks.md` checkboxes** with Beads status:
   ```bash
   # Get Beads state
   bd list --label feat-001 --json

   # Update tasks.md to match
   ```

3. **Leave breadcrumbs for next session:**
   ```bash
   bd update bd-current-work --note "Left off at: implementing auth middleware. Tests passing. Next: add rate limiting."
   ```

4. **Update progress tracking** in `tasks.md`:
   ```markdown
   ## Progress
   - Last session: 2025-01-15 14:30
   - Completed: T001-T005
   - In progress: T006 (rate limiting)
   - Velocity: ~3 tasks/hour
   ```

### Session Resumption

When starting a new session on existing work:

1. **Re-read all artifacts** in order:
   ```
   spec.md → plan.md → tasks.md → Beads (bd ready)
   ```

2. **Check what's ready:**
   ```bash
   bd ready --label feat-XXX --json
   ```

3. **Update session timestamp** in `tasks.md`

4. **Continue from where you left off** - don't restart or re-plan

## Autonomy & Long-Running Tasks

For multi-hour implementations, operate with maximum autonomy:

### Decision-Making

- **Resolve ambiguities autonomously** rather than stopping to ask
- **Proceed through milestones** without prompting for "next steps"
- **Make reasonable technical decisions** aligned with constitution
- **Document decisions** in the relevant artifact

When encountering a decision point:
1. Check `constitution.md` for guidance
2. Review similar patterns in existing code
3. Make the decision and document it
4. Continue working

Only stop to ask when:
- Decision has significant cost/risk implications
- Multiple valid approaches with major trade-offs exist
- Requirement is genuinely ambiguous and blocks all progress

### Multi-Hour Task Handling

For tasks spanning 4+ hours:

1. **Commit frequently** at sub-milestones:
   ```bash
   git commit -m "feat(auth): implement JWT validation [T003] - WIP"
   ```

2. **Update Beads** every 1-2 hours:
   ```bash
   bd update bd-task --note "Progress: middleware skeleton done, adding tests"
   ```

3. **Keep artifacts synchronized** - document discoveries immediately

4. **Don't expand tasks.md** with sub-tasks - use Beads for granular tracking

## Integration Checklist

When setting up a new repository with Spec Kit + Beads:

- [ ] Initialize Beads: `bd init`
- [ ] Install Beads MCP (if using Claude Desktop/Amp): `uv tool install beads-mcp`
- [ ] Add Beads principle to `.specify/memory/constitution.md`
- [ ] Verify `AGENTS.md` exists and is read by your agent
- [ ] Test workflow: create a small feature using Spec Kit, track tasks in Beads

## Agent-Specific Notes

### For Claude Code
- Read this file on startup
- Always use `bd` CLI commands via Bash tool
- Store Beads IDs in `tasks.md` as: `(bd-xxxx)`

### For GitHub Copilot
- Add this file to workspace
- Use shell scripts to interact with `bd`
- Reference Beads IDs in commit messages

### For Cursor
- Include this in `.cursor/` context
- Use terminal integration for `bd` commands
- Link Beads issues in code comments

### For Amp
- Install `beads-mcp` MCP server
- Use MCP tools instead of shell commands
- Configure in Amp settings

## Minimal vs Full Integration

### Lightweight Start (Recommended)

1. Keep existing Spec Kit workflow
2. After `/speckit.tasks`, manually create Beads issues
3. Paste `bd-*` IDs into `tasks.md`
4. Drive implementation from `bd ready`
5. Keep `tasks.md` and Beads in sync

### Full Integration

1. Bake Beads into `AGENTS.md` ✓ (this file)
2. Update `.specify/memory/constitution.md` with Beads principle
3. Modify `.claude/commands/speckit.*.md` to include Beads steps
4. Install `beads-mcp` for MCP-capable agents
5. Automate Beads issue creation in slash commands

## Example Workflow

```bash
# 1. Start new feature
/speckit.specify Add real-time notifications

# 2. Agent searches Beads first
bd search "notifications" --json
# (agent summarizes in spec.md if relevant)

# 3. Create plan
/speckit.plan

# 4. Agent creates Beads epics
bd create "[FEAT-002] Backend notification system" -t epic -l speckit,feat-002
bd create "[FEAT-002] Frontend notification UI" -t epic -l speckit,feat-002

# 5. Generate tasks
/speckit.tasks

# 6. Agent creates Beads task issues
bd create "[T010] Create Notification model" -t task --parent bd-epic-1 -l speckit,feat-002
bd create "[T011] Add WebSocket endpoint" -t task --parent bd-epic-1 -l speckit,feat-002
# ... etc

# 7. Agent updates tasks.md with Beads IDs
# - [ ] (bd-t1) T010 [P] Create Notification model
# - [ ] (bd-t2) T011 [P] Add WebSocket endpoint

# 8. Implement
bd ready --label feat-002 --json
# Agent picks bd-t1, implements, closes, repeats
```

## Common Patterns

### Pattern: Feature Branch + Beads Label

```bash
# Create feature branch
git checkout -b 003-notifications

# Label all Beads work for this feature
bd create "..." -l speckit,feat-003
```

### Pattern: Epic → Tasks → Subtasks

```bash
# Epic for whole phase
bd create "Phase 1: Backend" -t epic -l feat-001

# Tasks under epic
bd create "Create models" -t task --parent bd-epic --l feat-001
bd create "Create API" -t task --parent bd-epic -l feat-001

# Subtasks for complex work
bd create "Add User model" -t task --parent bd-models-task -l feat-001
bd create "Add Post model" -t task --parent bd-models-task -l feat-001
```

### Pattern: Discovery → Issue → Dependency

```bash
# Working on bd-task-1, discover a problem
bd create "Fix auth token expiry bug" -t bug -l feat-001
bd dep add bd-task-1 bd-new-bug --type blocks
bd update bd-task-1 --note "Blocked by bd-new-bug. Switching context."

# Work on something else
bd ready --label feat-001 --json
```

## Philosophy: Why This Works

**Spec Kit** gives you:
- Clear intent (spec.md)
- Technical plan (plan.md)
- Task structure (tasks.md)
- Quality gates (checklists)

**Beads** gives you:
- Persistent memory across sessions
- Dependency graph that agents can traverse
- Discovery tracking (new work found during implementation)
- Context that survives "compaction" (when conversation is too long)

**Together:** You get spec-driven development with a memory that doesn't forget.

## Troubleshooting

### Beads Issues Not Showing in `bd ready`

Check:
1. Issue status: `bd list --label feat-XXX --json`
2. Dependencies: `bd deps bd-issue-id`
3. Labels: ensure `feat-XXX` label is applied

### `tasks.md` and Beads Out of Sync

Run audit:
```bash
# List all open Beads tasks
bd list --label feat-XXX --status open --json

# Compare to tasks.md checkboxes
# Update tasks.md or close Beads issues to match
```

### Lost Context After Session

Search Beads:
```bash
bd search "keywords from last session" --json
bd list --label feat-XXX --updated-since "2 days ago" --json
```

## Resources

- **Beads Documentation**: https://github.com/steveyegge/beads
- **Beads MCP**: https://pypi.org/project/beads-mcp/
- **Spec Kit Documentation**: https://github.com/YOUR_USERNAME/speckit
- **Steve Yegge's Intro to Beads**: https://steve-yegge.medium.com/introducing-beads-a-coding-agent-memory-system-637d7d92514a

---

**Remember:** Specs are structure. Beads is memory. Use both.
