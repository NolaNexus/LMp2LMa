# Archived skills

Retired skills live here as `<id>/SKILL.md` with `status: archived` and a
`reason` in the frontmatter.

The leading dot is load-bearing: OpenCode skips hidden directories when
discovering skills, so nothing under this directory is advertised or loaded.
An underscore-prefixed `_archive/` would still be scanned, and its skills would
load normally.

Rules, from `docs/adr/ADR-003-skill-lifecycle.md`:

- A skill moves here only after a human decision, recorded in the commit.
- `archived` is terminal. Do not restore a skill from this directory; derive a
  new one instead.
- The `reason` fields accumulate into the quarterly "don't rebuild this" list.

## Decommission checklist

1. Set `status: archived` and add `reason:` in the frontmatter.
2. Move the directory to `.opencode/skills/.archive/<id>/`.
3. Run `tools/skills-lint.sh` — it fails if `status` and location disagree.
4. Run `tools/skills_routing_eval.py` and drop the retired skill from
   `docs/skills/routing-tasks.json` if it appears there.
5. Reindex so the retired text leaves the search index: call
   `reindex(paths=[".opencode/skills"])` on the retrieval MCP.
