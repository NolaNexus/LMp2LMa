#!/usr/bin/env python3
"""Routing eval for the M2 gate: can `search` find the right skill, and only then?

Each task in docs/skills/routing-tasks.json is run through the retrieval store
restricted to `.opencode/skills`. A task passes when:

  * it names a skill (`"skill": "name"`) and that skill ranks first with a
    score at or above `--min-score`, or
  * it is a negative control (`"skill": null`) and no skill clears the score.

Run with the retrieval venv:

    tools/retrieval-mcp/.venv/bin/python tools/skills_routing_eval.py
    tools/retrieval-mcp/.venv/bin/python tools/skills_routing_eval.py --json

Exit status is 0 when the pass rate meets `--threshold` (default 0.8).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "tools" / "retrieval-mcp"
DEFAULT_TASKS = ROOT / "docs" / "skills" / "routing-tasks.json"
SKILLS_PREFIX = ".opencode/skills"
MIN_SCORE = 0.5


def load_store():
    sys.path.insert(0, str(MCP_DIR))
    import retrieval_mcp  # noqa: PLC0415 - path is set above

    return retrieval_mcp.STORE


def skill_of(path: str) -> str | None:
    prefix = SKILLS_PREFIX + "/"
    if not path.startswith(prefix):
        return None
    return path[len(prefix) :].split("/")[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill routing eval.")
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--threshold", type=float, default=0.8, help="required pass rate")
    parser.add_argument("--min-score", type=float, default=MIN_SCORE)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    spec = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    tasks = spec["tasks"]

    store = load_store()
    store.ensure_index()

    results = []
    for item in tasks:
        hits = store.search(item["task"], k=args.k, paths=[SKILLS_PREFIX])
        top = hits[0] if hits else None
        top_skill = skill_of(top.path) if top else None
        top_score = round(top.score, 4) if top else 0.0
        routed = top_skill if top_score >= args.min_score else None
        results.append(
            {
                "task": item["task"],
                "expected": item["skill"],
                "routed": routed,
                "top_skill": top_skill,
                "top_score": top_score,
                "ranked": [skill_of(hit.path) or "?" for hit in hits],
                "pass": routed == item["skill"],
            }
        )

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    rate = passed / total if total else 0.0
    ok = rate >= args.threshold

    if args.json:
        print(
            json.dumps(
                {
                    "passed": passed,
                    "total": total,
                    "rate": round(rate, 3),
                    "threshold": args.threshold,
                    "ok": ok,
                    "results": results,
                },
                indent=2,
            )
        )
        return 0 if ok else 1

    print(
        f"skills-routing: {passed}/{total} routed correctly "
        f"({rate:.0%}, threshold {args.threshold:.0%}, min score {args.min_score})"
    )
    for result in results:
        mark = "PASS" if result["pass"] else "FAIL"
        expected = result["expected"] or "(no skill)"
        routed = result["routed"] or "(none)"
        print(f"  {mark}  {result['task']}")
        print(
            f"        expected {expected:<18} routed {routed:<18} "
            f"top score {result['top_score']:.4f}"
        )
    print(f"skills-routing: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
