# .claude Directory

This directory contains Claude Code configuration for the Spec Kit framework.

## Structure

```
.claude/
├── settings.json           # Project settings (hooks, permissions, env)
├── settings.local.json     # Local overrides (gitignored, create if needed)
├── commands/               # Custom slash commands (user-invoked)
│   ├── speckit.*.md        # Spec Kit workflow commands
│   └── _example-command.md # Template for custom commands
├── skills/                 # Model-invoked skills (auto-triggered)
│   ├── spec-kit-workflow/  # Workflow guidance
│   │   └── SKILL.md
│   ├── beads-integration/  # Persistent memory
│   │   └── SKILL.md
│   └── spec-validation/    # Quality validation
│       └── SKILL.md
├── agents/                 # Custom AI subagents
│   ├── spec-validator.md   # Validates spec quality
│   ├── consistency-checker.md # Cross-artifact validation
│   └── beads-sync.md       # Beads synchronization
├── hooks/                  # External hook scripts
│   ├── session-start.sh    # Session initialization
│   ├── pre-compact.sh      # Pre-compaction tasks
│   └── post-edit.sh        # Post-edit automation (example)
└── README.md               # This file
```

## Project Root Files

In addition to the `.claude/` directory, Claude Code uses these project root files:

| File | Purpose | Git Status |
|------|---------|------------|
| `CLAUDE.md` | Project context and instructions | Tracked |
| `CLAUDE.local.md` | Personal overrides | Gitignored |
| `.mcp.json` | Project-scoped MCP servers | Tracked |

### CLAUDE.md vs .claude/

