"""Tests for the checkpoint grader using small fixture notebooks."""

import json
import sys
from pathlib import Path

import nbformat
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from final_exam_grader import _match_question, grade_track  # noqa: E402


def _write_notebook(path: Path, outputs: list[str] | None):
    nb = nbformat.v4.new_notebook()
    cell = nbformat.v4.new_code_cell("print('result')")
    cell.execution_count = 1
    if outputs:
        cell.outputs = [
            nbformat.v4.new_output("stream", name="stdout", text=text) for text in outputs
        ]
    nb.cells.append(cell)
    nbformat.write(nb, str(path))


@pytest.fixture
def graded_track(tmp_path):
    """Create one track with one checkpoint referencing a fixture notebook."""
    track_dir = tmp_path / "track-01-ml-programmer"
    track_dir.mkdir()
    cp_dir = tmp_path / "checkpoints"
    cp_dir.mkdir()

    checkpoint = {
        "track": "Track 1: ML Programmer",
        "checkpoints": [
            {
                "id": "cp1",
                "notebook": "01_demo.ipynb",
                "skills": ["demo"],
                "questions": [
                    {"id": "q1", "type": "code_output", "prompt": "true?", "expected": "True"},
                    {"id": "q2", "type": "metric", "prompt": "accuracy", "expected": "> 0.8"},
                    {
                        "id": "q3",
                        "type": "concept",
                        "prompt": "why",
                        "expected": "schema validation profiling",
                    },
                ],
            }
        ],
        "final_exam": {"questions": []},
    }
    (cp_dir / "track_01_ml_programmer.json").write_text(json.dumps(checkpoint))

    def _run(outputs):
        _write_notebook(track_dir / "01_demo.ipynb", outputs)
        return grade_track(
            "track_01_ml_programmer", notebook_dir=str(tmp_path), checkpoint_dir=str(cp_dir)
        )

    return _run


def test_all_questions_pass(graded_track):
    result = graded_track(
        [
            "True\n",
            "accuracy = 0.91\n",
            "Automated schema validation and profiling\n",
        ]
    )
    assert result["status"] == "PASS"
    assert result["total_score"] == 3
    assert result["percentage"] == 100.0


def test_metric_threshold_fails(graded_track):
    result = graded_track(["True\n", "accuracy = 0.55\n", "schema validation and profiling\n"])
    assert result["status"] == "FAIL"
    assert result["total_score"] == 2


def test_concept_requires_majority_of_keywords(graded_track):
    # Only one of three keywords present -> should not pass
    result = graded_track(["True\n", "accuracy = 0.95\n", "schema\n"])
    concept = result["checkpoints"][0]["questions"][2]
    assert concept["passed"] is False


def test_missing_outputs_reports_not_executed(graded_track):
    result = graded_track(None)
    assert result["status"] == "NOT_EXECUTED"
    assert result["notebooks_missing_outputs"] == ["01_demo.ipynb"]
    assert result["total_score"] == 0


def test_non_string_expected_does_not_crash():
    passed, actual = _match_question(
        {"id": "q", "type": "code_output", "expected": 1}, {"cell_0": ["1\n"]}
    )
    assert actual == "1\n"
    assert passed is True


def test_missing_checkpoint_file(tmp_path):
    result = grade_track(
        "track_01_ml_programmer", notebook_dir=str(tmp_path), checkpoint_dir=str(tmp_path)
    )
    assert result["status"] == "ERROR"
    assert "not found" in result["error"]
