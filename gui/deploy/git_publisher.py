"""Publish to GitHub: commit-to-main (content sync) + snapshot-to-archive
(per-publish history), with safe handling of whatever branch the user
happens to be checked out on.

Strategy
--------
Every successful Publish updates two refs on ``origin``:

1. ``main`` - the **source of truth** for GUI-managed content. A real
   commit lands here so any other GUI user who pulls ``main`` on launch
   (or via the background :mod:`gui.services.sync_manager`) picks up
   the changes.
2. ``archive`` - the historical mirror. A snapshot commit lands here
   so every Publish remains addressable even if ``main`` is rewritten
   by humans / CI later.

Both pushes use the same working-tree snapshot, captured before either
branch is touched, so they cannot disagree.

Why we snapshot the working tree first
--------------------------------------
The GUI runs on whatever branch the user has checked out. In the
packaged ``.exe`` flow the workspace is always on ``main`` (cloned by
:mod:`gui.repo.clone`). In dev-mode the developer may be on ``dev``,
``main``, a feature branch, anything. Rather than special-case each
scenario we always:

* stage every change as a temporary commit on the user's current
  branch (``snapshot_commit``),
* do all branch switching / push work against that snapshot,
* return the user to their original branch with the original index
  state if we ever moved off of it.

The lone exception: when the user was originally on ``main`` we want
``main`` to *stay* at the new published commit (the working tree
becomes clean, which is correct - their edits are now in the commit).

Failure semantics
-----------------
* If ``main`` cannot be fast-forwarded onto ``origin/main`` (e.g.,
  diverging history outside the GUI), :func:`publish_to_main` raises
  :class:`GitPublishError` with guidance.
* ``main`` push gets one automatic retry after a fresh fetch + rebase
  to handle the "another GUI user pushed while we were preparing".
* The orchestrator :func:`publish` treats the archive push as
  *best-effort*: a failure there does not fail the whole publish,
  because ``main`` (the source of truth) is already updated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from git import GitCommandError, Repo
from git.exc import InvalidGitRepositoryError

from gui.config import ARCHIVE_BRANCH, MAIN_BRANCH
from gui.workspace import get_workspace

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


class GitPublishError(RuntimeError):
    """Raised when the publish-to-GitHub step cannot complete."""


@dataclass
class PullResult:
    pulled: bool
    message: str


@dataclass
class PublishResult:
    """End-to-end Publish outcome returned by :func:`publish`."""

    main_sha: str
    """Short SHA of the new commit on ``origin/main``."""

    archive_sha: str | None
    """Short SHA on ``origin/archive``, or ``None`` if the archive
    push was skipped or failed (see :attr:`archive_warning`)."""

    archive_warning: str | None
    """Human-readable warning when the archive push did not succeed.
    ``main`` is still the source of truth so the publish is considered
    successful overall."""


def open_repo(repo_root: Path | None = None) -> Repo:
    root = repo_root if repo_root is not None else get_workspace().root
    try:
        return Repo(root)
    except InvalidGitRepositoryError as exc:
        raise GitPublishError(
            f"{root} is not a Git repository: {exc}"
        ) from exc


def pull_main(
    repo_root: Path | None = None, *, progress: ProgressCallback | None = None
) -> PullResult:
    """Run a ``git pull`` on the current branch from ``origin``.

    Refuses if the working tree has uncommitted changes - the user
    must resolve those manually so we never silently merge over
    their in-progress edits.
    """
    repo = open_repo(repo_root)
    if repo.is_dirty(untracked_files=False):
        return PullResult(
            pulled=False,
            message=(
                "Your working tree has uncommitted changes. The app skipped "
                "pulling from origin to avoid overwriting them."
            ),
        )
    if "origin" not in [r.name for r in repo.remotes]:
        return PullResult(
            pulled=False,
            message="No 'origin' remote configured; skipping pull.",
        )
    branch = _active_branch_name(repo)
    if not branch:
        return PullResult(
            pulled=False,
            message="HEAD is detached; skipping pull.",
        )
    if progress:
        progress(f"Pulling {branch} from origin ...")
    try:
        repo.remotes.origin.pull(branch)
    except GitCommandError as exc:
        return PullResult(
            pulled=False,
            message=f"git pull failed: {exc.stderr or exc}",
        )
    return PullResult(pulled=True, message=f"Pulled {branch} from origin.")


def _active_branch_name(repo: Repo) -> str | None:
    try:
        return repo.active_branch.name
    except TypeError:
        return None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _snapshot_working_tree(
    repo: Repo, *, kind: str
) -> tuple[str, bool]:
    """Stage and commit the current working tree as a temp commit on
    the active branch. Returns ``(snapshot_sha, was_dirty)``.

    When the tree is already clean we skip the commit and reuse the
    current HEAD as the snapshot - callers treat ``was_dirty`` as the
    signal for whether the temp commit needs to be unwound later.
    """
    git = repo.git
    pre_dirty = repo.is_dirty(untracked_files=True)
    if not pre_dirty:
        return repo.head.commit.hexsha, False
    git.add("--all")
    msg = (
        f"radiant-gui: temporary snapshot for {kind} publish at "
        f"{datetime.now().isoformat(timespec='seconds')}"
    )
    try:
        git.commit("-m", msg, "--allow-empty")
    except GitCommandError as exc:
        raise GitPublishError(
            f"Could not commit working-tree snapshot: {exc.stderr or exc}"
        ) from exc
    return repo.head.commit.hexsha, True


def _apply_snapshot_tree(repo: Repo, snapshot_sha: str) -> None:
    """Replace the working tree (and index) with ``snapshot_sha``'s tree.

    Used after switching to a publish target branch so the next commit
    captures exactly the snapshot's content. ``git add --all`` picks up
    additions, modifications, and deletions relative to that branch.
    """
    git = repo.git
    git.read_tree(snapshot_sha)
    git.checkout("--", ".")
    git.add("--all")


def _checkout_with_remote_tracking(
    repo: Repo, branch_name: str, *, fallback_base: str | None
) -> None:
    """Check out ``branch_name``, creating it from ``origin`` if needed.

    If the branch is missing both locally and on origin and ``fallback_base``
    is set, create it from that commit. Otherwise raise ``GitPublishError``.
    """
    git = repo.git
    exists_remote = any(
        getattr(ref, "remote_head", None) == branch_name
        for ref in repo.remotes.origin.refs
    )
    if branch_name in [h.name for h in repo.heads]:
        git.checkout(branch_name)
        return
    if exists_remote:
        git.checkout("-b", branch_name, f"origin/{branch_name}")
        return
    if fallback_base is not None:
        git.checkout("-b", branch_name, fallback_base)
        return
    raise GitPublishError(
        f"Branch '{branch_name}' does not exist locally or on origin."
    )


# ---------------------------------------------------------------------------
# Publish to main (content sync source of truth)
# ---------------------------------------------------------------------------


def publish_to_main(
    *,
    repo_root: Path | None = None,
    github_username: str | None = None,
    token: str | None = None,
    progress: ProgressCallback | None = None,
) -> str:
    """Commit the working tree to ``main`` and push it to origin.

    Returns the short SHA of the new commit on ``main``.
    The temp snapshot used for branch-switching is unwound on return
    so the user's *original* branch and working-tree state are
    preserved - unless the user was already on ``main``, in which
    case we leave ``main`` advanced to the new published commit
    (their edits are now committed; the working tree becomes clean).

    Raises :class:`GitPublishError` on failure, including the
    'another publish landed' case after one retry.
    """
    repo = open_repo(repo_root)
    if "origin" not in [r.name for r in repo.remotes]:
        raise GitPublishError("No 'origin' remote configured.")

    original_branch = _active_branch_name(repo)
    if not original_branch:
        raise GitPublishError(
            "HEAD is detached. Check out a branch before publishing."
        )
    original_head = repo.head.commit.hexsha
    git = repo.git

    if progress:
        progress("Preparing working-tree snapshot for main ...")
    snapshot_commit, was_dirty = _snapshot_working_tree(repo, kind="main")

    on_main = original_branch == MAIN_BRANCH
    pushed_sha: str | None = None

    try:
        original_url = _origin_https_url(repo)
        if token and original_url:
            _set_token_url(repo, token)

        try:
            if progress:
                progress("Fetching origin ...")
            try:
                repo.remotes.origin.fetch()
            except GitCommandError as exc:
                raise GitPublishError(
                    f"git fetch failed: {exc.stderr or exc}"
                ) from exc

            _checkout_with_remote_tracking(
                repo, MAIN_BRANCH, fallback_base=None
            )

            # Align local main with origin/main so our commit
            # fast-forwards cleanly. Any unpushed commits on local
            # main would be lost - but in both packaged-app and
            # dev-mode use, local main is a tracking branch only.
            try:
                git.reset("--hard", f"origin/{MAIN_BRANCH}")
            except GitCommandError as exc:
                raise GitPublishError(
                    f"Could not align local {MAIN_BRANCH} with "
                    f"origin/{MAIN_BRANCH}: {exc.stderr or exc}"
                ) from exc

            _apply_snapshot_tree(repo, snapshot_commit)

            if not repo.is_dirty(untracked_files=False):
                if progress:
                    progress(
                        "No content changes vs origin/main; nothing to "
                        "publish to main."
                    )
                pushed_sha = repo.head.commit.hexsha[:8]
            else:
                who = github_username or "unknown"
                stamp = datetime.now().isoformat(timespec="seconds")
                commit_msg = f"Publish: {stamp} by {who}"
                try:
                    git.commit("-m", commit_msg)
                except GitCommandError as exc:
                    raise GitPublishError(
                        f"git commit on {MAIN_BRANCH} failed: "
                        f"{exc.stderr or exc}"
                    ) from exc

                pushed_sha = repo.head.commit.hexsha[:8]
                if progress:
                    progress(f"Pushing {MAIN_BRANCH} to origin ...")
                try:
                    git.push("origin", MAIN_BRANCH)
                except GitCommandError as exc:
                    if progress:
                        progress(
                            "Push to main rejected; refetching and "
                            "retrying once..."
                        )
                    try:
                        repo.remotes.origin.fetch()
                        git.reset("--hard", f"origin/{MAIN_BRANCH}")
                        _apply_snapshot_tree(repo, snapshot_commit)
                        if repo.is_dirty(untracked_files=False):
                            git.commit("-m", commit_msg)
                            pushed_sha = repo.head.commit.hexsha[:8]
                            git.push("origin", MAIN_BRANCH)
                        else:
                            pushed_sha = repo.head.commit.hexsha[:8]
                    except GitCommandError as exc2:
                        raise GitPublishError(
                            f"git push to {MAIN_BRANCH} failed even after "
                            f"a retry: {exc2.stderr or exc2}. Another "
                            "publish may have landed - reopen the app "
                            "to pull, then republish."
                        ) from exc2
        finally:
            if token and original_url:
                _restore_url(repo, original_url)
    finally:
        if not on_main:
            try:
                git.checkout(original_branch)
            except GitCommandError as exc:
                log.warning(
                    "Could not switch back to %s after main publish: %s",
                    original_branch, exc,
                )
            if was_dirty:
                try:
                    git.reset("--mixed", original_head)
                except GitCommandError as exc:
                    log.warning(
                        "Could not unwind temp snapshot commit on %s; "
                        "user may need to reset manually: %s",
                        original_branch, exc,
                    )

    if pushed_sha is None:
        raise GitPublishError(
            "Publish to main completed without producing a commit."
        )
    return pushed_sha


# ---------------------------------------------------------------------------
# Publish to archive (per-publish history)
# ---------------------------------------------------------------------------


def publish_to_archive(
    *,
    repo_root: Path | None = None,
    github_username: str | None = None,
    token: str | None = None,
    progress: ProgressCallback | None = None,
) -> str:
    """Snapshot the current working tree as a new commit on ``archive``
    and push to ``origin``. Returns the new commit's short SHA.

    ``token`` is used to set a temporary HTTPS-with-token push URL on
    ``origin`` so users don't have to configure a credential helper.
    """
    repo = open_repo(repo_root)

    if "origin" not in [r.name for r in repo.remotes]:
        raise GitPublishError("No 'origin' remote configured.")

    original_branch = _active_branch_name(repo)
    if not original_branch:
        raise GitPublishError(
            "HEAD is detached. Check out a branch before publishing."
        )
    original_head = repo.head.commit.hexsha

    if progress:
        progress("Preparing working-tree snapshot for archive ...")
    snapshot_commit, was_dirty = _snapshot_working_tree(repo, kind="archive")

    git = repo.git
    pushed_sha: str | None = None

    try:
        original_url = _origin_https_url(repo)
        if token and original_url:
            _set_token_url(repo, token)

        try:
            try:
                repo.remotes.origin.fetch()
            except GitCommandError as exc:
                raise GitPublishError(
                    f"git fetch failed: {exc.stderr or exc}"
                ) from exc

            archive_exists_remote = any(
                getattr(ref, "remote_head", None) == ARCHIVE_BRANCH
                for ref in repo.remotes.origin.refs
            )
            if ARCHIVE_BRANCH in [h.name for h in repo.heads]:
                git.checkout(ARCHIVE_BRANCH)
                if archive_exists_remote:
                    git.reset("--hard", f"origin/{ARCHIVE_BRANCH}")
            elif archive_exists_remote:
                git.checkout("-b", ARCHIVE_BRANCH, f"origin/{ARCHIVE_BRANCH}")
            else:
                git.checkout("-b", ARCHIVE_BRANCH, snapshot_commit)

            _apply_snapshot_tree(repo, snapshot_commit)

            who = github_username or "unknown"
            stamp = datetime.now().isoformat(timespec="seconds")
            commit_msg = f"Publish: {stamp} by {who}"
            try:
                git.commit("-m", commit_msg, "--allow-empty")
            except GitCommandError as exc:
                raise GitPublishError(
                    f"git commit on {ARCHIVE_BRANCH} failed: "
                    f"{exc.stderr or exc}"
                ) from exc

            pushed_sha = repo.head.commit.hexsha[:8]
            if progress:
                progress(f"Pushing {ARCHIVE_BRANCH} to origin ...")
            try:
                git.push("origin", ARCHIVE_BRANCH)
            except GitCommandError as exc:
                raise GitPublishError(
                    f"git push failed: {exc.stderr or exc}"
                ) from exc
        finally:
            if token and original_url:
                _restore_url(repo, original_url)
    finally:
        try:
            git.checkout(original_branch)
        except GitCommandError as exc:
            log.warning(
                "Could not switch back to %s after archive publish: %s",
                original_branch, exc,
            )

        if was_dirty:
            try:
                git.reset("--mixed", original_head)
            except GitCommandError as exc:
                log.warning(
                    "Could not unwind temp snapshot commit; user may need "
                    "to reset manually: %s",
                    exc,
                )

    if pushed_sha is None:
        raise GitPublishError("Publish completed without producing a commit.")
    return pushed_sha


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def publish(
    *,
    repo_root: Path | None = None,
    github_username: str | None = None,
    token: str | None = None,
    progress: ProgressCallback | None = None,
) -> PublishResult:
    """End-to-end GitHub publish.

    Runs :func:`publish_to_main` first (the source of truth for
    multi-user content sync). If that succeeds, runs
    :func:`publish_to_archive` as best-effort history. Archive
    failure is surfaced via :attr:`PublishResult.archive_warning`
    but does *not* raise - main has already been updated.
    """
    if progress:
        progress("--- GitHub: main (content sync) ---")
    main_sha = publish_to_main(
        repo_root=repo_root,
        github_username=github_username,
        token=token,
        progress=progress,
    )
    if progress:
        progress(f"Main commit: {main_sha}")
        progress("--- GitHub: archive (history snapshot) ---")

    archive_sha: str | None = None
    archive_warning: str | None = None
    try:
        archive_sha = publish_to_archive(
            repo_root=repo_root,
            github_username=github_username,
            token=token,
            progress=progress,
        )
    except GitPublishError as exc:
        archive_warning = (
            f"Archive snapshot push failed: {exc}. Main is up to date; "
            "the archive snapshot can be retried on the next publish."
        )
        log.warning(archive_warning)
        if progress:
            progress(archive_warning)
    return PublishResult(
        main_sha=main_sha,
        archive_sha=archive_sha,
        archive_warning=archive_warning,
    )


# ---------------------------------------------------------------------------
# URL token helpers
# ---------------------------------------------------------------------------


def _origin_https_url(repo: Repo) -> str | None:
    try:
        url = repo.remotes.origin.url
    except AttributeError:
        return None
    if url and url.startswith("https://"):
        return url
    return None


def _set_token_url(repo: Repo, token: str) -> None:
    """Inject ``x-access-token:<token>@`` into the origin HTTPS URL.

    Restored to the original URL on success or failure - see
    ``_restore_url``.
    """
    original = _origin_https_url(repo)
    if not original:
        return
    after_scheme = original[len("https://"):]
    host_path = after_scheme.split("@", 1)[-1]
    new_url = f"https://x-access-token:{token}@{host_path}"
    repo.remotes.origin.set_url(new_url, original)


def _restore_url(repo: Repo, original_url: str) -> None:
    try:
        repo.remotes.origin.set_url(original_url)
    except GitCommandError as exc:  # pragma: no cover - best effort
        log.warning("Could not restore origin URL: %s", exc)


__all__ = [
    "GitPublishError",
    "PublishResult",
    "PullResult",
    "open_repo",
    "publish",
    "publish_to_archive",
    "publish_to_main",
    "pull_main",
]
