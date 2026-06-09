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
| Operating system | Windows 10 22H2 or newer, or Windows 11. macOS / Linux installers are not yet available. |
| Disk space | ~400 MB (installer + bundled runtime + your local website checkout). |
| Network | Required for sign-in and for publishing. The app keeps working offline once your workspace is cloned, but Publish is disabled. |
| NAU access | Publishing to the website requires being on an NAU-domain computer (campus workstation, NAU-issued laptop on the campus network, or RDP into an NAU machine). The bottom-right status indicator turns green when the NAU file share is reachable. |
| GitHub account | You need push access to `elliottmkinsley/website-GUI-test`. Ask an administrator to add you if you do not already have it. |

---

## 1. Download the installer

1. Go to https://github.com/elliottmkinsley/website-GUI-test/releases/latest
2. Under **Assets**, click `RadiantContentGUISetup.exe` to download it.
3. (Optional) Verify the download. Each release page lists the
   installer's **SHA-256** hash. On Windows you can verify with:

   ```powershell
   Get-FileHash -Algorithm SHA256 .\RadiantContentGUISetup.exe
   ```

   The output should match the hash in the release notes.

---

## 2. Dismiss the SmartScreen warning

The installer is currently **not code-signed**, so Microsoft
Defender SmartScreen will warn you when you double-click it:

> Windows protected your PC
> Microsoft Defender SmartScreen prevented an unrecognized app from
> starting. Running this app might put your PC at risk.

This is expected. To proceed:

1. Click **More info** in the warning dialog.
2. A **Run anyway** button appears below the publisher line. Click it.

Once enough downloads of a given version accumulate, SmartScreen
stops warning. A future release will be signed with a code-signing
certificate to remove the warning entirely.

---

## 3. Run the installer

1. Choose an install location when prompted, or accept the default
   (`%LOCALAPPDATA%\Programs\RadiantContentGUI` for per-user
   installs).
2. Check **Create a desktop shortcut** if you want one.
3. Click **Install**, then **Finish**.

The installer runs a quick self-test before exiting. If anything
unexpected appears, please report it so we can fix the next
release.

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
instructions. Short version: use an NAU machine (library
workstation, NAU laptop on the campus network, or RDP/VPN into
one). If you are on NAU and still see the warning, contact NAU
ITS to grant your account access to
`\\arshares.ucc.nau.edu\Web\radiant.nau.edu`.

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

Use the Windows **Settings -> Apps -> Installed apps** list to
remove **Radiant Content GUI**. The uninstaller removes the
program files but **leaves your workspace folder in place** in
case you have local edits you have not yet pushed. If you also
want to remove the workspace, manually delete:

- Windows: `%APPDATA%\Radiant Center for Remote Sensing\Radiant Content GUI`
