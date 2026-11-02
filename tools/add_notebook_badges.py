"""Inject Colab/Kaggle/Codespaces badges as the first markdown cell of every notebook.

The repository slug is resolved from (in order):
  1. --repo CLI argument
  2. GITHUB_REPOSITORY environment variable (e.g. ``owner/repo``)
  3. ``git remote get-url origin``

If no slug can be resolved the tool exits without modifying anything and prints
how to supply one. Badge cells are idempotent: re-running replaces the existing
badge cell instead of adding a duplicate.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- journey-badges -->"
TRACKS = [
    "track-01-ml-programmer",
    "track-02-dl-programmer",
    "track-03-ml-engineer",
    "track-04-ml-architect",
]


def repo_slug(explicit: str | None) -> str | None:
    if explicit:
        return explicit.strip("/")
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env.strip("/")
    try:
        url = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    match = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/.]+)", url)
    return match.group("slug") if match else None


def badge_cell(slug: str, nb_rel: str) -> str:
    path = nb_rel.replace(" ", "%20")
    colab = f"https://colab.research.google.com/github/{slug}/blob/main/{path}"
    kaggle = f"https://kaggle.com/kernels/welcome?src=https://github.com/{slug}/blob/main/{path}"
    codespaces = f"https://codespaces.new/{slug}"
    return (
        f"{MARKER}\n"
        f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({colab})\n"
        f"[![Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)]({kaggle})\n"
        f"[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)]({codespaces})"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=None, help="owner/repo slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    slug = repo_slug(args.repo)
    if not slug:
        print(
            "No repository slug available (no origin remote and GITHUB_REPOSITORY unset).\n"
            "Provide one with --repo owner/repo or set GITHUB_REPOSITORY. Nothing changed.",
            file=sys.stderr,
        )
        return 0

    updated = 0
    for track in TRACKS:
        for nb_path in sorted((ROOT / track).glob("*.ipynb")):
            nb = json.loads(nb_path.read_text())
            cells = nb.get("cells", [])
            rel = str(nb_path.relative_to(ROOT))
            text = badge_cell(slug, rel)

            existing = next(
                (i for i, c in enumerate(cells) if c.get("cell_type") == "markdown" and MARKER in "".join(c.get("source", []))),
                None,
            )
            if existing is not None:
                current = "".join(cells[existing]["source"])
                if current.strip() == text.strip():
                    continue
                cells[existing]["source"] = text.splitlines(keepends=True)
            else:
                cells.insert(
                    0,
                    {
                        "cell_type": "markdown",
                        "id": "journey-badges",
                        "metadata": {},
                        "source": text.splitlines(keepends=True),
                    },
                )
            if not args.dry_run:
                nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
            updated += 1
            print(("would update " if args.dry_run else "updated ") + rel)

    print(f"{updated} notebook(s) {'pending' if args.dry_run else 'updated'}; repo={slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())