#!/usr/bin/env bash
# Spec Kit Installation Script
# Supports both greenfield (new) and brownfield (existing) projects

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SPECKIT_REPO="https://github.com/YOUR_USERNAME/speckit.git"
SPECKIT_VERSION="${SPECKIT_VERSION:-main}"

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

# Check if directory is empty (greenfield)
is_empty_directory() {
    if [[ ! -d "$1" ]]; then
        return 0
    fi
    if [[ -z "$(ls -A "$1" 2>/dev/null)" ]]; then
        return 0
    fi
    return 1
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

    # Clone Spec Kit into temporary directory
    local temp_dir=$(mktemp -d)
    info "Downloading Spec Kit framework..."
    git clone --depth 1 --branch "$SPECKIT_VERSION" "$SPECKIT_REPO" "$temp_dir" >/dev/null 2>&1

    # Copy framework files
    info "Installing framework files..."
    mkdir -p .claude/commands .specify
    cp -r "$temp_dir/.specify/"* .specify/
    cp -r "$temp_dir/.claude/commands/speckit"*.md .claude/commands/
    cp "$temp_dir/.gitignore" .gitignore 2>/dev/null || true

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

See [Spec Kit Documentation](https://github.com/YOUR_USERNAME/speckit) for details.
EOF

    success "Created CLAUDE.md"

    # Create example README
    if [[ ! -f README.md ]]; then
        cat > README.md <<EOF
# ${project_name}

Project created with [Spec Kit](https://github.com/YOUR_USERNAME/speckit) - a specification-driven development framework.

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

## Documentation

- [Spec Kit Documentation](https://github.com/YOUR_USERNAME/speckit)
- [Quick Start Guide](https://github.com/YOUR_USERNAME/speckit/blob/main/QUICKSTART.md)
EOF
        success "Created README.md"
    fi

    # Cleanup
    rm -rf "$temp_dir"

    success "Spec Kit installed successfully!"
    echo ""
    info "Next steps:"
    echo "  1. Open this project in Claude Code"
    echo "  2. Run: /speckit.specify Your first feature description"
    echo "  3. Follow the workflow prompts"
    echo ""
    info "Documentation: https://github.com/YOUR_USERNAME/speckit"
}

# Install for brownfield (existing project)
install_brownfield() {
    info "Installing Spec Kit into existing project..."

    # Clone Spec Kit into temporary directory
    local temp_dir=$(mktemp -d)
    info "Downloading Spec Kit framework..."
    git clone --depth 1 --branch "$SPECKIT_VERSION" "$SPECKIT_REPO" "$temp_dir" >/dev/null 2>&1

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
            rm -rf "$temp_dir"
            exit 1
        fi
    fi

    # Install framework files
    info "Installing framework files..."
    mkdir -p .claude/commands .specify

    # Copy .specify (overwrite if exists)
    if [[ -d .specify ]]; then
        cp -r "$temp_dir/.specify/"* .specify/
        success "Updated .specify directory"
    else
        cp -r "$temp_dir/.specify/"* .specify/
        success "Installed .specify directory"
    fi

    # Copy slash commands
    cp -r "$temp_dir/.claude/commands/speckit"*.md .claude/commands/
    success "Installed Spec Kit slash commands"

    # Merge .gitignore if exists
    if [[ -f .gitignore ]] && [[ -f "$temp_dir/.gitignore" ]]; then
        # Add Spec Kit-specific ignores if not present
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

See [Spec Kit Documentation](https://github.com/YOUR_USERNAME/speckit) for details.
EOF
        success "Created CLAUDE.md"
    else
        info "CLAUDE.md already exists (not modified)"
        warning "Consider adding Spec Kit documentation to your existing CLAUDE.md"
    fi

    # Cleanup
    rm -rf "$temp_dir"

    success "Spec Kit installed successfully!"
    echo ""
    info "Next steps:"
    echo "  1. Review .specify/memory/constitution.md (customize for your project)"
    echo "  2. Run: /speckit.specify Your first feature description"
    echo "  3. Follow the workflow prompts"
    echo ""
    info "Documentation: https://github.com/YOUR_USERNAME/speckit"
}

# Update existing installation
update_speckit() {
    info "Updating Spec Kit framework..."

    if [[ ! -d .specify ]]; then
        error "Spec Kit not installed. Run without --update flag to install."
        exit 1
    fi

    # Clone latest version
    local temp_dir=$(mktemp -d)
    git clone --depth 1 --branch "$SPECKIT_VERSION" "$SPECKIT_REPO" "$temp_dir" >/dev/null 2>&1

    # Backup existing constitution if it exists
    local constitution_backup=""
    if [[ -f .specify/memory/constitution.md ]]; then
        constitution_backup=$(mktemp)
        cp .specify/memory/constitution.md "$constitution_backup"
        info "Backed up constitution.md"
    fi

    # Update framework files
    cp -r "$temp_dir/.specify/scripts" .specify/
    cp -r "$temp_dir/.specify/templates" .specify/
    cp -r "$temp_dir/.claude/commands/speckit"*.md .claude/commands/

    # Restore constitution
    if [[ -n "$constitution_backup" ]]; then
        cp "$constitution_backup" .specify/memory/constitution.md
        rm "$constitution_backup"
        success "Restored constitution.md"
    fi

    rm -rf "$temp_dir"

    success "Spec Kit updated to version: ${SPECKIT_VERSION}"
}

# Main installation logic
main() {
    local mode=""
    local project_name=""
    local update_mode=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --update)
                update_mode=true
                shift
                ;;
            --version)
                SPECKIT_VERSION="$2"
                shift 2
                ;;
            --help)
                cat <<EOF
Spec Kit Installation Script

USAGE:
    install.sh [OPTIONS] [PROJECT_NAME]

OPTIONS:
    --update            Update existing Spec Kit installation
    --version VERSION   Install specific version (default: main)
    --help             Show this help message

EXAMPLES:
    # Install in new project
    ./install.sh my-project

    # Install in current directory (existing project)
    ./install.sh

    # Update existing installation
    ./install.sh --update

    # Install specific version
    ./install.sh --version v1.0.0 my-project

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
    echo "║        Spec Kit Installer v1.0         ║"
    echo "║  Specification-Driven Development      ║"
    echo "╚════════════════════════════════════════╝"
    echo ""

    # Handle update mode
    if [[ "$update_mode" == true ]]; then
        update_speckit
        exit 0
    fi

    # Detect installation mode
    mode=$(detect_mode)

    if [[ "$mode" == "greenfield" ]]; then
        install_greenfield "$project_name"
    else
        install_brownfield
    fi
}

# Run main function
main "$@"
