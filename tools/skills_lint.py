#!/usr/bin/env python3
"""Lint the OpenCode skills in .opencode/skills.

Checks (error unless marked warning):

  S001  file does not start with a YAML frontmatter block
  S002  frontmatter is missing or has an empty `description`
  S003  skill directory name is not a valid skill ID
  S004  `status` missing or not one of active/suspect/archived
  S005  `status` disagrees with the directory (archive rule, ADR-001)
  S006  body has no "## Don't" section
  S007  body is shorter than 200 characters                       (warning)
  S008  inline `path` reference does not exist
  S009  command in a bash/sh/console fenced block does not resolve
  S010  two descriptions are near-duplicates (embedding cosine)
  S011  a referenced path was committed after the skill         (warning)
  S012  description longer than 300 characters                   (warning)

Usage:
    tools/skills-lint.sh [--json] [--verbose] [--no-embed] [--skills-dir DIR]

Exit status is 1 when any error is reported.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKILL_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
FENCE_RE = re.compile(r"^```([\w-]*)\s*$", re.MULTILINE)

SHELL_LANGS = {"bash", "sh", "shell", "console", "zsh"}
SHELL_KEYWORDS = {
    "cd",
    "export",
    "set",
    "source",
    ".",
    "echo",
    "for",
    "do",
    "done",
    "if",
    "then",
    "else",
    "fi",
    "while",
    "case",
    "esac",
    "true",
    "false",
    "exit",
    "return",
    "local",
    "alias",
    "wait",
    "read",
}
KNOWN_EXTS = {
    ".py",
    ".md",
    ".mdx",
    ".ipynb",
    ".toml",
    ".sh",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".jsonc",
    ".cfg",
    ".ini",
    ".lock",
    ".csv",
}

EMBED_URL = os.environ.get("SKILLS_EMBED_URL", "http://127.0.0.1:1234/v1").rstrip("/")
EMBED_MODEL = os.environ.get("SKILLS_EMBED_MODEL", "").strip()
OVERLAP_ERROR = float(os.environ.get("SKILLS_OVERLAP_ERROR", "0.92"))
OVERLAP_WARN = float(os.environ.get("SKILLS_OVERLAP_WARN", "0.85"))
DESCRIPTION_MAX = 300
BODY_MIN = 200

STATUS_VALUES = {"active", "suspect", "archived"}


@dataclass
class Finding:
    level: str
    code: str
    skill: str
    message: str


@dataclass
class Skill:
    id: str
    path: Path
    archived: bool
    meta: dict[str, str] = field(default_factory=dict)
    body: str = ""
    text: str = ""

    @property
    def description(self) -> str:
        return self.meta.get("description", "").strip()

    @property
    def status(self) -> str:
        return self.meta.get("status", "").strip()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (top-level scalar keys, body). Nested blocks are ignored."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
    if end is None:
        return {}, text
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip() != line or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        meta[key.strip()] = value
    return meta, "\n".join(lines[end + 1 :])


def collect_skills(skills_dir: Path) -> list[Skill]:
    skills: list[Skill] = []
    if not skills_dir.is_dir():
        return skills
    archive = skills_dir / ".archive"
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        entry = child / "SKILL.md"
        if entry.is_file():
            skills.append(_load(entry, archived=False))
    if archive.is_dir():
        for child in sorted(archive.iterdir()):
            entry = child / "SKILL.md"
            if child.is_dir() and entry.is_file():
                skills.append(_load(entry, archived=True))
    return skills


def _load(path: Path, archived: bool) -> Skill:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_frontmatter(text)
    return Skill(
        id=path.parent.name,
        path=path,
        archived=archived,
        meta=meta,
        body=body,
        text=text,
    )


# ---------------------------------------------------------------------------
# Reference extraction
# ---------------------------------------------------------------------------


def _looks_like_path(token: str) -> bool:
    if not token or "://" in token:
        return False
    if any(ch in token for ch in "<>*{}[] \t|$#"):
        return False
    if token.startswith("-"):
        return False
    suffix = Path(token.rstrip("/")).suffix.lower()
    if suffix in KNOWN_EXTS:
        return True
    if token.endswith("/"):
        return True
    return token.startswith(("./", "../", "/", "~/")) and "/" in token


def extract_paths(text: str) -> list[str]:
    seen: list[str] = []
    for raw in INLINE_CODE_RE.findall(text):
        token = raw.strip().strip("\"'`").rstrip(".,;:)")
        if not _looks_like_path(token):
            continue
        if token not in seen:
            seen.append(token)
    return seen


def resolve_reference(token: str) -> Path | None:
    if token.startswith("~/"):
        return Path(token).expanduser()
    if token.startswith("/"):
        return Path(token)
    return ROOT / token


_BASENAME_CACHE: set[str] | None = None
_SKIP_WALK = {".git", ".venv", "node_modules", "__pycache__", ".ipynb_checkpoints"}


def _basenames() -> set[str]:
    """Every file and directory name in the tree, for bare-name references."""
    global _BASENAME_CACHE
    if _BASENAME_CACHE is None:
        names: set[str] = set()
        for path in ROOT.rglob("*"):
            if any(part in _SKIP_WALK for part in path.parts):
                continue
            names.add(path.name)
        _BASENAME_CACHE = names
    return _BASENAME_CACHE


def reference_ok(token: str) -> bool:
    """A reference is live if it resolves, or if a bare name exists anywhere.

    Machine-local paths (home config, /tmp) and generated, gitignored artefacts
    are not repo references, so they are skipped: a fresh clone must lint clean.
    """
    target = resolve_reference(token)
    if target is not None:
        try:
            target.relative_to(ROOT)
        except ValueError:
            return True  # outside the repo: user config, absolute system path
    if target is not None and target.exists():
        return True
    if target is not None and _gitignored(token):
        return True
    bare = token.rstrip("/")
    if "/" not in bare:
        return bare in _basenames()
    return False


def _gitignored(token: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "-q", token],
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def extract_commands(text: str) -> list[str]:
    commands: list[str] = []
    blocks = FENCE_RE.split(text)
    # blocks = [pre, lang, body, lang, body, ...]
    for index in range(1, len(blocks) - 1, 2):
        lang = blocks[index].strip().lower()
        if lang and lang not in SHELL_LANGS:
            continue
        if not lang:
            continue
        for line in blocks[index + 1].splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped[0] in "|&\\>)}":
                continue
            if stripped.startswith("$ "):
                stripped = stripped[2:].strip()
            token = stripped.split()[0].strip("\"'`")
            if token in SHELL_KEYWORDS or not token:
                continue
            if token not in commands:
                commands.append(token)
    return commands


def command_ok(token: str) -> bool:
    if "/" in token:
        return resolve_reference(token).exists()  # type: ignore[union-attr]
    return shutil.which(token) is not None


# ---------------------------------------------------------------------------
# Git staleness
# ---------------------------------------------------------------------------


def _git_commit_time(paths: list[str]) -> int | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%ct", "--", *paths],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return int(value) if value.isdigit() else None


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------


def _embed_urls() -> str:
    return EMBED_URL


def embed_descriptions(descriptions: dict[str, str]) -> dict[str, list[float]] | None:
    if not descriptions:
        return {}
    model = EMBED_MODEL
    if not model:
        try:
            with urllib.request.urlopen(f"{_embed_urls()}/models", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            ids = [item["id"] for item in payload.get("data", []) if "id" in item]
            model = next((i for i in ids if "embed" in i.lower()), "")
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            return None
    if not model:
        return None
    body = json.dumps({"model": model, "input": [descriptions[k] for k in descriptions]}).encode(
        "utf-8"
    )
    request = urllib.request.Request(
        f"{_embed_urls()}/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    vectors = [row["embedding"] for row in payload.get("data", [])]
    if len(vectors) != len(descriptions):
        return None
    return dict(zip(descriptions, vectors))


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_skill(skill: Skill) -> list[Finding]:
    findings: list[Finding] = []
    add = lambda level, code, msg: findings.append(  # noqa: E731
        Finding(level, code, skill.id, msg)
    )

    if not skill.meta:
        add("error", "S001", "missing YAML frontmatter block")
    if not skill.description:
        add("error", "S002", "frontmatter `description` is missing or empty")

    if not SKILL_ID_RE.match(skill.id) or len(skill.id) > 64:
        add("error", "S003", f"directory name {skill.id!r} is not a valid skill ID")

    status = skill.status
    if not status:
        add("error", "S004", "frontmatter `status` is missing")
    elif status not in STATUS_VALUES:
        add(
            "error",
            "S004",
            f"`status: {status}` is not one of {', '.join(sorted(STATUS_VALUES))}",
        )
    else:
        archived_shaped = status == "archived"
        if archived_shaped and not skill.archived:
            add(
                "error",
                "S005",
                "`status: archived` but the skill is still in the active directory "
                "(move it to .archive/, the loader ignores `status`)",
            )
        if skill.archived and not archived_shaped:
            add("error", "S005", f"skill is in .archive/ but `status: {status}`")
        if skill.archived and not skill.meta.get("reason", "").strip():
            add("error", "S005", "archived skill has no `reason` in frontmatter")

    if skill.archived:
        # The archive is a ledger of decisions, not guidance. Check only that
        # the record is consistent; its body and references are historical.
        return findings

    headings = [h.strip() for h in HEADING_RE.findall(skill.body)]
    has_dont = any(h.lower().startswith(("don't", "dont", "do not")) for h in headings)
    if not has_dont:
        add("error", "S006", 'body has no "## Don\'t" section')
    if not [h for h in headings if not h.lower().startswith(("don't", "dont", "do not"))]:
        add("error", "S006", "body has no section other than Don't")
    if len(skill.body.strip()) < BODY_MIN:
        add("warning", "S007", f"body is only {len(skill.body.strip())} characters")

    for token in extract_paths(skill.text):
        if not reference_ok(token):
            add("error", "S008", f"referenced path does not exist: {token}")

    for token in extract_commands(skill.text):
        if not command_ok(token):
            add("error", "S009", f"command not found: {token}")

    if len(skill.description) > DESCRIPTION_MAX:
        add(
            "warning",
            "S012",
            f"description is {len(skill.description)} characters (target < {DESCRIPTION_MAX})",
        )

    if not skill.archived:
        try:
            skill_rel = str(skill.path.resolve().relative_to(ROOT))
        except ValueError:
            skill_rel = None
        skill_commit = _git_commit_time([skill_rel]) if skill_rel else None
        if skill_commit is not None:
            for token in extract_paths(skill.text):
                target = resolve_reference(token)
                if target is None or not reference_ok(token):
                    continue
                try:
                    rel = str(target.resolve().relative_to(ROOT))
                except ValueError:
                    continue
                ref_commit = _git_commit_time([rel])
                if ref_commit is not None and ref_commit > skill_commit:
                    add(
                        "warning",
                        "S011",
                        f"{token} was committed after this skill; re-read it",
                    )

    return findings


def check_overlap(skills: list[Skill], no_embed: bool) -> list[Finding]:
    active = [s for s in skills if not s.archived and s.description]
    if no_embed or len(active) < 2:
        return []
    vectors = embed_descriptions({s.id: s.description for s in active})
    if vectors is None:
        return [
            Finding(
                "warning",
                "S010",
                "-",
                f"description overlap not checked (no embedding endpoint at {EMBED_URL})",
            )
        ]
    findings: list[Finding] = []
    for a, b in combinations(active, 2):
        score = cosine(vectors[a.id], vectors[b.id])
        if score >= OVERLAP_ERROR:
            level = "error"
        elif score >= OVERLAP_WARN:
            level = "warning"
        else:
            continue
        findings.append(
            Finding(
                level,
                "S010",
                f"{a.id}/{b.id}",
                f"descriptions are {score:.3f} similar "
                f"(error >= {OVERLAP_ERROR}, warn >= {OVERLAP_WARN})",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint OpenCode skills.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--verbose", action="store_true", help="per-skill detail")
    parser.add_argument("--no-embed", action="store_true", help="skip overlap check")
    parser.add_argument(
        "--skills-dir",
        default=os.environ.get("SKILLS_DIR", str(ROOT / ".opencode" / "skills")),
        help="skills root (default: .opencode/skills)",
    )
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir).expanduser().resolve()
    skills = collect_skills(skills_dir)

    if not skills:
        message = f"no skills found under {skills_dir}"
        if args.json:
            print(json.dumps({"skills": [], "findings": [], "message": message}, indent=2))
        else:
            print(f"skills-lint: {message}")
        return 1

    findings: list[Finding] = []
    for skill in skills:
        findings.extend(check_skill(skill))
    findings.extend(check_overlap(skills, args.no_embed))

    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]

    if args.json:
        print(
            json.dumps(
                {
                    "skills_dir": str(skills_dir),
                    "active": [s.id for s in skills if not s.archived],
                    "archived": [s.id for s in skills if s.archived],
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "findings": [f.__dict__ for f in findings],
                },
                indent=2,
            )
        )
        return 1 if errors else 0

    active = [s.id for s in skills if not s.archived]
    archived = [s.id for s in skills if s.archived]
    print(
        f"skills-lint: {len(active)} active ({', '.join(active) or 'none'}), "
        f"{len(archived)} archived"
    )
    if args.verbose:
        for skill in skills:
            print(
                f"  {skill.id:<22} status={skill.status or '?':<9} "
                f"description={len(skill.description)}ch body={len(skill.body.strip())}ch"
            )
    for finding in findings:
        print(f"  {finding.level.upper():<7} {finding.skill:<24} {finding.code}  {finding.message}")

    status = "FAIL" if errors else "PASS"
    print(f"skills-lint: {status} — {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
