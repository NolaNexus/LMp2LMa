"""Auto-graded final exam grader - reads checkpoints/*.json and extracts notebook outputs.

Status semantics:
  PASS          percentage >= 70 and every checkpoint notebook was executed
  FAIL          percentage < 70
  NOT_EXECUTED  one or more checkpoints could not be graded because the notebook
                has no stored outputs (run the notebook first)

Exit codes: 0 only for PASS. FAIL, NOT_EXECUTED and ERROR exit 1, so CI cannot
mistake an ungraded notebook for a passing one (ROADMAP §0.2).
"""

import argparse
import json
import os
import re
import sys

import nbformat

CHECKPOINT_DIR = "checkpoints"
NOTEBOOK_DIR = "."

TRACK_DIRS = {
    "track_01_ml_programmer": "track-01-ml-programmer",
    "track_02_dl_programmer": "track-02-dl-programmer",
    "track_03_ml_engineer": "track-03-ml-engineer",
    "track_04_ml_architect": "track-04-ml-architect",
}


def extract_notebook_outputs(notebook_path):
    """Return {cell_key: [output strings]} and whether the notebook had any outputs."""
    outputs = {}
    try:
        with open(notebook_path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:  # pragma: no cover - defensive
        print(f"Warning: could not read {notebook_path}: {e}", file=sys.stderr)
        return outputs, False

    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code" or not cell.get("outputs"):
            continue
        cell_outputs = []
        for output in cell.outputs:
            if output.output_type == "execute_result":
                cell_outputs.append(output.data.get("text/plain", ""))
            elif output.output_type == "stream":
                cell_outputs.append(output.text)
            elif output.output_type == "error":
                cell_outputs.append(f"ERROR: {output.ename}: {output.evalue}")
        if cell_outputs:
            outputs[f"cell_{i}"] = cell_outputs
    return outputs, bool(outputs)


def _as_text(value) -> str:
    return "" if value is None else str(value)


def _match_question(question, outputs):
    """Return (passed, actual) for one checkpoint question.

    Checkpoints do not map questions to cells, so every stored output is
    considered a candidate and the question passes if any candidate satisfies
    it. `actual` reports the first satisfying output (or the closest concept
    match) for diagnostics.
    """
    q_type = question.get("type", "")
    expected = _as_text(question.get("expected"))
    candidates = [_as_text(out) for outs in outputs.values() for out in outs]
    if not candidates:
        return False, None

    if q_type == "concept":
        keywords = [kw for kw in expected.lower().split() if kw]
        if not keywords:
            return False, None
        needed = max(1, (len(keywords) + 1) // 2)
        scored = [(sum(1 for kw in keywords if kw in cand.lower()), cand) for cand in candidates]
        best_hits, best = max(scored, key=lambda pair: pair[0])
        return best_hits >= needed, best if best_hits else None

    if q_type == "metric":
        numbers = []
        for cand in candidates:
            match = re.search(r"[\d.]+", cand)
            if match:
                try:
                    numbers.append((float(match.group()), cand))
                except ValueError:
                    continue
        if not numbers:
            return False, None
        try:
            expected_num = float(re.search(r"[\d.]+", expected).group())
        except (AttributeError, ValueError):
            return False, numbers[0][1]
        if ">" in expected:
            winners = [cand for num, cand in numbers if num > expected_num]
            return bool(winners), winners[0] if winners else numbers[0][1]
        if "<" in expected:
            winners = [cand for num, cand in numbers if num < expected_num]
            return bool(winners), winners[0] if winners else numbers[0][1]
        winners = [cand for num, cand in numbers if abs(num - expected_num) <= 0.1]
        return bool(winners), winners[0] if winners else numbers[0][1]

    if q_type == "code_output":
        for cand in candidates:
            if expected and expected.lower() in cand.lower():
                return True, cand
        return False, None

    for cand in candidates:
        if expected and expected in cand:
            return True, cand
    return False, None


def _normalise_scope(only_notebooks):
    """Accept None, an iterable of paths, or a path to a newline-separated file."""
    if only_notebooks is None:
        return None
    if isinstance(only_notebooks, (str, os.PathLike)):
        candidate = os.fspath(only_notebooks)
        if os.path.isfile(candidate):
            with open(candidate, encoding="utf-8") as f:
                entries = [line.strip() for line in f if line.strip()]
        else:
            entries = [part.strip() for part in candidate.split(",") if part.strip()]
    else:
        entries = list(only_notebooks)
    return {os.path.basename(entry) for entry in entries}


def grade_track(
    track_id, notebook_dir=NOTEBOOK_DIR, checkpoint_dir=CHECKPOINT_DIR, only_notebooks=None
):
    """Grade a track by comparing checkpoint expectations to notebook outputs.

    `only_notebooks` scopes grading to the notebooks the caller actually
    executed. Checkpoints for other notebooks are not counted, so a scoped CI
    run reports NOT_EXECUTED only when a notebook it *did* run lacks outputs.
    """
    checkpoint_file = os.path.join(checkpoint_dir, f"{track_id}.json")
    if not os.path.exists(checkpoint_file):
        return {
            "track": track_id,
            "error": "Checkpoint file not found",
            "score": 0,
            "status": "ERROR",
        }

    with open(checkpoint_file, encoding="utf-8") as f:
        data = json.load(f)

    track_name = data.get("track", track_id)
    checkpoints = data.get("checkpoints", [])
    final_exam = data.get("final_exam", {})
    scope = _normalise_scope(only_notebooks)
    if scope is not None:
        checkpoints = [cp for cp in checkpoints if cp.get("notebook") in scope]
        if not checkpoints:
            return {
                "track": track_name,
                "error": "No checkpoints match the requested notebook scope",
                "score": 0,
                "status": "ERROR",
            }

    results = {
        "track": track_name,
        "checkpoints": [],
        "total_score": 0,
        "max_score": 0,
        "notebooks_missing_outputs": [],
        "scoped_notebooks": sorted(scope) if scope is not None else None,
    }

    track_dir = TRACK_DIRS.get(track_id, track_id)

    for cp in checkpoints:
        cp_id = cp.get("id", "")
        notebook_name = cp.get("notebook", "")
        questions = cp.get("questions", [])

        notebook_path = os.path.join(notebook_dir, track_dir, notebook_name)
        outputs, had_outputs = extract_notebook_outputs(notebook_path)
        if not had_outputs:
            results["notebooks_missing_outputs"].append(notebook_name)

        cp_result = {
            "id": cp_id,
            "notebook": notebook_name,
            "executed": had_outputs,
            "questions": [],
            "score": 0,
            "max_score": len(questions),
        }

        for q in questions:
            passed, actual = _match_question(q, outputs) if had_outputs else (False, None)
            cp_result["questions"].append(
                {
                    "id": q.get("id", ""),
                    "type": q.get("type", ""),
                    "prompt": q.get("prompt", ""),
                    "expected": _as_text(q.get("expected")),
                    "actual": actual,
                    "passed": passed,
                }
            )
            if passed:
                cp_result["score"] += 1

        results["checkpoints"].append(cp_result)
        results["total_score"] += cp_result["score"]
        results["max_score"] += cp_result["max_score"]

    results["final_exam"] = final_exam
    results["percentage"] = (
        round(results["total_score"] / results["max_score"] * 100, 1)
        if results["max_score"] > 0
        else 0.0
    )

    if results["notebooks_missing_outputs"]:
        results["status"] = "NOT_EXECUTED"
    elif results["percentage"] >= 70:
        results["status"] = "PASS"
    else:
        results["status"] = "FAIL"

    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Grade ML Architect track checkpoints")
    parser.add_argument("track", help="Track ID (e.g., track_01_ml_programmer)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--notebook-dir",
        default=NOTEBOOK_DIR,
        help="Directory containing track folders (default: repo root)",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=CHECKPOINT_DIR,
        help="Directory containing checkpoint JSON (default: checkpoints)",
    )
    parser.add_argument(
        "--only-notebooks",
        default=None,
        help="Grade only these notebooks: a file with one path per line, or a comma list",
    )
    args = parser.parse_args(argv)

    result = grade_track(
        args.track,
        notebook_dir=args.notebook_dir,
        checkpoint_dir=args.checkpoint_dir,
        only_notebooks=args.only_notebooks,
    )

    # NOT_EXECUTED is a failure: a checkpoint that could not be graded is not a
    # pass (ROADMAP §0.2). Only a fully executed, >=70% track exits 0.
    exit_code = 0 if result.get("status") == "PASS" else 1

    if args.json:
        print(json.dumps(result, indent=2))
        return exit_code

    print(f"Track: {result['track']}")
    if result.get("error"):
        print(f"Error: {result['error']}")
        return exit_code
    print(f"Score: {result['total_score']}/{result['max_score']} ({result['percentage']}%)")
    print(f"Status: {result['status']}")
    for cp in result["checkpoints"]:
        executed = "" if cp["executed"] else "  [not executed]"
        print(f"  {cp['id']}: {cp['score']}/{cp['max_score']}{executed}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
