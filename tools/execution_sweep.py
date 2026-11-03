"""Execute every notebook in QUICK_MODE and record pass/fail in a report.

Usage:
    python tools/execution_sweep.py [--quick / --no-quick] [--timeout SECONDS]
                                    [--only track-01-ml-programmer]
                                    [--env-check]

`--env-check` verifies the required imports and exits without sweeping.

Runs `jupyter nbconvert --execute` per notebook into a temporary directory so
the source notebooks are never modified. Writes `artifacts/execution_report.md`
incrementally, so an interrupted sweep still leaves a usable report.
"""

import argparse
import datetime as dt
import importlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKS = [
    "track-01-ml-programmer",
    "track-02-dl-programmer",
    "track-03-ml-engineer",
    "track-04-ml-architect",
]
REPORT = ROOT / "artifacts" / "execution_report.md"

# Root-cause exception header, e.g. "ModuleNotFoundError: No module named 'x'".
_EXC_RE = re.compile(r"^([A-Za-z_][\w.]*(?:Error|Exception|Interrupt|Exit)):\s*(.+)$")

REQUIRED_IMPORTS = [
    "nbformat",
    "nbconvert",
    "pandas",
    "numpy",
    "sklearn",
    "matplotlib",
    "torch",
    "mlflow",
]


def notebooks(only: str | None):
    for track in TRACKS:
        if only and track != only:
            continue
        yield from sorted((ROOT / track).glob("*.ipynb"))


def first_error(output: str) -> str:
    """Return the root-cause exception, not the traceback's `raise` statement."""
    matches = [m for m in (_EXC_RE.match(ln.strip()) for ln in output.splitlines()) if m]
    if matches:
        m = matches[-1]
        # nbconvert reports module-qualified names; the short form classifies.
        name = m.group(1).rsplit(".", 1)[-1]
        return f"{name}: {m.group(2)}"[:300]
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    return lines[-1][:300] if lines else ""


def classify(ok: bool, detail: str) -> str:
    if ok:
        return "PASS"
    if "CellTimeoutError" in detail:
        return "NEEDS_GPU"
    return "FAIL"


def env_check() -> bool:
    missing = []
    for name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(name)
        except Exception:
            missing.append(name)
    if missing:
        print("MISSING IMPORTS: " + ", ".join(missing))
        print(
            "Install before sweeping:\n"
            "  uv pip install --python .venv/bin/python "
            "-r requirements-assessment-heavy.txt"
        )
        return False
    print("Environment OK: " + ", ".join(REQUIRED_IMPORTS))
    return True


def write_report(results, quick: bool, timeout: int, stamp: str) -> None:
    passed = sum(1 for _, s, _ in results if s == "PASS")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Notebook Execution Report",
        "",
        f"- Generated: {stamp}",
        f"- QUICK_MODE: {quick}",
        f"- Timeout per cell: {timeout}s",
        f"- Result: {passed}/{len(results)} passed",
        "",
        "| Notebook | Status | First error |",
        "|---|---|---|",
    ]
    for rel, status, detail in results:
        safe = detail.replace("|", "\\|")
        lines.append(f"| `{rel}` | {status} | {safe} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", dest="quick", action="store_true", default=True)
    parser.add_argument("--no-quick", dest="quick", action="store_false")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--only", default=None)
    parser.add_argument(
        "--env-check",
        action="store_true",
        help="verify required imports and exit (0 ok, 2 missing)",
    )
    args = parser.parse_args()

    if args.env_check:
        return 0 if env_check() else 2

    env = dict(os.environ)
    env["QUICK_MODE"] = "1" if args.quick else "0"
    stamp = dt.datetime.now().isoformat(timespec="seconds")

    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for nb in notebooks(args.only):
            rel = nb.relative_to(ROOT)
            cmd = [
                sys.executable,
                "-m",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                f"--ExecutePreprocessor.timeout={args.timeout}",
                "--output-dir",
                tmp,
                str(nb),
            ]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
            ok = proc.returncode == 0
            detail = "" if ok else first_error(proc.stderr or proc.stdout)
            status = classify(ok, detail)
            results.append((str(rel), status, detail))
            write_report(results, args.quick, args.timeout, stamp)  # incremental
            suffix = f" :: {detail}" if detail else ""
            print(f"{status} {rel}{suffix}")

    write_report(results, args.quick, args.timeout, stamp)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    print(f"\n{passed}/{len(results)} passed. Report: {REPORT.relative_to(ROOT)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
