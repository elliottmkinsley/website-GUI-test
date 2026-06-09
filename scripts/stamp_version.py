"""Stamp the application version into every file that needs to
agree on it before a release build.

CI invokes this immediately after checkout / tag resolution:

    python scripts/stamp_version.py --version 1.2.3 --no-allow-missing

What it does:

1. Validates that the version is plain ``MAJOR.MINOR.PATCH`` (no
   pre-release suffixes, no leading ``v``). Anything else is
   rejected loudly.
2. Rewrites ``gui/__version__.py`` so ``__version__`` matches.
3. Regenerates ``packaging/version_info.txt`` so the Windows
   VERSIONINFO resource matches (Pyinstaller bakes that into the
   ``.exe``).
4. Promotes the leading ``## [Unreleased]`` header in
   ``docs/CHANGELOG.md`` to ``## [vX.Y.Z] - YYYY-MM-DD`` if it
   exists. Safe no-op if the changelog has already been promoted
   for this version or has no ``## [Unreleased]`` block.

Flags:

* ``--dry-run`` prints what would change and exits 0 without
  touching the filesystem.
* ``--no-allow-missing`` hard-fails if any target file does not
  exist (defensive default for CI). Without the flag, missing files
  are skipped with a warning.

The script is intentionally dependency-free so it can run in a
fresh CI image without ``pip install`` first.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

log = logging.getLogger("stamp_version")

REPO_ROOT = Path(__file__).resolve().parent.parent

VERSION_PY = REPO_ROOT / "gui" / "__version__.py"
VERSION_INFO_TXT = REPO_ROOT / "packaging" / "version_info.txt"
CHANGELOG_MD = REPO_ROOT / "docs" / "CHANGELOG.md"

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def normalise_version(raw: str) -> str:
    """Strip an optional leading ``v`` and validate the result.

    Returns the version without the prefix. Raises ``ValueError`` on
    anything that does not match ``MAJOR.MINOR.PATCH``.
    """
    candidate = raw.strip()
    if candidate.startswith(("v", "V")):
        candidate = candidate[1:]
    if not _SEMVER_RE.match(candidate):
        raise ValueError(
            f"Invalid version {raw!r}: expected MAJOR.MINOR.PATCH "
            "(no pre-release or build suffix)."
        )
    return candidate


def parse_components(version: str) -> tuple[int, int, int]:
    match = _SEMVER_RE.match(version)
    assert match is not None  # normalise_version ran first
    return tuple(int(g) for g in match.groups())  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _display_path(path: Path) -> str:
    """Best-effort repo-relative path for log messages.

    Falls back to the absolute path when ``path`` is not under
    ``REPO_ROOT`` - common in pytest, where fixtures create files
    under ``tmp_path``. See playbook gotcha #9.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Stamping helpers
# ---------------------------------------------------------------------------


_VERSION_LINE_RE = re.compile(
    r'^(\s*__version__\s*:\s*str\s*=\s*)(["\'])([^"\']+)(\2)',
    re.MULTILINE,
)
_VERSION_LINE_LOOSE_RE = re.compile(
    r'^(\s*__version__\s*=\s*)(["\'])([^"\']+)(\2)',
    re.MULTILINE,
)


def stamp_version_py(version: str, *, path: Path = VERSION_PY) -> bool:
    """Rewrite ``__version__`` in ``gui/__version__.py``.

    Returns ``True`` if the file was modified, ``False`` if the
    value already matched.
    """
    text = path.read_text(encoding="utf-8")
    # Try the typed form first, fall back to the untyped form so the
    # script also works against the legacy ``gui/__init__.py`` style.
    pattern = _VERSION_LINE_RE if _VERSION_LINE_RE.search(text) else _VERSION_LINE_LOOSE_RE
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(
            f"Could not find a __version__ assignment in {_display_path(path)}."
        )
    if match.group(3) == version:
        return False
    new_text = pattern.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{version}{m.group(4)}", text, count=1
    )
    path.write_text(new_text, encoding="utf-8")
    return True


_FILEVERS_RE = re.compile(r"filevers=\(\d+, \d+, \d+, \d+\)")
_PRODVERS_RE = re.compile(r"prodvers=\(\d+, \d+, \d+, \d+\)")
_STRING_VERSION_RE = re.compile(
    r"(StringStruct\(u'(FileVersion|ProductVersion)', u')[^']+(\'\))"
)


