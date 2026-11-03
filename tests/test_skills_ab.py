"""Regression tests for tools/skills_ab.py.

The expensive part of the A/B (agent runs) is not tested here. What is tested
is the pair of defects that made the first pilot meaningless:

  * a failed `skill` call counted as a skill load
  * the `without` arm restorable with `git checkout -- .opencode/skills`
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import skills_ab as ab  # noqa: E402


def event(part: dict) -> str:
    return json.dumps({"type": "x", "part": part})


def skill_part(status: str, content=None, id_: str = "authoring-skills") -> dict:
    state = {"status": status, "input": {"id": id_}}
    if content is not None:
        state["content"] = content
    return {"type": "tool", "tool": "skill", "state": state}


def test_failed_skill_call_is_not_a_load():
    stdout = "\n".join(
        [
            event({"type": "text", "text": "trying"}),
            event(skill_part("error")),
        ]
    )
    text, tools, skills = ab.parse_transcript(stdout)
    assert tools == 1
    assert skills == []
    assert text == "trying"


def test_completed_skill_call_without_content_is_not_a_load():
    stdout = event(skill_part("completed"))
    _, _, skills = ab.parse_transcript(stdout)
    assert skills == []


def test_completed_skill_call_with_content_is_a_load():
    stdout = event(skill_part("completed", content=[{"type": "text", "text": "body"}]))
    _, _, skills = ab.parse_transcript(stdout)
    assert skills == ["authoring-skills"]


def test_execute_calls_count_as_tools_not_skills():
    stdout = event({"type": "tool", "tool": "execute", "state": {"status": "completed"}})
    _, tools, skills = ab.parse_transcript(stdout)
    assert tools == 1
    assert skills == []


def test_non_json_lines_are_ignored():
    text, tools, skills = ab.parse_transcript("not json\n{bad json\n")
    assert (text, tools, skills) == ("", 0, [])


def _run(task: str, arm: str, ok: bool) -> ab.Run:
    return ab.Run(task=task, arm=arm, ok=ok)


def test_verdict_kept_when_a_covered_task_passes_only_with_skills():
    tasks = {"gt-05": {"id": "gt-05", "skills": ["authoring-skills"]}}
    results = [_run("gt-05", "with", True), _run("gt-05", "without", False)]
    assert ab.skill_verdicts(results, tasks) == {"authoring-skills": "kept"}


def test_verdict_suspect_when_both_arms_agree():
    tasks = {"gt-05": {"id": "gt-05", "skills": ["authoring-skills"]}}
    for both in (True, False):
        results = [_run("gt-05", "with", both), _run("gt-05", "without", both)]
        assert ab.skill_verdicts(results, tasks) == {"authoring-skills": "suspect"}


def test_verdict_suspect_when_with_arm_fails():
    tasks = {"gt-05": {"id": "gt-05", "skills": ["authoring-skills"]}}
    results = [_run("gt-05", "with", False), _run("gt-05", "without", True)]
    assert ab.skill_verdicts(results, tasks) == {"authoring-skills": "suspect"}


def test_controls_produce_no_verdict():
    tasks = {"gt-09": {"id": "gt-09", "skills": []}}
    results = [_run("gt-09", "with", True), _run("gt-09", "without", True)]
    assert ab.skill_verdicts(results, tasks) == {}


@pytest.mark.skipif(
    subprocess.run(["git", "rev-parse", "--git-dir"], cwd=ROOT, capture_output=True).returncode
    != 0,
    reason="not a git checkout",
)
def test_without_arm_cannot_restore_skills_with_git():
    """The seal: after the without-arm commit, git has nothing to restore."""
    task_id = "unit-seal"
    worktree = ab.make_sandbox(task_id, "without")
    try:
        subprocess.run("git rm -r -q .opencode/skills", cwd=worktree, shell=True, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=skills-ab",
                "-c",
                "user.email=skills-ab@local",
                "commit",
                "-q",
                "-m",
                "without arm: remove skills",
            ],
            cwd=worktree,
            check=True,
            capture_output=True,
        )
        restore = subprocess.run(
            "git checkout -- .opencode/skills",
            cwd=worktree,
            shell=True,
            capture_output=True,
            text=True,
        )
        assert restore.returncode != 0
        assert not (worktree / ".opencode" / "skills").exists()
    finally:
        ab.drop_sandbox(task_id, "without")


def test_index_cache_paths_are_per_arm():
    with_cache = ab.SANDBOX_ROOT / "index-cache" / "with"
    without_cache = ab.SANDBOX_ROOT / "index-cache" / "without"
    assert with_cache != without_cache
