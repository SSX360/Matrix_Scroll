# Rules

Rules provide system-level instructions to Agent. They bundle prompts, scripts, and more together, making it easy to manage and share workflows across your team.

Cursor supports four types of rules:

### Project Rules
Stored in `.cursor/rules`, version-controlled and scoped to your codebase.

### User Rules
Global to your Cursor environment. Used by Agent (Chat).

### Team Rules
Team-wide rules managed from the dashboard. Available on Team and Enterprise plans.

### AGENTS.md
Agent instructions in markdown format. Simple alternative to `.cursor/rules`.

## How rules work

Large language models don't retain memory between completions. Rules provide persistent, reusable context at the prompt level. When applied, rule contents are included at the start of the model context.

## Project rules

Project rules live in `.cursor/rules` as markdown files and are version-controlled. They are scoped using path patterns, invoked manually, or included based on relevance. Use them to encode domain-specific knowledge, automate project-specific workflows, and standardize style or architecture decisions.

Cursor supports `.md` and `.mdc` extensions. Use `.mdc` files with frontmatter to specify `description` and `globs`.

### Rule anatomy

Control how rules are applied from the type dropdown:

| Rule Type | Description |
| :--- | :--- |
| `Always Apply` | Apply to every chat session |
| `Apply Intelligently` | When Agent decides it's relevant based on description |
| `Apply to Specific Files` | When file matches a specified pattern |
| `Apply Manually` | When @-mentioned in chat (e.g., `@my-rule`) |

### Creating a rule
- `/create-rule` in chat: type it in Agent and describe what you want.
- From settings: open `Cursor Settings > Rules, Commands` and click `+ Add Rule`.

## Best practices

- Keep rules under 500 lines
- Split large rules into multiple, composable rules
- Provide concrete examples or referenced files
- Avoid vague guidance. Write rules like clear internal docs
- Reference files instead of copying their contents

Start simple. Add rules only when you notice Agent making the same mistake repeatedly.

## AGENTS.md

`AGENTS.md` is a simple markdown file for defining agent instructions. Place it in your project root as an alternative to `.cursor/rules`. Cursor supports AGENTS.md in the project root and subdirectories. Nested files are combined with parent directories, with more specific instructions taking precedence.

## User Rules

User Rules are global preferences defined in Cursor Settings → Rules that apply across all projects. They are used by Agent (Chat).

## FAQ

### Why isn't my rule being applied?
Check the rule type. For `Apply Intelligently`, ensure a description is defined. For `Apply to Specific Files`, ensure the file pattern matches.

### Do rules impact Cursor Tab?
No. Rules do not impact Cursor Tab or other AI features.

### Do User Rules apply to Inline Edit (Cmd/Ctrl+K)?
No. User Rules are only used by Agent (Chat).
