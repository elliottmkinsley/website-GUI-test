"""Workspace bootstrap: clone the website repo on first launch and
keep it up to date on subsequent launches.

The packaged ``.exe`` ships without the website data baked in - it
needs a real ``git`` checkout of ``elliottmkinsley/website-GUI-test``
on the user's disk to read manifests, edit JSON, generate WebP
variants, etc. On first launch (after the user signs in with
GitHub) we clone the ``main`` branch into ``user_data_dir() /
"workspace"``. On every subsequent launch we fast-forward pull so
the user sees fresh content from whoever else has been publishing.

The GitHub OAuth token from sign-in is injected into the clone /
fetch URLs as ``x-access-token:<token>@`` so we never need a
credential helper on disk. We restore the unauthenticated URL after
each operation so the token does not leak into ``.git/config``.

When running from a developer source tree (auto-detected by
:mod:`gui.workspace`) the workspace is the in-repo checkout and
this module is a no-op; the developer manages their own git state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from git import GitCommandError, Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from gui.config import GITHUB_REPO_FULL
from gui.workspace import Workspace

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]

# The branch we clone / pull. Tracked separately from the archive
# branch (which is the publish *destination*) so they cannot drift.
WORKSPACE_BRANCH = "main"

# HTTPS clone URL template - the token is injected before the host
# at clone/fetch time.
_HTTPS_URL = f"https://github.com/{GITHUB_REPO_FULL}.git"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CloneResult:
    """Outcome of :func:`clone_workspace`."""

    workspace: Workspace
    fresh: bool  # True if we cloned, False if the repo was already valid.


@dataclass(frozen=True)
class PullResult:
    """Outcome of :func:`pull_workspace`."""

    updated: bool
    message: str


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def is_valid_workspace(path: Path | str) -> bool:
    """``True`` iff ``path`` is a git checkout AND has the website
    marker files - both of which are required before any other GUI
    module can touch it."""
    target = Path(path)
    if not target.is_dir():
        return False
    if not (target / ".git").exists():
        return False
    if not (target / "index.html").exists():
        return False
    try:
        Repo(target)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return False
    return True


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------


def _token_url(token: str | None) -> str:
    """Return the clone URL, with a token-auth prefix when present."""
    if not token:
        return _HTTPS_URL
    return f"https://x-access-token:{token}@github.com/{GITHUB_REPO_FULL}.git"


def clone_workspace(
    target: Path | str,
    *,
    token: str | None = None,
    branch: str = WORKSPACE_BRANCH,
    progress: ProgressCallback | None = None,
) -> CloneResult:
    """Clone the website repo into ``target``.

    If ``target`` already contains a valid workspace the function is
    a no-op (returns ``fresh=False``). Otherwise the directory is
    created (parents and all) and ``git clone`` runs. The token is
    used only during the clone itself and is then scrubbed from
    ``origin``'s URL so it never lands in ``.git/config``.
    """
    target_path = Path(target).expanduser().resolve()
    if is_valid_workspace(target_path):
        if progress:
            progress(f"Workspace already present at {target_path}.")
        return CloneResult(workspace=Workspace(root=target_path), fresh=False)

    if target_path.exists() and any(target_path.iterdir()):
        # Pre-existing non-empty directory that is NOT a valid
        # workspace. Refuse rather than git-clone-into-a-half-state.
        raise RuntimeError(
            f"Cannot clone into {target_path}: directory is non-empty "
            "but does not contain a valid website checkout. Move or "
            "delete it, then try again."
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if progress:
        progress(f"Cloning {GITHUB_REPO_FULL} into {target_path} ...")

    auth_url = _token_url(token)
    try:
        repo = Repo.clone_from(auth_url, target_path, branch=branch)
    except GitCommandError as exc:
        raise RuntimeError(
            f"git clone failed: {exc.stderr.strip() if exc.stderr else exc}"
        ) from exc

    # Restore the un-authenticated URL so the token does not persist
    # on disk. Subsequent fetches still work because the GUI sets a
    # token URL on demand inside ``pull_workspace``.
    try:
        repo.remotes.origin.set_url(_HTTPS_URL)
    except GitCommandError as exc:  # pragma: no cover - best effort
        log.warning("Could not scrub token URL after clone: %s", exc)

    if progress:
        progress("Clone complete.")
    return CloneResult(workspace=Workspace(root=target_path), fresh=True)


# ---------------------------------------------------------------------------
# Pull
# ---------------------------------------------------------------------------


def pull_workspace(
    target: Path | str,
    *,
    token: str | None = None,
    branch: str = WORKSPACE_BRANCH,
    progress: ProgressCallback | None = None,
) -> PullResult:
    """Fast-forward pull the workspace from ``origin``.

    Refuses to pull when the working tree has uncommitted changes
    (the GUI's own writes are committed and pushed via
    :mod:`gui.deploy.git_publisher`; un-committed changes here mean
    a developer was hand-editing the checkout). Network failures
    are reported as ``updated=False`` rather than raised, so a
    stale workspace remains usable offline.
    """
    target_path = Path(target).expanduser().resolve()
    if not is_valid_workspace(target_path):
        return PullResult(
            updated=False,
            message=f"{target_path} is not a valid workspace; cannot pull.",
        )

    repo = Repo(target_path)
    if repo.is_dirty(untracked_files=False):
        return PullResult(
            updated=False,
            message=(
                "Workspace has uncommitted changes; skipped pull to "
                "avoid clobbering them."
            ),
        )

    if "origin" not in [r.name for r in repo.remotes]:
        return PullResult(
            updated=False,
            message="No 'origin' remote configured; skipping pull.",
        )

    if progress:
        progress(f"Pulling {branch} from origin ...")

    auth_url = _token_url(token)
    original_url: str | None = None
    try:
        original_url = repo.remotes.origin.url
        if token:
            repo.remotes.origin.set_url(auth_url, original_url)
        try:
            before = repo.head.commit.hexsha
            repo.remotes.origin.pull(branch, ff_only=True)
            after = repo.head.commit.hexsha
        except GitCommandError as exc:
            return PullResult(
                updated=False,
                message=f"git pull failed: {exc.stderr.strip() if exc.stderr else exc}",
            )
    finally:
        if original_url and token:
            try:
                repo.remotes.origin.set_url(original_url)
            except GitCommandError as exc:  # pragma: no cover
                log.warning("Could not restore origin URL after pull: %s", exc)

    if before == after:
        return PullResult(updated=False, message="Workspace already up to date.")
    return PullResult(
        updated=True,
        message=f"Pulled {branch} from origin ({before[:7]} -> {after[:7]}).",
    )


__all__ = [
    "CloneResult",
    "PullResult",
    "WORKSPACE_BRANCH",
    "clone_workspace",
    "is_valid_workspace",
    "pull_workspace",
]
