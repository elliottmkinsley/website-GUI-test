# Installing the Radiant Content GUI

The Radiant Content GUI is the desktop application Radiant editors
use to add, edit, reorder, and publish website content (People,
Projects, Events, Jobs) without touching JSON or HTML by hand.

Releases are published on the GitHub Releases page:

> https://github.com/elliottmkinsley/website-GUI-test/releases/latest

---

## System requirements

| Component | Requirement |
| --- | --- |
| Operating system | **Windows 10 22H2 or newer, or Windows 11** (64-bit). **macOS 11 (Big Sur) or newer** on Apple Silicon (M1/M2/M3/M4) or Intel - the macOS download is a single universal binary that runs natively on both. Linux installers are not yet available. |
| Disk space | ~400 MB (installer + bundled runtime + your local website checkout). |
| Network | Required for sign-in and for publishing. The app keeps working offline once your workspace is cloned, but Publish is disabled. |
| NAU access | Publishing to the website requires being on an NAU-domain computer (campus workstation, NAU-issued laptop on the campus network, or RDP into an NAU machine). The bottom-right status indicator turns green when the NAU file share is reachable. |
| GitHub account | You need push access to `elliottmkinsley/website-GUI-test`. Ask an administrator to add you if you do not already have it. |

---

## 1. Download the installer

1. Go to https://github.com/elliottmkinsley/website-GUI-test/releases/latest
2. Under **Assets**, click the download for your operating system:
   - **Windows:** `RadiantContentGUISetup.exe`
   - **macOS:** `RadiantContentGUI-<version>.dmg` (works on Apple
     Silicon *and* Intel - one universal download for every Mac).
3. (Optional) Verify the download. Each release page lists the
   download's **SHA-256** hash:

   ```powershell
   # Windows
   Get-FileHash -Algorithm SHA256 .\RadiantContentGUISetup.exe
   ```

   ```bash
   # macOS
   shasum -a 256 ~/Downloads/RadiantContentGUI-*.dmg
   ```

   The output should match the hash in the release notes.

---

## 2. First-launch security warnings

The app is currently **not code-signed**, so both Windows and
macOS show a one-time warning the first time you launch it. This
is expected and harmless; signing certificates are on the roadmap.

### Windows: SmartScreen

When you double-click the installer, Microsoft Defender SmartScreen
warns:

> Windows protected your PC
> Microsoft Defender SmartScreen prevented an unrecognized app from
> starting. Running this app might put your PC at risk.

To proceed:

1. Click **More info** in the warning dialog.
2. A **Run anyway** button appears below the publisher line. Click it.

Once enough downloads of a given version accumulate, SmartScreen
stops warning.

### macOS: Gatekeeper

The first time you double-click `RadiantContentGUI.app`, macOS
warns:

> "RadiantContentGUI.app" cannot be opened because the developer
> cannot be verified.

To proceed (you only do this **once** per install):

1. Click **Cancel** on the warning dialog.
2. In Finder, **right-click** (or Control-click) the app and choose
   **Open** from the context menu.
3. macOS now shows a slightly different dialog with an **Open**
   button. Click it.

After this one-time approval, the app launches normally from
Spotlight, the Dock, or Launchpad with no further warnings.

If you instead see *"...is damaged and can't be opened. You should
move it to the Trash"*, that usually means macOS quarantined the
download. Open Terminal and run:

```bash
xattr -dr com.apple.quarantine /Applications/RadiantContentGUI.app
```

Then retry the right-click -> Open dance above.

---

## 3. Install

### Windows

1. Choose an install location when prompted, or accept the default
   (`%LOCALAPPDATA%\Programs\RadiantContentGUI` for per-user
   installs).
2. Check **Create a desktop shortcut** if you want one.
3. Click **Install**, then **Finish**.

The installer runs a quick self-test before exiting.

### macOS

1. Double-click the downloaded `RadiantContentGUI-<version>.dmg`.
2. A window opens with the app icon on the left and an
   `Applications` shortcut on the right.
3. **Drag** `RadiantContentGUI.app` onto the `Applications`
   shortcut.
4. Wait a few seconds for the copy to finish, then **eject** the
   disk image (Cmd+E in Finder, or right-click the mounted volume
   in the sidebar and pick *Eject*).
