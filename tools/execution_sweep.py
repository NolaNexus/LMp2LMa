"""Execute every notebook in QUICK_MODE and record pass/fail in a report.

Usage:
    python tools/execution_sweep.py [--quick / --no-quick] [--timeout SECONDS]
                                    [--only track-01-ml-programmer]

Runs `jupyter nbconvert --execute` per notebook into a temporary directory so
the source notebooks are never modified. Writes `.kilo/execution_report.md`.
"""
import argparse
import datetime as dt
import os
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
REPORT = ROOT / ".kilo" / "execution_report.md"


def notebooks(only: str | None):
    for track in TRACKS:
        if only and track != only:
            continue
        yield from sorted((ROOT / track).glob("*.ipynb"))


def first_error(output: str) -> str:
    lines = [ln.strip() for ln in output.splitlines() if ln.strip()]
    for ln in lines:
        if "Error" in ln or "Exception" in ln or "error:" in ln:
            return ln[:300]
    return lines[-1][:300] if lines else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", dest="quick", action="store_true", default=True)
    parser.add_argument("--no-quick", dest="quick", action="store_false")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--only", default=None)
    args = parser.parse_args()

    env = dict(os.environ)
    env["QUICK_MODE"] = "1" if args.quick else "0"

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
            results.append((str(rel), ok, detail))
            suffix = f" :: {detail}" if detail else ""
            print(f"{'PASS' if ok else 'FAIL'} {rel}{suffix}")

    passed = sum(1 for _, ok, _ in results if ok)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Notebook Execution Report",
        "",
        f"- Generated: {stamp}",
        f"- QUICK_MODE: {args.quick}",
        f"- Timeout per notebook: {args.timeout}s",
        f"- Result: {passed}/{len(results)} passed",
        "",
        "| Notebook | Status | First error |",
        "|---|---|---|",
    ]
    for rel, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        safe_detail = detail.replace("|", "\\|")
        lines.append(f"| `{rel}` | {status} | {safe_detail} |")
    REPORT.write_text("\n".join(lines) + "\n")

    print(f"\n{passed}/{len(results)} passed. Report: {REPORT.relative_to(ROOT)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())