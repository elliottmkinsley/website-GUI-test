"""Tests for scripts/stamp_version.py.

These cover the playbook §4.1 contract:

* Valid versions round-trip.
* Invalid versions are rejected.
* ``--dry-run`` does not touch the filesystem.
* CHANGELOG ``## [Unreleased]`` promotion fires once and is a no-op
  the second time.
* ``_display_path`` does not crash on paths outside REPO_ROOT
  (playbook gotcha #9).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from scripts import stamp_version as sv


# ---------------------------------------------------------------------------
# normalise_version
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.0.0", "1.0.0"),
        ("v1.2.3", "1.2.3"),
        ("V0.0.1", "0.0.1"),
        ("  v9.8.7  ", "9.8.7"),
        ("12.34.56", "12.34.56"),
    ],
)
def test_normalise_accepts_valid(raw: str, expected: str) -> None:
    assert sv.normalise_version(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "1",
        "1.2",
        "1.2.3.4",
        "1.2.3-rc1",
        "1.2.3+build",
        "latest",
        "1.2.x",
    ],
)
def test_normalise_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        sv.normalise_version(raw)


# ---------------------------------------------------------------------------
# stamp_version_py
# ---------------------------------------------------------------------------


def _write_version_py(path: Path, version: str) -> None:
    path.write_text(
        '"""Test fixture."""\n\n'
        f'__version__: str = "{version}"\n',
        encoding="utf-8",
    )


def test_stamp_version_py_round_trip(tmp_path: Path) -> None:
    fixture = tmp_path / "__version__.py"
    _write_version_py(fixture, "0.0.1")
    assert sv.stamp_version_py("1.2.3", path=fixture) is True
    assert '__version__: str = "1.2.3"' in fixture.read_text(encoding="utf-8")
    # Idempotent: running with the same version is a no-op.
    assert sv.stamp_version_py("1.2.3", path=fixture) is False


def test_stamp_version_py_raises_when_missing_assignment(tmp_path: Path) -> None:
    fixture = tmp_path / "__version__.py"
    fixture.write_text("# no version here\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        sv.stamp_version_py("1.2.3", path=fixture)


# ---------------------------------------------------------------------------
# stamp_version_info
# ---------------------------------------------------------------------------


_VERSION_INFO_TEMPLATE = """\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(0, 0, 1, 0),
    prodvers=(0, 0, 1, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'FileVersion', u'0.0.1.0'),
            StringStruct(u'ProductVersion', u'0.0.1.0'),
          ]
        ),
      ]
    ),
  ]
)
"""


def test_stamp_version_info_round_trip(tmp_path: Path) -> None:
    fixture = tmp_path / "version_info.txt"
    fixture.write_text(_VERSION_INFO_TEMPLATE, encoding="utf-8")
    assert sv.stamp_version_info("2.5.0", path=fixture) is True
    text = fixture.read_text(encoding="utf-8")
    assert "filevers=(2, 5, 0, 0)" in text
    assert "prodvers=(2, 5, 0, 0)" in text
    assert "FileVersion', u'2.5.0.0'" in text
    assert "ProductVersion', u'2.5.0.0'" in text
    # Idempotent.
    assert sv.stamp_version_info("2.5.0", path=fixture) is False


# ---------------------------------------------------------------------------
# promote_changelog
# ---------------------------------------------------------------------------


def test_promote_changelog_promotes_unreleased(tmp_path: Path) -> None:
    fixture = tmp_path / "CHANGELOG.md"
    fixture.write_text(
        "# Changelog\n\n## [Unreleased]\n\n- thing\n", encoding="utf-8"
    )
    assert sv.promote_changelog("1.0.0", path=fixture) is True
    text = fixture.read_text(encoding="utf-8")
    assert f"## [v1.0.0] - {date.today().isoformat()}" in text
    assert "## [Unreleased]" not in text


def test_promote_changelog_is_noop_when_already_promoted(tmp_path: Path) -> None:
    fixture = tmp_path / "CHANGELOG.md"
    fixture.write_text(
        "# Changelog\n\n## [v1.0.0] - 2025-01-01\n\n- thing\n",
        encoding="utf-8",
    )
    assert sv.promote_changelog("1.0.0", path=fixture) is False


def test_promote_changelog_is_noop_when_no_unreleased_header(tmp_path: Path) -> None:
    fixture = tmp_path / "CHANGELOG.md"
    fixture.write_text("# Changelog\n\n- only this\n", encoding="utf-8")
    assert sv.promote_changelog("1.0.0", path=fixture) is False


# ---------------------------------------------------------------------------
# stamp_all
# ---------------------------------------------------------------------------


def _set_up_full_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    version_py = tmp_path / "__version__.py"
    version_info = tmp_path / "version_info.txt"
    changelog = tmp_path / "CHANGELOG.md"
    _write_version_py(version_py, "0.0.1")
    version_info.write_text(_VERSION_INFO_TEMPLATE, encoding="utf-8")
    changelog.write_text(
        "# Changelog\n\n## [Unreleased]\n\n- thing\n", encoding="utf-8"
    )
    monkeypatch.setattr(sv, "VERSION_PY", version_py)
    monkeypatch.setattr(sv, "VERSION_INFO_TXT", version_info)
    monkeypatch.setattr(sv, "CHANGELOG_MD", changelog)
    return version_py, version_info, changelog


def test_stamp_all_dry_run_does_not_touch_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    version_py, version_info, changelog = _set_up_full_fixture(tmp_path, monkeypatch)
    before = {
        version_py: version_py.read_text(encoding="utf-8"),
        version_info: version_info.read_text(encoding="utf-8"),
        changelog: changelog.read_text(encoding="utf-8"),
    }
    sv.stamp_all("v1.2.3", allow_missing=False, dry_run=True)
    for path, expected in before.items():
        assert path.read_text(encoding="utf-8") == expected


def test_stamp_all_writes_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    version_py, version_info, changelog = _set_up_full_fixture(tmp_path, monkeypatch)
    sv.stamp_all("1.2.3", allow_missing=False, dry_run=False)
    assert '__version__: str = "1.2.3"' in version_py.read_text(encoding="utf-8")
    assert "filevers=(1, 2, 3, 0)" in version_info.read_text(encoding="utf-8")
    assert "## [v1.2.3]" in changelog.read_text(encoding="utf-8")


def test_stamp_all_hard_fails_when_no_allow_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sv, "VERSION_PY", tmp_path / "missing.py")
    monkeypatch.setattr(sv, "VERSION_INFO_TXT", tmp_path / "missing.txt")
    monkeypatch.setattr(sv, "CHANGELOG_MD", tmp_path / "missing.md")
    with pytest.raises(FileNotFoundError):
        sv.stamp_all("1.0.0", allow_missing=False)


# ---------------------------------------------------------------------------
# _display_path (playbook gotcha #9)
# ---------------------------------------------------------------------------


def test_display_path_falls_back_when_not_under_repo_root(tmp_path: Path) -> None:
    # tmp_path is never under REPO_ROOT - exercise the fallback.
    result = sv._display_path(tmp_path / "wibble" / "version_info.txt")
    assert "wibble" in result and "version_info.txt" in result
