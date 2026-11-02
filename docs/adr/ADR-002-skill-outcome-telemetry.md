# ADR-002: Skill outcome telemetry

- **Status:** Accepted
- **Date:** 2026-11-02
- **Depends on:** ADR-001

## Context

The loop needs to know three things about every skill load:

1. Which queries were asked (`search`).
2. Which skill fired in response.
3. Whether the turn ended well.

The original plan put the query log at the retrieval MCP `search` boundary
and added an `outcome` field to each record. Phase 0 established that this
cannot work as written:

- The MCP runs as a separate long-lived process (tmux session
  `retrieval-mcp`, port `8765`, path `/mcp`). It has no session identity.
- The tool signature is `search(query, k, rerank)`. It receives no caller,
  agent, or session ID.
- There is no hook from the OpenCode server into the MCP process.

An `outcome` written server-side would therefore have to be guessed at write
time or filled by a second `report_outcome` tool call the model is asked to
remember. Both are fabrication or compliance theatre.

Meanwhile, better evidence already exists one layer up, in the OpenCode
session database `~/.local/share/opencode/opencode.db`:

- `part.data` for `type: "tool"` rows stores the tool name, its input, its
  output, and its status — so both `retrieval_search` queries and `skill`
  loads are persisted exactly as they happened.
- `session_v2` carries `idle_outcome` (observed values: `null` and
  `"succeeded"`), plus `cost`, token counters, `summary_files`, and
  `time_idle`.

## Decision

### The retrieval MCP stays unmodified

M1–M2 add no writes to `retrieval_mcp.py` telemetry. If the search log is
kept at all, it is a separate append-only file written by the MCP for its own
latency, with no `outcome` field. Do not add one.

### Telemetry is extracted from the session database

An offline, read-only extractor (`tools/skills_telemetry.py`) reconstructs
events:

| Event | Source |
|---|---|
| query → results | `part` rows where tool is `retrieval_search` (input `query`, output `results[].path`) |
| skill fired | `part` rows where tool is `skill` (input `id`) |
| turn ended | `session_v2.idle_outcome` |
| corrective turn | subsequent user `text` parts matching correction markers |

The extractor opens the database **read-only** (`file:...?mode=ro`). It never
writes, migrates, or vacuums.

### Accepted outcome definition

A skill load counts as a success when **all** hold:

1. `idle_outcome = "succeeded"` for the session, and
2. no corrective user turn occurs within the next **N = 3** user messages, and
3. the skill load is not followed by an `idle_outcome` reset to `null`.

A corrective turn is a user message matching a fixed marker list (`no`,
`wrong`, `still`, `actually`, `not what`, `that's not`, `doesn't work`,
`broken`, `try again`, `I said`). The list lives in
`tools/skills_telemetry.py`. This is a heuristic, and it is labelled as one
everywhere it is reported.

The extractor reads both persisted schema families — the current
`session_message` content blocks (`{"type": "tool", "name": ...}`) and the
older `part` rows (`{"type": "tool", "tool": ...}`) — and both call shapes:
direct MCP calls, and Code Mode `execute` calls whose JavaScript contains
`tools.retrieval.search({ query: ... })`.

### Proxy is not ground truth

This is the single most important line in this ADR:

> The session-database outcome is a **proxy**. The only labelled outcomes in
> this system come from the Phase 5 golden task set.

Every report generated from the extractor carries the word "proxy", and
trigger precision numbers derived from it are reported separately from the
golden-task numbers. Conflating them would let a heuristic optics problem
retire a working skill.

### Where reports live

- Raw extract: `artifacts/skills/` (gitignored, like `artifacts/retrieval/`).
- Weekly gap report, once reviewed: `docs/skills/gap-report-YYYY-Www.md`
  (committed — the archive's "don't rebuild this" ledger depends on it
  surviving).

## Consequences

- Zero agent cooperation required. Nothing depends on a model remembering to
  call a reporting tool, so the >70%-populated gate in the build plan becomes
  a property of the harness rather than of compliance.
- `idle_outcome` is populated on a minority of sessions today (5 of 34
  observed). Records without it are still useful: they establish that a skill
  fired and that a query preceded it. They are counted in the denominator and
  reported as unlabelled, never dropped.
- The extraction schema depends on OpenCode internals. It will break on a
  major version change, and when it does it fails loudly, because it reads
  named columns rather than a blob.

## Alternatives rejected

- **`report_outcome` MCP tool.** Compliance-dependent, adds a write surface
  to a read-only service, and the model would have to be instructed to use it
  — which is exactly the context tax this system exists to remove.
- **An OpenCode server plugin writing hook events.** Works, and is the better
  long-term home for live instrumentation, but it adds a TypeScript/Bun
  toolchain and a plugin lifecycle to a repository that has neither. Deferred
  until the extractor proves the data is worth collecting live.
- **Server-side heuristic outcome (e.g. "results were fetched").** Measures
  whether the agent continued, not whether the answer was right.
