# Radiant Content GUI

A desktop app for editors of the Radiant Center for Remote Sensing
website. It provides forms for adding, editing, deleting, and
reordering the four data domains the site renders from JSON
(`People/`, `Projects/`, `Events/`, `Jobs/`), then publishes the
resulting working tree to:

1. The NAU SMB share at `\\arshares.ucc.nau.edu\Web\radiant.nau.edu`
   (the live website files).
2. `origin/main` on GitHub - the source of truth that every other
   GUI user pulls from on launch and every five minutes in the
   background.
3. `origin/archive` on GitHub - a per-publish snapshot, kept as
   history.

When one editor publishes, every other open GUI app picks up the
change on its next sync without anyone having to restart.

## For end users

Editors do **not** need Python or Git. Download the latest installer
from
[the Releases page](https://github.com/elliottmkinsley/website-GUI-test/releases/latest)
and follow [docs/INSTALLING.md](../docs/INSTALLING.md). The installed
app auto-clones the website repo into your user-data folder on
first launch.

The rest of this README is the **developer** guide for running from
source and producing new installers.

---

## Requirements (developer)

- Python 3.11 or newer (CI builds on 3.13)
- Git installed and on `PATH`
- A GitHub account with push access to `elliottmkinsley/website-GUI-test`
- For Publish: an NAU computer or remote-desktop session with the SMB
  share already mounted (the app shows you exactly how to mount it on
  Windows, macOS, and Linux when it can't reach the share)

## Setup (one-time)

```bash
# 1. Clone the website repo (the GUI lives at gui/ inside it)
git clone https://github.com/elliottmkinsley/website-GUI-test.git
cd website-GUI-test

# 2. Create a virtual environment and install deps
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r gui/requirements.txt
```

## Run from source

```bash
python -m gui
```

When running from source the workspace auto-detection finds the
website checkout you cloned above (because `gui/` lives at
`<repo>/gui/`), so the app reads and writes JSON files in place.
For end users running the packaged `.exe`, the workspace is instead
auto-cloned into `%APPDATA%\Radiant Center for Remote Sensing\Radiant Content GUI\workspace`
on first launch.

To point the app at a custom workspace (e.g. a throwaway test
checkout), set `RADIANT_GUI_WORKSPACE`:

```bash
set RADIANT_GUI_WORKSPACE=C:\tmp\test-checkout
python -m gui
```

## Run tests

```bash
pip install pytest
python -m pytest tests/
```

The suite covers:

- `scripts/stamp_version.py` (round-trip, validation, dry-run).
- The GitPython console-flash patch in `gui/services/git_safe.py`.
- The dual-push publisher in `gui/deploy/git_publisher.py` (happy
  path, behind-remote auto-fast-forward, non-ff push retry,
  orchestrator behaviour when the archive push fails).
- The background-sync service in `gui/services/sync_manager.py`
  (timer-driven pull, pause/resume reference counting, coalescing,
  signal emission).

## Build a frozen app locally

PyInstaller is the freezer. The same spec
(`packaging/radiant_content_gui.spec`) drives both OSes; per-OS
shell wrappers live next to it.

### Windows

```powershell
# Install the build tools if you haven't already:
pip install "pyinstaller>=6.0"
choco install innosetup -y  # one-time, requires admin

# Produce dist\RadiantContentGUI\RadiantContentGUI.exe
pwsh packaging\build_app.ps1            # or: powershell on Windows PowerShell 5.1

# Verify the bundle imports cleanly
.\dist\RadiantContentGUI\RadiantContentGUI.exe --selftest

# Wrap the bundle into dist\RadiantContentGUISetup.exe
pwsh packaging\build_installer.ps1 -SkipVendor
```

Both scripts work under PowerShell 5.1 (`powershell`) or PowerShell
7+ (`pwsh`). CI uses `pwsh` on `windows-latest`.

### macOS

Requires macOS 11+ with Python 3.11+ (universal2 build - the
official `python.org` installers and `actions/setup-python` macOS
images both qualify; Homebrew's arm64-only Python does **not**, so
PyInstaller would silently produce a single-arch app):

```bash
# Install the build tools if you haven't already:
pip install "pyinstaller>=6.0"
brew install create-dmg                 # nice drag-to-Applications layout

# Produce dist/RadiantContentGUI.app
bash packaging/build_app.sh

# Verify the bundle imports cleanly
./dist/RadiantContentGUI.app/Contents/MacOS/RadiantContentGUI --selftest

# Wrap the .app into dist/RadiantContentGUI-<version>.dmg
bash packaging/build_dmg.sh
```

If `create-dmg` is missing the DMG script falls back to plain
`hdiutil`; the resulting DMG is functional but lacks the curated
icon-and-Applications-shortcut layout.

The app icon `.icns` is generated from the same placeholder design
as `.ico` (`packaging/make_icns.py`). Both are checked into the
repo so CI does not need `iconutil` or Pillow ICNS support; only
re-run the generator scripts after replacing the placeholder
design.

### `--selftest`

The `--selftest` argv flag imports every top-level GUI module and
exits 0. It's the cheapest way to catch PyInstaller hidden-import
misses inside the frozen environment and is called from both the
Windows Inno Setup post-install step and the macOS CI job.

## Cut a release

The single source of truth for the version is
[`gui/__version__.py`](__version__.py). `scripts/stamp_version.py`
keeps that file, `packaging/version_info.txt` (Windows VERSIONINFO),
and `docs/CHANGELOG.md` in sync.

To release `v1.2.3`:

```powershell
# Optional dry-run: see what would change without writing.
python scripts/stamp_version.py --version v1.2.3 --dry-run --no-allow-missing

# Then push the tag - CI does everything else.
git tag v1.2.3
git push origin v1.2.3
```

`.github/workflows/release.yml` is triggered by lowercase `v*` tags
and produces a GitHub Release with **both** `RadiantContentGUISetup.exe`
(Windows) **and** `RadiantContentGUI-<version>.dmg` (macOS universal)
attached. The workflow has two sequential jobs:

1. `build-windows` (windows-latest):
   1. Stamps the version into every target file.
   2. Runs the unit tests headlessly (`QT_QPA_PLATFORM=offscreen`).
   3. Freezes the app with PyInstaller.
   4. Selftests the frozen `.exe`.
   5. Signs it (no-op until a code-signing cert is added).
   6. Builds the installer with Inno Setup (`/DSingleFile=1` for a
      single-exe online installer).
   7. Computes SHA-256 and extracts this version's CHANGELOG section.
   8. Creates the GitHub Release with the Windows installer and the
      composed release body.
2. `build-macos` (macos-latest, `needs: build-windows`):
   1. Re-stamps the version (fresh checkout).
   2. Installs `create-dmg` via Homebrew.
   3. Runs the unit tests headlessly.
   4. Freezes a universal2 `.app` with PyInstaller.
   5. Selftests the frozen launcher.
   6. Wraps it in a DMG via `packaging/build_dmg.sh`.
   7. Appends the DMG as an additional asset on the same Release.
   8. Patches the Release body to splice in the DMG SHA-256
      (via `scripts/insert_dmg_hash_in_body.py`).

Sequential (rather than parallel matrix) keeps the release body
authored by exactly one job, avoiding races where both would try
to create the Release simultaneously. The Mac job costs ~10 extra
minutes per tag.

Always use **lowercase** `v` in tag names; the workflow trigger is
case-sensitive and uppercase `V` collides with the lowercase form on
Windows filesystems.

On the very first launch the app shows a **Setup** screen that asks
for a GitHub OAuth App Client ID. Two steps, no code editing:

1. Click **Register new OAuth App on GitHub**. The form opens in your
   browser pre-suggested with the right values (Application name,
   Homepage URL, Authorization callback URL, **Enable Device Flow**
   checked).
2. Save the GitHub form, copy the **Client ID** from the resulting
   settings page, paste it back into the Setup screen, and click
   **Save & Continue**.

The Client ID is stored in your user profile via Qt's `QSettings`
(Windows registry, macOS plist, or Linux conf file) so subsequent
launches go straight to the login screen. You can change the Client
ID at any time via **File > GitHub OAuth Client ID...**.

After Setup the app shows the GitHub login screen using OAuth Device
Flow:

1. The app shows you a short user code (e.g. `ABCD-1234`).
2. Click **Open GitHub** (or visit `https://github.com/login/device`).
3. Paste the code, authorize the app.
4. Back in the app, the screen advances automatically once the token
   is issued. The token is stored securely in your OS keychain via
   `keyring`, so subsequent launches skip straight to the dashboard.

If your GitHub user does not have push access to the gating repo, the
app shows an error and refuses to continue.

## Workflow

```
Login -> Workspace bootstrap (clone or pull) -> Dashboard ->
    {People, Projects, Events, Jobs} -> Publish
```

The bottom-right status bar shows two indicators:

- **Workspace sync**: relative time since the last successful
  `git pull` from `origin/main`. Clicking it (or hitting **F5**)
  forces an immediate sync. A background timer runs the pull every
  5 minutes; the timer is paused automatically while a publish is
  in flight so it cannot race the push.
- **NAU server**: green when the SMB share is reachable, red with a
  `?` button explaining what to do otherwise.

Each domain page lets you:

- Add an entry through a form matching the schema in
  [docs/DATA_MODEL.md](../docs/DATA_MODEL.md).
- Edit any existing entry (the form is pre-filled).
- Delete an entry (removes the JSON file and its manifest path).
- Reorder entries by drag-and-drop (rewrites the manifest array).

For People entries the app:

- Copies the chosen headshot into `Images/People/`.
- Auto-generates the two WebP variants
  (`Images/People/variants/card/<basename>.webp` and
  `Images/People/variants/team/<basename>.webp`) at the recommended
  sizes (360x420 q80 and 600x720 q82) using a center-crop.
- Bumps the hard-coded "Core Researchers" counter in `index.html`
  whenever you add or remove a Core Researcher.

After every successful save the app bumps `assetVersion` in
`JS/site-config.js` so visitors see the new content immediately.

### Publish to website

The Publish page does three things in order:

1. **Copy to the NAU share** (file-explorer drop). On failure (e.g.
   you're not on an NAU computer / you didn't mount the share yet)
   the app shows OS-specific instructions and a Retry button.
2. **Push to `origin/main`** - a real commit on `main` containing
   the working tree, fast-forwarded against any concurrent
   publishes. This is the commit that every other GUI user picks
   up on their next workspace sync.
3. **Snapshot to `origin/archive`** as a one-commit history of the
   publish. This is best-effort: if it fails, the publish is still
   considered successful because `main` (the source of truth) is
   already up to date.

`gui/`, `docs/`, `.git/`, `.vscode/`, `.venv/`, and the usual
build/cache leftovers are excluded from the SMB copy so only the
actual website files end up on the server. They are *not* excluded
from the git pushes (the GUI runs from inside the same repo it
edits, so removing them would break the workspace).

## Configuring the OAuth App Client ID

The recommended way is via the in-app **Setup** screen described
above - no code editing required.

Three resolution sources, checked in this order:

1. `RADIANT_GUI_GITHUB_CLIENT_ID` environment variable (highest
   priority - useful for developer overrides).
2. Value entered in the **Setup** screen (persisted via `QSettings`).
3. `GITHUB_OAUTH_CLIENT_ID_DEFAULT` in [`gui/config.py`](config.py)
   (empty by default - leave it empty in distributed builds so each
   user goes through the GUI Setup the first time).

### Creating the OAuth App on GitHub (once per organization)

If your team doesn't already have an OAuth App, create one:

1. Go to <https://github.com/settings/applications/new>.
2. **Application name:** Radiant Content GUI.
3. **Homepage URL:** any URL (e.g. the website's GitHub repo URL).
4. **Authorization callback URL:** any URL - Device Flow ignores it.
5. **Enable Device Flow** - this is the important checkbox.
6. Click **Register application**. Copy the resulting **Client ID**
   (under the app name on the next page). The Client ID is public-by-
   design - no client secret is needed.

## Troubleshooting

- **"You don't have access to elliottmkinsley/website-GUI-test"** -
  Ask the repo owner to add your GitHub account as a collaborator.
- **"Could not reach the NAU share"** - The dialog tells you how to
  mount it. You must be on an NAU computer or remote desktop.
- **"git pull failed: uncommitted local changes"** - Resolve any
  uncommitted edits in the repo manually, then relaunch the app.
- **"git push to main failed even after a retry"** - Another GUI
  user landed a publish in the brief window between your two push
  attempts. Close the Publish page, hit **F5** (or wait for the
  next background sync) to pull the new state, then republish.
- **Sync status shows "Sync failed - click to retry"** - The
  background pull hit a network or git error. Click the refresh
  button in the indicator to retry; hover for the full error
  message.

## Conventions and constraints honored

The app strictly preserves:

- The manifest pattern (no entry is "live" until its path is in
  `manifest.json`) - documented in [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
- The kebab-case filename convention for entry JSONs.
- The `Images/People/variants/card` and `Images/People/variants/team`
  WebP layout, with exact-case filenames matching the base headshot.
- The `assetVersion` cache buster in `JS/site-config.js`.

It deliberately does **not** touch CSS, JS source other than
`site-config.js`, or the HTML pages other than the single Core
Researchers metric counter in `index.html`. All other site edits stay
the responsibility of a developer.
