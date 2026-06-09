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

from gui.workspace import get_workspace

PeopleKey = Literal["leadership", "faculty", "affiliation", "staff", "postdocs", "graduate"]
ProjectKey = Literal["featured", "page"]
EventsKey = Literal["homepage"]
JobsKey = Literal["jobs"]


def _people_manifest() -> Path:
    return get_workspace().people_manifest


def _projects_manifest() -> Path:
    return get_workspace().projects_manifest


def _events_manifest() -> Path:
    return get_workspace().events_manifest


def _jobs_manifest() -> Path:
    return get_workspace().jobs_manifest

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
    return _load(_people_manifest())


def load_projects() -> dict[str, list[str]]:
    return _load(_projects_manifest())


def load_events() -> dict[str, list[str]]:
    return _load(_events_manifest())


def load_jobs() -> dict[str, list[str]]:
    return _load(_jobs_manifest())


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
    add_path(_people_manifest(), group, repo_relative_path)


def remove_person(group: PeopleKey, repo_relative_path: str) -> bool:
    return remove_path(_people_manifest(), group, repo_relative_path)


def reorder_people(group: PeopleKey, paths: Iterable[str]) -> None:
    replace_section(_people_manifest(), group, paths)


def add_project(surface: ProjectKey, repo_relative_path: str) -> None:
    add_path(_projects_manifest(), surface, repo_relative_path)


def remove_project(surface: ProjectKey, repo_relative_path: str) -> bool:
    return remove_path(_projects_manifest(), surface, repo_relative_path)


def reorder_projects(surface: ProjectKey, paths: Iterable[str]) -> None:
    replace_section(_projects_manifest(), surface, paths)


def add_event(repo_relative_path: str) -> None:
    add_path(_events_manifest(), "homepage", repo_relative_path)


def remove_event(repo_relative_path: str) -> bool:
    return remove_path(_events_manifest(), "homepage", repo_relative_path)


def reorder_events(paths: Iterable[str]) -> None:
    replace_section(_events_manifest(), "homepage", paths)


def add_job(repo_relative_path: str) -> None:
    add_path(_jobs_manifest(), "jobs", repo_relative_path)


def remove_job(repo_relative_path: str) -> bool:
    return remove_path(_jobs_manifest(), "jobs", repo_relative_path)


def reorder_jobs(paths: Iterable[str]) -> None:
    replace_section(_jobs_manifest(), "jobs", paths)
