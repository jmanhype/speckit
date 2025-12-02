# Spec Kit - Specification-Driven Development with Beads Integration

**Spec Kit** is a comprehensive workflow system that guides software features from conception through implementation using a structured, specification-driven approach.

## Overview

Spec Kit enforces a rigorous development workflow that separates concerns and ensures quality at each phase:

```
constitution → specify → clarify → plan → checklist → tasks → analyze → implement
```

### The Killer Combo: Spec Kit + Beads 💎

**Spec Kit** provides structure (WHAT/WHY/HOW).
**Beads** provides memory (persistent task graph that survives context limits).

| Tool | What It Does | Integration Point |
|------|--------------|------------------|
| **Spec Kit** | Specs, plans, and task structure | `specs/*/spec.md`, `plan.md`, `tasks.md` |
| **Beads** | Living memory, task graph, discoveries | `.beads/` JSONL + SQLite database |

Together they solve:
- ✅ Structured specification-driven development
- ✅ Long-term memory across sessions
- ✅ Dependency tracking that doesn't disappear
- ✅ Work discovery and prioritization

**`tasks.md` becomes an index** pointing to Beads issues, not a massive backlog.
**Beads stores the actual work** with dependencies, notes, and discoveries.

See **[AGENTS.md](AGENTS.md)** for full Beads + Spec Kit workflow.

### Key Principles

- **Specification-first**: Define WHAT and WHY before HOW
- **Technology-agnostic specs**: Keep implementation details out of specifications
- **Quality gates**: Validate completeness and consistency at each phase
- **Executable tasks**: Generate dependency-ordered, testable task lists
- **User story prioritization**: Enable incremental delivery and independent testing
- **Beads integration**: Persistent memory layer for long-running work and discoveries

### Pivotal Labs Methodology

Spec Kit + Beads implements practices from **Pivotal Labs** (VMware Tanzu Labs):

| Pivotal Practice | Spec Kit Implementation |
|-----------------|------------------------|
| **TDD** | `test-gate.sh` enforces 100% test pass after edits |
| **User Stories** | spec.md with P0/P1/P2/P3 priorities |
| **Story Types** | Beads `--type epic/task/bug` |
| **Story States** | Beads `--status todo/in-progress/done` |
| **Acceptance Criteria** | spec.md sections → Beads epic description |
| **IPM (Planning)** | `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` |
| **Velocity** | `bd ready` shows unblocked work |
| **Dependencies** | Automatic P0 → P1 → P2 → P3 blocking |

**New in this version:**
- `create-beads-epic.sh` - Creates Pivotal-style epics with Problem Statement, Business Value, Architectural Vision
- `create-beads-issues.sh` - Bulk imports tasks with automatic dependency setup
- Templates include Pivotal-aligned sections (Problem Statement, Business Value, etc.)

## Installation

### Prerequisites