- **CLAUDE.md** (root): Project memory and instructions for Claude
- **.claude/** (directory): Configuration, commands, skills, etc.

Both work together. CLAUDE.md provides context; .claude/ provides tools.

### .mcp.json

For team-shared MCP servers, create `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-memory"]
    }
  }
}
```

See `.mcp.json.example` for a complete template.

Enable in settings:
```json
{
  "enableAllProjectMcpServers": true
}
```

---

## Settings Hierarchy

Settings are applied in order of precedence (highest to lowest):

1. **Enterprise managed policies** (`/etc/claude-code/managed-settings.json`)
2. **Command line arguments** (temporary session overrides)
3. **Local project settings** (`.claude/settings.local.json`) - gitignored
4. **Shared project settings** (`.claude/settings.json`) - this file
5. **User settings** (`~/.claude/settings.json`)

---

## Skills (Model-Invoked)

The `skills/` directory contains **model-invoked skills** - specialized capabilities that Claude automatically activates based on conversation context. Unlike slash commands (user-invoked), skills are triggered by Claude when relevant.

### Available Skills

| Skill | Purpose | Auto-Triggered When... |
|-------|---------|------------------------|
| `spec-kit-workflow` | Guides workflow phases | Discussing features, specs, or planning |
| `beads-integration` | Manages persistent memory | Working on tasks or multi-session projects |
| `spec-validation` | Validates spec quality | Creating/reviewing specifications |

### Skill Format

Skills live in subdirectories with a `SKILL.md` file:

```
.claude/skills/
├── my-skill-name/
│   ├── SKILL.md              (REQUIRED - skill definition)
│   ├── reference.md          (optional - supporting docs)
│   ├── scripts/              (optional - helper scripts)
│   └── templates/            (optional - file templates)
```

**SKILL.md Format:**
```yaml
---
name: skill-name              # lowercase, hyphens only (max 64 chars)
description: What it does...  # Claude uses this to decide when to invoke
allowed-tools:                # Optional tool restrictions
  - Read
  - Write
  - Bash
---

# Skill Title

Instructions for Claude when this skill is active...
```

### Skills vs Commands vs Agents

| Feature | User-Invoked? | Auto-Triggered? | Use Case |
|---------|---------------|-----------------|----------|
| **Commands** (commands/) | ✅ Yes (`/command`) | ❌ No | Explicit workflows |
| **Skills** (skills/) | ❌ No | ✅ Yes | Contextual guidance |
| **Agents** (agents/) | ✅ Yes (via Task) | ❌ No | Specialized sub-tasks |

### Creating Custom Skills

1. Create directory: `.claude/skills/my-skill/`
2. Create `SKILL.md` with YAML frontmatter
3. Write clear `description` (Claude uses this to decide invocation)
4. Include instructions and examples in the body

**User-level skills**: Place in `~/.claude/skills/` for cross-project availability.

---

## Custom Agents

The `agents/` directory contains custom AI subagents that extend Claude Code with specialized capabilities for the Spec Kit workflow.

### Available Agents

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| `spec-validator` | Validates spec quality | After creating/editing spec.md |
| `consistency-checker` | Cross-artifact validation | Before implementation |
| `beads-sync` | Syncs tasks with Beads | During long-running projects |

### Agent Format

Agents are Markdown files with YAML frontmatter:

```markdown
---
name: my-agent
description: What this agent does
tools:
  - Read
  - Grep
  - Bash
---

# Agent Name

You are a specialized agent that...

## Instructions

1. First, do this
2. Then, do that
```

### Using Agents

Agents can be invoked through the Task tool:

```
Use the spec-validator agent to check specs/001-my-feature/spec.md
```

### Creating Custom Agents

1. Create a new `.md` file in `.claude/agents/`
2. Add YAML frontmatter with name, description, and tools
3. Write the agent's system prompt in Markdown
4. The agent will be available in your project

**User-level agents**: Place in `~/.claude/agents/` for cross-project availability.

---

## Hook Scripts

The `hooks/` directory contains external scripts that can be referenced from `settings.json` instead of inline commands.

### Available Scripts

| Script | Purpose | Trigger |
|--------|---------|---------|
| `session-start.sh` | Prime Beads + show status | SessionStart |
| `pre-compact.sh` | Preserve Beads context | PreCompact |
| `post-edit.sh` | Auto-format edited files | PostToolUse (Edit) |

### Using External Hook Scripts

To use scripts instead of inline commands, update `settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "./.claude/hooks/session-start.sh",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ]
  }
}
```

### Hook Script Benefits

- **Complex logic**: Scripts can have conditionals, loops, etc.
- **Reusability**: Same script for multiple hooks
- **Testing**: Can test scripts independently
- **Version control**: Track changes to hook logic

### Creating Custom Hooks

1. Create a script in `.claude/hooks/`
2. Make it executable: `chmod +x script.sh`
3. Reference it in `settings.json`
4. Available variables:
   - `$CLAUDE_FILE_PATH` - File being edited (for PostToolUse)
   - `$CLAUDE_TOOL_NAME` - Tool being used

---

## Slash Commands

The `commands/` directory contains slash command definitions.

### Spec Kit Commands

| Command | Purpose |
|---------|---------|
| `/speckit.specify` | Create feature specification |
| `/speckit.clarify` | Resolve spec ambiguities |
| `/speckit.plan` | Create technical plan |
| `/speckit.tasks` | Generate task list |
| `/speckit.implement` | Execute implementation |
| `/speckit.analyze` | Cross-artifact validation |
| `/speckit.checklist` | Quality checklists |
| `/speckit.constitution` | Project principles |
| `/speckit.taskstoissues` | Convert tasks to GitHub issues |
| `/speckit-workflow-v2` | Full orchestrated workflow |
| `/speckit-orchestrate` | Quick workflow |

### Creating Custom Commands

See `_example-command.md` for a template. Key features:

- **$ARGUMENTS**: Passes user input to the prompt
- **Structured prompts**: Guide Claude through steps
- **Project commands**: `.claude/commands/` (project-specific)
- **User commands**: `~/.claude/commands/` (global)

---

## Configuration Reference

### Hooks

Hooks run custom commands at specific lifecycle events:

| Hook | When It Fires |
|------|---------------|
| `SessionStart` | Claude Code session begins |
| `PreCompact` | Before context compaction |
| `Stop` | Session ends |
| `PreToolUse` | Before any tool execution |
| `PostToolUse` | After any tool execution |

**Spec Kit Default Hooks:**

- **SessionStart**: Primes Beads at session start (loads persistent context)
- **PreCompact**: Primes Beads before context compaction (preserves memory)

Both hooks gracefully skip if Beads (`bd`) is not installed.

### Permissions

Control what Claude can and cannot do:

**Allow Rules** - Pre-approve tools to skip permission prompts:
```json
{
  "permissions": {
    "allow": [
      "Bash(./.specify/scripts/bash/*)",
      "Bash(bd:*)",
      "Bash(git status:*)",
      "Bash(npm run test:*)",
      "Read(specs/**)"
    ]
  }
}
```

**Deny Rules** - Block access to sensitive files:
```json
{
  "permissions": {
    "deny": [
      "Read(.env)",
      "Read(.env.*)",
      "Read(./secrets/**)",
      "Read(./**/*.pem)",
      "Read(~/.ssh/**)"
    ]
  }
}
```

### Environment Variables

Set environment variables for all sessions:

```json
{
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "0"
  }
}
```

### All Available Settings

| Key | Description | Example |
|-----|-------------|---------|
| `hooks` | Custom commands for lifecycle events | See above |
| `permissions` | Allow/deny rules for tools | See above |
| `env` | Environment variables | `{"FOO": "bar"}` |
| `model` | Override default model | `"claude-sonnet-4-5-20250929"` |
| `cleanupPeriodDays` | Chat transcript retention | `30` |
| `includeCoAuthoredBy` | Add co-authored-by in commits | `true` |
| `disableAllHooks` | Disable all hooks | `false` |

---

## Files

### settings.json (Shared)

Committed to source control. Contains:

- **Hooks**: SessionStart and PreCompact for Beads integration
- **Permissions**:
  - Allow: Spec Kit scripts, Beads, git read commands, test runners
  - Deny: .env files, secrets, credentials, SSH keys
- **Env**: Telemetry disabled by default

### settings.local.json (Personal)

Create this file for user-specific overrides. It's gitignored.

Example use cases:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "command": "./.claude/hooks/session-start.sh",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(docker:*)"
    ]
  },
  "env": {
    "ANTHROPIC_MODEL": "claude-sonnet-4-5-20250929"
  }
}
```

