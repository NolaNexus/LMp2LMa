#!/usr/bin/env python3
"""Phase 5 A/B: does having a skill change what the agent actually does?

Each task in docs/skills/golden-tasks.json runs twice in a throwaway git
worktree at HEAD:

  with     .opencode/skills present
  without  .opencode/skills removed

Both arms see the same repository content, the same model, and the same agent.
Only the skill tree differs. Success is mechanical: every `check` entry must
exit 0 and every `expect_contains` substring must appear in the agent's text.

Sandbox sealing (two known leak paths, both controlled):

  * OpenCode resolves its session directory from $PWD, not the process cwd,
    so the harness launches every opencode run with PWD set to the sandbox.
  * The global retrieval MCP is rooted at the real checkout, so each sandbox
    gets an identical project-level opencode.jsonc (discovered from the
    sandbox parent directory, never inside the worktree) that overrides the
    `retrieval` server with a local stdio instance rooted at the sandbox.
    A seal probe runs before every arm and fails loudly if skills are
    reachable in `without` or if stats.root is not the sandbox.

Metrics per run: success, tool calls, skill loads, corrective markers,
duration.

Usage:
    tools/skills_ab.py --dry-run
    tools/skills_ab.py --task gt-06
    tools/skills_ab.py --arm with --task gt-01 gt-03
    tools/skills_ab.py --out artifacts/skills/ab/$(date +%Y%m%d-%H%M)

Exit status is 0 when the run completed, 1 on harness failure (not on task
failure -- task results are data, not errors).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS = ROOT / "docs" / "skills" / "golden-tasks.json"
SANDBOX_ROOT = Path("/tmp/opencode/skills-ab")
MCP_VENV_PY = ROOT / "tools" / "retrieval-mcp" / ".venv" / "bin" / "python"

sys.path.insert(0, str(ROOT / "tools"))
from skills_telemetry import CORRECTIVE_RE  # noqa: E402


@dataclass
class Run:
    task: str
    arm: str
    ok: bool = False
    duration: float = 0.0
    tool_calls: int = 0
    skill_loads: list[str] = field(default_factory=list)
    corrections: int = 0
    failed_checks: list[str] = field(default_factory=list)
    missing_expected: list[str] = field(default_factory=list)
    agent_exit: int | None = None
    text: str = ""
    error: str | None = None


class TreeEscape(RuntimeError):
    """Raised when the main working tree changed during an arm."""


def run(cmd: list[str] | str, cwd: Path, timeout: float, shell: bool = False, env=None):
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=shell,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def tree_state() -> tuple[str, str]:
    head = run(["git", "rev-parse", "HEAD"], ROOT, 30).stdout.strip()
    status = run(["git", "status", "--porcelain"], ROOT, 30).stdout
    return head, status


def make_sandbox(task_id: str, arm: str) -> Path:
    """Create the sandbox worktree under its per-task parent directory.

    Layout: <root>/<arm>/<task>/opencode.jsonc + <root>/<arm>/<task>/wt.
    The project config lives in the parent so OpenCode discovers it from the
    worktree without adding anything the worktree's own git status would see.
    """
    parent = SANDBOX_ROOT / arm / task_id
    path = parent / "wt"
    if path.exists():
        run(["git", "worktree", "remove", "--force", str(path)], ROOT, 120)
        if path.exists():
            run(f"rm -rf {path}", ROOT, 120, shell=True)
    parent.mkdir(parents=True, exist_ok=True)
    result = run(["git", "worktree", "add", "--detach", str(path), "HEAD"], ROOT, 180)
    if result.returncode != 0:
        raise RuntimeError(f"worktree add failed: {result.stderr.strip()}")
    return path


def drop_sandbox(task_id: str, arm: str) -> None:
    path = SANDBOX_ROOT / arm / task_id / "wt"
    run(["git", "worktree", "remove", "--force", str(path)], ROOT, 120)
    if path.exists():
        run(f"rm -rf {path}", ROOT, 120, shell=True)


def agent_env(cwd: Path) -> dict[str, str]:
    """OpenCode resolves the session directory from $PWD; subprocess.run only
    sets the process cwd. Pin both to the sandbox."""
    return {**os.environ, "PWD": str(cwd)}


def write_mcp_config(parent: Path, worktree: Path) -> None:
    """Override the global retrieval MCP with a local instance rooted at the
    sandbox. Identical mechanism for both arms; only RETRIEVAL_ROOT differs."""
    script = worktree / "tools" / "retrieval-mcp" / "retrieval_mcp.py"
    config = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "servers": {
                "retrieval": {
                    "type": "local",
                    "command": [
                        str(MCP_VENV_PY),
                        str(script),
                        "--transport",
                        "stdio",
                    ],
                    "environment": {
                        "RETRIEVAL_ROOT": str(worktree),
                        "RETRIEVAL_INDEX_DIR": str(worktree / "artifacts" / "retrieval" / "index"),
                    },
                    "timeout": {"startup": 120000},
                }
            }
        },
    }
    (parent / "opencode.jsonc").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def build_index(worktree: Path, arm: str, timeout: float = 900) -> None:
    """Give the sandbox an index it can load inside the MCP startup budget.

    Embedding 1000+ chunks takes minutes, so the index is built once per arm
    and copied into later sandboxes. Both arms get the same treatment, so the
    staleness (a task's `setup` edits are not re-embedded) is symmetric.
    """
    target = worktree / "artifacts" / "retrieval" / "index"
    cache = SANDBOX_ROOT / "index-cache" / arm
    if cache.is_dir():
        shutil.copytree(cache, target)
        return
    env = {
        **os.environ,
        "RETRIEVAL_ROOT": str(worktree),
        "RETRIEVAL_INDEX_DIR": str(target),
    }
    proc = run(
        [
            str(MCP_VENV_PY),
            str(worktree / "tools" / "retrieval-mcp" / "retrieval_mcp.py"),
            "--reindex",
            "--build-only",
        ],
        worktree,
        timeout,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"index build failed: {proc.stderr.strip()[:300]}")
    if arm == "without":
        chunks = json.loads((target / "chunks.json").read_text(encoding="utf-8"))
        leaked = [c["path"] for c in chunks if ".opencode/skills" in c["path"]]
        if leaked:
            raise RuntimeError(f"index build: {len(leaked)} skill chunks in the without arm")
    cache.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target, cache)


SEAL_PROMPT = (
    "Do exactly two things, then print one final line and nothing else after it. "
    "1) Call the skill tool with id 'repo-orientation'. "
    "2) Call the retrieval MCP 'stats' tool. "
    "Final line, exactly this format: PROBE SKILL=loaded|failed ROOT=<stats root path> "
    "Use SKILL=loaded if the skill tool returned content, SKILL=failed if it errored."
)
SKILL_RE = re.compile(r"SKILL=(loaded|failed)")
ROOT_RE = re.compile(r"ROOT=(\S+)")


def seal_probe(worktree: Path, arm: str, agent: str) -> None:
    """Prove the seal before the real task runs; a leak is a harness failure."""
    proc = run(
        [
            "opencode",
            "run",
            "--format",
            "json",
            "--agent",
            agent,
            "--auto",
            "--title",
            f"ab-seal {arm}",
            SEAL_PROMPT,
        ],
        worktree,
        240,
        env=agent_env(worktree),
    )
    text, _, _ = parse_transcript(proc.stdout)
    skill = SKILL_RE.search(text)
    root = ROOT_RE.search(text)
    if not skill or not root:
        raise RuntimeError(f"seal probe unparseable: {text.strip()[:200]!r}")
    if root.group(1) != str(worktree):
        raise RuntimeError(f"seal probe: retrieval root is {root.group(1)}, expected {worktree}")
    if arm == "without" and skill.group(1) != "failed":
        raise RuntimeError("seal probe: skill loaded in the without arm")
    if arm == "without":
        # The without arm must not be able to git-restore skills either.
        restore = run("git checkout -- .opencode/skills 2>&1", worktree, 60, shell=True)
        if Path(worktree / ".opencode" / "skills").exists():
            raise RuntimeError(f"seal probe: git restored skills ({restore.stdout.strip()[:120]})")
    if arm == "with" and skill.group(1) != "loaded":
        raise RuntimeError("seal probe: skill failed to load in the with arm")


def parse_transcript(stdout: str) -> tuple[str, int, list[str]]:
    text_parts: list[str] = []
    tools = 0
    skills: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        part = event.get("part") or {}
        if part.get("type") == "text":
            text_parts.append(part.get("text", ""))
        elif part.get("type") == "tool":
            tools += 1
            if str(part.get("tool", "")).lower() == "skill":
                state = part.get("state") or {}
                inputs = state.get("input") or {}
                # A load must have completed with content; an errored or empty
                # call is an attempt, not a load.
                succeeded = state.get("status") in (None, "completed") and bool(
                    state.get("content") or state.get("output")
                )
                if succeeded:
                    skills.append(str(inputs.get("id") or "unknown"))
    return "\n".join(text_parts), tools, skills


def run_arm(
    task: dict,
    arm: str,
    agent: str,
    timeout: float,
    keep: bool,
    baseline: tuple[str, str],
) -> Run:
    result = Run(task=task["id"], arm=arm)
    started = time.time()
    sandbox = None
    try:
        sandbox = make_sandbox(task["id"], arm)
        write_mcp_config(sandbox.parent, sandbox)
        if arm == "without":
            # Deleting tracked files is not enough: an agent can (and did)
            # `git checkout -- .opencode/skills` them back from HEAD. Commit
            # the deletion so the sandbox history has no skills to restore.
            run("git rm -r -q .opencode/skills", sandbox, 60, shell=True)
            run(
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
                sandbox,
                60,
            )

        for step in task.get("setup", []) or []:
            if "python" in step:
                proc = run([sys.executable, "-c", step["python"]], sandbox, 120)
            else:
                proc = run(step["cmd"], sandbox, 120, shell=True)
            if proc.returncode != 0:
                result.error = f"setup failed: {proc.stderr.strip()[:300]}"
                return result

        build_index(sandbox, arm)
        seal_probe(sandbox, arm, agent)

        head, status = tree_state()
        if (head, status) != baseline:
            raise TreeEscape("main tree changed before the agent run")

        cmd = [
            "opencode",
            "run",
            "--format",
            "json",
            "--agent",
            agent,
            "--auto",
            "--title",
            f"ab {task['id']} {arm}",
            task["prompt"],
        ]
        proc = run(cmd, sandbox, timeout, env=agent_env(sandbox))
        result.agent_exit = proc.returncode
        result.text, result.tool_calls, result.skill_loads = parse_transcript(proc.stdout)
        result.corrections = len(CORRECTIVE_RE.findall(result.text))

        head, status = tree_state()
        if (head, status) != baseline:
            raise TreeEscape("main tree changed during the agent run")

        for check in task.get("check", []) or []:
            if "python" in check:
                label = "python: " + check["python"].splitlines()[0][:70]
                run_result = run([sys.executable, "-c", check["python"]], sandbox, 180)
            else:
                label = check["cmd"]
                run_result = run(check["cmd"], sandbox, 180, shell=True)
            if run_result.returncode != 0:
                result.failed_checks.append(label)

        for expected in task.get("expect_contains", []) or []:
            if expected not in result.text:
                result.missing_expected.append(expected)

        result.ok = (
            result.agent_exit == 0 and not result.failed_checks and not result.missing_expected
        )
    except subprocess.TimeoutExpired:
        result.error = f"timeout after {timeout}s"
    except (RuntimeError, TreeEscape) as exc:
        result.error = str(exc)
    finally:
        result.duration = round(time.time() - started, 1)
        if sandbox is not None and not keep:
            drop_sandbox(task["id"], arm)
    return result


def render_markdown(results: list[Run], tasks: dict[str, dict]) -> str:
    lines = [
        "| task | skills | with | without | tools (w/wo) | skills loaded (w/wo) | corr (w/wo) |",
        "|---|---|---|---|---|---|---|",
    ]
    by_key = {(r.task, r.arm): r for r in results}
    for task_id, task in tasks.items():
        w = by_key.get((task_id, "with"))
        wo = by_key.get((task_id, "without"))
        mark = lambda r: "-" if r is None else ("PASS" if r.ok else "FAIL")  # noqa: E731
        tools = lambda r: "-" if r is None else f"{r.tool_calls}"  # noqa: E731
        loads = lambda r: "-" if r is None else (",".join(r.skill_loads) or "none")  # noqa: E731
        corr = lambda r: "-" if r is None else f"{r.corrections}"  # noqa: E731
        skills = ",".join(task.get("skills") or []) or "(control)"
        lines.append(
            f"| {task_id} | {skills} | {mark(w)} | {mark(wo)} | "
            f"{tools(w)}/{tools(wo)} | {loads(w)}/{loads(wo)} | {corr(w)}/{corr(wo)} |"
        )
    return "\n".join(lines)


def skill_verdicts(results: list[Run], tasks: dict[str, dict]) -> dict[str, str]:
    """kept: at least one task the skill covers passes only with skills.
    suspect: every covered task behaves identically in both arms."""
    by_key = {(r.task, r.arm): r for r in results}
    verdicts: dict[str, str] = {}
    for skill in sorted({s for t in tasks.values() for s in t.get("skills") or []}):
        covered = [t for t in tasks.values() if skill in (t.get("skills") or [])]
        delta = [
            t_id
            for t in covered
            if (t_id := t["id"])
            and by_key.get((t_id, "with"))
            and by_key.get((t_id, "without"))
            and by_key[(t_id, "with")].ok
            and not by_key[(t_id, "without")].ok
        ]
        verdicts[skill] = "kept" if delta else "suspect"
    return verdicts


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 skill A/B runner.")
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--task", nargs="*", default=None, help="subset of task ids")
    parser.add_argument("--arm", choices=["with", "without", "both"], default="both")
    parser.add_argument("--agent", default="build")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--out", default=None, help="directory for report + transcripts")
    parser.add_argument("--keep", action="store_true", help="keep sandbox worktrees")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    spec = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    tasks = {task["id"]: task for task in spec["tasks"]}
    if args.task:
        missing = [t for t in args.task if t not in tasks]
        if missing:
            print(f"unknown task(s): {', '.join(missing)}", file=sys.stderr)
            return 1
        tasks = {k: v for k, v in tasks.items() if k in args.task}

    arms = ["with", "without"] if args.arm == "both" else [args.arm]

    if args.dry_run:
        print(
            f"skills-ab: {len(tasks)} task(s) x {len(arms)} arm(s) = {len(tasks) * len(arms)} run(s)"
        )
        for task_id, task in tasks.items():
            print(
                f"  {task_id}  arms={'/'.join(arms)}  skills={','.join(task.get('skills') or []) or '(control)'}"
            )
            print(f"        {task['prompt'][:100]}")
        print(f"  sandbox root: {SANDBOX_ROOT}")
        return 0

    if not MCP_VENV_PY.exists():
        print(f"skills-ab: MCP venv missing: {MCP_VENV_PY}", file=sys.stderr)
        return 1

    baseline = tree_state()
    results: list[Run] = []
    for task_id, task in tasks.items():
        for arm in arms:
            print(f"  running {task_id} [{arm}] ...", flush=True)
            result = run_arm(task, arm, args.agent, args.timeout, args.keep, baseline)
            results.append(result)
            if result.error and "main tree changed" in result.error:
                print(f"    ABORT ({result.error})", file=sys.stderr)
                _write_out(args, results, tasks)
                return 1
            verdict = "PASS" if result.ok else "FAIL"
            detail = ""
            if result.error:
                detail = f" ({result.error})"
            elif not result.ok:
                bits = result.failed_checks + [f"missing:{m}" for m in result.missing_expected]
                detail = f" ({'; '.join(bits)[:160]})"
            print(
                f"    {verdict}  tools={result.tool_calls} "
                f"skills={','.join(result.skill_loads) or 'none'} "
                f"{result.duration:.0f}s{detail}",
                flush=True,
            )

    head, status = tree_state()
    if (head, status) != baseline:
        print(
            "skills-ab: ABORT — the main working tree changed during the run; "
            "a task escaped its sandbox. Inspect `git status` before continuing.",
            file=sys.stderr,
        )
        _write_out(args, results, tasks)
        return 1

    controls = [r for r in results if not (tasks[r.task].get("skills") or []) and r.skill_loads]
    for r in controls:
        print(
            f"skills-ab: WARNING control {r.task} [{r.arm}] loaded skills: "
            f"{','.join(r.skill_loads)}",
            file=sys.stderr,
        )

    if args.out:
        _write_out(args, results, tasks)

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return 0

    print("\n" + render_markdown(results, tasks))
    verdicts = skill_verdicts(results, tasks)
    if len(arms) == 2:
        print("\nskills-ab: verdicts (kept = a covered task passes only with skills)")
        for skill, verdict in verdicts.items():
            print(f"  {skill:<22} {verdict}")
    return 0


def _write_out(args, results: list[Run], tasks: dict[str, dict]) -> None:
    if not args.out:
        return
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8"
    )
    verdicts = skill_verdicts(results, tasks) if len({r.arm for r in results}) == 2 else {}
    lines = [render_markdown(results, tasks)]
    if verdicts:
        lines += [
            "",
            "verdicts:",
            *(f"- {skill}: {verdict}" for skill, verdict in verdicts.items()),
        ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nreport: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    sys.exit(main())
