# Example Custom Slash Command

> This is a template for creating your own custom slash commands.
> Rename this file to your-command-name.md and customize it.
> Delete this file if you don't need it.

## Usage

```
/project:example-command <your arguments here>
```

## What This Command Does

This command template demonstrates the key features of custom slash commands:

1. **$ARGUMENTS** - Captures everything after the command name
2. **Structured prompts** - Guide Claude through specific steps
3. **Tool suggestions** - Recommend specific tools for tasks

## Command Prompt

Analyze and work on: $ARGUMENTS

Follow these steps:

1. **Understand the Request**
   - Parse what the user is asking for
   - Identify key requirements and constraints

2. **Research the Codebase**
   - Use `Glob` to find relevant files
   - Use `Grep` to search for patterns
   - Use `Read` to examine file contents

3. **Plan the Approach**
   - Outline the steps needed
   - Identify potential challenges
   - Consider edge cases

4. **Implement Changes**
   - Make targeted edits using `Edit`
   - Create new files only if necessary using `Write`
   - Run tests to verify changes

5. **Verify and Clean Up**
   - Run linting and type checking
   - Ensure tests pass
   - Create a descriptive commit message

## Notes

- Commands in `.claude/commands/` are project-specific
- Commands in `~/.claude/commands/` are available globally
- Use descriptive filenames: `fix-github-issue.md`, `deploy-staging.md`
- The `$ARGUMENTS` keyword passes user input to the prompt
