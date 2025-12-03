# CLAUDE.md

This repository contains the **Spec Kit Workflow System** - a specification-driven development framework for Claude Code.

## Repository Structure

This repository provides a framework that can be integrated into any software project. It is NOT a standalone application, but rather a set of tools, templates, and workflows.

### Directory Layout

```
.
├── .claude/
│   ├── settings.json          # Claude Code hooks (Beads integration)
│   ├── README.md              # Configuration documentation
│   ├── commands/              # Slash command definitions for Claude Code
│   │   ├── speckit.specify.md    # Create feature specifications
│   │   ├── speckit.clarify.md    # Resolve ambiguities
│   │   ├── speckit.plan.md       # Create technical plans
│   │   ├── speckit.tasks.md      # Generate task lists
│   │   ├── speckit.implement.md  # Execute implementation
│   │   ├── speckit.analyze.md    # Cross-artifact validation
│   │   ├── speckit.checklist.md  # Quality checklists
│   │   ├── speckit.constitution.md   # Project principles
│   │   ├── speckit.fix.md        # Quick fixes (bypasses full workflow)
│   │   ├── speckit.taskstoissues.md  # Convert tasks to GitHub issues
│   │   ├── speckit-workflow-v2.md    # Full workflow orchestration
│   │   └── speckit-orchestrate.md    # Quick workflow
│   ├── agents/                # Specialized sub-agent definitions
│   │   ├── openapi-spec-author.md    # API design and contract validation
│   │   ├── backend-api-engineer.md   # Backend TDD implementation
│   │   ├── frontend-react-engineer.md # Frontend React/TypeScript
│   │   ├── integration-tester.md     # E2E and integration testing
│   │   ├── spec-validator.md         # Spec quality validation
│   │   ├── consistency-checker.md    # Cross-artifact consistency
│   │   └── beads-sync.md             # Beads synchronization
│   └── skills/                # On-demand context skills
│       ├── spec-kit-workflow/    # Workflow phase guidance
│       ├── beads-integration/    # Persistent memory patterns
│       ├── spec-validation/      # Spec quality validation
│       └── project-standards/    # Constitution principles (on-demand)
├── .specify/
│   ├── memory/
│   │   └── constitution.md    # Template for project architectural principles
│   ├── scripts/bash/          # Automation scripts
│   │   ├── common.sh              # Shared utilities
│   │   ├── check-prerequisites.sh # Validate workflow state
│   │   ├── create-new-feature.sh  # Initialize feature branches
│   │   ├── create-beads-epic.sh   # Create Pivotal-style Beads epics
│   │   ├── create-beads-issues.sh # Bulk import tasks with dependencies
│   │   ├── setup-plan.sh          # Initialize planning artifacts
│   │   └── update-agent-context.sh # Update context files
│   └── templates/             # Document templates
│       ├── spec-template.md       # Feature specification structure
│       ├── plan-template.md       # Technical plan structure
│       ├── tasks-template.md      # Task list format
│       ├── checklist-template.md  # Quality checklist format
│       └── agent-file-template.md # Agent context file
├── README.md                  # Framework documentation
└── LICENSE                    # MIT License
```

## Pivotal Labs Methodology

Spec Kit + Beads implements practices from **Pivotal Labs** (VMware Tanzu Labs):

| Pivotal Practice | Spec Kit Implementation |
|-----------------|------------------------|
| **TDD** | `test-gate.sh` enforces 100% test pass after edits |
| **User Stories** | spec.md with P0/P1/P2/P3 priorities |
| **Story Types** | Beads `--type epic/task/bug` |
| **Story States** | Beads `--status todo/in-progress/done` |
| **Acceptance Criteria** | spec.md sections → Beads epic description |
| **IPM (Planning)** | `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` |
| **Dependencies** | Automatic P0 → P1 → P2 → P3 blocking |

### Pivotal-Style Beads Workflow

```bash
# 1. Create spec with Problem Statement, Business Value, Acceptance Criteria
/speckit.specify Add payment processing

# 2. Create plan with Architectural Vision
/speckit.plan

# 3. Create Pivotal-style epic (extracts from spec.md + plan.md)
./.specify/scripts/bash/create-beads-epic.sh specs/001-feature P0

# 4. Generate tasks
/speckit.tasks

# 5. Bulk import tasks with P0→P1→P2 dependencies
EPIC_ID=$(cat specs/001-feature/.beads-epic-id)
./.specify/scripts/bash/create-beads-issues.sh specs/001-feature/tasks.md $EPIC_ID

# 6. Drive implementation from Beads
bd ready  # Shows P0 tasks first, then P1 as P0 completes
```

