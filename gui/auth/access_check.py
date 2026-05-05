"""Verify the signed-in user has push access to the gating repo.

Uses ``PyGithub`` for clarity. Returns a small structured result so
the UI can show a precise message when access is denied.
"""

from __future__ import annotations

import dataclasses
import logging

from github import Auth, Github
from github.GithubException import GithubException, UnknownObjectException

from gui.config import GITHUB_REPO_FULL

log = logging.getLogger(__name__)


@dataclasses.dataclass
class AccessResult:
    allowed: bool
    username: str | None
    message: str

    @property
    def ok(self) -> bool:
        return self.allowed


def check_repo_push_access(token: str) -> AccessResult:
    """Confirm the user behind ``token`` can push to the gating repo.

    The function is forgiving about which permission shape GitHub
    returns: it counts ``permissions.push``, ``permissions.maintain``,
    or ``permissions.admin`` as valid push access.
    """
    try:
        gh = Github(auth=Auth.Token(token), per_page=1)
        user = gh.get_user()
        username = user.login
    except GithubException as exc:
        return AccessResult(
            allowed=False,
            username=None,
            message=(
                "Could not authenticate with GitHub using that token "
                f"(status {exc.status}). Try logging in again."
            ),
        )

    try:
        repo = gh.get_repo(GITHUB_REPO_FULL)
    except UnknownObjectException:
        return AccessResult(
            allowed=False,
            username=username,
            message=(
                f"The GitHub user '{username}' cannot see "
                f"{GITHUB_REPO_FULL}. Ask the repo owner to grant access."
            ),
        )
    except GithubException as exc:
        return AccessResult(
            allowed=False,
            username=username,
            message=(
                f"GitHub returned an error fetching {GITHUB_REPO_FULL} "
                f"(status {exc.status}). Try again, or sign in with a "
                "different account."
            ),
        )

    perms = getattr(repo, "permissions", None)
    has_push = bool(
        perms
        and (
            getattr(perms, "push", False)
            or getattr(perms, "maintain", False)
            or getattr(perms, "admin", False)
        )
    )

    if has_push:
        return AccessResult(
            allowed=True,
            username=username,
            message=f"Signed in as {username}.",
        )

    return AccessResult(
        allowed=False,
        username=username,
        message=(
            f"'{username}' does not have push access to {GITHUB_REPO_FULL}. "
            "Ask the repo owner to add you as a collaborator."
        ),
    )
