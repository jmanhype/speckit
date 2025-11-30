#!/usr/bin/env bash
# Local installation script (for use before pushing to GitHub)
# This version copies from the local speckit directory instead of cloning from GitHub

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Helper functions
info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Detect installation mode
detect_mode() {
    if [[ -d .git ]] || [[ -f package.json ]] || [[ -f requirements.txt ]] || [[ -f Cargo.toml ]] || [[ -d src ]] || [[ -d lib ]]; then
        echo "brownfield"
    else
        echo "greenfield"
    fi
}

# Install for greenfield (new project)
install_greenfield() {
    local project_name="$1"

    info "Installing Spec Kit for new project: ${project_name}"

    # Create project directory
    if [[ -n "$project_name" ]] && [[ ! -d "$project_name" ]]; then
        mkdir -p "$project_name"
        cd "$project_name"
        success "Created directory: ${project_name}"
    fi

    # Initialize git if not present
    if [[ ! -d .git ]]; then
        git init
        success "Initialized git repository"
    fi

    # Copy framework files
    info "Installing framework files from: ${SCRIPT_DIR}"
    mkdir -p .claude/commands .specify
    cp -r "$SCRIPT_DIR/.specify/"* .specify/
    cp -r "$SCRIPT_DIR/.claude/commands/speckit"*.md .claude/commands/
    cp "$SCRIPT_DIR/.gitignore" .gitignore 2>/dev/null || true

    # Create CLAUDE.md
    cat > CLAUDE.md <<'EOF'
# CLAUDE.md

This repository uses **Spec Kit** for specification-driven development.

## Overview

Spec Kit enforces a structured workflow:
constitution → specify → clarify → plan → checklist → tasks → analyze → implement

## Commands

- `/speckit.specify <description>` - Create feature specification
- `/speckit.clarify` - Resolve ambiguities
- `/speckit.plan` - Create technical implementation plan
- `/speckit.checklist` - Generate quality checklists
- `/speckit.tasks` - Generate executable task list
- `/speckit.analyze` - Validate cross-artifact consistency
- `/speckit.implement` - Execute implementation
- `/speckit-workflow-v2 <brief> [options]` - Run complete workflow

## Quick Start

```bash
# Create your first feature
/speckit.specify Add user authentication

# Review and continue
/speckit.plan
/speckit.tasks
/speckit.implement
```

See [Spec Kit](https://github.com/YOUR_USERNAME/speckit) for full documentation.
EOF

    success "Created CLAUDE.md"

    # Create example README
    if [[ ! -f README.md ]]; then
        cat > README.md <<EOF
# ${project_name}

Project created with Spec Kit - a specification-driven development framework.

## Getting Started

1. Define your first feature:
   \`\`\`bash
   /speckit.specify Add your feature description here
   \`\`\`

2. Follow the workflow:
   - Review generated \`spec.md\`
   - Create technical plan with \`/speckit.plan\`
   - Generate tasks with \`/speckit.tasks\`
   - Implement with \`/speckit.implement\`

## Project Structure

\`\`\`
.
├── .claude/commands/     # Spec Kit slash commands
├── .specify/            # Templates and automation scripts
├── specs/               # Feature specifications (created as you work)
└── CLAUDE.md           # Claude Code instructions
\`\`\`
EOF
        success "Created README.md"
    fi

    success "Spec Kit installed successfully!"
    echo ""
    info "Next steps:"
    echo "  1. Open this project in Claude Code"
    echo "  2. Run: /speckit.specify Your first feature description"
    echo "  3. Follow the workflow prompts"
}

# Install for brownfield (existing project)
install_brownfield() {
    info "Installing Spec Kit into existing project..."

    # Check for existing files
    local has_conflicts=false

    if [[ -d .specify ]]; then
        warning "Directory .specify already exists"
        has_conflicts=true
    fi

    if [[ -d .claude/commands ]] && ls .claude/commands/speckit*.md >/dev/null 2>&1; then
        warning "Spec Kit commands already exist in .claude/commands"
        has_conflicts=true
    fi

    if [[ "$has_conflicts" == true ]]; then
        echo ""
        warning "Existing Spec Kit installation detected."
        read -p "Do you want to update/overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Installation cancelled"
            exit 1
        fi
    fi

    # Install framework files
    info "Installing framework files from: ${SCRIPT_DIR}"
    mkdir -p .claude/commands .specify

    # Copy .specify
    cp -r "$SCRIPT_DIR/.specify/"* .specify/
    success "Installed .specify directory"

    # Copy slash commands
    cp -r "$SCRIPT_DIR/.claude/commands/speckit"*.md .claude/commands/
    success "Installed Spec Kit slash commands"

    # Merge .gitignore if exists
    if [[ -f .gitignore ]]; then
        if ! grep -q "# Spec Kit" .gitignore; then
            echo "" >> .gitignore
            echo "# Spec Kit temporary files" >> .gitignore
            echo "specs/*/checklists/*.tmp" >> .gitignore
            success "Updated .gitignore"
        fi
    fi

    # Create or update CLAUDE.md
    if [[ ! -f CLAUDE.md ]]; then
        cat > CLAUDE.md <<'EOF'
# CLAUDE.md

This repository uses **Spec Kit** for specification-driven development.

## Commands

- `/speckit.specify <description>` - Create feature specification
- `/speckit.plan` - Create technical implementation plan
- `/speckit.tasks` - Generate executable task list
- `/speckit.implement` - Execute implementation

See [Spec Kit](https://github.com/YOUR_USERNAME/speckit) for full documentation.
EOF
        success "Created CLAUDE.md"
    else
        info "CLAUDE.md already exists (not modified)"
        warning "Consider adding Spec Kit documentation to your existing CLAUDE.md"
    fi

    success "Spec Kit installed successfully!"
    echo ""
    info "Next steps:"
    echo "  1. Review .specify/memory/constitution.md (customize for your project)"
    echo "  2. Run: /speckit.specify Your first feature description"
    echo "  3. Follow the workflow prompts"
}

# Main installation logic
main() {
    local project_name=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                cat <<EOF
Spec Kit Local Installation Script

USAGE:
    install-local.sh [PROJECT_NAME]

EXAMPLES:
    # Install in new project
    ./install-local.sh my-project

    # Install in current directory (existing project)
    ./install-local.sh

NOTES:
    This script copies Spec Kit from the local directory.
    Use install.sh (after pushing to GitHub) for remote installations.

EOF
                exit 0
                ;;
            *)
                project_name="$1"
                shift
                ;;
        esac
    done

    # Show banner
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║    Spec Kit Local Installer v1.0       ║"
    echo "║  Specification-Driven Development      ║"
    echo "╚════════════════════════════════════════╝"
    echo ""

    # Detect installation mode
    local mode=$(detect_mode)

    if [[ "$mode" == "greenfield" ]]; then
        install_greenfield "$project_name"
    else
        install_brownfield
    fi
}

# Run main function
main "$@"
