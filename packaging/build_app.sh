#!/usr/bin/env bash
# Freeze the Radiant Content GUI into dist/RadiantContentGUI.app on macOS.
#
# This is the macOS counterpart to packaging/build_app.ps1; both scripts
# share the same PyInstaller spec (packaging/radiant_content_gui.spec)
# so a clean local build on either OS strongly predicts CI will also
# succeed.
#
# Pipeline mirrors the Windows script:
#   1. Pick an interpreter. Prefers the project venv at .venv/bin/python
#      so local dev gets predictable dependencies, falls back to whatever
#      python3 is on PATH (which is what GitHub Actions provides).
#   2. Optionally runs pytest first. Skipped with --skip-tests so CI does
#      not run the test suite twice in the same workflow.
#   3. Cleans the previous build/ and dist/RadiantContentGUI* trees so
#      stale slices from a previous arch / version cannot poison the
#      bundle.
#   4. Invokes pyinstaller against packaging/radiant_content_gui.spec.
#   5. Verifies the expected .app bundle exists and prints its path.
#
# Usage:
#   bash packaging/build_app.sh             # full build with tests
#   bash packaging/build_app.sh --skip-tests
#   bash packaging/build_app.sh --python /opt/homebrew/bin/python3.13
#
# Output:
#   dist/RadiantContentGUI.app   - the application bundle
#   dist/RadiantContentGUI/      - the raw PyInstaller COLLECT folder
#                                  (an internal byproduct; the .app is
#                                  what end users see)

set -euo pipefail

# --- Parse args -----------------------------------------------------------

SKIP_TESTS=0
PYTHON_EXE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-tests)
            SKIP_TESTS=1
            shift
            ;;
        --python)
            PYTHON_EXE="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            echo "[build] unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

# Resolve repo root regardless of where the script was invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# --- Resolve interpreter --------------------------------------------------

if [[ -z "${PYTHON_EXE}" ]]; then
    if [[ -x ".venv/bin/python" ]]; then
        PYTHON_EXE=".venv/bin/python"
    else
        PYTHON_EXE="python3"
    fi
fi

echo "[build] using Python at ${PYTHON_EXE}"
"${PYTHON_EXE}" --version

# --- Tests (optional) -----------------------------------------------------

if [[ "${SKIP_TESTS}" -eq 0 ]]; then
    echo "[build] running pytest ..."
    # Headless Qt - mirrors the workflow's offscreen env so behaviour
    # matches between local and CI runs.
    QT_QPA_PLATFORM=offscreen "${PYTHON_EXE}" -m pytest tests/
fi

# --- Clean previous output ------------------------------------------------

# Remove both the .app bundle and the raw COLLECT folder so a stale
# slice from a previous arch (e.g. an arm64-only test build before
# switching to universal2) cannot leak into this build.
for path in build dist/RadiantContentGUI dist/RadiantContentGUI.app; do
    if [[ -e "${path}" ]]; then
        echo "[build] removing ${path}"
        rm -rf "${path}"
    fi
done

# --- Run PyInstaller ------------------------------------------------------

SPEC="packaging/radiant_content_gui.spec"
echo "[build] freezing with ${SPEC}"
"${PYTHON_EXE}" -m PyInstaller "${SPEC}" --noconfirm --clean --log-level WARN

# --- Verify artifact ------------------------------------------------------

APP_PATH="dist/RadiantContentGUI.app"
BINARY="${APP_PATH}/Contents/MacOS/RadiantContentGUI"

if [[ ! -d "${APP_PATH}" ]]; then
    echo "[build] ERROR: expected .app bundle not found at ${APP_PATH}" >&2
    exit 1
fi
if [[ ! -x "${BINARY}" ]]; then
    echo "[build] ERROR: launcher missing or not executable: ${BINARY}" >&2
    exit 1
fi

# Report the slice list so a developer can spot accidentally non-
# universal binaries before pushing a tag. ``lipo -archs`` exits 1
# on a non-Mach-O file, so the ``|| true`` swallow keeps the script
# usable when run from a Linux CI smoke check (which never happens
# today but is cheap insurance).
echo ""
echo "[build] SUCCESS"
echo "[build] app   : ${APP_PATH}"
SIZE_BYTES="$(stat -f%z "${BINARY}" 2>/dev/null || stat -c%s "${BINARY}" 2>/dev/null || echo unknown)"
echo "[build] launcher size: ${SIZE_BYTES} bytes"
ARCHS="$(lipo -archs "${BINARY}" 2>/dev/null || echo "(unknown)")"
echo "[build] launcher archs: ${ARCHS}"
echo ""
echo "[build] Tip: run the selftest to verify hidden imports:"
echo "    ${BINARY} --selftest"
