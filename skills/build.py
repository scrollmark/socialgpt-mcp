#!/usr/bin/env python3
"""Build / validate the SocialGPT MCP skills.

Each skill folder is an **independently installable artifact** (Claude.ai uploads
one skill at a time as a zip), so the shared helper library
``_shared/sgpt_lib.py`` is *vendored* into every skill's ``scripts/`` directory
rather than imported across folders. This script is the single source of truth
for that vendoring plus packaging.

    python skills/build.py            # sync vendored libs + write dist/<skill>.zip
    python skills/build.py --check    # CI: fail if any vendored lib is out of sync
    python skills/build.py --no-zip   # just sync the vendored libs

A built zip contains a top-level ``<skill>/`` folder with ``SKILL.md`` at its
root — the shape Claude.ai's "upload skill" expects.

Two classes of skill are supported:

* **script-based** — has a ``scripts/`` directory with an ``analyze.py``. The
  shared lib is vendored into it and it ships a deterministic analysis. (The
  three analysis skills.)
* **orchestrator** — has **no** ``scripts/`` directory; it ships a ``SKILL.md``
  plus a ``references/`` knowledge base and conducts the other skills + MCP tools
  rather than computing anything itself. Nothing is vendored into it. (The
  ``going-viral`` skill.)
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARED_LIB = ROOT / "_shared" / "sgpt_lib.py"
DIST = ROOT / "dist"
VENDOR_NAME = "sgpt_lib.py"
_SKIP = {"_shared", "dist", "__pycache__"}


def skill_dirs() -> list[Path]:
    return sorted(
        p for p in ROOT.iterdir()
        if p.is_dir() and p.name not in _SKIP and (p / "SKILL.md").exists()
    )


def is_script_based(skill: Path) -> bool:
    """A skill is script-based if it has a ``scripts/`` directory; otherwise it is
    an orchestrator skill (SKILL.md + references/, no vendored lib)."""
    return (skill / "scripts").is_dir()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_skill(skill: Path) -> list[str]:
    """Lightweight structural checks; returns a list of problems (empty = ok)."""
    problems: list[str] = []
    md = (skill / "SKILL.md").read_text(encoding="utf-8")
    if not md.startswith("---"):
        problems.append("SKILL.md is missing YAML frontmatter")
    else:
        front = md.split("---", 2)[1]
        if "name:" not in front:
            problems.append("SKILL.md frontmatter missing `name`")
        if "description:" not in front:
            problems.append("SKILL.md frontmatter missing `description`")
        if f"name: {skill.name}" not in front and f"name:\n" not in front:
            # name should match the folder; allow folded scalars but warn otherwise
            if f"name: {skill.name}" not in front:
                problems.append(f"SKILL.md `name` should equal folder name '{skill.name}'")
    if is_script_based(skill):
        if not (skill / "scripts" / "analyze.py").exists():
            problems.append("missing scripts/analyze.py")
    else:
        # orchestrator skill: must ship a non-empty references/ instead of a script
        refs = skill / "references"
        if not refs.is_dir() or not any(refs.glob("*.md")):
            problems.append("orchestrator skill (no scripts/) must ship a non-empty references/")
    return problems


def sync_vendored(check: bool) -> bool:
    """Copy the shared lib into each skill/scripts/. In --check mode, only report."""
    shared = SHARED_LIB.read_bytes()
    shared_hash = _digest(SHARED_LIB)
    ok = True
    for skill in skill_dirs():
        if not is_script_based(skill):
            continue  # orchestrator skill — nothing to vendor
        target = skill / "scripts" / VENDOR_NAME
        target.parent.mkdir(parents=True, exist_ok=True)
        if check:
            if not target.exists() or _digest(target) != shared_hash:
                print(f"  OUT OF SYNC: {target.relative_to(ROOT)} — run `python skills/build.py`")
                ok = False
        else:
            if not target.exists() or _digest(target) != shared_hash:
                target.write_bytes(shared)
                print(f"  vendored sgpt_lib.py -> {target.relative_to(ROOT)}")
    return ok


def build_zip(skill: Path) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill.name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill.rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.is_file():
                # arcname keeps the skill folder as the zip's top-level dir.
                zf.write(path, Path(skill.name) / path.relative_to(skill))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="CI: verify vendored libs are in sync")
    ap.add_argument("--no-zip", action="store_true", help="sync vendored libs only")
    args = ap.parse_args()

    if not SHARED_LIB.exists():
        print(f"missing shared lib: {SHARED_LIB}", file=sys.stderr)
        return 2

    skills = skill_dirs()
    if not skills:
        print("no skills found", file=sys.stderr)
        return 2

    problems = False
    for skill in skills:
        issues = validate_skill(skill)
        for issue in issues:
            print(f"  INVALID {skill.name}: {issue}")
            problems = True
    if problems:
        return 1

    if args.check:
        print(f"Checking {len(skills)} skills against {SHARED_LIB.name}…")
        return 0 if sync_vendored(check=True) else 1

    print(f"Syncing shared lib into {len(skills)} skills…")
    sync_vendored(check=False)

    if args.no_zip:
        return 0

    print("Building zips…")
    for skill in skills:
        out = build_zip(skill)
        size = out.stat().st_size
        print(f"  {out.relative_to(ROOT)}  ({size:,} bytes)")
    print(f"\nDone. {len(skills)} skills packaged into {DIST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
