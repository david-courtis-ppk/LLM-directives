# LLM-directives

Directives for AI coding agents, and engineering documentation for PrecisePK (the PreciseRx platform). One repo holds three kinds of material: rules loaded into every agent session, guides read on demand, and the source of the user-facing Codebase Atlas.

## Layout

| Path | What it is | Who reads it |
| --- | --- | --- |
| `agent.md`, `architecture.md`, `file-reference.md`, `quirks.md`, `style.md` | Always-on directives, imported into every Claude Code session by `~/.claude/CLAUDE.md`. Keep them short, because every session pays for them. | Agents, every session |
| `guides/` | Engineering guides: machine setup, git and pull requests, frontend conventions, PK-Library, platform. `guides/README.md` lists them and says when to read each. | Engineers; agents on demand |
| `atlas/` | Source of the [PreciseRx Codebase Atlas](https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht), the reference site for every PrecisePK repository. `atlas/README.md` covers building, publishing and the content rules. | Engineers; agents only use `atlas/INDEX.md` to link to sections |
| `handoffs/` | Local notes for in-flight work. Gitignored. | Whoever picks up the work |

## How it is wired into Claude Code

`~/.claude/CLAUDE.md` imports the five root files:

```text
@/Users/david/git/LLM-directives/agent.md
@/Users/david/git/LLM-directives/architecture.md
@/Users/david/git/LLM-directives/file-reference.md
@/Users/david/git/LLM-directives/quirks.md
@/Users/david/git/LLM-directives/style.md
```

Nothing else is imported. `style.md` points to the guide for each task, and `architecture.md` points to the atlas index, so guides and the atlas cost context only when a task needs them.

## Changing things

- Edit a root file only when the rule belongs in every session. Put detail in a guide and link to it.
- Follow the writing rules in `guides/README.md` for guides, and in `atlas/README.md` for the atlas. Both are pure documentation: they describe the system, never how the document was written.
- After changing the atlas, run `python3 atlas/build.py` and republish to the same URL.
