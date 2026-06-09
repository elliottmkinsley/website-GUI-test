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

- **Auto-sync workspace on launch.** Every app launch fast-forwards
  the local website checkout from `origin/main`, and a quiet
  background timer (default: every 5 minutes) keeps it current
  while the app is open. Other GUI users now see your published
  edits automatically.
- **`Help > Sync workspace now`** menu item (and **F5** shortcut)
  for an on-demand sync, plus a refresh button on the new
  bottom-right sync indicator.
- **Sync status indicator** in the bottom-right of the window:
  shows "Workspace synced just now / 3m ago", "Syncing...",
  "Sync paused", or "Sync failed - click to retry".

### Changed

- **Publish now writes to `origin/main` in addition to
  `origin/archive`.** The push to `main` is the source of truth
  that other GUI users pull on their next sync; the push to
  `archive` continues to record every publish as a snapshot for
  history. If the archive push fails, the publish is still
  considered successful and `main` is up to date.
- The Publish page now shows three step indicators (NAU share,
  GitHub `main`, GitHub `archive`) so it is clear which parts of
  a publish succeeded.

## [0.1.0] - 2026-06-08

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
