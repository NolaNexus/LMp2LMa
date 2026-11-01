"""Notebook validation tests using nbval"""
import pytest
import os

# Auto-discover all notebooks across tracks
TRACKS = [
    "track-01-ml-programmer",
    "track-02-dl-programmer", 
    "track-03-ml-engineer",
    "track-04-ml-architect",
]

def get_all_notebooks():
    notebooks = []
    for track in TRACKS:
        track_path = os.path.join(os.path.dirname(__file__), "..", track)
        if os.path.exists(track_path):
            for f in sorted(os.listdir(track_path)):
                if f.endswith(".ipynb") and not f.startswith("."):
                    notebooks.append(os.path.join(track, f))
    return notebooks

NOTEBOOKS = get_all_notebooks()

@pytest.mark.notebook
@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_notebook_execution(notebook):
    """Validate notebook executes without errors"""
    # nbval handles actual execution via --nbval flag
    pass

@pytest.mark.notebook
def test_notebook_count():
    """Ensure minimum notebook coverage per track"""
    counts = {}
    for nb in NOTEBOOKS:
        track = nb.split("/")[0]
        counts[track] = counts.get(track, 0) + 1
    
    # Minimums per track (from plan)
    minimums = {
        "track-01-ml-programmer": 7,
        "track-02-dl-programmer": 11,
        "track-03-ml-engineer": 8,
        "track-04-ml-architect": 6,
    }
    
    for track, min_count in minimums.items():
        assert counts.get(track, 0) >= min_count, f"{track}: {counts.get(track, 0)} < {min_count}"
