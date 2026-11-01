"""Auto-graded final exam grader - reads checkpoints/*.json and extracts notebook outputs"""
import json
import sys
import os
import re
import nbformat
from pathlib import Path

CHECKPOINT_DIR = "checkpoints"
NOTEBOOK_DIR = "."

TRACK_DIRS = {
    "track_01_ml_programmer": "track-01-ml-programmer",
    "track_02_dl_programmer": "track-02-dl-programmer",
    "track_03_ml_engineer": "track-03-ml-engineer",
    "track_04_ml_architect": "track-04-ml-architect",
}


def extract_notebook_outputs(notebook_path):
    """Extract outputs from executed notebook cells"""
    outputs = {}
    try:
        with open(notebook_path, 'r') as f:
            nb = nbformat.read(f, as_version=4)

        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code' and cell.outputs:
                cell_outputs = []
                for output in cell.outputs:
                    if output.output_type == 'execute_result':
                        cell_outputs.append(output.data.get('text/plain', ''))
                    elif output.output_type == 'stream':
                        cell_outputs.append(output.text)
                    elif output.output_type == 'error':
                        cell_outputs.append(f"ERROR: {output.ename}: {output.evalue}")
                if cell_outputs:
                    outputs[f'cell_{i}'] = cell_outputs
    except Exception as e:
        print(f"Warning: Could not extract outputs from {notebook_path}: {e}")
    return outputs


def grade_track(track_id):
    """Grade a track by comparing checkpoint expectations to notebook outputs"""
    checkpoint_file = os.path.join(CHECKPOINT_DIR, f"{track_id}.json")
    if not os.path.exists(checkpoint_file):
        return {"track": track_id, "error": "Checkpoint file not found", "score": 0}

    with open(checkpoint_file) as f:
        data = json.load(f)

    track_name = data.get("track", track_id)
    checkpoints = data.get("checkpoints", [])
    final_exam = data.get("final_exam", {})

    results = {
        "track": track_name,
        "checkpoints": [],
        "total_score": 0,
        "max_score": 0
    }

    for cp in checkpoints:
        cp_id = cp.get("id", "")
        notebook_name = cp.get("notebook", "")
        questions = cp.get("questions", [])

        notebook_path = os.path.join(NOTEBOOK_DIR, track_id.replace("Track ", "track-").lower().replace(" ", "-"), notebook_name)
        if not os.path.exists(notebook_path):
            # Try track-specific directory mapping
            track_dir = TRACK_DIRS.get(track_id, track_id.replace("Track ", "track-").lower().replace(" ", "-"))
            notebook_path = os.path.join(NOTEBOOK_DIR, track_dir, notebook_name)
        if not os.path.exists(notebook_path):
            notebook_path = os.path.join(NOTEBOOK_DIR, notebook_name)

        outputs = extract_notebook_outputs(notebook_path)

        cp_result = {
            "id": cp_id,
            "notebook": notebook_name,
            "questions": [],
            "score": 0,
            "max_score": len(questions)
        }

        for q in questions:
            q_id = q.get("id", "")
            q_type = q.get("type", "")
            prompt = q.get("prompt", "")
            expected = q.get("expected", "")

            q_result = {
                "id": q_id,
                "type": q_type,
                "prompt": prompt,
                "expected": expected,
                "actual": None,
                "passed": False
            }

            # Try to find matching output
            actual = None
            for cell_key, cell_outputs in outputs.items():
                for out in cell_outputs:
                    if expected in str(out) or (isinstance(expected, str) and expected.lower() in out.lower()):
                        actual = out
                        break
                if actual:
                    break

            q_result["actual"] = actual

            # Simple pass/fail logic
            if actual is not None:
                if q_type == "code_output" and expected in ["True", "true"]:
                    q_result["passed"] = "True" in str(actual)
                elif q_type == "metric":
                    # Extract number and compare
                    try:
                        actual_num = float(re.search(r'[\d.]+', str(actual)).group())
                        expected_num = float(re.search(r'[\d.]+', str(expected)).group())
                        if ">" in str(expected):
                            q_result["passed"] = actual_num > expected_num
                        elif "<" in str(expected):
                            q_result["passed"] = actual_num < expected_num
                        else:
                            q_result["passed"] = abs(actual_num - expected_num) < 0.1
                    except:
                        q_result["passed"] = False
                elif q_type == "concept":
                    # Keyword matching for concept questions
                    expected_keywords = expected.lower().split()
                    actual_text = str(actual).lower()
                    q_result["passed"] = any(kw in actual_text for kw in expected_keywords)
                else:
                    q_result["passed"] = str(expected) in str(actual)

            if q_result["passed"]:
                cp_result["score"] += 1

            cp_result["questions"].append(q_result)

        results["checkpoints"].append(cp_result)
        results["total_score"] += cp_result["score"]
        results["max_score"] += cp_result["max_score"]

    # Final exam score (placeholder)
    results["final_exam"] = final_exam
    results["percentage"] = round(results["total_score"] / results["max_score"] * 100, 1) if results["max_score"] > 0 else 0
    results["status"] = "PASS" if results["percentage"] >= 70 else "FAIL"

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Grade ML Architect track checkpoints")
    parser.add_argument("track", help="Track ID (e.g., track_01_ml_programmer)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = grade_track(args.track)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Track: {result['track']}")
        print(f"Score: {result['total_score']}/{result['max_score']} ({result['percentage']}%)")
        print(f"Status: {result['status']}")
        for cp in result["checkpoints"]:
            print(f"  {cp['id']}: {cp['score']}/{cp['max_score']}")


if __name__ == "__main__":
    main()