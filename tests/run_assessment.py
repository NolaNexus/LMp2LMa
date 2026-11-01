"""Assessment runner: executes pytest + nbval + checkpoint validation"""
import subprocess
import sys
import json
from pathlib import Path

def run_nbval():
    """Run nbval on all notebooks"""
    cmd = [
        sys.executable, "-m", "pytest", 
        "--nbval", "--nbval-lax",
        "-v", "--tb=short",
        "track-01-ml-programmer", "track-02-dl-programmer",
        "track-03-ml-engineer", "track-04-ml-architect"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    return result.returncode == 0, result.stdout, result.stderr

def run_unit_tests():
    """Run unit tests"""
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-m", "not slow"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return result.returncode == 0, result.stdout, result.stderr

def validate_checkpoints():
    """Validate checkpoint JSON structure"""
    cp_dir = Path("checkpoints")
    errors = []
    for cp_file in cp_dir.glob("*.json"):
        try:
            with open(cp_file) as f:
                data = json.load(f)
            # Validate required fields
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
    return len(errors) == 0, errors

if __name__ == "__main__":
    print("=" * 60)
    print("ML ARCHITECT JOURNEY - ASSESSMENT RUNNER")
    print("=" * 60)
    
    # Validate checkpoints
    print("\n[1/3] Validating checkpoint JSON...")
    ok, errors = validate_checkpoints()
    if ok:
        print("  ✅ Checkpoints valid")
    else:
        print("  ❌ Checkpoint errors:")
        for e in errors:
            print(f"    - {e}")
    
    # Run unit tests
    print("\n[2/3] Running unit tests...")
    ok, out, err = run_unit_tests()
    if ok:
        print("  ✅ Unit tests passed")
    else:
        print("  ❌ Unit tests failed")
        print(err[:500])
    
    # Run nbval (notebook validation)
    print("\n[3/3] Running nbval notebook validation...")
    print("  (This may take several minutes...)")
    ok, out, err = run_nbval()
    if ok:
        print("  ✅ All notebooks execute successfully")
    else:
        print("  ⚠️  Some notebooks had errors (see output)")
        print(err[:1000])
    
    print("\n" + "=" * 60)
    print("ASSESSMENT COMPLETE")
    print("=" * 60)
