# Changelog

All notable user-facing changes to the Radiant Content GUI are
recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

CI promotes the `## [Unreleased]` block below to a versioned entry
on every release (see `scripts/stamp_version.py`). When adding a
new change, append it under the appropriate sub-heading
(`### Added`, `### Changed`, `### Fixed`, `### Removed`) inside the
`## [Unreleased]` block.

## [Unreleased]

### Added

- First public installer for Windows, distributed via GitHub
  Releases (`RadiantContentGUISetup.exe`).
- First-launch workspace bootstrap that auto-clones the website
  repo into the user's app-data folder.
- NAU server reachability indicator in the bottom-right corner.
- "Check for updates..." link under the Help menu.

### Known limitations

- macOS and Linux installers are not yet provided; the application
  still runs from source on those platforms.
- The installer is currently unsigned, so Windows SmartScreen will
  ask you to confirm "More info -> Run anyway" on first launch.
