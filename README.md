# Spec Kit - Specification-Driven Development Framework

**Spec Kit** is a comprehensive workflow system that guides software features from conception through implementation using a structured, specification-driven approach.

## Overview

Spec Kit enforces a rigorous development workflow that separates concerns and ensures quality at each phase:

```
constitution → specify → clarify → plan → checklist → tasks → analyze → implement
```

### Key Principles

- **Specification-first**: Define WHAT and WHY before HOW
- **Technology-agnostic specs**: Keep implementation details out of specifications
- **Quality gates**: Validate completeness and consistency at each phase
- **Executable tasks**: Generate dependency-ordered, testable task lists
- **User story prioritization**: Enable incremental delivery and independent testing

## Installation

### Prerequisites

- **Claude Code** (claude.ai/code) - Spec Kit is designed to work with Claude Code's slash command system
- **Git** (recommended but optional)
- **Bash** (for automation scripts)

### Quick Start

1. **Clone or download this repository**:
   ```bash
   git clone <your-speckit-repo-url> .speckit-framework
   ```

2. **Copy Spec Kit into your project**:
   ```bash
   cd your-project
   cp -r ../speckit-framework/.specify ./
   cp -r ../speckit-framework/.claude/commands/speckit*.md ./.claude/commands/
   ```

3. **Add CLAUDE.md to your project root** (see Setup section below)

4. **Initialize your first feature**:
   ```bash
   # In Claude Code
   /speckit.specify Add user authentication with email/password
   ```

## Directory Structure

```
your-project/
├── .claude/
│   └── commands/              # Slash command definitions
│       ├── speckit.specify.md
│       ├── speckit.plan.md
│       ├── speckit.tasks.md
│       ├── speckit.implement.md
│       ├── speckit.clarify.md
│       ├── speckit.checklist.md
│       ├── speckit.analyze.md
│       ├── speckit.constitution.md
│       ├── speckit.taskstoissues.md
│       ├── speckit-workflow-v2.md
│       └── speckit-orchestrate.md
├── .specify/
│   ├── memory/
│   │   └── constitution.md    # Project architectural principles
│   ├── scripts/bash/          # Workflow automation
│   │   ├── common.sh
│   │   ├── check-prerequisites.sh
│   │   ├── create-new-feature.sh
│   │   ├── setup-plan.sh
│   │   └── update-agent-context.sh
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
│       ├── tasks.md           # Executable task list
│       └── checklists/        # Quality validation checklists
└── CLAUDE.md                  # Instructions for Claude Code
```

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