## Contract-Driven Development

Spec Kit integrates with **Specmatic** for contract-driven development, enabling parallel frontend/backend implementation with API contracts as the source of truth.

### MCP Integrations

The `.mcp.json` configures three MCP servers:
- **Linear**: Issue tracking and project management
- **Specmatic**: Contract testing, backward compatibility, service virtualization
- **Playwright**: E2E testing and browser automation

### Backward Compatibility Gate

Before any API changes are finalized:

```bash
# Validate OpenAPI changes don't break existing consumers
specmatic backward-compatibility-check --target-path ./specs/<feature>/contracts/openapi.yaml
```

Rules:
- Adding optional fields: ✅ ALLOWED
- Adding new endpoints: ✅ ALLOWED
- Removing endpoints/fields: ❌ BREAKING
- Changing field types: ❌ BREAKING

### Parallel Development Flow

```
Phase 1: API Design
├── openapi-spec-author agent
├── Specmatic backward-compatibility-check
└── Gate: No breaking changes

Phase 2: Parallel Implementation (Backend + Frontend simultaneously)
├── backend-api-engineer
│   └── Uses Specmatic for contract testing
├── frontend-react-engineer
│   └── Uses Specmatic stub server for mocking
└── Both work from same OpenAPI contract

Phase 3: Integration
├── integration-tester agent
├── Playwright for E2E tests
└── Validates full flow
```

## Specialized Sub-Agents

Spec Kit provides specialized agents for different implementation tracks:

| Agent | Role | Tools |
|-------|------|-------|
| `openapi-spec-author` | API design, OpenAPI specs, backward compatibility | Specmatic MCP |
| `backend-api-engineer` | Backend implementation, TDD, contract testing | Specmatic MCP |
| `frontend-react-engineer` | React/TypeScript, accessibility, mock backends | Specmatic + Playwright MCP |
| `integration-tester` | E2E testing, performance validation, smoke tests | Playwright MCP |

### Using Sub-Agents

Sub-agents are invoked during `/speckit.implement`:

```bash
# Standard implementation (sequential)
/speckit.implement

# Parallel implementation with sub-agents
/speckit.implement --parallel
```

Each sub-agent:
- Invokes the `project-standards` skill for constitution guidance
- Updates Beads with progress (`bd update`, `bd note`)
- Follows TDD (tests first, then implementation)
- Validates against OpenAPI contract

## Skills System

Skills provide on-demand context without polluting the main context window:

| Skill | Purpose | Auto-Invokes When |
|-------|---------|-------------------|
| `spec-kit-workflow` | Workflow phase guidance | Discussing features, planning |
| `beads-integration` | Persistent memory patterns | Task tracking, session persistence |
| `spec-validation` | Spec quality validation | Reviewing specs, before planning |
| `project-standards` | Constitution principles | Writing code, making decisions |

### Quick Fix Command

For simple changes that don't need full workflow:

```bash
/speckit.fix Fix typo in README
/speckit.fix Change button color from blue to green
/speckit.fix Add missing import in UserProfile
```

This bypasses specify → plan → tasks → implement for trivial fixes while still respecting test gates and project standards.

## Working with This Repository

### For Framework Development

When making changes to Spec Kit itself:

1. **Modify templates**: Edit files in `.specify/templates/`
2. **Update scripts**: Modify bash scripts in `.specify/scripts/bash/`
3. **Enhance commands**: Edit slash command files in `.claude/commands/`
4. **Update documentation**: Keep README.md and CLAUDE.md in sync

### For Integration into Projects

To use Spec Kit in your project:

1. **Copy framework files**:
   ```bash
   cd your-project
   cp -r /path/to/speckit/.specify ./
   mkdir -p .claude/commands
   cp -r /path/to/speckit/.claude/commands/speckit*.md ./.claude/commands/
   cp /path/to/speckit/.claude/settings.json ./.claude/
   ```

2. **Create project-specific CLAUDE.md**:
   See README.md for example template