5. Launch from Spotlight (Cmd+Space, type "Radiant") or from
   Launchpad. The first launch needs the right-click -> Open dance
   from step 2 above.

---

## 4. First launch

The first time you start the GUI it will walk you through three
quick steps:

1. **GitHub OAuth Client ID setup.** Paste the Client ID you were
   given (or follow the on-screen instructions to create your own
   OAuth App on GitHub). You only do this once - it's stored in
   the OS user-settings store.

2. **Sign in with GitHub.** The app shows a one-time device code
   and opens your browser to `https://github.com/login/device`.
   Paste the code, authorize the app, and wait a moment.

3. **Workspace download.** The app clones `elliottmkinsley/website-GUI-test`
   into your user-data folder so it has the website's current files
   to edit:

   - Windows: `%APPDATA%\Radiant Center for Remote Sensing\Radiant Content GUI\workspace`
   - macOS:   `~/Library/Application Support/Radiant Center for Remote Sensing/Radiant Content GUI/workspace`

   The first clone takes 30 seconds to a few minutes depending on
   your connection. On subsequent launches the app does a fast
   `git pull` instead - usually under a second.

After the workspace is ready you land on the dashboard with tiles
for People, Projects, Events, Jobs, and Publish.

---

## 5. Publishing

When you're ready to push your changes live:

1. Make sure the bottom-right indicator says **NAU server active**
   (green). If it shows red, see the troubleshooting section below.
2. Click **Publish** on the dashboard.
3. The app runs three steps and reports success for each:
   - **Step 1:** copies the website tree to the NAU file share
     (the live website files).
   - **Step 2:** commits and pushes the same content to the `main`
     branch of `elliottmkinsley/website-GUI-test`. This is what
     other GUI users see on their next workspace sync.
   - **Step 3:** also pushes a snapshot commit to the `archive`
     branch as a history record.

### Seeing changes from other editors

The app pulls the latest `main` from GitHub automatically:

- Once on every launch (the **Setting up your local workspace**
  page you saw on first launch).
- Quietly in the background every 5 minutes while the app is open.
- Immediately after any publish you do yourself.

The bottom-right corner shows a sync indicator with text like
**Workspace synced 3m ago**. Click the refresh button (or press
**F5** / pick **Help > Sync workspace now**) to pull immediately.

---

## Troubleshooting

**"NAU server unreachable" indicator (red)**
You are not on an NAU-domain computer, or the NAU file share is
not mounted. Click the `?` next to the indicator for full
instructions. Short version:

- **Windows:** use an NAU machine (library workstation, NAU laptop
  on the campus network, or RDP/VPN into one).
- **macOS:** in Finder choose **Go > Connect to Server** (Cmd+K),
  enter `smb://arshares.ucc.nau.edu/Web/radiant.nau.edu`, sign in
  with your NAU credentials, then click **Retry** in the GUI. The
  share mounts at `/Volumes/radiant.nau.edu`.

If you are on NAU and still see the warning, contact NAU ITS to
grant your account access to `\\arshares.ucc.nau.edu\Web\radiant.nau.edu`.

**Sign-in says "Access denied: you do not have push access"**
Your GitHub account is not on the access list for the website
repository. Ask the project administrator to add you.

**Workspace clone fails with "git clone failed"**
Verify your network can reach `github.com` and that the access
token saved in your sign-in is current. **Sign Out** from the
File menu and sign in again to refresh the token.

**Checking for updates**
Choose **Help > Check for updates...** to open the latest GitHub
Release page in your browser. Compare the version shown there to
the one in **Help > About**.

---

## Uninstalling

### Windows

Use **Settings -> Apps -> Installed apps** to remove **Radiant
Content GUI**. The uninstaller removes the program files but
**leaves your workspace folder in place** in case you have local
edits you have not yet pushed. To remove the workspace too,
manually delete `%APPDATA%\Radiant Center for Remote Sensing\Radiant Content GUI`.

### macOS

Drag `RadiantContentGUI.app` from **Applications** to the Trash.
This also leaves your workspace in place. To remove the workspace
too, delete `~/Library/Application Support/Radiant Center for Remote Sensing/Radiant Content GUI`
(reveal in Finder via **Go > Go to Folder** / Shift+Cmd+G).
