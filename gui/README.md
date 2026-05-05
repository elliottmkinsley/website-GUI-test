# Radiant Content GUI

A desktop app for editors of the Radiant Center for Remote Sensing
website. It provides forms for adding, editing, deleting, and
reordering the four data domains the site renders from JSON
(`People/`, `Projects/`, `Events/`, `Jobs/`), then publishes the
resulting working tree to the NAU SMB share at
`\\arashres.ucc.nau.edu\Web\radiant.nau.edu` and snapshots the change
to a dedicated `archive` branch on GitHub.

The app is intentionally bundled inside the website repo so it always
operates on the same files the live site renders from.

## Requirements

- Python 3.11 or newer
- Git installed and on `PATH`
- A GitHub account with push access to the gating repo
  (`elliottmkinsley/website-GUI-test`)
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

## Run

```bash
python -m gui
```

On first launch the app shows a GitHub login screen using OAuth Device
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
Login -> Dashboard -> {People, Projects, Events, Jobs} -> Publish
```

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

The Publish page does two things in order:

1. **Copy to the NAU share** (file-explorer drop). On failure (e.g.
   you're not on an NAU computer / you didn't mount the share yet)
   the app shows OS-specific instructions and a Retry button.
2. **Snapshot to GitHub** by committing the current working tree to
   the `archive` branch and pushing to `origin`.

`gui/`, `docs/`, `.git/`, `.vscode/`, `.venv/`, and the usual
build/cache leftovers are excluded from the SMB copy so only the
actual website files end up on the server.

## Setup the OAuth App (project owner only)

This step happens once per project, not per user.

1. Go to <https://github.com/settings/applications/new>.
2. Name the app something like "Radiant Content GUI".
3. Homepage URL: anything (e.g. `https://radiant.nau.edu`).
4. Authorization callback URL: anything - Device Flow does not use it.
5. **Enable Device Flow**.
6. Save. Copy the resulting **Client ID**.
7. Paste it as `GITHUB_OAUTH_CLIENT_ID` in [`gui/config.py`](config.py)
   and commit. (No secret is needed for Device Flow public clients.)

For local testing without committing the change, set the env var:

```bash
export RADIANT_GUI_GITHUB_CLIENT_ID=Iv1.your_client_id_here
```

## Troubleshooting

- **"You don't have access to elliottmkinsley/website-GUI-test"** -
  Ask the repo owner to add your GitHub account as a collaborator.
- **"Could not reach the NAU share"** - The dialog tells you how to
  mount it. You must be on an NAU computer or remote desktop.
- **"git pull failed: uncommitted local changes"** - Resolve any
  uncommitted edits in the repo manually, then relaunch the app.

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
