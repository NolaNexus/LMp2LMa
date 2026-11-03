# ADR-001: Skill format and location

- **Status:** Accepted
- **Date:** 2026-11-02
- **Supersedes:** none

## Context

OpenCode V2 discovers skills from these sources (project-scoped ones are
searched from the current directory up to the project root):

| Scope | Source |
|---|---|
| Project | `.opencode/skills` |
| Project compatibility | `.claude/skills`, `.agents/skills` |
| Global | `~/.config/opencode/skills` |

Two shapes are accepted inside a source: a flat `skills/<id>.md`, or a
directory `skills/<id>/SKILL.md`. A directory containing `SKILL.md` is one
skill — OpenCode does not search inside it for more skills. Hidden
directories and `node_modules` are skipped, and the search stops six
directories below the source root.

Nothing in this repository existed before this decision: there is no
`.opencode/` directory and no project `opencode.jsonc`. The global config at
`~/.config/opencode/opencode.jsonc` holds the model routing and the
`retrieval` MCP server; agent definitions live at
`~/.config/opencode/agents/*.md`.

Two loader behaviours drive the design:

1. **Unknown frontmatter keys are carried but not interpreted.** Only
   `name`, `description`, `metadata.opencode/autoinvoke`, and
   `disable-model-invocation` change behaviour.
2. **Skill IDs come from the path, not from `name`.** `name` is a display
   label; the model calls `skill` with the path-derived ID.

## Decision

### Location

Skills live in the repository, at `.opencode/skills/`:

```
.opencode/skills/
├── authoring-skills/SKILL.md
├── notebook-editing/SKILL.md
├── repo-orientation/SKILL.md
├── retrieval-mcp/SKILL.md
└── .archive/
    └── <retired-id>/SKILL.md
```

The directory form is mandatory because it gives supporting files
(`references/`, `scripts/`) a private base directory and a file sample in the
loaded context. Flat `skills/<id>.md` files are not used.

### ID and naming

The directory name is the skill ID and must match
`^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 characters. The frontmatter `name` is a
human label and is not validated against the directory.

### Frontmatter

```yaml
---
name: Notebook editing
description: One sentence stating the trigger. This is the only text the model sees before loading.
status: active
---
```

| Field | Required | Enforced by |
|---|---|---|
| `description` | yes | loader (skills without one are not advertised) and lint |
| `name` | recommended | nothing — display only |
| `status` | yes | **lint only** — one of `active`, `suspect`, `archived` |
| `reason` | only when `status: archived` | **lint only** |

`status` and `reason` are documentation for humans. The loader ignores them.
This is deliberate: see the consequences below.

### Archive

Retired skills move to `.opencode/skills/.archive/<id>/SKILL.md`.

The dot prefix is load-bearing. An underscore-prefixed `_archive/` would
still be a discoverable source directory, and an underscore-prefixed
`_archive/<id>/SKILL.md` would therefore load as a live skill. Only hidden
directories are skipped.

## Consequences

- **The lint script is the only enforcement of lifecycle state.** A skill with
  `status: archived` sitting in `.opencode/skills/` is still live. `tools/skills-lint.sh`
  must fail when the frontmatter `status` disagrees with the directory
  (archived-shaped `status` outside `.archive/`, or non-archived `status`
  inside it).
- Skills inherit the repository's agent set (`docsmith`, `reviewer`, `scout`,
  `worker` are global), so a repo-scoped skill is available to every agent
  working in this tree. There is no per-agent skill allowlist in v1; scoping
  is done with `permissions` entries of action `skill` if that becomes
  necessary.
- The retrieval indexer indexes `.md` files. `.archive` is listed in
  `SKIP_PARTS` in `tools/retrieval-mcp/retrieval_mcp.py`, so archived skills do
  not surface in semantic search. The active skill files *are* indexed — that
  is what makes "which skill applies to this task" a search (see
  `tools/skills_routing_eval.py`).
- Six-directory depth limit: nesting under `.opencode/skills/` beyond
  `.archive/<id>/` is not permitted by lint.

## Alternatives rejected

- **Custom `archived: true` flag instead of a directory move.** The loader
  would still advertise the skill. Rejected: silently loads retired content.
- **Global `~/.config/opencode/skills`.** Keeps skills out of reviewed diffs
  and out of the git history that staleness detection relies on.
- **Flat `.md` files.** No private base directory for references or scripts,
  and no file sample in the loaded context.
