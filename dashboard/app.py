"""Progress Tracking Dashboard - Streamlit"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ML Architect Journey - Progress", layout="wide")

TRACK_TITLES = {
    "track-01-ml-programmer": "Track 1: ML Programmer (Foundations)",
    "track-02-dl-programmer": "Track 2: DL Programmer (Specialization)",
    "track-03-ml-engineer": "Track 3: ML Engineer (MLOps)",
    "track-04-ml-architect": "Track 4: ML Architect (Architecture)",
}

CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints"
NOTEBOOK_DIR = Path(__file__).parent.parent


def track_title(track_id: str) -> str:
    """Display name for a track directory, derived when not in TRACK_TITLES."""
    if track_id in TRACK_TITLES:
        return TRACK_TITLES[track_id]
    return track_id.replace("track-", "Track ").replace("-", " ").title()


def discover_tracks() -> dict:
    """Every `track-*` directory holds a track (A1).

    Deriving the set from the filesystem means a new track appears in the
    dashboard without editing this file, and `st.columns` can size itself.
    """
    dirs = sorted(p for p in NOTEBOOK_DIR.glob("track-*") if p.is_dir())
    return {p.name: track_title(p.name) for p in dirs}


TRACKS = discover_tracks()

# Plan-level notebook counts, used only for the progress denominator. A track
# missing from the map falls back to what is on disk, so it cannot KeyError.
EXPECTED_NOTEBOOKS = {
    "track-01-ml-programmer": 7,
    "track-02-dl-programmer": 11,
    "track-03-ml-engineer": 8,
    "track-04-ml-architect": 12,
}


@st.cache_data
def load_checkpoints(track_id):
    fp = CHECKPOINT_DIR / f"{track_id}.json"
    if fp.exists():
        with open(fp) as f:
            return json.load(f)
    return {}


@st.cache_data
def count_notebooks(track_id):
    track_path = NOTEBOOK_DIR / track_id
    if track_path.exists():
        return len(list(track_path.glob("*.ipynb")))
    return 0


def main():
    st.title("📊 ML Programmer → ML Architect Journey Progress")

    # Sidebar
    st.sidebar.header("Navigation")
    view = st.sidebar.radio("View", ["Overview", "Track Detail", "Checkpoints", "Final Exams"])

    if view == "Overview":
        show_overview()
    elif view == "Track Detail":
        show_track_detail()
    elif view == "Checkpoints":
        show_checkpoints()
    elif view == "Final Exams":
        show_final_exams()


def show_overview():
    st.header("📈 Journey Overview")

    cols = st.columns(max(len(TRACKS), 1))
    total_notebooks = 0
    total_checkpoints = 0

    for i, (track_id, track_name) in enumerate(TRACKS.items()):
        with cols[i]:
            nb_count = count_notebooks(track_id)
            cp_data = load_checkpoints(track_id)
            cp_count = len(cp_data.get("checkpoints", []))

            total_notebooks += nb_count
            total_checkpoints += cp_count

            st.metric(track_name, f"{nb_count} notebooks", f"{cp_count} checkpoints")

    st.metric("Total", f"{total_notebooks} notebooks", f"{total_checkpoints} checkpoints")

    # Progress bars per track
    st.subheader("Track Completion")
    for track_id, track_name in TRACKS.items():
        nb_count = count_notebooks(track_id)
        cp_data = load_checkpoints(track_id)
        cp_count = len(cp_data.get("checkpoints", []))

        exp = EXPECTED_NOTEBOOKS.get(track_id, nb_count)
        pct = min(nb_count / exp * 100, 100) if exp > 0 else 0

        st.progress(pct / 100, text=f"{track_name}: {nb_count}/{exp} notebooks ({pct:.0f}%)")


def show_track_detail():
    st.header("📚 Track Detail")
    track_id = st.selectbox("Select Track", list(TRACKS.keys()), format_func=lambda x: TRACKS[x])

    cp_data = load_checkpoints(track_id)
    notebooks = (
        sorted((NOTEBOOK_DIR / track_id).glob("*.ipynb"))
        if (NOTEBOOK_DIR / track_id).exists()
        else []
    )

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Notebooks")
        for nb in notebooks:
            st.write(f"📓 {nb.name}")

    with col2:
        st.subheader("Checkpoints")
        for cp in cp_data.get("checkpoints", []):
            with st.expander(f"{cp['id']}: {cp['notebook']}"):
                st.write("**Skills:**", ", ".join(cp["skills"]))
                for q in cp["questions"]:
                    st.write(f"- {q['prompt']} (`{q['type']}`)")


def show_checkpoints():
    st.header("✅ Skill Checkpoints")

    all_data = []
    for track_id, track_name in TRACKS.items():
        cp_data = load_checkpoints(track_id)
        for cp in cp_data.get("checkpoints", []):
            for q in cp["questions"]:
                all_data.append(
                    {
                        "Track": track_name,
                        "Checkpoint": cp["id"],
                        "Notebook": cp["notebook"],
                        "Question": q["prompt"],
                        "Type": q["type"],
                        "Skill": ", ".join(cp["skills"][:2]),
                    }
                )

    if all_data:
        df = pd.DataFrame(all_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Checkpoints CSV", csv, "checkpoints.csv", "text/csv")


def show_final_exams():
    st.header("📝 Final Exams")

    for track_id, track_name in TRACKS.items():
        cp_data = load_checkpoints(track_id)
        exam = cp_data.get("final_exam", {})

        with st.expander(f"{track_name} - Final Exam"):
            st.write(f"**Questions:** {exam.get('questions', 'N/A')}")
            st.write(f"**Time:** {exam.get('time_minutes', 'N/A')} minutes")
            passing = exam.get("passing_score")
            passing_text = f"{passing * 100:.0f}%" if isinstance(passing, (int, float)) else "N/A"
            st.write(f"**Passing Score:** {passing_text}")
            st.write("**Topics:**")
            for topic in exam.get("topics", []):
                st.write(f"  - {topic}")


if __name__ == "__main__":
    main()