- **Claude Code** (claude.ai/code) - Spec Kit is designed to work with Claude Code's slash command system
- **Git** (recommended but optional)
- **Bash** (for automation scripts)
- **Docker** (required) - For running CI locally via act
- **act** (required) - [nektos/act](https://github.com/nektos/act) for local GitHub Actions
- **Beads CLI** (optional but recommended) - For persistent task memory

#### Installing act

```bash
# macOS
brew install act

# Linux (via script)
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Or download from GitHub releases
# https://github.com/nektos/act/releases
```

### Quick Start (Spec Kit Only)

1. **Clone or download this repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/speckit.git .speckit-framework
   ```

2. **Copy Spec Kit into your project**:
   ```bash
   cd your-project
   cp -r ../speckit-framework/.specify ./
   cp -r ../speckit-framework/.claude ./
   chmod +x ./.claude/hooks/*.sh  # Make hooks executable
   ```

3. **Add CLAUDE.md to your project root** (see Setup section below)

4. **Initialize your first feature**:
   ```bash
   # In Claude Code
   /speckit.specify Add user authentication with email/password
   ```

### Full Setup (Spec Kit + Beads)

For the complete experience with persistent memory:

1. **Install Beads CLI**:
   ```bash
   # Homebrew (macOS/Linux)
   brew tap steveyegge/beads
   brew install bd

   # Or install script
   curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
   ```

2. **Install Spec Kit**:
   ```bash
   cd your-project

   # Copy framework files
   cp -r /path/to/speckit/.specify ./
   cp -r /path/to/speckit/.claude ./
   cp /path/to/speckit/AGENTS.md ./

   # Make hook scripts executable
   chmod +x ./.claude/hooks/*.sh
   ```

3. **Initialize Beads**:
   ```bash
   bd init
   bd doctor  # Optional: verify setup
   ```

4. **(Optional) Install Beads MCP** for Claude Desktop/Amp:
   ```bash
   uv tool install beads-mcp
   # Then configure in your agent's MCP settings
   ```

5. **Start your first feature**:
   ```bash
   # In Claude Code
   /speckit.specify Add user authentication

   # Agent will automatically integrate with Beads
   ```

### Linear Integration Setup

To use Spec Kit with your Linear backlog:

1. **Get Linear API Key**:
   - Go to `linear.app/YOUR-TEAM/settings/api`
   - Create a new API key with appropriate permissions

2. **Configure Linear MCP Server**:

   **Option A: Use the official Linear MCP (OAuth)**:
   ```json
   // In .claude/settings.local.json
   {
     "mcpServers": {
       "linear": {
         "url": "https://mcp.linear.app/sse",
         "transport": "sse"
       }
     }
   }
   ```

   **Option B: Use community package (API Key)**:
   ```bash
   # Copy the example config
   cp .mcp.json.linear-example .mcp.json

   # Set your API key
   export LINEAR_API_KEY=lin_api_xxx
   ```

3. **Enable project MCP servers** in `.claude/settings.json`:
   ```json
   {
     "enableAllProjectMcpServers": true
   }
   ```

4. **Test the integration**:
   ```bash
   # In Claude Code
   /speckit.linear.import TEAM-123
   ```

#### Linear Workflow

```bash
# 1. Import from Linear backlog
/speckit.linear.import TEAM-123

# 2. Run normal Spec Kit workflow
/speckit.clarify
/speckit.plan
/speckit.tasks

# 3. Export tasks back to Linear as sub-issues
/speckit.linear.export

# 4. Implement with bidirectional sync
/speckit.implement
/speckit.linear.sync --bidirectional
```

### Brownfield Repos (Existing Projects)

For projects with existing code, tests, and conventions:

#### 1. Install Spec Kit (same as above)

```bash
cd your-existing-project

# Copy framework files
cp -r /path/to/speckit/.specify ./
cp -r /path/to/speckit/.claude ./
chmod +x ./.claude/hooks/*.sh
```

#### 2. Bootstrap Your Constitution

The constitution captures your project's existing decisions and constraints:

```bash
# In Claude Code
/speckit.constitution
```

**Answer these prompts based on your existing codebase:**
- What tech stack is already in use? (languages, frameworks, databases)
- What testing patterns exist? (Jest, pytest, existing test commands)
- What architectural patterns are established? (MVC, Clean Architecture, etc.)
- What CI/CD pipeline is in place?
- What coding standards are enforced? (linters, formatters, style guides)

The constitution will be created at `.specify/memory/constitution.md`.

#### 3. Document Existing Test Commands

Update your constitution or `CLAUDE.md` with your actual test commands:

```markdown
## Existing Test Infrastructure

**Run tests:**
- Unit: `npm test` or `pytest tests/unit/`
- Integration: `npm run test:integration` or `pytest tests/integration/`
- All: `npm run test:all` or `pytest`

**Coverage:** `npm run coverage` or `pytest --cov`
```

#### 4. Start with One Feature

Don't try to spec your entire codebase. Pick ONE new feature:

```bash
# In Claude Code
/speckit.specify Add password reset functionality
```

Spec Kit will:
- Respect your existing code structure
- Use your established patterns (from constitution)
- Ensure 100% test pass rate (including existing tests)
- Generate tasks that fit your project

#### 5. Key Brownfield Considerations

| Concern | How Spec Kit Handles It |
|---------|------------------------|
| **Existing tests** | 100% pass gate includes ALL existing tests (no regressions) |
| **Existing patterns** | Constitution captures them; plan references them |
| **Existing CI/CD** | Hook into existing pipelines; don't replace |
| **Incremental adoption** | One feature at a time; no big bang |
| **Legacy code** | Specs can include "refactor" user stories |

#### 6. Example: Adding Feature to Django Project

```bash
# 1. Install Spec Kit
cp -r /path/to/speckit/.specify ./
cp -r /path/to/speckit/.claude ./
chmod +x ./.claude/hooks/*.sh

# 2. Bootstrap constitution (capture Django conventions)
# /speckit.constitution → answers: Django 4.2, pytest-django, REST framework, etc.

# 3. Specify new feature
# /speckit.specify Add user notification preferences API

# 4. Plan respects Django conventions
# → Uses existing models.py, serializers.py, views.py patterns
# → Tests go in existing tests/ structure
# → Migrations use existing Alembic/Django setup

# 5. Implement with test gate
# Every task runs `pytest` → must pass 100%
# Existing tests + new tests all green
```

#### 7. Gradual Constitution Evolution

As you add features, your constitution grows:

```markdown
## Recent Decisions (append as you go)

### 2025-01 Password Reset
- Using SendGrid for transactional email (not SES)
- Reset tokens expire in 1 hour
- Rate limited to 3 requests per hour per email

### 2025-02 Notifications
- WebSocket for real-time (not polling)
- Fallback to email for offline users
```

This creates institutional memory that persists across sessions.

## Directory Structure

```
your-project/
├── .beads/                    # Beads task database (if using Beads)
│   ├── issues.jsonl           # Issue storage
│   └── beads.db               # SQLite cache
├── .claude/
│   ├── settings.json          # Project settings (hooks, permissions, env)
│   ├── settings.local.json    # Local overrides (gitignored)
│   ├── README.md              # Configuration documentation
│   ├── commands/              # Slash commands (user-invoked)
│   │   ├── speckit.*.md       # Spec Kit workflow commands
│   │   └── _example-command.md
│   ├── skills/                # Model-invoked skills (auto-triggered)
│   │   ├── beads-integration/ # Persistent memory
│   │   ├── spec-kit-workflow/ # Workflow guidance
│   │   └── spec-validation/   # Quality validation
│   ├── agents/                # Custom AI subagents
│   │   ├── spec-validator.md
│   │   ├── consistency-checker.md
│   │   └── beads-sync.md
│   └── hooks/                 # External hook scripts
│       ├── session-start.sh   # Session initialization
│       ├── pre-compact.sh     # Pre-compaction tasks
│       └── post-edit.sh       # Post-edit automation
├── .mcp.json                  # Project-scoped MCP servers (optional)
├── .specify/
│   ├── memory/
│   │   └── constitution.md    # Project architectural principles
│   ├── scripts/bash/          # Workflow automation
│   │   ├── common.sh
│   │   ├── check-prerequisites.sh
│   │   ├── create-new-feature.sh
│   │   ├── setup-plan.sh
│   │   ├── update-agent-context.sh
│   │   ├── create-beads-issues.sh        # Bulk import tasks to Beads
│   │   ├── update-tasks-with-beads-ids.sh  # Link Beads IDs
│   │   ├── pre-push-ci.sh                # Run CI locally before push
│   │   └── install-hooks.sh              # Install git hooks
│   └── templates/             # Document templates
│       ├── spec-template.md
│       ├── plan-template.md
│       ├── tasks-template.md
│       ├── checklist-template.md
│       └── agent-file-template.md
├── specs/                     # Created per feature
│   └── [###-feature-name]/
│       ├── spec.md            # User-focused specification (WHAT/WHY)
│       ├── plan.md            # Technical implementation plan (HOW)
│       ├── tasks.md           # Executable task list (with Beads IDs)
│       └── checklists/        # Quality validation checklists
├── AGENTS.md                  # Instructions for AI agents (Beads workflow)
└── CLAUDE.md                  # Instructions for Claude Code
```

## Extensibility

Spec Kit provides three extension mechanisms for Claude Code. See [.claude/README.md](.claude/README.md) for full documentation.

### Skills (Model-Invoked)

Skills in `.claude/skills/` are automatically activated by Claude based on conversation context - no user action required.

| Skill | Auto-Triggered When... |
|-------|------------------------|
| `spec-kit-workflow` | Discussing features, specs, or planning |
| `beads-integration` | Working on tasks or multi-session projects |
| `spec-validation` | Creating or reviewing specifications |

### Agents (Subagents)

Agents in `.claude/agents/` are specialized AI subagents invoked via the Task tool for focused sub-tasks.

| Agent | Purpose |
|-------|---------|
| `spec-validator` | Validates spec quality and technology-agnosticism |
| `consistency-checker` | Cross-artifact validation (spec ↔ plan ↔ tasks) |
| `beads-sync` | Synchronizes tasks.md with Beads |

### Hooks (Automation)

Hooks in `.claude/hooks/` run at Claude Code lifecycle events:

| Hook | When It Fires |
|------|---------------|
| `session-start.sh` | Session begins (primes Beads) |
| `pre-compact.sh` | Before context compaction |
| `post-edit.sh` | After file edits (example for auto-formatting) |

## Workflow Commands

### Core Workflow

All commands are executed as slash commands in Claude Code:

#### 1. `/speckit.specify <feature description>`
Creates a new feature specification from natural language description.

**What it does**:
- Generates a concise short-name (2-4 words)
- Creates feature branch `###-short-name`
- Initializes `specs/###-short-name/spec.md`
- Runs quality validation
- Identifies clarification needs (max 3 questions)

**Example**:
```
/speckit.specify Add user authentication with email/password and OAuth2 support
```

#### 2. `/speckit.clarify`
Resolves ambiguities in the specification through targeted questions.

**What it does**:
- Analyzes spec for unclear requirements
- Asks maximum 3 high-impact questions
- Updates spec with clarified answers
- Re-validates specification quality

#### 3. `/speckit.plan`
Creates a technical implementation plan.

**What it does**:
- Defines architecture and tech stack
- Specifies file structure and dependencies
- Documents technical decisions
- Creates `plan.md` with HOW details

#### 4. `/speckit.checklist`
Generates domain-specific quality checklists.

**What it does**:
- Creates validation checklists (security, accessibility, performance, etc.)
- Identifies domain-specific requirements
- Documents compliance needs
- Validates against best practices

#### 5. `/speckit.tasks`
Generates executable, dependency-ordered task list.

**What it does**:
- Breaks plan into atomic tasks
- Organizes by user story priority (P1, P2, P3)
- Marks parallelizable tasks with `[P]`
- Creates `tasks.md` with task IDs and file paths

**Task format**: `- [ ] [T###] [P] [US#] Description with path/to/file.ext`

#### 6. `/speckit.analyze`
Performs cross-artifact consistency analysis.

**What it does**:
- Validates alignment between spec.md, plan.md, and tasks.md
- Identifies gaps and inconsistencies
- Ensures all requirements have tasks
- Checks for scope creep

#### 7. `/speckit.implement`
Executes implementation following tasks.md.

**What it does**:
- Follows task order and dependencies
- Implements code according to plan
- Marks tasks as complete `[X]`
- Runs tests for each task

### Orchestration Commands

#### `/speckit-workflow-v2 <feature brief> [options]`
Runs the complete workflow with all quality gates.

**Options**:
- `--domains 'security,accessibility,performance'` - Specify checklist domains
- `--strict` - Halt on validation failures
- `--auto` - Skip confirmations
- `--parallel` - Run independent tasks concurrently

**Example**:
```
/speckit-workflow-v2 Add payment processing with Stripe --domains 'security,pci-compliance' --strict
```

#### `/speckit-orchestrate <feature brief> [options]`
Quick workflow without all quality gates (specify → plan → tasks → implement).

**Options**:
- `--meta` - Run TCHES metaprompt first
- `--parallel` - Parallel task execution

### Utility Commands

#### `/speckit.constitution`
Create or update project constitution (architectural principles).

#### `/speckit.taskstoissues`
Convert tasks.md into GitHub issues with dependencies.

### Linear Integration Commands

#### `/speckit.linear.import <issue-id>`
Import a Linear issue as a new Spec Kit feature specification.

**What it does**:
- Fetches issue from Linear via MCP
- Creates feature directory and spec.md
- Maps Linear fields to spec sections
- Adds bidirectional link (comment on Linear issue)

**Example**:
```
/speckit.linear.import TEAM-123
```

#### `/speckit.linear.export [issue-id]`
Export tasks.md as Linear sub-issues linked to a parent issue.

**What it does**:
- Parses tasks.md and creates Linear sub-issues
- Sets priority, labels, and parent relationship
- Creates `.specify/linear-mapping.json` for tracking
- Updates tasks.md with Linear IDs

**Example**:
```
/speckit.linear.export TEAM-123
```

#### `/speckit.linear.sync [options]`
Synchronize status between tasks.md and Linear issues.

**Options**:
- `--to-linear` - Push local status to Linear (default)
- `--from-linear` - Pull Linear status to local
- `--bidirectional` - Two-way sync (Linear wins conflicts)
- `--dry-run` - Show changes without applying

**Example**:
```
/speckit.linear.sync --bidirectional
```

## Setup

### 1. Create CLAUDE.md

Add this file to your project root to enable Spec Kit commands:

```markdown
# CLAUDE.md

This repository uses the **Spec Kit Workflow System** for specification-driven development.

## Workflow

Features follow this workflow:
constitution → specify → clarify → plan → checklist → tasks → analyze → implement

See `.specify/templates/` for document templates.

## Commands

- `/speckit.specify <description>` - Create feature spec
- `/speckit.clarify` - Resolve ambiguities
- `/speckit.plan` - Create technical plan
- `/speckit.checklist` - Generate quality checklists
- `/speckit.tasks` - Generate executable tasks
- `/speckit.analyze` - Validate consistency
- `/speckit.implement` - Execute implementation
- `/speckit-workflow-v2 <brief> [options]` - Run full workflow

## Branch Naming

Feature branches: `###-short-name` (e.g., `001-user-auth`, `002-payment-integration`)

## Spec Directories

Features are organized in `specs/###-feature-name/`:
- `spec.md` - User-focused specification (WHAT/WHY)
- `plan.md` - Technical plan (HOW)
- `tasks.md` - Executable task list
- `checklists/` - Quality validation

See [Spec Kit Documentation](link-to-your-speckit-repo) for full details.
```

### 2. Customize Constitution

Edit `.specify/memory/constitution.md` to define your project's architectural principles:

```markdown
# Project Constitution

## Core Principles

1. **Test-Driven Development**: Write tests before implementation
2. **API-First Design**: Define contracts before implementation
3. **Immutable Infrastructure**: Infrastructure as code
4. **Zero Trust Security**: Verify every request

## Technology Constraints

- Language: Python 3.11+
- Framework: FastAPI
- Database: PostgreSQL 15+
- Testing: pytest with 90%+ coverage

## Quality Standards

- All features must have specifications
- All code must have tests
- All APIs must have contracts
- All deployments must be automated
```

### 3. Customize Templates

Modify templates in `.specify/templates/` to match your project's needs:

- `spec-template.md` - Specification structure
- `plan-template.md` - Technical plan structure
- `tasks-template.md` - Task list format
- `checklist-template.md` - Quality checklist format

## Usage Examples

### Example 1: Create a New Feature

```bash
# Start specification
/speckit.specify Add user profile management with avatar upload and bio editing

# Review generated spec, clarify if needed
/speckit.clarify

# Create technical plan
/speckit.plan

# Generate tasks
/speckit.tasks

# Validate consistency (IMPORTANT: Always run before implementing!)
/speckit.analyze

# Implement
/speckit.implement
```

### Example 2: Full Workflow with Quality Gates

```bash
/speckit-workflow-v2 Add real-time chat with WebSockets --domains 'security,accessibility,performance' --strict
```

### Example 3: Check Prerequisites

```bash
# In your terminal
./.specify/scripts/bash/check-prerequisites.sh --json

# Get just the paths
eval $(./.specify/scripts/bash/check-prerequisites.sh --paths-only)
echo $FEATURE_DIR  # prints: specs/001-user-auth
```

### Example 4: Beads Integration Workflow

For long-running projects with persistent task memory:

```bash
# 1. Initialize Beads (one-time setup)
bd init
bd doctor  # Verify setup

# 2. Create feature and generate tasks
/speckit.specify Add payment processing with Stripe
/speckit.plan
/speckit.tasks
/speckit.analyze  # Validate before creating Beads issues

# 3. Create epic for this feature
bd create "Payment Processing" --type epic --priority P1
# Note the epic ID, e.g., speckit-abc123

# 4. Bulk import tasks to Beads
./.specify/scripts/bash/create-beads-issues.sh specs/001-payment-processing/tasks.md speckit-abc123

# 5. Link Beads IDs back to tasks.md
./.specify/scripts/bash/update-tasks-with-beads-ids.sh specs/001-payment-processing/tasks.md

# 6. Drive implementation from Beads
bd ready                              # Show tasks ready to work on
bd update speckit-abc123.1 --status in-progress
# ... implement the task ...
bd update speckit-abc123.1 --status done

# 7. Continue with next ready task
bd ready
```

**Why Beads?** Provides persistent memory across sessions, survives context limits, and enables long-running AI-assisted projects.

## Task Organization

Tasks are organized by **user story priority** for independent implementation:

```markdown
## Phase 3: User Stories

### P1 - Core Authentication (MVP)
- [ ] [T010] [P] [US1] Create User model in src/models/user.py
- [ ] [T011] [P] [US1] Create AuthService in src/services/auth.py
- [ ] [T012] [US1] Implement login endpoint in src/api/auth.py

### P2 - Social Login
- [ ] [T020] [P] [US2] Add OAuth2 provider in src/services/oauth.py
- [ ] [T021] [US2] Create social login endpoint in src/api/auth.py

### P3 - Advanced Features
- [ ] [T030] [P] [US3] Add 2FA support in src/services/mfa.py
```

**Task Format**:
- `[T###]` - Unique task ID
- `[P]` - Parallelizable (can run concurrently)
- `[US#]` - User story reference
- File path included for clarity

## Quality Gates

### Specification Quality
- Technology-agnostic (no frameworks, languages, or tools)
- Testable and unambiguous requirements
- Measurable success criteria
- Clear user scenarios

### Test Pass Gate (MANDATORY)

**100% of all tests must pass** at every level:

| Level | Tests Required | Pass Rate |
|-------|---------------|-----------|
| Task | Unit tests | 100% |
| User Story | Integration tests | 100% |
| Feature | Smoke tests | 100% |

**Rules:**
- A task is NOT complete if any test fails
- A story is NOT complete if integration tests fail
- A feature is NOT shippable if smoke tests fail
- No regressions allowed (existing tests must keep passing)

#### Automated Enforcement

Spec Kit provides three layers of automated test enforcement:

**1. Post-Edit Hook** (runs after every file edit):
```bash
# Already configured in settings.json
# Runs: .claude/hooks/test-gate.sh after Edit|Write|MultiEdit
# Result: Claude sees test failures immediately
```

**2. Pre-Commit Hook** (blocks commits with failing tests):
```bash
# Install the hook
cp .specify/templates/pre-commit-hook.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Now: git commit will fail if tests fail
```

**3. Pre-Push Hook** (runs full CI locally before push):
```bash
# Install the hook
./.specify/scripts/bash/install-hooks.sh

# Now: git push will run act to verify CI passes locally
# Bypass (emergency): SPECKIT_SKIP_CI=1 git push
```

**4. GitHub Actions** (blocks PRs with failing tests):
```bash
# Copy workflow template
mkdir -p .github/workflows
cp .specify/templates/github-workflows/test-gate.yml .github/workflows/

# Edit to uncomment your language section (Python, Node, Go, etc.)
```

| Layer | When It Runs | What It Blocks |
|-------|-------------|----------------|
| Post-Edit Hook | After Claude edits code | Nothing (advisory) |
| Pre-Commit Hook | On `git commit` | Commits with failing tests |
| **Pre-Push Hook** | On `git push` | **Pushes if CI would fail** |
| GitHub Actions | On push/PR | Merges with failing tests |

### Local CI with act

Spec Kit enforces CI-green-before-push using [act](https://github.com/nektos/act) to run GitHub Actions locally.

#### Setup

```bash
# 1. Verify prerequisites
./.specify/scripts/bash/check-prerequisites.sh --check-ci

# 2. Install the pre-push hook
./.specify/scripts/bash/install-hooks.sh

# 3. (Optional) Customize .actrc for your project
# Edit .actrc to configure act behavior
```

#### How It Works

1. You run `git push`
2. Pre-push hook intercepts and runs `act push`
3. act executes your GitHub Actions workflow locally in Docker
4. If CI passes → push proceeds
5. If CI fails → push is blocked with error details

#### Configuration

The `.actrc` file configures act behavior:

```bash
# .actrc
--container-architecture linux/amd64
--env CI=true
-P ubuntu-latest=catthehacker/ubuntu:act-latest
```

#### Escape Hatch

For emergencies (use sparingly):

```bash
SPECKIT_SKIP_CI=1 git push
```

Skips are logged to `.specify/ci-skip.log` for audit.

#### Troubleshooting act

| Issue | Solution |
|-------|----------|
| "act not found" | Install: `brew install act` |
| "Docker not running" | Start Docker Desktop or daemon |
| Slow first run | act pulls Docker images (~500MB-2GB) |
| Action not supported | Some actions don't work locally; check [act compatibility](https://github.com/nektos/act#known-issues) |
| Secrets needed | Create `.secrets` file or pass via `--secret` |

### Checklist Validation
Domain-specific checklists ensure:
- Security best practices
- Accessibility (WCAG 2.1)
- Performance targets
- Compliance requirements

### Consistency Analysis
Cross-artifact validation:
- All spec requirements have tasks
- All tasks reference plan sections
- No implementation drift from spec

## Best Practices

### 1. Specs Are Non-Technical
❌ **Bad**: "Use React hooks to fetch data from REST API"
✅ **Good**: "Users can view their order history"

### 2. Plans Are Technical
❌ **Bad**: "Create a way to store data"
✅ **Good**: "Use PostgreSQL 15 with SQLAlchemy ORM and Alembic migrations"

### 3. Tasks Are Executable
❌ **Bad**: "Set up authentication"
✅ **Good**: "[T010] [P] [US1] Create User model with email, password_hash, created_at in src/models/user.py"

### 4. One Concept Per User Story
Each user story should be independently testable and deliverable.

### 5. Prioritize Ruthlessly
- P1 = MVP (must have)
- P2 = Important (should have)
- P3 = Nice to have (could have)

## Troubleshooting

### "Not on a feature branch" Error
Ensure branch name follows `###-feature-name` pattern, or set:
```bash
export SPECIFY_FEATURE="001-my-feature"
```

### Missing Prerequisites
Run diagnostics:
```bash
./.specify/scripts/bash/check-prerequisites.sh --json
```

### Tasks Not Executing in Order
- Sequential tasks: NO `[P]` marker
- Parallel tasks: Include `[P]` marker

### Beads Bulk Import Issues

**Problem**: `bd create --file` segfaults with markdown files

**Solution**: Use the provided workaround scripts:

```bash
# 1. Create issues individually (workaround for segfault)
./.specify/scripts/bash/create-beads-issues.sh specs/###-feature/tasks.md <epic-id>

# 2. Link Beads IDs back to tasks.md
./.specify/scripts/bash/update-tasks-with-beads-ids.sh specs/###-feature/tasks.md
```

**What these scripts do**:
- `create-beads-issues.sh`: Extracts tasks from tasks.md, creates Beads issues with intelligent priority/label detection, adds 0.1s delay between creates to avoid overwhelming the system
- `update-tasks-with-beads-ids.sh`: Updates tasks.md to link each task with its Beads ID (converts `- [ ] T001` to `- [ ] (speckit-abc.1) T001`)

Both scripts include validation, error handling, backup creation, and colored output for better UX.

### Analyze Phase Warnings

If `/speckit.analyze` reports missing requirements or inconsistencies:

1. **Missing tasks for spec requirements**: Add tasks to tasks.md for uncovered requirements
2. **Scope creep detected**: Remove tasks that don't align with spec.md
3. **Graceful degradation tasks missing**: If constitution requires fallback strategies, ensure tasks.md includes error handling implementation

Always run `/speckit.analyze` after generating tasks.md and before starting implementation.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs or request features at [GitHub Issues](link-to-issues)
- **Discussions**: Join the community at [GitHub Discussions](link-to-discussions)
- **Documentation**: Full docs at [link-to-docs]

## Acknowledgments

Built for use with [Claude Code](https://claude.com/claude-code) by Anthropic.
