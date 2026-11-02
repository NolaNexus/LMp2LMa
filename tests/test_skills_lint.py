"""Regression tests for tools/skills_lint.py.

The lint is the only enforcement of ADR-001 (archive location) and ADR-003
(lifecycle state), so its behaviour is pinned here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT = ROOT / "tools" / "skills_lint.py"
SKILLS = ROOT / ".opencode" / "skills"

GOOD_BODY = textwrap.dedent(
    """
    ## Workflow

    Do the thing with enough words that the body length warning stays quiet,
    which requires a little more prose than one might first expect.

    ## Don't

    Don't do the other thing.
    """
)


def write_skill(root: Path, skill_id: str, frontmatter: str, body: str = GOOD_BODY) -> Path:
    directory = root / skill_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "SKILL.md"
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
    return path


def run_lint(skills_dir: Path, *extra: str) -> tuple[int, dict]:
    result = subprocess.run(
        [
            sys.executable,
            str(LINT),
            "--json",
            "--no-embed",
            "--skills-dir",
            str(skills_dir),
            *extra,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode, json.loads(result.stdout)


def codes(payload: dict) -> set[str]:
    return {finding["code"] for finding in payload["findings"]}


def test_repo_skills_pass_lint():
    code, payload = run_lint(SKILLS)
    errors = [f for f in payload["findings"] if f["level"] == "error"]
    assert errors == [], errors
    assert code == 0
    assert payload["active"], "no active skills found"


def test_missing_frontmatter_and_description(tmp_path):
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    code, payload = run_lint(tmp_path)
    assert code == 1
    assert {"S001", "S002"} <= codes(payload)


def test_missing_dont_section(tmp_path):
    write_skill(
        tmp_path,
        "no-dont",
        "name: x\ndescription: Something.\nstatus: active\n",
        "## Only\n\nText.\n",
    )
    code, payload = run_lint(tmp_path)
    assert code == 1
    assert "S006" in codes(payload)


def test_dead_path_and_command(tmp_path):
    body = (
        "## Workflow\n\nUse `missing/does-not-exist.md`.\n\n"
        "```bash\nnot-a-real-command --flag\n```\n\n## Don't\n\nDon't.\n"
    )
    write_skill(tmp_path, "dead", "name: x\ndescription: Something.\nstatus: active\n", body)
    code, payload = run_lint(tmp_path)
    assert code == 1
    assert {"S008", "S009"} <= codes(payload)


def test_invalid_skill_id(tmp_path):
    write_skill(tmp_path, "Not An Id", "name: x\ndescription: Something.\nstatus: active\n")
    code, payload = run_lint(tmp_path)
    assert code == 1
    assert "S003" in codes(payload)


def test_archived_status_outside_archive(tmp_path):
    write_skill(
        tmp_path,
        "zombie",
        "name: x\ndescription: Something.\nstatus: archived\nreason: done\n",
    )
    code, payload = run_lint(tmp_path)
    assert code == 1
    assert "S005" in codes(payload)


def test_archived_skill_inside_archive_is_clean(tmp_path):
    root = tmp_path / ".archive" / "retired"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "---\nname: x\ndescription: Something.\nstatus: archived\nreason: superseded\n---\n\nold\n",
        encoding="utf-8",
    )
    code, payload = run_lint(tmp_path)
    assert payload["archived"] == ["retired"]
    assert payload["findings"] == []
    assert code == 0


def test_duplicate_descriptions_fail(tmp_path):
    same = "Search the repository semantically with the local retrieval server instead of grep."
    template = "name: x\ndescription: {}\nstatus: active\n"
    write_skill(tmp_path, "alpha", template.format(same))
    write_skill(tmp_path, "beta", template.format(same))
    payload = json.loads(
        subprocess.run(
            [sys.executable, str(LINT), "--json", "--skills-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        ).stdout
    )
    errors = [f for f in payload["findings"] if f["code"] == "S010" and f["level"] == "error"]
    assert errors, payload["findings"]
