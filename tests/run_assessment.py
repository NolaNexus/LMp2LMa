"""Assessment runner: structural validation + unit tests + notebook execution."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAST_SUBSET = [
    "track-01-ml-programmer/01_data_preprocessing.ipynb",
    "track-01-ml-programmer/02_experiment_tracking.ipynb",
    "track-02-dl-programmer/01_nn_fundamentals.ipynb",
    "track-02-dl-programmer/02_cnn_vision.ipynb",
]


def _run(cmd, timeout):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def run_validator():
    result = _run([sys.executable, "tools/validate_notebooks.py"], timeout=300)
    return result.returncode == 0, result.stdout, result.stderr


def run_unit_tests():
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "-m", "not slow"]
    result = _run(cmd, timeout=600)
    return result.returncode == 0, result.stdout, result.stderr


def run_nbval():
    """Execute the fast subset and compare with nbval in lax mode."""
    cmd = [sys.executable, "-m", "pytest", "--nbval-lax", "-q", "--tb=short"] + FAST_SUBSET
    result = _run(cmd, timeout=3600)
    return result.returncode == 0, result.stdout, result.stderr


def validate_checkpoints():
    errors = []
    for cp_file in (ROOT / "checkpoints").glob("*.json"):
        try:
            data = json.loads(cp_file.read_text())
            assert "track" in data
            assert "checkpoints" in data
            assert "final_exam" in data
            for cp in data["checkpoints"]:
                assert "id" in cp
                assert "notebook" in cp
                assert "skills" in cp
                assert "questions" in cp
        except Exception as e:
            errors.append(f"{cp_file}: {e}")
    return not errors, errors


def main() -> int:
    print("=" * 60)
    print("ML ARCHITECT JOURNEY - ASSESSMENT RUNNER")
    print("=" * 60)

    print("\n[1/4] Validating notebook structure...")
    ok, out, err = run_validator()
    print("  PASS" if ok else f"  FAIL\n{err[:2000]}")
    if not ok:
        return 1

    print("\n[2/4] Validating checkpoint JSON...")
    ok, errors = validate_checkpoints()
    print("  PASS" if ok else "  FAIL\n  - " + "\n  - ".join(errors))
    if not ok:
        return 1

    print("\n[3/4] Running unit tests...")
    ok, out, err = run_unit_tests()
    print("  PASS" if ok else f"  FAIL\n{out[-2000:]}")
    if not ok:
        return 1

    print("\n[4/4] Executing fast notebook subset (nbval lax)...")
    ok, out, err = run_nbval()
    print("  PASS" if ok else f"  FAIL\n{(out + err)[-3000:]}")
    print("\n" + "=" * 60)
    print("ASSESSMENT COMPLETE" if ok else "ASSESSMENT HAS FAILURES")
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())