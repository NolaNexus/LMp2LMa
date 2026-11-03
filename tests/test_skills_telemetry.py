"""Regression tests for tools/skills_telemetry.py.

Builds a throwaway session database with the real table shapes and checks the
ADR-002 outcome proxy: `idle_outcome = succeeded` with no corrective user turn
in the next 3 user messages.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import skills_telemetry as telemetry  # noqa: E402

SCHEMA = """
create table session_v2 (
    id text primary key,
    directory text,
    agent text,
    time_created integer,
    idle_outcome text
);
create table session_message (
    id text,
    session_id text,
    type text,
    seq integer,
    time_created integer,
    time_updated integer,
    data text
);
create table part (
    id text,
    message_id text,
    session_id text,
    time_created integer,
    time_updated integer,
    data text
);
"""


def build_db(path: Path) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)

    conn.execute(
        "insert into session_v2 values (?, ?, ?, ?, ?)",
        ("ses-ok", "/repo", "build", 1, "succeeded"),
    )
    conn.execute(
        "insert into session_v2 values (?, ?, ?, ?, ?)",
        ("ses-corrected", "/repo", "build", 1, "succeeded"),
    )
    conn.execute(
        "insert into session_v2 values (?, ?, ?, ?, ?)",
        ("ses-unlabelled", "/repo", "build", 1, None),
    )

    def tool_message(message_id: str, session: str, when: int, blocks: list[dict]) -> None:
        conn.execute(
            "insert into session_message values (?, ?, ?, ?, ?, ?, ?)",
            (
                message_id,
                session,
                "assistant",
                when,
                when,
                when,
                json.dumps({"content": blocks}),
            ),
        )

    def user_message(message_id: str, session: str, when: int, text: str) -> None:
        conn.execute(
            "insert into session_message values (?, ?, ?, ?, ?, ?, ?)",
            (message_id, session, "user", when, when, when, json.dumps({"text": text})),
        )

    def exec_search(query: str, when: int) -> dict:
        return {
            "type": "tool",
            "name": "execute",
            "state": {
                "status": "completed",
                "input": {"code": f'tools.retrieval.search({{ query: "{query}" }})'},
            },
        }

    def skill(id_: str) -> dict:
        return {
            "type": "tool",
            "name": "skill",
            "state": {"status": "completed", "input": {"id": id_}},
        }

    # Session 1: search, then a skill load, then a clean finish.
    user_message("m1", "ses-ok", 1000, "find the retrieval docs")
    tool_message("m2", "ses-ok", 1100, [exec_search("how does the index work", 1100)])
    tool_message("m3", "ses-ok", 1200, [skill("retrieval-mcp")])
    user_message("m4", "ses-ok", 1300, "thanks, that worked")

    # Session 2: skill load, then a corrective turn.
    tool_message("m5", "ses-corrected", 2100, [skill("notebook-editing")])
    user_message("m6", "ses-corrected", 2200, "no, that's wrong, the notebook is broken")

    # Session 3: skill load with no outcome recorded.
    tool_message("m7", "ses-unlabelled", 3100, [skill("repo-orientation")])

    conn.commit()
    conn.close()
    return path


def test_clean_session_is_succeeded(tmp_path):
    loads, searches, base = telemetry.collect(build_db(tmp_path / "ok.db"))
    by_skill = {load.skill: load for load in loads}
    assert len(searches) == 1
    assert searches[0].query == "how does the index work"
    load = by_skill["retrieval-mcp"]
    assert load.outcome == "succeeded"
    assert load.search_query == "how does the index work"
    assert load.agent == "build"
    assert base["sessions_with_idle_outcome"] == 2


def test_corrective_turn_overrides_succeeded_idle_outcome(tmp_path):
    loads, _, _ = telemetry.collect(build_db(tmp_path / "corr.db"))
    by_skill = {load.skill: load for load in loads}
    assert by_skill["notebook-editing"].outcome == "corrected"
    assert by_skill["notebook-editing"].corrective_turn in {"no", "that's not", "broken"}


def test_missing_idle_outcome_is_unlabelled(tmp_path):
    loads, _, _ = telemetry.collect(build_db(tmp_path / "unl.db"))
    by_skill = {load.skill: load for load in loads}
    assert by_skill["repo-orientation"].outcome == "unlabelled"


def test_summary_math(tmp_path):
    loads, searches, base = telemetry.collect(build_db(tmp_path / "sum.db"))
    summary = telemetry.summarize(loads, searches, base)
    assert summary["skill_loads"] == 3
    assert summary["labelled_loads"] == 2
    assert summary["succeeded"] == 1
    assert summary["corrected"] == 1
    assert summary["unlabelled"] == 1
    assert summary["proxy_success_rate"] == 0.5
    assert summary["per_skill"]["retrieval-mcp"]["loads"] == 1


def test_legacy_part_schema_is_read(tmp_path):
    path = build_db(tmp_path / "legacy.db")
    conn = sqlite3.connect(path)
    conn.execute(
        "insert into part values (?, ?, ?, ?, ?, ?)",
        (
            "p1",
            "m9",
            "ses-ok",
            1400,
            1400,
            json.dumps(
                {
                    "type": "tool",
                    "tool": "skill",
                    "state": {"status": "completed", "input": {"id": "authoring-skills"}},
                }
            ),
        ),
    )
    conn.commit()
    conn.close()
    loads, _, _ = telemetry.collect(path)
    assert "authoring-skills" in {load.skill for load in loads}


def test_missing_database_raises():
    with pytest.raises(FileNotFoundError):
        telemetry.collect(Path("/tmp/does-not-exist-opencode.db"))


def test_database_is_opened_read_only(tmp_path):
    path = build_db(tmp_path / "ro.db")
    before = path.read_bytes()
    telemetry.collect(path)
    assert path.read_bytes() == before
