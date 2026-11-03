#!/usr/bin/env python3
"""Extract skill and retrieval telemetry from the OpenCode session database.

Read-only. Opens `opencode.db` with `mode=ro` and never writes, migrates, or
vacuums. See docs/adr/ADR-002-skill-outcome-telemetry.md.

What it reconstructs, per session:

  * retrieval `search` calls and their queries
  * `skill` loads and which skill ID was loaded
  * whether each skill load was followed by a corrective user turn
  * the session's `idle_outcome`

The success figure produced here is a **proxy**: `idle_outcome = succeeded`
with no corrective turn in the next 3 user messages. The only labelled
outcomes in this system come from the Phase 5 golden task set.

Usage:
    tools/skills_telemetry.py
    tools/skills_telemetry.py --json --since 14
    tools/skills_telemetry.py --out artifacts/skills/events.jsonl
    tools/skills_telemetry.py --explain

Exit status is 0 on a successful read, 1 when the database is unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"

# Wording that suggests the user is correcting the agent. Heuristic by design.
CORRECTIVE_PATTERNS = [
    r"\bno\b",
    r"\bnope\b",
    r"\bwrong\b",
    r"\bstill\b",
    r"\bactually\b",
    r"\bnot what\b",
    r"\bthat'?s not\b",
    r"\bdoesn'?t work\b",
    r"\bbroken\b",
    r"\btry again\b",
    r"\bi said\b",
]
CORRECTIVE_RE = re.compile("|".join(CORRECTIVE_PATTERNS), re.IGNORECASE)
CORRECTIVE_WINDOW = 3

QUERY_RE = re.compile(r'"?query"?\s*:\s*"([^"]+)"')
SKILL_ID_RE = re.compile(r'"id"\s*:\s*"\s*([a-z0-9][a-z0-9-]*)\s*"')

SKILL_TOOL_NAMES = {"skill"}
EXECUTE_TOOL_NAMES = {"execute", "run", "bash"}


@dataclass
class SkillLoad:
    session_id: str
    time: int
    skill: str
    agent: str | None
    directory: str | None
    search_query: str | None
    idle_outcome: str | None
    corrective_turn: str | None
    outcome: str


@dataclass
class SearchCall:
    session_id: str
    time: int
    query: str
    tool: str


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"session database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=10)


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}


def _loads(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _tool_blocks(conn: sqlite3.Connection, tables: set[str]) -> list[tuple[str, int, dict]]:
    """Yield (session_id, time_created, tool_block) from both schema families."""
    blocks: list[tuple[str, int, dict]] = []
    if "session_message" in tables:
        for session_id, created, data in conn.execute(
            "select session_id, time_created, data from session_message "
            "where type = 'assistant' order by time_created"
        ):
            payload = _loads(data)
            for block in payload.get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "tool":
                    blocks.append((session_id, created, block))
    if "part" in tables:
        for session_id, created, data in conn.execute(
            "select session_id, time_created, data from part order by time_created"
        ):
            payload = _loads(data)
            if payload.get("type") == "tool":
                blocks.append((session_id, created, payload))
    blocks.sort(key=lambda item: item[1])
    return blocks


def _user_messages(conn: sqlite3.Connection, tables: set[str]) -> dict[str, list[tuple[int, str]]]:
    """session_id -> [(time_created, text)] for user turns."""
    messages: dict[str, list[tuple[int, str]]] = {}
    if "session_message" in tables:
        for session_id, created, data in conn.execute(
            "select session_id, time_created, data from session_message "
            "where type = 'user' order by time_created"
        ):
            payload = _loads(data)
            text = payload.get("text") or ""
            if not text:
                for block in payload.get("content", []) or []:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")
            messages.setdefault(session_id, []).append((created, text))
    if "message" in tables:
        # Older schema: user text lives in message/part rows.
        for session_id, created, data in conn.execute(
            "select session_id, time_created, data from message order by time_created"
        ):
            payload = _loads(data)
            if payload.get("role") != "user":
                continue
            messages.setdefault(session_id, []).append((created, json.dumps(payload)))
    for items in messages.values():
        items.sort()
    return messages


def _sessions(conn: sqlite3.Connection, tables: set[str]) -> dict[str, dict]:
    if "session_v2" not in tables:
        if "session" in tables:
            return {
                row[0]: {"directory": None, "agent": None, "idle_outcome": None}
                for row in conn.execute("select id from session")
            }
        return {}
    columns = {row[1] for row in conn.execute("pragma table_info(session_v2)")}
    select = ["id", "directory", "agent", "time_created"]
    select.append("idle_outcome" if "idle_outcome" in columns else "null")
    rows = conn.execute(f"select {', '.join(select)} from session_v2").fetchall()
    return {
        row[0]: {
            "directory": row[1],
            "agent": row[2],
            "time_created": row[3],
            "idle_outcome": row[4],
        }
        for row in rows
    }


def _block_tool_name(block: dict) -> str:
    return str(block.get("name") or block.get("tool") or "").lower()


def _block_input(block: dict) -> dict:
    state = block.get("state")
    if isinstance(state, dict) and isinstance(state.get("input"), dict):
        return state["input"]
    if isinstance(block.get("input"), dict):
        return block["input"]
    return {}


def _block_ok(block: dict) -> bool:
    state = block.get("state")
    if isinstance(state, dict) and state.get("status") not in (None, "completed"):
        return False
    return True


def _query_from(inputs: dict) -> str | None:
    query = inputs.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    # Code-mode calls carry a JS snippet: tools.retrieval.search({ query: "..." })
    # Un-escape the JSON dump first so both `"query":` and `query:` match.
    blob = json.dumps(inputs).replace('\\"', '"')
    match = QUERY_RE.search(blob)
    if match:
        return match.group(1).strip()
    return None


def _skill_from(name: str, inputs: dict) -> str | None:
    if name in SKILL_TOOL_NAMES:
        for key in ("id", "skill", "name"):
            value = inputs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        blob = json.dumps(inputs)
        match = SKILL_ID_RE.search(blob)
        if match:
            return match.group(1)
        return None
    if "skill" in name:
        value = inputs.get("id")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_search(name: str, inputs: dict) -> bool:
    if "search" in name and "websearch" not in name:
        return True
    if name in EXECUTE_TOOL_NAMES:
        blob = json.dumps(inputs)
        return "retrieval" in blob and "search" in blob
    return False


def _corrective(messages: list[tuple[int, str]], after: int) -> str | None:
    later = [text for (created, text) in messages if created > after][:CORRECTIVE_WINDOW]
    for text in later:
        match = CORRECTIVE_RE.search(text)
        if match:
            return match.group(0).lower()
    return None


def collect(db_path: Path) -> tuple[list[SkillLoad], list[SearchCall], dict]:
    conn = _connect(db_path)
    try:
        tables = _table_names(conn)
        sessions = _sessions(conn, tables)
        blocks = _tool_blocks(conn, tables)
        user_messages = _user_messages(conn, tables)
    finally:
        conn.close()

    searches: list[SearchCall] = []
    loads: list[SkillLoad] = []

    for session_id, created, block in blocks:
        if not _block_ok(block):
            continue
        name = _block_tool_name(block)
        inputs = _block_input(block)

        if _is_search(name, inputs):
            query = _query_from(inputs)
            if query:
                searches.append(
                    SearchCall(session_id=session_id, time=created, query=query, tool=name)
                )
            continue

        skill = _skill_from(name, inputs)
        if not skill:
            continue

        session = sessions.get(session_id, {})
        recent = [
            call for call in searches if call.session_id == session_id and call.time <= created
        ]
        search_query = recent[-1].query if recent else None
        corrective = _corrective(user_messages.get(session_id, []), created)
        idle = session.get("idle_outcome")

        if corrective:
            outcome = "corrected"
        elif idle == "succeeded":
            outcome = "succeeded"
        else:
            outcome = "unlabelled"

        loads.append(
            SkillLoad(
                session_id=session_id,
                time=created,
                skill=skill,
                agent=session.get("agent"),
                directory=session.get("directory"),
                search_query=search_query,
                idle_outcome=idle,
                corrective_turn=corrective,
                outcome=outcome,
            )
        )

    summary = {
        "sessions": len(sessions),
        "sessions_with_idle_outcome": sum(1 for s in sessions.values() if s.get("idle_outcome")),
        "search_calls": len(searches),
        "skill_loads": len(loads),
    }
    return loads, searches, summary


def summarize(loads: list[SkillLoad], searches: list[SearchCall], base: dict) -> dict:
    labelled = [load for load in loads if load.outcome != "unlabelled"]
    succeeded = [load for load in loads if load.outcome == "succeeded"]
    corrected = [load for load in loads if load.outcome == "corrected"]

    per_skill: dict[str, dict[str, int]] = {}
    for load in loads:
        bucket = per_skill.setdefault(
            load.skill, {"loads": 0, "succeeded": 0, "corrected": 0, "unlabelled": 0}
        )
        bucket["loads"] += 1
        bucket[load.outcome] += 1

    return {
        **base,
        "labelled_loads": len(labelled),
        "succeeded": len(succeeded),
        "corrected": len(corrected),
        "unlabelled": len(loads) - len(labelled),
        "proxy_success_rate": (round(len(succeeded) / len(labelled), 3) if labelled else None),
        "search_to_skill_rate": (round(len(loads) / len(searches), 3) if searches else None),
        "per_skill": per_skill,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="path to opencode.db (opened read-only)",
    )
    parser.add_argument("--since", type=float, default=None, help="days of history")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--explain", action="store_true", help="print every event")
    parser.add_argument("--out", default=None, help="write events as JSONL")
    args = parser.parse_args()

    try:
        loads, searches, base = collect(Path(args.db))
    except (FileNotFoundError, sqlite3.Error, OSError) as exc:
        print(f"skills-telemetry: {exc}", file=sys.stderr)
        return 1

    if args.since is not None:
        cutoff = int((time.time() - args.since * 86400) * 1000)
        loads = [load for load in loads if load.time >= cutoff]
        searches = [call for call in searches if call.time >= cutoff]
        base["since_days"] = args.since

    summary = summarize(loads, searches, base)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as handle:
            for load in loads:
                handle.write(json.dumps(asdict(load), sort_keys=True) + "\n")

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summary,
                    "loads": [asdict(load) for load in loads],
                    "searches": [asdict(call) for call in searches],
                },
                indent=2,
            )
        )
        return 0

    print("skills-telemetry: proxy outcomes from the OpenCode session database")
    for key in (
        "sessions",
        "sessions_with_idle_outcome",
        "search_calls",
        "skill_loads",
        "labelled_loads",
        "succeeded",
        "corrected",
        "unlabelled",
        "proxy_success_rate",
        "search_to_skill_rate",
    ):
        print(f"  {key:<28} {summary[key]}")
    if summary["per_skill"]:
        print("  per skill:")
        for skill, bucket in sorted(summary["per_skill"].items()):
            print(
                f"    {skill:<22} loads={bucket['loads']:<3} "
                f"succeeded={bucket['succeeded']:<3} corrected={bucket['corrected']:<3} "
                f"unlabelled={bucket['unlabelled']}"
            )
    if args.explain:
        print("  events:")
        for load in loads:
            stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(load.time / 1000))
            print(
                f"    {stamp}  {load.skill:<22} {load.outcome:<12} "
                f"agent={load.agent or '?'} query={(load.search_query or '-')[:40]}"
            )
    if not loads:
        print("  no skill loads recorded yet (expected until skills have been used)")
    print("  note: proxy, not ground truth — labelled outcomes come from the golden task set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
