"""Read/write per-entry JSON files for the four data domains.

This module is the bridge between the typed pydantic models and the
working-tree JSON files, plus the matching ``manifest.json`` updates.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from gui.config import PEOPLE_GROUPS
from gui.models.event import Event
from gui.models.job import Job
from gui.models.person import Person
from gui.models.project import Project
from gui.repo import manifest
from gui.repo.paths import (
    filesafe_basename,
    from_repo_relative,
    repo_relative,
    slugify,
)
from gui.workspace import get_workspace

log = logging.getLogger(__name__)
_INDENT = 2


# ---------------------------------------------------------------------------
# Generic JSON I/O
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=_INDENT, ensure_ascii=False)
        fh.write("\n")


def _unique_path(target: Path) -> Path:
    """Return ``target`` if it doesn't exist, else target with ``-2``,
    ``-3``... suffix until unique."""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    parent = target.parent
    n = 2
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


def people_group_folder(group_key: str) -> Path:
    """Return the absolute folder under ``People/`` for the given key."""
    for key, _label, folder in PEOPLE_GROUPS:
        if key == group_key:
            return get_workspace().root / "People" / folder
    raise KeyError(f"Unknown people group key: {group_key!r}")


def list_people(group_key: str) -> list[tuple[str, Person]]:
    """Return ``(repo_relative_path, Person)`` pairs in manifest order."""
    paths = manifest.get_section(get_workspace().people_manifest, group_key)
    out: list[tuple[str, Person]] = []
    for rel in paths:
        abs_path = from_repo_relative(rel)
        if not abs_path.exists():
            log.warning("Manifest references missing People file: %s", rel)
            continue
        try:
            person = Person.model_validate(_read_json(abs_path))
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            log.warning("Skipping invalid People entry %s: %s", rel, exc)
            continue
        out.append((rel, person))
    return out


def load_person(repo_relative_path: str) -> Person:
    return Person.model_validate(_read_json(from_repo_relative(repo_relative_path)))


def save_person(
    person: Person,
    *,
    group_key: str,
    existing_relative_path: str | None = None,
) -> str:
    """Write ``person`` to disk and update the manifest.

    On *create*, ``existing_relative_path`` is ``None`` and a unique
    kebab-case filename is chosen from the person's name. Returns
    the repo-relative path of the saved JSON.
    """
    folder = people_group_folder(group_key)
    folder.mkdir(parents=True, exist_ok=True)

    if existing_relative_path:
        target = from_repo_relative(existing_relative_path)
    else:
        slug = slugify(person.name)
        target = _unique_path(folder / f"{slug}.json")

    _write_json(target, person.to_json_dict())
    rel = repo_relative(target)
    if not existing_relative_path:
        manifest.add_person(group_key, rel)  # type: ignore[arg-type]
    return rel


def move_person_group(
    repo_relative_path: str, *, from_group: str, to_group: str
) -> str:
    """Move a person JSON to a different group folder + manifest section."""
    if from_group == to_group:
        return repo_relative_path
    src = from_repo_relative(repo_relative_path)
    if not src.exists():
        raise FileNotFoundError(repo_relative_path)
    dest_folder = people_group_folder(to_group)
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest = _unique_path(dest_folder / src.name)
    src.rename(dest)
    new_rel = repo_relative(dest)
    manifest.remove_person(from_group, repo_relative_path)  # type: ignore[arg-type]
    manifest.add_person(to_group, new_rel)  # type: ignore[arg-type]
    return new_rel


def delete_person(
    repo_relative_path: str, *, group_key: str, delete_file: bool = True
) -> None:
    manifest.remove_person(group_key, repo_relative_path)  # type: ignore[arg-type]
    if delete_file:
        path = from_repo_relative(repo_relative_path)
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def projects_surface_folder(surface: str) -> Path:
    root = get_workspace().root
    if surface == "featured":
        return root / "Projects" / "Featured"
    if surface == "page":
        return root / "Projects" / "Page"
    raise KeyError(f"Unknown project surface: {surface!r}")


def list_projects(surface: str) -> list[tuple[str, Project]]:
    paths = manifest.get_section(get_workspace().projects_manifest, surface)
    out: list[tuple[str, Project]] = []
    for rel in paths:
        abs_path = from_repo_relative(rel)
        if not abs_path.exists():
            log.warning("Manifest references missing Project file: %s", rel)
            continue
        try:
            project = Project.model_validate(_read_json(abs_path))
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            log.warning("Skipping invalid Project entry %s: %s", rel, exc)
            continue
        out.append((rel, project))
    return out


def load_project(repo_relative_path: str) -> Project:
    return Project.model_validate(_read_json(from_repo_relative(repo_relative_path)))


def save_project(
    project: Project,
    *,
    surface: str,
    existing_relative_path: str | None = None,
) -> str:
    folder = projects_surface_folder(surface)
    folder.mkdir(parents=True, exist_ok=True)
    if existing_relative_path:
        target = from_repo_relative(existing_relative_path)
    else:
        slug = slugify(project.title)
        target = _unique_path(folder / f"{slug}.json")
    _write_json(target, project.to_json_dict())
    rel = repo_relative(target)
    if not existing_relative_path:
        manifest.add_project(surface, rel)  # type: ignore[arg-type]
    return rel


def delete_project(
    repo_relative_path: str, *, surface: str, delete_file: bool = True
) -> None:
    manifest.remove_project(surface, repo_relative_path)  # type: ignore[arg-type]
    if delete_file:
        path = from_repo_relative(repo_relative_path)
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def events_folder() -> Path:
    return get_workspace().root / "Events"


def list_events() -> list[tuple[str, Event]]:
    paths = manifest.get_section(get_workspace().events_manifest, "homepage")
    out: list[tuple[str, Event]] = []
    for rel in paths:
        abs_path = from_repo_relative(rel)
        if not abs_path.exists():
            log.warning("Manifest references missing Event file: %s", rel)
            continue
        try:
            raw = _read_json(abs_path)
            # docs say "headline (or use title as fallback)"
            if "headline" not in raw and "title" in raw:
                raw = {**raw, "headline": raw["title"]}
            event = Event.model_validate(raw)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            log.warning("Skipping invalid Event entry %s: %s", rel, exc)
            continue
        out.append((rel, event))
    return out


def load_event(repo_relative_path: str) -> Event:
    raw = _read_json(from_repo_relative(repo_relative_path))
    if "headline" not in raw and "title" in raw:
        raw = {**raw, "headline": raw["title"]}
    return Event.model_validate(raw)


def save_event(
    event: Event,
    *,
    existing_relative_path: str | None = None,
) -> str:
    folder = events_folder()
    folder.mkdir(parents=True, exist_ok=True)
    if existing_relative_path:
        target = from_repo_relative(existing_relative_path)
    else:
        slug = event.slug or slugify(event.headline)
        target = _unique_path(folder / f"{slug}.json")
    _write_json(target, event.to_json_dict())
    rel = repo_relative(target)
    if not existing_relative_path:
        manifest.add_event(rel)
    return rel


def delete_event(repo_relative_path: str, *, delete_file: bool = True) -> None:
    manifest.remove_event(repo_relative_path)
    if delete_file:
        path = from_repo_relative(repo_relative_path)
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


def jobs_folder() -> Path:
    return get_workspace().root / "Jobs"


def list_jobs() -> list[tuple[str, Job]]:
    paths = manifest.get_section(get_workspace().jobs_manifest, "jobs")
    out: list[tuple[str, Job]] = []
    for rel in paths:
        abs_path = from_repo_relative(rel)
        if not abs_path.exists():
            log.warning("Manifest references missing Job file: %s", rel)
            continue
        try:
            job = Job.model_validate(_read_json(abs_path))
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            log.warning("Skipping invalid Job entry %s: %s", rel, exc)
            continue
        out.append((rel, job))
    return out


def load_job(repo_relative_path: str) -> Job:
    return Job.model_validate(_read_json(from_repo_relative(repo_relative_path)))


def save_job(
    job: Job,
    *,
    existing_relative_path: str | None = None,
) -> str:
    folder = jobs_folder()
    folder.mkdir(parents=True, exist_ok=True)
    if existing_relative_path:
        target = from_repo_relative(existing_relative_path)
    else:
        slug = job.slug or slugify(job.title)
        target = _unique_path(folder / f"{slug}.json")
    _write_json(target, job.to_json_dict())
    rel = repo_relative(target)
    if not existing_relative_path:
        manifest.add_job(rel)
    return rel


def delete_job(repo_relative_path: str, *, delete_file: bool = True) -> None:
    manifest.remove_job(repo_relative_path)
    if delete_file:
        path = from_repo_relative(repo_relative_path)
        if path.exists():
            path.unlink()


# ---------------------------------------------------------------------------
# Suggested filename helpers (used by image picker for ``First_Last``).
# ---------------------------------------------------------------------------


def suggest_image_basename_for_person(name: str) -> str:
    """Return a ``First_Last`` style basename matching the existing repo style."""
    cleaned = filesafe_basename(name)
    parts = [p for p in cleaned.split("_") if p]
    return "_".join(parts) if parts else "headshot"


__all__ = [
    "delete_event",
    "delete_job",
    "delete_person",
    "delete_project",
    "events_folder",
    "jobs_folder",
    "list_events",
    "list_jobs",
    "list_people",
    "list_projects",
    "load_event",
    "load_job",
    "load_person",
    "load_project",
    "move_person_group",
    "people_group_folder",
    "projects_surface_folder",
    "save_event",
    "save_job",
    "save_person",
    "save_project",
    "suggest_image_basename_for_person",
]
