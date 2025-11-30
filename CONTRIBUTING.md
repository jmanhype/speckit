# Contributing to Spec Kit

Thank you for your interest in contributing to Spec Kit! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive. We're building a tool to help developers work more effectively.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template** when creating new issues
3. **Include details**:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment (OS, Claude Code version, etc.)
   - Relevant logs or error messages

### Suggesting Features

1. **Check existing feature requests** first
2. **Use the feature request template**
3. **Explain the use case**:
   - What problem does this solve?
   - Who would benefit?
   - How would it work?

### Submitting Pull Requests

#### Before You Start

1. **Create an issue** to discuss major changes
2. **Check existing PRs** to avoid duplicate work
3. **Review the architecture** in CLAUDE.md

#### Development Workflow

1. **Fork the repository**

2. **Create a feature branch**:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make your changes**:
   - Follow existing code style
   - Update documentation
   - Add examples if relevant

4. **Test your changes**:
   ```bash
   # Create a test project
   mkdir test-project && cd test-project
   git init

   # Copy your modified Spec Kit
   cp -r ../speckit/.specify ./
   cp -r ../speckit/.claude/commands/speckit*.md ./.claude/commands/

   # Test the workflow
   # (in Claude Code)
   /speckit.specify Add test feature
   /speckit.plan
   /speckit.tasks
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: Add new capability to speckit.tasks"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feat/your-feature-name
   ```

7. **Submit a Pull Request**:
   - Use a clear, descriptive title
   - Reference related issues
   - Describe what changed and why
   - Include before/after examples if applicable

## Development Guidelines

### Bash Scripts

- Follow [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- Use `#!/usr/bin/env bash` shebang
- Include error handling with `set -euo pipefail`
- Add comments for complex logic
- Support both git and non-git repositories
- Output JSON when `--json` flag is present

**Example**:
```bash
#!/usr/bin/env bash
set -euo pipefail

# Get the repository root directory
get_repo_root() {
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git rev-parse --show-toplevel
    else
        pwd
    fi
}
```

### Markdown Documentation

- Use GitHub-flavored markdown
- Include code examples with language tags
- Keep line length reasonable (80-100 characters)
- Use relative links for internal references
- Include table of contents for long documents

### Slash Commands

Slash commands in `.claude/commands/` should:

- Include YAML frontmatter:
  ```yaml
  ---
  description: Brief description of what this command does
  handoffs:
    - label: Next Step
      agent: speckit.nextcommand
      prompt: What to do next
  ---
  ```

- Follow this structure:
  1. User Input section
  2. Outline/Instructions
  3. Execution flow
  4. Error handling
  5. Success criteria
  6. Examples

- Use clear, imperative language
- Include error cases and edge cases
- Reference related commands in handoffs

**Example**:
```markdown
---
description: Generate executable task list from plan.md
handoffs:
  - label: Implement Tasks
    agent: speckit.implement
    prompt: Execute tasks from tasks.md
---

## User Input

```text
$ARGUMENTS
```

## Outline

Given the feature plan in `plan.md`, generate an executable task list...
```

### Templates

Templates in `.specify/templates/` should:

- Use clear, descriptive section headers
- Include placeholders in `[SQUARE BRACKETS]`
- Provide inline guidance and examples
- Maintain consistent formatting
- Be technology-agnostic (except plan-template.md)

**Example**:
```markdown
# [FEATURE NAME]

## Overview

[Brief 2-3 sentence description of what this feature does and why it matters]

## User Scenarios

### Scenario 1: [Name]

**As a** [user type]
**I want to** [action]
**So that** [benefit]
```

## Commit Message Format

Use conventional commits format:

```
<type>: <description>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature or enhancement
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code restructuring without changing behavior
- `test`: Test additions or modifications
- `chore`: Maintenance tasks (dependencies, tooling)
- `style`: Code style changes (formatting, whitespace)

### Examples

```
feat: Add --parallel flag to speckit.tasks

Enables concurrent execution of parallelizable tasks marked with [P].

Closes #42
```

```
fix: Handle missing spec.md gracefully in check-prerequisites.sh

Previously would error with unclear message. Now provides helpful
guidance to run /speckit.specify first.
```

```
docs: Add examples for custom checklist domains

Added security, accessibility, and performance checklist examples
to help users customize quality gates.
```

## Testing Checklist

Before submitting a PR, verify:

- [ ] All bash scripts run without errors
- [ ] Templates generate valid markdown
- [ ] Slash commands follow existing patterns
- [ ] Documentation is updated (README.md, CLAUDE.md)
- [ ] Examples are accurate and tested
- [ ] No hardcoded paths or assumptions
- [ ] Works in both git and non-git repositories
- [ ] JSON output is valid (for scripts with `--json`)

## Review Process

1. **Automated checks**: Linting, formatting (when available)
2. **Manual review**: Code quality, design, documentation
3. **Testing**: Reviewers will test in sample projects
4. **Feedback**: Address comments and suggestions
5. **Approval**: At least one maintainer approval required
6. **Merge**: Squash and merge when approved

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an issue with the bug report template
- **Features**: Create an issue with the feature request template
- **PRs**: Tag maintainers if no response after 48 hours

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- Release notes for significant contributions
- README.md acknowledgments section

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for helping make Spec Kit better!