3. **Customize constitution**:
   Edit `.specify/memory/constitution.md` with your project's principles

4. **Start using commands**:
   ```bash
   /speckit.specify Your first feature description
   ```

## Developing Spec Kit Features

### Adding New Slash Commands

1. Create new command file in `.claude/commands/speckit.newcommand.md`
2. Follow the existing command structure:
   - YAML frontmatter with description and handoffs
   - Clear outline of command behavior
   - Examples and error handling
3. Update README.md with command documentation

### Modifying Templates

Templates in `.specify/templates/` define the structure of generated documents:

- **spec-template.md**: User-facing feature specification (WHAT/WHY)
- **plan-template.md**: Technical implementation plan (HOW)
- **tasks-template.md**: Executable task list with dependencies
- **checklist-template.md**: Quality validation checklist
- **agent-file-template.md**: Agent context and instructions

When modifying templates:
- Maintain clear section headers
- Preserve placeholder syntax `[PLACEHOLDER]`
- Keep templates technology-agnostic (except plan-template.md)
- Update corresponding slash commands if structure changes

### Updating Automation Scripts

Bash scripts in `.specify/scripts/bash/` handle workflow automation:

- **common.sh**: Shared functions used by other scripts
- **check-prerequisites.sh**: Validates workflow state and paths
- **create-new-feature.sh**: Initializes feature branches and directories
- **setup-plan.sh**: Prepares planning phase artifacts
- **update-agent-context.sh**: Refreshes agent context files

When modifying scripts:
- Maintain compatibility with both git and non-git repositories
- Use JSON output format for programmatic consumption
- Handle errors gracefully with clear messages
- Update corresponding slash commands if interfaces change

## Testing Changes

### Manual Testing Workflow

1. **Create a test project**:
   ```bash
   mkdir test-project && cd test-project
   git init
   ```

2. **Copy Spec Kit files**:
   ```bash
   cp -r ../speckit/.specify ./
   cp -r ../speckit/.claude/commands/speckit*.md ./.claude/commands/
   ```

3. **Test full workflow**:
   ```bash
   /speckit.specify Add sample feature for testing
   /speckit.plan
   /speckit.tasks
   ```

4. **Verify outputs**:
   - Check `specs/001-sample-feature/spec.md` structure
   - Validate `plan.md` completeness
   - Verify `tasks.md` format and dependencies

### Quality Checks

Before submitting changes:

- [ ] All bash scripts run without errors
- [ ] Templates generate valid markdown
- [ ] Slash commands follow existing patterns
- [ ] Documentation is updated
- [ ] Examples in README.md are accurate

## Multi-Session & Long-Running Tasks

Spec Kit is designed to support complex features that span multiple hours or sessions. Follow these practices for continuity:

### Session Resumption

When resuming work on an existing feature:

1. **Re-read all artifacts** at session start:
   ```
   Read: spec.md → plan.md → tasks.md (in that order)
   ```

2. **Check progress state**:
   - Review completed tasks (checked items in `tasks.md`)
   - Identify current task (first unchecked item)
   - Note any blockers or discoveries logged in Beads

3. **Update timestamps** in `tasks.md` header:
   ```markdown
   ## Progress
   - Started: 2025-01-15 09:00
   - Last session: 2025-01-15 14:30
   - Current session: 2025-01-16 10:00
   - Velocity: ~3 tasks/hour
   ```

### Autonomy During Implementation

For long-running tasks, operate with maximum autonomy:

- **Resolve ambiguities autonomously** rather than stopping to ask for clarification
- **Proceed through milestones** without prompting for "next steps"
- **Make reasonable technical decisions** aligned with constitution principles
- **Document decisions** in the relevant artifact (plan.md for architecture, tasks.md for implementation notes)

When you encounter a decision point:
1. Check constitution.md for guidance
2. Review similar patterns in existing code
3. Make the decision and document it
4. Continue working

Only stop to ask the user when:
- The decision has significant cost/risk implications
- Multiple valid approaches exist with major trade-offs
- The requirement is genuinely ambiguous and blocks all progress

### Breakpoint Practices

At natural stopping points (end of phase, major milestone, session end):

1. **Update all living documents**:
   - Mark completed tasks in `tasks.md`
   - Add implementation notes to `plan.md` if architecture evolved
   - Log discoveries in Beads