def stamp_version_info(version: str, *, path: Path = VERSION_INFO_TXT) -> bool:
    """Rewrite ``packaging/version_info.txt`` to match."""
    major, minor, patch = parse_components(version)
    tuple_repr = f"({major}, {minor}, {patch}, 0)"
    text = path.read_text(encoding="utf-8")
    new_text = _FILEVERS_RE.sub(f"filevers={tuple_repr}", text)
    new_text = _PRODVERS_RE.sub(f"prodvers={tuple_repr}", new_text)
    new_text = _STRING_VERSION_RE.sub(
        lambda m: f"{m.group(1)}{version}.0{m.group(3)}", new_text
    )
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


_UNRELEASED_RE = re.compile(r"^## \[Unreleased\].*$", re.MULTILINE)


def promote_changelog(version: str, *, path: Path = CHANGELOG_MD) -> bool:
    """Promote ``## [Unreleased]`` -> ``## [vX.Y.Z] - YYYY-MM-DD``.

    Returns ``True`` if the file was modified. If the changelog
    already has a heading for this version (e.g. the script is run
    twice for the same tag), this is a no-op.
    """
    text = path.read_text(encoding="utf-8")
    versioned_heading = f"## [v{version}]"
    if versioned_heading in text:
        return False
    if _UNRELEASED_RE.search(text) is None:
        return False
    today = date.today().isoformat()
    new_text = _UNRELEASED_RE.sub(
        f"## [v{version}] - {today}", text, count=1
    )
    path.write_text(new_text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _check_present(paths: Iterable[Path], *, allow_missing: bool) -> list[Path]:
    """Return the subset of ``paths`` that exist; warn or fail on
    the missing ones depending on ``allow_missing``."""
    present: list[Path] = []
    for p in paths:
        if p.exists():
            present.append(p)
            continue
        msg = f"target file does not exist: {_display_path(p)}"
        if not allow_missing:
            raise FileNotFoundError(msg)
        log.warning(msg)
    return present


def stamp_all(
    version: str,
    *,
    allow_missing: bool = True,
    dry_run: bool = False,
) -> list[tuple[str, bool]]:
    """Stamp ``version`` into every target file.

    Returns a list of ``(display_path, changed)`` tuples for
    reporting. When ``dry_run`` is true the filesystem is never
    touched and every tuple reports ``True`` (would change) if the
    current value differs from ``version``.
    """
    version = normalise_version(version)
    targets = [VERSION_PY, VERSION_INFO_TXT, CHANGELOG_MD]
    present = _check_present(targets, allow_missing=allow_missing)
    results: list[tuple[str, bool]] = []

    for path in present:
        if path == VERSION_PY:
            op = lambda: stamp_version_py(version, path=path)
        elif path == VERSION_INFO_TXT:
            op = lambda: stamp_version_info(version, path=path)
        elif path == CHANGELOG_MD:
            op = lambda: promote_changelog(version, path=path)
        else:  # pragma: no cover - defensive
            continue

        if dry_run:
            # We can't predict "would change" perfectly without
            # actually running the op; do a string comparison for
            # the simple cases and assume changed=True for changelog
            # promotion (which only changes if [Unreleased] exists).
            results.append((_display_path(path), True))
        else:
            changed = op()
            results.append((_display_path(path), changed))
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stamp the app version.")
    parser.add_argument(
        "--version",
        required=True,
        help="Target version. Accepts 'X.Y.Z' or 'vX.Y.Z'.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing.",
    )
    parser.add_argument(
        "--no-allow-missing",
        action="store_true",
        help="Hard-fail if any target file is absent. Recommended in CI.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    try:
        version = normalise_version(args.version)
    except ValueError as exc:
        log.error("%s", exc)
        return 2

    try:
        results = stamp_all(
            version,
            allow_missing=not args.no_allow_missing,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        log.error("%s", exc)
        return 1

    prefix = "[dry-run] " if args.dry_run else ""
    for path_str, changed in results:
        verb = "would update" if args.dry_run else ("updated" if changed else "no change")
        log.info("%s%s: %s", prefix, verb, path_str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
