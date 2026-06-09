"""Tests for ``gui.deploy.git_publisher.publish_to_main`` and the
end-to-end orchestrator ``publish``.

The tests use a *local* bare repository as the ``origin`` remote so
they never hit the network. A second working clone (``other_clone``)
is used to simulate a competing GUI user who pushes while ours is in
flight, exercising the non-ff retry path.

Each test sets the GUI's active workspace via :func:`gui.workspace.set_workspace`
so :func:`gui.deploy.git_publisher.open_repo` resolves to our fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from git import Repo

from gui.config import ARCHIVE_BRANCH, MAIN_BRANCH
from gui.deploy.git_publisher import (
    GitPublishError,
    publish,
    publish_to_archive,
    publish_to_main,
)
from gui.workspace import set_workspace


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _commit(repo: Repo, message: str, *, allow_empty: bool = True) -> str:
    repo.git.add("--all")
    args = ["-m", message]
    if allow_empty:
        args.append("--allow-empty")
    repo.git.commit(*args)
    return repo.head.commit.hexsha


def _make_marker(root: Path, content: str = "<!doctype html><html></html>") -> None:
    """Drop an ``index.html`` marker so ``is_valid_workspace`` would pass."""
    (root / "index.html").write_text(content, encoding="utf-8")


def _write_data(root: Path, rel: str, content: str) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _init_named_repo(path: Path, name: str, email: str) -> Repo:
    """Init a repo with ``main`` as the default branch and a stable identity."""
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path, initial_branch=MAIN_BRANCH)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", name).release()
    with repo.config_writer() as cw:
        cw.set_value("user", "email", email).release()
    return repo


@pytest.fixture
def origin_dir(tmp_path: Path) -> Path:
    """Bare ``origin`` repo populated with an initial main commit."""
    seed_dir = tmp_path / "seed"
    seed = _init_named_repo(seed_dir, "Seed", "seed@example.com")
    _make_marker(seed_dir)
    _write_data(seed_dir, "People/manifest.json", '{"order": []}')
    _commit(seed, "seed commit", allow_empty=False)

    bare_dir = tmp_path / "origin.git"
    Repo.clone_from(str(seed_dir), str(bare_dir), bare=True)
    return bare_dir


@pytest.fixture
def workspace(tmp_path: Path, origin_dir: Path) -> Iterator[Path]:
    """Clone the bare origin into ``tmp_path/workspace`` and set it
    as the active GUI workspace for the duration of the test."""
    ws = tmp_path / "workspace"
    Repo.clone_from(str(origin_dir), str(ws), branch=MAIN_BRANCH)
    repo = Repo(ws)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Workspace User").release()
    with repo.config_writer() as cw:
        cw.set_value("user", "email", "workspace@example.com").release()
    set_workspace(ws)
    try:
        yield ws
    finally:
        set_workspace(None)


@pytest.fixture
def other_clone(tmp_path: Path, origin_dir: Path) -> Path:
    """A second working clone of origin, used to simulate a competing
    publisher who pushes between our fetch and our push."""
    other = tmp_path / "other"
    Repo.clone_from(str(origin_dir), str(other), branch=MAIN_BRANCH)
    repo = Repo(other)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Other User").release()
    with repo.config_writer() as cw:
        cw.set_value("user", "email", "other@example.com").release()
    return other


# ---------------------------------------------------------------------------
# publish_to_main
# ---------------------------------------------------------------------------


def test_publish_to_main_happy_path_pushes_dirty_working_tree(
    workspace: Path, origin_dir: Path
) -> None:
    _write_data(workspace, "People/manifest.json", '{"order": ["alice"]}')

    sha = publish_to_main(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    assert sha and len(sha) >= 7
    bare = Repo(origin_dir)
    head_commit = bare.commit(MAIN_BRANCH)
    assert head_commit.hexsha.startswith(sha)
    blob = head_commit.tree / "People" / "manifest.json"
    assert blob.data_stream.read().decode() == '{"order": ["alice"]}'


def test_publish_to_main_no_changes_is_noop_against_origin(
    workspace: Path, origin_dir: Path
) -> None:
    bare = Repo(origin_dir)
    before = bare.commit(MAIN_BRANCH).hexsha

    sha = publish_to_main(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    after = bare.commit(MAIN_BRANCH).hexsha
    assert after == before, "Clean workspace should not advance origin/main"
    assert sha == before[:8]


def test_publish_to_main_picks_up_behind_remote_state(
    workspace: Path, origin_dir: Path, other_clone: Path
) -> None:
    """Origin moves forward via ``other_clone`` BEFORE our publish.
    The fetch+reset inside publish_to_main should base our commit on
    that new state and our push should succeed first-try."""
    other = Repo(other_clone)
    _write_data(other_clone, "Projects/manifest.json", '{"order": ["bob"]}')
    _commit(other, "other publishes projects", allow_empty=False)
    other.remotes.origin.push(MAIN_BRANCH)

    _write_data(workspace, "People/manifest.json", '{"order": ["alice"]}')

    sha = publish_to_main(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    bare = Repo(origin_dir)
    head_commit = bare.commit(MAIN_BRANCH)
    assert head_commit.hexsha.startswith(sha)
    # Both our edit AND the other user's edit must be present.
    people_blob = head_commit.tree / "People" / "manifest.json"
    projects_blob = head_commit.tree / "Projects" / "manifest.json"
    assert people_blob.data_stream.read().decode() == '{"order": ["alice"]}'
    assert projects_blob.data_stream.read().decode() == '{"order": ["bob"]}'


def test_publish_to_main_retries_on_non_ff_rejection(
    workspace: Path,
    origin_dir: Path,
    other_clone: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Origin advances between our local fetch and our first push.
    The single retry inside ``publish_to_main`` should re-fetch,
    rebase our snapshot on top of the new tip, and push successfully.

    We race by patching ``git.cmd.Git._call_process`` at the class
    level (GitPython's ``Remote`` uses ``__slots__``, so per-instance
    attribute injection is not available). On the FIRST ``fetch``
    invocation we let the real fetch complete (so our local
    ``origin/main`` ref is still at the old tip) and *then* push a
    competing commit from ``other_clone``. publish_to_main resets
    to its now-stale local ``origin/main``, commits, hits a non-ff
    rejection on push, then the retry fetch sees the racer's commit
    and the second push wins.
    """
    import git.cmd as git_cmd

    _write_data(workspace, "People/manifest.json", '{"order": ["alice"]}')
    state: dict = {"injected": False}
    original_call_process = git_cmd.Git._call_process

    def _racing_call_process(self, name, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = original_call_process(self, name, *args, **kwargs)
        if name == "fetch" and not state["injected"]:
            state["injected"] = True
            other = Repo(other_clone)
            _write_data(
                other_clone, "Projects/manifest.json", '{"order": ["bob"]}'
            )
            _commit(other, "other races our push", allow_empty=False)
            other.remotes.origin.push(MAIN_BRANCH)
        return result

    monkeypatch.setattr(git_cmd.Git, "_call_process", _racing_call_process)

    sha = publish_to_main(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    bare = Repo(origin_dir)
    head_commit = bare.commit(MAIN_BRANCH)
    assert head_commit.hexsha.startswith(sha)
    # Final state must contain BOTH our edit AND the racer's edit -
    # proves the retry rebased our snapshot on top of the new tip.
    people = (head_commit.tree / "People" / "manifest.json").data_stream.read().decode()
    projects = (head_commit.tree / "Projects" / "manifest.json").data_stream.read().decode()
    assert people == '{"order": ["alice"]}'
    assert projects == '{"order": ["bob"]}'
    assert state["injected"], "Race fixture should have fired on the first fetch"


def test_publish_to_main_returns_to_original_branch_when_not_on_main(
    workspace: Path, origin_dir: Path
) -> None:
    """If the developer is on ``dev`` (in-repo dev mode), publish_to_main
    should leave them on ``dev`` with their dirty working tree intact."""
    repo = Repo(workspace)
    repo.git.checkout("-b", "dev")
    dev_head = repo.head.commit.hexsha

    _write_data(workspace, "People/manifest.json", '{"order": ["alice"]}')

    publish_to_main(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    assert repo.active_branch.name == "dev"
    assert repo.head.commit.hexsha == dev_head
    assert (workspace / "People" / "manifest.json").read_text() == '{"order": ["alice"]}'
    assert repo.is_dirty(untracked_files=False)


# ---------------------------------------------------------------------------
# Orchestrator: publish()
# ---------------------------------------------------------------------------


def test_publish_orchestrator_pushes_to_both_main_and_archive(
    workspace: Path, origin_dir: Path
) -> None:
    _write_data(workspace, "Events/manifest.json", '{"order": ["x"]}')

    result = publish(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    assert result.main_sha
    assert result.archive_sha
    assert result.archive_warning is None

    bare = Repo(origin_dir)
    main_head = bare.commit(MAIN_BRANCH)
    archive_head = bare.commit(ARCHIVE_BRANCH)
    assert main_head.hexsha.startswith(result.main_sha)
    assert archive_head.hexsha.startswith(result.archive_sha)
    # Both branches should contain the new file.
    for tree_head in (main_head, archive_head):
        events_blob = tree_head.tree / "Events" / "manifest.json"
        assert events_blob.data_stream.read().decode() == '{"order": ["x"]}'


def test_publish_orchestrator_treats_archive_failure_as_warning(
    workspace: Path, origin_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If publish_to_archive raises, publish() must still report the
    main_sha and surface the failure in archive_warning rather than
    propagating the exception."""
    import gui.deploy.git_publisher as gp

    _write_data(workspace, "Events/manifest.json", '{"order": ["x"]}')

    def _explode(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise GitPublishError("simulated archive push failure")

    monkeypatch.setattr(gp, "publish_to_archive", _explode)

    result = publish(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    assert result.main_sha
    assert result.archive_sha is None
    assert result.archive_warning is not None
    assert "simulated archive push failure" in result.archive_warning

    bare = Repo(origin_dir)
    assert bare.commit(MAIN_BRANCH).hexsha.startswith(result.main_sha)


# ---------------------------------------------------------------------------
# Sanity: publish_to_archive still works in isolation
# ---------------------------------------------------------------------------


def test_publish_to_archive_creates_archive_branch_from_scratch(
    workspace: Path, origin_dir: Path
) -> None:
    """First-ever archive push: the branch does not exist on origin
    and must be created from the snapshot commit."""
    _write_data(workspace, "Jobs/manifest.json", '{"order": ["j1"]}')

    sha = publish_to_archive(
        repo_root=workspace,
        github_username="tester",
        token=None,
    )

    bare = Repo(origin_dir)
    head = bare.commit(ARCHIVE_BRANCH)
    assert head.hexsha.startswith(sha)
    blob = head.tree / "Jobs" / "manifest.json"
    assert blob.data_stream.read().decode() == '{"order": ["j1"]}'