2. **Commit frequently** with descriptive messages:
   ```bash
   git commit -m "feat(auth): implement JWT validation middleware [T003]"
   ```

3. **Write breadcrumbs** for next session:
   ```markdown
   ## Session Notes
   - Completed: T001-T005 (auth foundation)
   - In progress: T006 (rate limiting) - middleware skeleton done
   - Next: Add Redis backend for rate limit counters
   - Blocker: None
   ```

### Handling Multi-Hour Tasks

For tasks spanning 4+ hours:

1. **Break into sub-milestones** mentally (don't expand tasks.md excessively)
2. **Commit at each sub-milestone** even if task isn't complete
3. **Update Beads** with progress notes every 1-2 hours
4. **Keep artifacts synchronized** - if you discover something, document it immediately

## Key Principles

### Separation of Concerns

- **Spec**: WHAT the feature does and WHY it matters (user-focused, technology-agnostic)
- **Plan**: HOW to implement (technical, includes frameworks, architecture, dependencies)
- **Tasks**: WHEN and in what ORDER (executable, dependency-ordered, with file paths)

### Quality Gates

Each phase has validation:

1. **Specify**: Spec must be testable, unambiguous, technology-agnostic
2. **Clarify**: Maximum 3 high-impact questions to resolve ambiguities
3. **Checklist**: Domain-specific validation (security, accessibility, etc.)
4. **Analyze**: Cross-artifact consistency check
5. **Implement**: Tests must pass before marking tasks complete

### User Story Prioritization

Tasks organized by priority:
- **P1**: MVP - Minimum viable product
- **P2**: Important - Should have
- **P3**: Nice to have - Could have

This enables:
- Independent implementation and testing
- Incremental delivery
- Clear MVP definition

## Architecture Decisions

### Why Bash Scripts?

- Cross-platform compatibility (works on macOS, Linux, Windows with Git Bash)
- No additional dependencies
- Easy to read and modify
- Integrates well with git workflows

### Why Separate .specify and .claude Directories?

- `.claude/`: Claude Code-specific integration (slash commands)
- `.specify/`: Framework core (templates, scripts, principles)
- Separation allows non-Claude-Code integrations in the future

### Why Numbered Feature Branches?

- Prevents branch name collisions
- Creates clear ordering and history
- Enables quick feature lookup
- Simplifies cross-referencing

## Contributing Guidelines

### Code Style

- Bash: Follow Google Shell Style Guide
- Markdown: Use GitHub-flavored markdown
- Templates: Keep language clear and concise

### Commit Messages

Format: `<type>: <description>`

Types:
- `feat`: New feature or enhancement
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code restructuring
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

Examples:
- `feat: Add --parallel flag to speckit.tasks`
- `fix: Handle missing spec.md gracefully in check-prerequisites.sh`
- `docs: Update README with new workflow examples`

### Pull Request Process

1. Create feature branch: `###-short-description`
2. Make changes with clear commits
3. Update relevant documentation
4. Test manually in a sample project
5. Submit PR with description of changes

## Maintenance

### Regular Updates

- Review and update templates quarterly
- Keep bash scripts compatible with latest bash versions
- Update documentation for Claude Code changes
- Add new domain checklists as needed

### Version Strategy

- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Major: Breaking changes to workflow or command interfaces
- Minor: New features, new commands, template enhancements
- Patch: Bug fixes, documentation updates

## Support

For questions or issues:

1. Check README.md for usage documentation
2. Review existing slash commands for examples
3. Examine bash scripts for automation details
4. Open GitHub issue for bugs or feature requests

## License

MIT License - See LICENSE file for details.

## Active Technologies
- Python 3.11+ (backend), TypeScript 5.x/React 18 (frontend) + FastAPI 0.104+, SQLAlchemy 2.0, scikit-learn 1.3+, pandas 2.0+, React 18, React Query, Tailwind CSS (001-market-inventory-predictor)
- PostgreSQL 15+ (primary database), Redis 7+ (caching, session storage) (001-market-inventory-predictor)

## Recent Changes
- 001-market-inventory-predictor: Added Python 3.11+ (backend), TypeScript 5.x/React 18 (frontend) + FastAPI 0.104+, SQLAlchemy 2.0, scikit-learn 1.3+, pandas 2.0+, React 18, React Query, Tailwind CSS
