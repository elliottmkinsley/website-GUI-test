"""Read/write helpers for the four ``manifest.json`` files.

Manifest is the source of truth for what's "live" on the site. A
JSON entry on disk that's missing from its manifest is silently
ignored at runtime - so add/edit/delete/reorder all flow through
this module.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Literal

from gui.config import (
    EVENTS_MANIFEST,
    JOBS_MANIFEST,
    PEOPLE_MANIFEST,
    PROJECTS_MANIFEST,
)

PeopleKey = Literal["leadership", "faculty", "affiliation", "staff", "postdocs", "graduate"]
ProjectKey = Literal["featured", "page"]
EventsKey = Literal["homepage"]
JobsKey = Literal["jobs"]

_INDENT = 2


def _load(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object at the top level")
    return {k: list(v or []) for k, v in data.items()}


def _save(path: Path, data: dict[str, list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=_INDENT, ensure_ascii=False)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def load_people() -> dict[str, list[str]]:
    return _load(PEOPLE_MANIFEST)


def load_projects() -> dict[str, list[str]]:
    return _load(PROJECTS_MANIFEST)


def load_events() -> dict[str, list[str]]:
    return _load(EVENTS_MANIFEST)


def load_jobs() -> dict[str, list[str]]:
    return _load(JOBS_MANIFEST)


# ---------------------------------------------------------------------------
# Generic write helpers
# ---------------------------------------------------------------------------


def _ensure_section(data: dict[str, list[str]], key: str) -> list[str]:
    return data.setdefault(key, [])


def add_path(
    manifest_path: Path, section: str, repo_relative_path: str
) -> None:
    """Append ``repo_relative_path`` to the named section if absent."""
    data = _load(manifest_path)
    arr = _ensure_section(data, section)
    if repo_relative_path not in arr:
        arr.append(repo_relative_path)
    _save(manifest_path, data)


def remove_path(
    manifest_path: Path, section: str, repo_relative_path: str
) -> bool:
    data = _load(manifest_path)
    arr = data.get(section, [])
    if repo_relative_path in arr:
        arr.remove(repo_relative_path)
        data[section] = arr
        _save(manifest_path, data)
        return True
    return False


def replace_section(
    manifest_path: Path, section: str, ordered_paths: Iterable[str]
) -> None:
    """Rewrite a section's array, preserving the given order."""
    data = _load(manifest_path)
    data[section] = list(ordered_paths)
    _save(manifest_path, data)


def get_section(manifest_path: Path, section: str) -> list[str]:
    """Return a copy of the named section's array."""
    return list(_load(manifest_path).get(section, []))


# ---------------------------------------------------------------------------
# Domain-specific convenience wrappers (typed to ease IDE autocompletion).
# ---------------------------------------------------------------------------


def add_person(group: PeopleKey, repo_relative_path: str) -> None:
    add_path(PEOPLE_MANIFEST, group, repo_relative_path)


def remove_person(group: PeopleKey, repo_relative_path: str) -> bool:
    return remove_path(PEOPLE_MANIFEST, group, repo_relative_path)


def reorder_people(group: PeopleKey, paths: Iterable[str]) -> None:
    replace_section(PEOPLE_MANIFEST, group, paths)


def add_project(surface: ProjectKey, repo_relative_path: str) -> None:
    add_path(PROJECTS_MANIFEST, surface, repo_relative_path)


def remove_project(surface: ProjectKey, repo_relative_path: str) -> bool:
    return remove_path(PROJECTS_MANIFEST, surface, repo_relative_path)


def reorder_projects(surface: ProjectKey, paths: Iterable[str]) -> None:
    replace_section(PROJECTS_MANIFEST, surface, paths)


def add_event(repo_relative_path: str) -> None:
    add_path(EVENTS_MANIFEST, "homepage", repo_relative_path)


def remove_event(repo_relative_path: str) -> bool:
    return remove_path(EVENTS_MANIFEST, "homepage", repo_relative_path)


def reorder_events(paths: Iterable[str]) -> None:
    replace_section(EVENTS_MANIFEST, "homepage", paths)


def add_job(repo_relative_path: str) -> None:
    add_path(JOBS_MANIFEST, "jobs", repo_relative_path)


def remove_job(repo_relative_path: str) -> bool:
    return remove_path(JOBS_MANIFEST, "jobs", repo_relative_path)


def reorder_jobs(paths: Iterable[str]) -> None:
    replace_section(JOBS_MANIFEST, "jobs", paths)
