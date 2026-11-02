---
name: Authoring skills
description: Write or revise an OpenCode skill in .opencode/skills — the frontmatter contract, ID rules, the archive convention, and the facts-first brief a reviewer will check.
status: active
---

# Authoring skills

Use when adding a skill, revising one, or retiring one. This skill encodes how
this repository writes skills; the loader's behaviour is documented in
`docs/adr/ADR-001-skill-format-and-location.md`.

## Before drafting: facts first

A skill that states something false is worse than no skill, because the model
cannot tell the difference. Build the brief before the prose:

1. Every path, command, port, and filename in the draft must have been seen —
   in a file listing, a `search` result, or a command you ran. Cite the source
   next to the claim while drafting, then delete the citations.
2. Anything unverified is written as an open question, not as guidance.
3. If a fact cannot be established, cut the sentence. Do not hedge it into
   vagueness — a vague instruction is still an instruction.

## Format

```
.opencode/skills/<id>/SKILL.md
```

- `<id>` is the directory name, matches `^[a-z0-9]+(-[a-z0-9]+)*$`, and is what
  the model passes to the `skill` tool. The frontmatter `name` is display only.
- Frontmatter requires `description` and `status`. `status` is `active`,
  `suspect`, or `archived`, and is enforced by lint, not by the loader.
- Required sections: a `## Don't` section, and at least one other `##` heading.

## Writing the description

The description is the entire context cost of a skill that never fires, and
the entire trigger signal of a skill that does. It must say **when to use it**,
not what the skill contains:

- Lead with the trigger: "Use when …", or a verb phrase naming the task.
- Name the concrete nouns a task will contain (file types, paths, tool names).
- Stay under roughly 300 characters.
- Stay clearly distinct from every other skill's description —
  `tools/skills-lint.sh` embeds descriptions and fails on near-duplicates.

## Body

- Short and imperative. Target 40–80 lines.
- Tables for layout facts, ordered steps for procedures, bold only for the one
  line that matters most.
- Put the failure mode in `## Don't` — the mistakes the model would make
  without the skill.

## The handoff

A skill draft goes Docsmith → Reviewer → merge. Docsmith writes prose from a
facts-first brief. Reviewer checks only two things: whether every factual
claim is supported, and whether the description would fire on the intended
tasks and stay silent on the rest. Two correction rounds maximum, then stop
and escalate.

## Lifecycle

- Lint failure or staleness flags a skill; a human sets `status: suspect`.
- Retirement moves the directory to `.opencode/skills/.archive/<id>/` and sets
  `status: archived` plus a `reason`. See
  `docs/adr/ADR-003-skill-lifecycle.md`.
- Archived skills are never revived; a new need produces a new skill.

## Verify before committing

```bash
tools/skills-lint.sh
```

It checks frontmatter, required sections, dead path and command references,
description overlap, and staleness against git history. It exits non-zero on
errors. Advisory warnings do not block.

## Don't

- Don't name the archive directory with an underscore prefix. The loader skips
  hidden directories only, so an underscore-prefixed archive would load as a
  set of live skills.
- Don't set `archived: true` and expect the loader to respect it. Custom
  frontmatter keys are inert; only the directory location removes a skill.
- Don't write a skill for something a single `AGENTS.md` line already covers.
  The rule of three applies: three occurrences before a skill exists.
- Don't restate `AGENTS.md` routing tables inside a skill — they drift, and
  the duplicate is the copy that goes stale.
- Don't ship a skill whose description was never tested against real task
  phrasings. Routing failures are silent.
