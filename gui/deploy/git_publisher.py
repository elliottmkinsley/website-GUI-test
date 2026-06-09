"""Pull-at-startup + snapshot-to-archive-branch publish via ``GitPython``.

Strategy
--------
The *current* branch (``main``, ``dev``, whatever the user has
checked out) is left alone - we never commit to it from the GUI. On
publish we snapshot the working tree onto the dedicated ``archive``
branch, push it, then return to the original branch.

The snapshot strategy is: copy every staged + untracked + modified
*tracked* file path into a fresh commit on ``archive`` whose tree
matches the current working tree. This is done via a low-level
``git read-tree`` style approach using GitPython's ``IndexFile`` so
we don't rely on stash/reset gymnastics that could surprise the user.

For simplicity (and given the typical "edit + publish + done"
workflow), we use a more pragmatic approach instead: we ``git add -A``
all changes onto a temporary commit on the user's current branch (so
nothing is lost), then ``git switch`` to ``archive``, ``git checkout
<temp> -- .`` to materialize the same tree, commit, push, and
finally switch back and reset the user's branch back to where it
was. Any changes the user had in their working tree are preserved.

If anything goes wrong mid-way we abort the operation cleanly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from git import GitCommandError, Repo
from git.exc import InvalidGitRepositoryError

from gui.config import ARCHIVE_BRANCH
from gui.workspace import get_workspace

log = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


class GitPublishError(RuntimeError):
    """Raised when the publish-to-GitHub step cannot complete."""


@dataclass
class PullResult:
    pulled: bool
    message: str


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

    # Prepare a temporary commit to capture the current working tree.
    temp_branch_name = f"radiant-gui-publish-{int(datetime.now().timestamp())}"
    if progress:
        progress(f"Snapshotting working tree as {temp_branch_name} ...")

    git = repo.git
    original_head = repo.head.commit.hexsha

    # Capture the user's index state to restore later. We don't want
    # to leave staged-but-not-committed changes silently committed.
    pre_dirty = repo.is_dirty(untracked_files=True)
    if pre_dirty:
        git.add("--all")
        snapshot_msg = (
            f"radiant-gui: temporary snapshot for archive publish at "
            f"{datetime.now().isoformat(timespec='seconds')}"
        )
        try:
            git.commit("-m", snapshot_msg, "--allow-empty")
        except GitCommandError as exc:
            raise GitPublishError(
                f"Could not commit working-tree snapshot: {exc.stderr or exc}"
            ) from exc
        snapshot_commit = repo.head.commit.hexsha
    else:
        snapshot_commit = original_head

    pushed_sha: str | None = None

    try:
        # Configure the temporary token-authenticated push URL.
        original_url = _origin_https_url(repo)
        if token and original_url:
            _set_token_url(repo, token)

        try:
            # Fetch so we know if origin/archive exists.
            try:
                repo.remotes.origin.fetch()
            except GitCommandError as exc:
                raise GitPublishError(
                    f"git fetch failed: {exc.stderr or exc}"
                ) from exc

            # Switch to archive (or create it).
            archive_exists_remote = any(
                ref.remote_head == ARCHIVE_BRANCH
                for ref in repo.remotes.origin.refs
                if hasattr(ref, "remote_head")
            )
            if ARCHIVE_BRANCH in [h.name for h in repo.heads]:
                git.checkout(ARCHIVE_BRANCH)
                if archive_exists_remote:
                    git.reset("--hard", f"origin/{ARCHIVE_BRANCH}")
            elif archive_exists_remote:
                git.checkout("-b", ARCHIVE_BRANCH, f"origin/{ARCHIVE_BRANCH}")
            else:
                git.checkout("-b", ARCHIVE_BRANCH, snapshot_commit)

            # Bring the snapshot tree onto the archive branch.
            git.read_tree(snapshot_commit)
            git.checkout("--", ".")

            # Stage everything (including deletions); commit.
            git.add("--all")

            who = github_username or "unknown"
            stamp = datetime.now().isoformat(timespec="seconds")
            commit_msg = f"Publish: {stamp} by {who}"
            try:
                git.commit("-m", commit_msg, "--allow-empty")
            except GitCommandError as exc:
                raise GitPublishError(
                    f"git commit on {ARCHIVE_BRANCH} failed: {exc.stderr or exc}"
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
        # Always switch back, then unwind the snapshot commit so the
        # user's branch looks exactly like it did before.
        try:
            git.checkout(original_branch)
        except GitCommandError as exc:
            log.warning(
                "Could not switch back to %s after archive publish: %s",
                original_branch,
                exc,
            )

        if pre_dirty:
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
    # Strip any existing creds, then inject token.
    after_scheme = original[len("https://"):]
    host_path = after_scheme.split("@", 1)[-1]
    new_url = f"https://x-access-token:{token}@{host_path}"
    repo.remotes.origin.set_url(new_url, original)


def _restore_url(repo: Repo, original_url: str) -> None:
    try:
        repo.remotes.origin.set_url(original_url)
    except GitCommandError as exc:  # pragma: no cover - best effort
        log.warning("Could not restore origin URL: %s", exc)
