# Spec Kit Quick Start

Get started with Spec Kit in 5 minutes.

## Prerequisites

- Claude Code installed (claude.ai/code)
- Git (optional but recommended)

## Installation

### 1. Copy Spec Kit into Your Project

```bash
cd your-project

# Create necessary directories
mkdir -p .claude/commands .specify

# Copy Spec Kit files
cp -r /path/to/speckit/.specify/* ./.specify/
cp -r /path/to/speckit/.claude/commands/speckit*.md ./.claude/commands/
```

### 2. Add CLAUDE.md

Create `CLAUDE.md` in your project root:

```markdown
# CLAUDE.md

This repository uses **Spec Kit** for specification-driven development.

## Commands

- `/speckit.specify <description>` - Create feature spec
- `/speckit.plan` - Create technical plan
- `/speckit.tasks` - Generate executable tasks
- `/speckit.implement` - Execute implementation
- `/speckit-workflow-v2 <brief>` - Run full workflow

See [Spec Kit](link-to-repo) for full documentation.
```

### 3. (Optional) Customize Constitution

Edit `.specify/memory/constitution.md` with your project's principles:

```markdown
# Project Constitution

## Core Principles

1. Test-Driven Development
2. API-First Design
3. Security by Default

## Technology Stack

- Language: [Your language]
- Framework: [Your framework]
- Database: [Your database]
```

## Your First Feature

### Quick Workflow

Open Claude Code in your project and run:

```bash
/speckit.specify Add user login with email and password
```

This will:
1. Create a feature branch `001-user-login`
2. Generate `specs/001-user-login/spec.md` with requirements
3. Validate specification quality
4. Ask clarification questions if needed

### Continue the Workflow

```bash
# Create technical plan
/speckit.plan

# Generate executable tasks
/speckit.tasks

# Implement the feature
/speckit.implement
```

### Full Workflow (One Command)

```bash
/speckit-workflow-v2 Add user login with email and password --auto
```

## Understanding Generated Files

After running the workflow, you'll have:

```
specs/001-user-login/
├── spec.md          # What the feature does and why
├── plan.md          # How to implement it technically
├── tasks.md         # Ordered list of implementation tasks
└── checklists/      # Quality validation checklists
    ├── security.md
    └── requirements.md
```

### spec.md - The WHAT and WHY

Technology-agnostic description of the feature:

```markdown
# User Login

## Overview
Allow users to authenticate using email and password...

## User Scenarios
**As a** registered user
**I want to** log in with my email and password
**So that** I can access my account

## Success Criteria
- Users can log in within 3 seconds
- Failed login attempts show clear error messages
```

### plan.md - The HOW

Technical implementation details:

```markdown
# Implementation Plan: User Login

## Technology Stack
- FastAPI for auth endpoints
- bcrypt for password hashing
- JWT for session tokens

## Architecture
- POST /auth/login endpoint
- UserService.authenticate() method
- JWT token generation
```

### tasks.md - The EXECUTION

Ordered, executable tasks:

```markdown
## Phase 3: User Stories

### P1 - Basic Login (MVP)
- [ ] [T010] [P] [US1] Create User model in src/models/user.py
- [ ] [T011] [P] [US1] Create AuthService in src/services/auth.py
- [ ] [T012] [US1] Create login endpoint in src/api/auth.py
- [ ] [T013] [US1] Add login tests in tests/test_auth.py
```

## Common Workflows

### Feature Development

```bash
# 1. Specify what you want
/speckit.specify Add real-time notifications

# 2. Review and clarify (if questions are asked)
/speckit.clarify

# 3. Create technical plan
/speckit.plan

# 4. Generate tasks
/speckit.tasks

# 5. Implement
/speckit.implement
```

### Quick Iteration

```bash
# Run entire workflow at once
/speckit-workflow-v2 Add export to PDF feature --auto
```

### Quality-First Development

```bash
# Include security and accessibility checks
/speckit-workflow-v2 Add payment processing --domains 'security,pci-compliance' --strict
```

## Task Format Explained

Tasks follow this format:

```
- [ ] [T010] [P] [US1] Create User model in src/models/user.py
  │     │     │    │    │
  │     │     │    │    └─ Description with file path
  │     │     │    └────── User Story reference
  │     │     └─────────── [P] = Parallelizable
  │     └───────────────── Task ID
  └─────────────────────── Checkbox (marks completion)
```

- **Task ID**: Unique identifier for tracking
- **[P]**: Can be done in parallel with other [P] tasks
- **[US#]**: References user story from spec.md
- **File path**: Where to implement the change

## Checking Your Progress

### View Current Feature

```bash
# In your terminal
./.specify/scripts/bash/check-prerequisites.sh --json
```

Returns:
```json
{
  "branch": "001-user-login",
  "feature_dir": "specs/001-user-login",
  "spec_file": "specs/001-user-login/spec.md",
  "plan_file": "specs/001-user-login/plan.md",
  "tasks_file": "specs/001-user-login/tasks.md"
}
```

### Mark Tasks Complete

As you implement each task, mark it complete in `tasks.md`:

```markdown
- [X] [T010] [P] [US1] Create User model in src/models/user.py
- [ ] [T011] [P] [US1] Create AuthService in src/services/auth.py
```

## Tips and Best Practices

### 1. Start Small

Your first spec doesn't need to be perfect. You can clarify later:

```bash
/speckit.specify Add basic user profile page
/speckit.clarify  # Claude will ask targeted questions
```

### 2. Review Generated Specs

Always review the generated `spec.md` before continuing. It's easier to fix specifications than code.

### 3. Use Priorities

Implement P1 tasks first for a working MVP, then add P2 and P3 features incrementally.

### 4. Independent User Stories

Each user story (US1, US2, US3) should be independently testable. You can stop after any story and have a working feature.

### 5. Leverage Quality Gates

Use `--strict` flag for critical features:

```bash
/speckit-workflow-v2 Add payment processing --strict
```

This will halt on validation failures instead of proceeding.

## Troubleshooting

### "Not on a feature branch" Error

Make sure you're on a branch following the pattern `###-feature-name`:

```bash
git checkout -b 001-my-feature
```

Or set manually:
```bash
export SPECIFY_FEATURE="001-my-feature"
```

### Files Not Generated

Run diagnostics:
```bash
./.specify/scripts/bash/check-prerequisites.sh --json
```

This shows what's available and what's missing.

### Want to Start Over

```bash
# Delete the spec directory
rm -rf specs/001-old-feature

# Checkout main and create new branch
git checkout main
git branch -D 001-old-feature
```

## Next Steps

1. **Read the Full Documentation**: See [README.md](README.md) for detailed explanations
2. **Customize Templates**: Edit `.specify/templates/` to match your project style
3. **Define Your Constitution**: Add project-specific principles to `.specify/memory/constitution.md`
4. **Explore Advanced Features**: Try checklists, analysis, and GitHub issue generation

## Getting Help

- **Full Documentation**: [README.md](README.md)
- **Framework Details**: [CLAUDE.md](CLAUDE.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues**: Report bugs or request features on GitHub

## Example Project Structure

After a few features, your project will look like:

```
your-project/
├── .claude/
│   └── commands/
│       ├── speckit.specify.md
│       ├── speckit.plan.md
│       └── ... (other Spec Kit commands)
├── .specify/
│   ├── memory/
│   │   └── constitution.md
│   ├── scripts/bash/
│   └── templates/
├── specs/
│   ├── 001-user-login/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   ├── 002-user-profile/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   └── 003-notifications/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── src/
│   └── (your application code)
├── tests/
│   └── (your tests)
└── CLAUDE.md
```

Happy building! 🚀
