# ADR-003: Skill lifecycle transitions

- **Status:** Accepted
- **Date:** 2026-11-02
- **Depends on:** ADR-001, ADR-002

## Context

A skill costs context on every model step where its description is
advertised, and it costs attention on every step where it is loaded. That
cost is only repaid while the skill is accurate, correctly triggered, and
still describing the repository as it is. ADR-001 established that the loader
ignores `status` and `reason`, so lifecycle state is a convention enforced by
`tools/skills-lint.sh` and by the directory the skill lives in.

## Decision

### States

| State | Location | `status` | Meaning |
|---|---|---|---|
| `active` | `.opencode/skills/<id>/` | `active` | Loaded and advertised |
| `suspect` | `.opencode/skills/<id>/` | `suspect` | Still loaded; flagged for review at the next cycle |
| `archived` | `.opencode/skills/.archive/<id>/` | `archived` | Not loaded; kept as a historical record |

The `active`/`suspect` distinction is advisory — both are loaded. It exists
so a human reviewer sees the flag in the diff and in the gap report, without
depriving the workspace of a skill that has not yet been retired.

### Automatic transitions (no human in the loop)

These are applied by tooling, and they may only ever move a skill **to
`suspect`**:

| Trigger | Mechanism |
|---|---|
| Lint error on a committed skill | `tools/skills-lint.sh` exit 1; the gap report lists it |
| Referenced path no longer exists | lint check `S006` |
| No fire in a completed review cycle | telemetry extract; gap report |
| Trigger precision below 80% in two consecutive cycles | telemetry extract; gap report |

Automation never writes to a skill file. It surfaces the flag; it does not
edit the frontmatter. A human sets `status: suspect` in the commit that
acknowledges the flag.

### Human-only transitions

Every transition below requires a person, recorded in the commit that makes
it:

| Transition | Requirement |
|---|---|
| `active` → `suspect` | acknowledgement of an automatic flag (commit) |
| `suspect` → `active` | the defect is fixed and lint passes again |
| `suspect` → `archived` | `reason` in frontmatter, directory moved to `.archive/`, reviewer approval |
| `archived` → `active` | **not permitted** |

`archived → active` is forbidden on purpose. Resurrecting a skill restores
the text that already failed, along with whatever assumptions went stale. If
the need is real, derive a new skill from the "don't rebuild this" ledger.

### The archive is a ledger, not a graveyard

`.archive/<id>/SKILL.md` keeps `status: archived` and a `reason` field. The
quarterly review compiles those reasons into a list of approaches this
repository has already rejected, and that list is what the next author reads
before drafting.

## Consequences

- Any state change is visible in `git log` and in a code review, because the
  state is encoded in a path and a frontmatter field — not in a database.
- A skill cannot silently disappear. Retiring it produces a diff.
- A drift between `status` and location is a lint error, so the two cannot
  desynchronise without the build failing.
- Two review cycles must complete before a skill can be archived on
  "no measured delta" grounds, which bounds the damage from one bad
  measurement and bounds the context tax to two cycles.

## Alternatives rejected

- **Automatic archiving.** A tool that both measures and retires can retire
  everything in one bad heuristic, and the failure is silent because the
  skill stops being advertised.
- **Deletion instead of archiving.** Loses the reason, and the same skill
  gets rebuilt six months later.
- **A registry file listing states.** A second source of truth that drifts
  from the directory tree; the tree is already the loader's source of truth.
