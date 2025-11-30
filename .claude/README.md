# .claude Directory

This directory contains Claude Code configuration for the Spec Kit framework.

## Structure

```
.claude/
├── settings.json       # Project settings (hooks, permissions)
├── settings.local.json # Local overrides (gitignored, create if needed)
├── commands/           # Custom slash commands
│   └── speckit.*.md    # Spec Kit workflow commands
└── README.md           # This file
```

## Files

### settings.json

Shared project settings committed to the repository. Contains:

- **SessionStart hook**: Primes Beads at session start (loads persistent context)
- **PreCompact hook**: Primes Beads before context compaction (preserves memory)

Both hooks gracefully skip if Beads (`bd`) is not installed.

### settings.local.json

Create this file for user-specific overrides. It's gitignored and won't be committed.

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
  "mcpServers": {
    "your-custom-server": {
      "command": "your-mcp-server",
      "args": []
    }
  }
}
```

### commands/

Slash commands for the Spec Kit workflow:

| Command | Purpose |
|---------|---------|
| `speckit.specify` | Create feature specification |
| `speckit.clarify` | Resolve spec ambiguities |
| `speckit.plan` | Create technical plan |
| `speckit.tasks` | Generate task list |
| `speckit.implement` | Execute implementation |
| `speckit.analyze` | Cross-artifact validation |
| `speckit.checklist` | Quality checklists |
| `speckit.constitution` | Project principles |
| `speckit.taskstoissues` | Convert tasks to GitHub issues |
| `speckit-workflow-v2` | Full orchestrated workflow |
| `speckit-orchestrate` | Quick workflow |

## Integrating Into Your Project

When copying Spec Kit to your project:

```bash
# Copy the entire .claude directory
cp -r /path/to/speckit/.claude ./

# Or copy selectively
cp -r /path/to/speckit/.claude/commands/speckit*.md ./.claude/commands/
cp /path/to/speckit/.claude/settings.json ./.claude/
```

## Customization

### Adding Project-Specific Hooks

Edit `settings.json` or create `settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "echo 'Tool completed'",
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

Add to `settings.local.json` (not settings.json, since paths are machine-specific):

```json
{
  "mcpServers": {
    "beads": {
      "command": "uvx",
      "args": ["beads-mcp"]
    }
  }
}
```

### Available Hooks

| Hook | When It Fires |
|------|---------------|
| `SessionStart` | Claude Code session begins |
| `PreCompact` | Before context compaction |
| `Stop` | Session ends |
| `PreToolUse` | Before any tool execution |
| `PostToolUse` | After any tool execution |
| `Notification` | On notifications |

## Beads Integration

The default `settings.json` includes hooks for [Beads](https://github.com/steveyegge/beads) - a persistent task memory system:

- **SessionStart**: `bd prime` loads your task graph into context
- **PreCompact**: `bd prime` preserves memory before context is compacted

If you don't use Beads, these hooks silently skip (no errors).

To install Beads:
```bash
brew tap steveyegge/beads
brew install bd
bd init
```

## Troubleshooting

### Hooks not running?

1. Check hook syntax in settings.json
2. Ensure commands are executable
3. Check Claude Code logs for errors

### Beads not priming?

1. Verify Beads is installed: `bd --version`
2. Initialize in project: `bd init`
3. Check `.beads/` directory exists