---

## Integrating Into Your Project

When copying Spec Kit to your project:

```bash
# Copy the entire .claude directory (recommended)
cp -r /path/to/speckit/.claude ./

# Or copy selectively
mkdir -p .claude/commands .claude/agents .claude/hooks .claude/skills
cp -r /path/to/speckit/.claude/commands/speckit*.md ./.claude/commands/
cp /path/to/speckit/.claude/settings.json ./.claude/
cp -r /path/to/speckit/.claude/agents/*.md ./.claude/agents/
cp -r /path/to/speckit/.claude/skills/* ./.claude/skills/
cp -r /path/to/speckit/.claude/hooks/*.sh ./.claude/hooks/
chmod +x ./.claude/hooks/*.sh
```

---

## Customization Examples

### Adding Project-Specific Permissions

Edit `settings.json` to allow your project's commands:

```json
{
  "permissions": {
    "allow": [
      "Bash(make:*)",
      "Bash(cargo test:*)",
      "Bash(go test:*)"
    ]
  }
}
```

### Adding Tool-Specific Hooks

Run commands before/after specific tools:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "./.claude/hooks/post-edit.sh \"$CLAUDE_FILE_PATH\"",
            "type": "command"
          }
        ],
        "matcher": "Edit|Write"
      }
    ]
  }
}
```

### Adding MCP Servers

Add to `settings.local.json` (paths are machine-specific):

```json
{
  "mcpServers": {
    "beads": {
      "command": "uvx",
      "args": ["beads-mcp"]
    },
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-puppeteer"]
    }
  }
}
```

### Using with .mcp.json

For team-shared MCP servers, create `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-memory"]
    }
  }
}
```

Then enable in settings:
```json
{
  "enableAllProjectMcpServers": true
}
```

---

## Beads Integration

The default `settings.json` includes hooks for [Beads](https://github.com/steveyegge/beads):

- **SessionStart**: `bd prime` loads your task graph into context
- **PreCompact**: `bd prime` preserves memory before context compaction

If you don't use Beads, these hooks silently skip (no errors).

To install Beads:
```bash
brew tap steveyegge/beads
brew install bd
bd init
bd doctor  # Verify setup
```

---

## Troubleshooting

### Hooks not running?

1. Check hook syntax in settings.json (must be valid JSON)
2. Ensure commands are executable: `chmod +x .claude/hooks/*.sh`
3. Test command manually in terminal
4. Check Claude Code logs for errors

### Permission denied for allowed command?

1. Bash rules use **prefix matching**, not regex
2. Ensure the pattern matches the start of the command
3. Try more specific patterns: `Bash(npm run test:*)` not `Bash(*test*)`

### Beads not priming?

1. Verify Beads is installed: `bd --version`
2. Initialize in project: `bd init`
3. Check `.beads/` directory exists
4. Try running `bd prime` manually

### Settings not taking effect?

1. Check for JSON syntax errors
2. Verify file is in correct location
3. Check precedence - local settings override shared settings
4. Restart Claude Code after changes

### Agents not appearing?

1. Check YAML frontmatter syntax
2. Ensure file is in `.claude/agents/`
3. Verify file extension is `.md`
4. Check for required fields: name, description, tools

---

## Best Practices

From [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices):

1. **Keep CLAUDE.md concise** - Put frequently used instructions there
2. **Tune your allowlists** - Pre-approve safe commands to reduce prompts
3. **Use hooks for automation** - Auto-format, auto-lint after edits
4. **Leverage MCP servers** - Extend Claude with additional tools
5. **Use /clear frequently** - Reset context between unrelated tasks
6. **Create custom agents** - For repeated specialized tasks
7. **Use external hook scripts** - For complex automation logic

---

## Further Reading

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Settings Reference](https://docs.anthropic.com/en/docs/claude-code/settings)
- [Skills Documentation](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Hooks Guide](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Subagents Documentation](https://docs.anthropic.com/en/docs/claude-code/sub-agents)
- [MCP Configuration](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Permissions (IAM)](https://docs.anthropic.com/en/docs/claude-code/iam)
