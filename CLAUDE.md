# CLAUDE.md

This repository contains the **Spec Kit Workflow System** - a specification-driven development framework for Claude Code.

## Repository Structure

This repository provides a framework that can be integrated into any software project. It is NOT a standalone application, but rather a set of tools, templates, and workflows.

### Directory Layout

```
.
├── .claude/
│   └── commands/              # Slash command definitions for Claude Code
│       ├── speckit.specify.md    # Create feature specifications
│       ├── speckit.clarify.md    # Resolve ambiguities
│       ├── speckit.plan.md       # Create technical plans
│       ├── speckit.tasks.md      # Generate task lists
│       ├── speckit.implement.md  # Execute implementation
│       ├── speckit.analyze.md    # Cross-artifact validation
│       ├── speckit.checklist.md  # Quality checklists
│       ├── speckit.constitution.md   # Project principles
│       ├── speckit.taskstoissues.md  # Convert tasks to GitHub issues
│       ├── speckit-workflow-v2.md    # Full workflow orchestration
│       └── speckit-orchestrate.md    # Quick workflow
├── .specify/
│   ├── memory/
│   │   └── constitution.md    # Template for project architectural principles
│   ├── scripts/bash/          # Automation scripts
│   │   ├── common.sh              # Shared utilities
│   │   ├── check-prerequisites.sh # Validate workflow state
│   │   ├── create-new-feature.sh  # Initialize feature branches
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
   cp -r /path/to/speckit/.claude/commands/speckit*.md ./.claude/commands/
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
