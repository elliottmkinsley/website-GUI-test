#!/usr/bin/env bash
# Wrap dist/RadiantContentGUI.app into a downloadable .dmg disk image.
#
# Why a DMG? It is the convention every Mac user already knows:
# double-click the download, a drag-to-Applications window opens,
# you drop the app in Applications, eject the disk image. Compared
# to a plain .zip the user does not have to manually copy the app
# into Applications, and compared to a .pkg installer there are no
# pre/post-install scripts to maintain.
#
# Tooling: this script uses `create-dmg` (Homebrew package) for the
# pretty drag-to-Applications layout. If create-dmg is unavailable
# it falls back to plain `hdiutil`, which still produces a valid
# DMG - just without the curated layout. CI installs create-dmg
# explicitly so the released DMG always uses the nice layout.
#
# Usage:
#   bash packaging/build_dmg.sh                  # picks version from gui/__version__.py
#   bash packaging/build_dmg.sh --version 0.3.0  # explicit version (CI passes this)
#
# Output:
#   dist/RadiantContentGUI-<VERSION>.dmg
#
# Pre-requisite: packaging/build_app.sh must have been run first so
# dist/RadiantContentGUI.app exists. This script does NOT rebuild the
# app on its own; the two-step split makes CI logs easier to read.

set -euo pipefail

# --- Parse args -----------------------------------------------------------

APP_VERSION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)
            APP_VERSION="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,28p' "$0"
            exit 0
            ;;
        *)
            echo "[dmg] unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

APP_PATH="dist/RadiantContentGUI.app"
if [[ ! -d "${APP_PATH}" ]]; then
    echo "[dmg] ERROR: ${APP_PATH} not found. Run packaging/build_app.sh first." >&2
    exit 1
fi

# --- Resolve version ------------------------------------------------------

if [[ -z "${APP_VERSION}" ]]; then
    # Read gui/__version__.py with a tiny inline Python invocation
    # so this script stays dependency-free and does not pin a
    # Python interpreter choice (which would conflict with the
    # build_app.sh --python override).
    APP_VERSION="$(python3 - <<'PY'
import re, pathlib
text = pathlib.Path("gui/__version__.py").read_text(encoding="utf-8")
m = re.search(r'__version__\s*[:=][^"\']*["\']([^"\']+)["\']', text)
print(m.group(1) if m else "0.0.0")
PY
)"
fi

echo "[dmg] packaging version: ${APP_VERSION}"

DMG_NAME="RadiantContentGUI-${APP_VERSION}.dmg"
DMG_PATH="dist/${DMG_NAME}"
VOLUME_NAME="Radiant Content GUI ${APP_VERSION}"

# Always remove a stale .dmg with the same name; hdiutil will
# otherwise fail with EEXIST and create-dmg refuses to overwrite.
if [[ -e "${DMG_PATH}" ]]; then
    echo "[dmg] removing stale ${DMG_PATH}"
    rm -f "${DMG_PATH}"
fi

# --- Build the DMG --------------------------------------------------------

if command -v create-dmg >/dev/null 2>&1; then
    echo "[dmg] building with create-dmg ..."
    # ``--window-size``, ``--icon-size``, ``--app-drop-link`` together
    # produce the standard drag-to-Applications window every Mac user
    # has seen a thousand times.
    # ``--no-internet-enable`` keeps macOS from quarantine-flagging
    # the volume itself (only the app inside it gets quarantined,
    # which is what we want).
    create-dmg \
        --volname "${VOLUME_NAME}" \
        --window-size 540 380 \
        --icon-size 110 \
        --icon "RadiantContentGUI.app" 140 180 \
        --app-drop-link 400 180 \
        --no-internet-enable \
        --hdiutil-quiet \
        "${DMG_PATH}" \
        "${APP_PATH}" \
        || {
            # create-dmg sometimes exits non-zero even when the .dmg
            # is produced (e.g. when ``--codesign`` is set and the
            # cert is absent). If the file is on disk we treat the
            # build as successful and continue.
            if [[ ! -f "${DMG_PATH}" ]]; then
                echo "[dmg] ERROR: create-dmg failed and no DMG was produced." >&2
                exit 1
            fi
            echo "[dmg] create-dmg returned non-zero but DMG was produced; continuing."
        }
else
    echo "[dmg] create-dmg not found; falling back to hdiutil (plain layout) ..."
    STAGING="$(mktemp -d)"
    trap 'rm -rf "${STAGING}"' EXIT
    cp -R "${APP_PATH}" "${STAGING}/"
    # Sym-link to /Applications so the user can drag-drop even with
    # the basic layout. hdiutil will preserve the alias inside the
    # produced disk image.
    ln -s /Applications "${STAGING}/Applications"
    hdiutil create \
        -volname "${VOLUME_NAME}" \
        -srcfolder "${STAGING}" \
        -ov \
        -format UDZO \
        "${DMG_PATH}"
fi

# --- Verify artifact ------------------------------------------------------

if [[ ! -f "${DMG_PATH}" ]]; then
    echo "[dmg] ERROR: expected ${DMG_PATH} was not produced." >&2
    exit 1
fi

DMG_SIZE_BYTES="$(stat -f%z "${DMG_PATH}" 2>/dev/null || stat -c%s "${DMG_PATH}" 2>/dev/null || echo unknown)"
echo ""
echo "[dmg] SUCCESS"
echo "[dmg] dmg  : ${DMG_PATH}"
echo "[dmg] size : ${DMG_SIZE_BYTES} bytes"
