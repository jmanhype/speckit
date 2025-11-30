# .claude Directory

This directory contains Claude Code configuration for the Spec Kit framework.

## Structure

```
.claude/
├── settings.json       # Project settings (hooks, permissions, env)
├── settings.local.json # Local overrides (gitignored, create if needed)
├── commands/           # Custom slash commands
│   └── speckit.*.md    # Spec Kit workflow commands
└── README.md           # This file
```

## Settings Hierarchy

Settings are applied in order of precedence (highest to lowest):

1. **Enterprise managed policies** (`/etc/claude-code/managed-settings.json`)
2. **Command line arguments** (temporary session overrides)
3. **Local project settings** (`.claude/settings.local.json`) - gitignored
4. **Shared project settings** (`.claude/settings.json`) - this file
5. **User settings** (`~/.claude/settings.json`)

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
      "Bash(./.specify/scripts/bash/*)",  // Spec Kit scripts
      "Bash(bd:*)",                        // Beads commands
      "Bash(git status:*)",                // Git read commands
      "Bash(npm run test:*)",              // Test commands
      "Read(specs/**)"                     // Spec files
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
            "command": "echo 'Custom session start'",
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

### commands/

Slash commands for the Spec Kit workflow:

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

## Integrating Into Your Project

When copying Spec Kit to your project:

```bash
# Copy the entire .claude directory
cp -r /path/to/speckit/.claude ./

# Or copy selectively
mkdir -p .claude/commands
cp -r /path/to/speckit/.claude/commands/speckit*.md ./.claude/commands/
cp /path/to/speckit/.claude/settings.json ./.claude/
```

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
            "command": "npm run lint --fix",
            "type": "command"
          }
        ],
        "matcher": "Edit"
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

## Troubleshooting

### Hooks not running?

1. Check hook syntax in settings.json (must be valid JSON)
2. Ensure commands are executable
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

## Best Practices

From [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices):

1. **Keep CLAUDE.md concise** - Put frequently used instructions there
2. **Tune your allowlists** - Pre-approve safe commands to reduce prompts
3. **Use hooks for automation** - Auto-format, auto-lint after edits
4. **Leverage MCP servers** - Extend Claude with additional tools
5. **Use /clear frequently** - Reset context between unrelated tasks

## Further Reading

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Settings Reference](https://docs.anthropic.com/en/docs/claude-code/settings)
- [Hooks Guide](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [MCP Configuration](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Permissions (IAM)](https://docs.anthropic.com/en/docs/claude-code/iam)
