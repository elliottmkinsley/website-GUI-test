<#
.SYNOPSIS
    Freeze the Radiant Content GUI into ``dist/RadiantContentGUI/RadiantContentGUI.exe``.

.DESCRIPTION
    Thin wrapper around ``pyinstaller``. Used by both the maintainer's
    local "make me an installer" workflow and by the CI release job.
    Both paths share this script so a green local build means CI will
    almost certainly also build cleanly.

    The script:

      1. Picks an interpreter. Prefers the project's own venv at
         ``.venv\Scripts\python.exe`` (so local dev gets predictable
         dependencies) and falls back to whatever ``python`` is on
         PATH (which is what CI provides).
      2. Optionally runs ``pytest`` first. Skipped with ``-SkipTests``
         (CI passes this because tests already ran in a separate
         job on the PR).
      3. Cleans the previous ``build/`` and ``dist/RadiantContentGUI/``
         trees so stale files cannot poison the bundle.
      4. Invokes ``pyinstaller`` against
         ``packaging/radiant_content_gui.spec``.
      5. Verifies the expected ``.exe`` exists and prints its path.

.PARAMETER SkipTests
    Skip ``pytest``. CI sets this; local maintainers usually do not.

.PARAMETER PythonExe
    Override the interpreter used. Defaults to the project venv if
    present, else ``python``.

.EXAMPLE
    pwsh packaging\build_app.ps1

.EXAMPLE
    pwsh packaging\build_app.ps1 -SkipTests
#>

[CmdletBinding()]
param(
    [switch]$SkipTests,
    [string]$PythonExe
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

# --- Resolve interpreter --------------------------------------------------

if (-not $PythonExe) {
    $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPython) {
        $PythonExe = $venvPython
    } else {
        $PythonExe = 'python'
    }
}

Write-Host "[build] using Python at $PythonExe"
& $PythonExe --version
if ($LASTEXITCODE -ne 0) {
    throw "Could not invoke $PythonExe."
}

# --- Tests (optional) -----------------------------------------------------

if (-not $SkipTests) {
    Write-Host '[build] running pytest ...'
    & $PythonExe -m pytest tests/
    if ($LASTEXITCODE -ne 0) {
        throw 'pytest failed; aborting build.'
    }
}

# --- Clean previous output -------------------------------------------------

$buildDir = Join-Path $repoRoot 'build'
$distDir = Join-Path $repoRoot 'dist\RadiantContentGUI'

if (Test-Path $buildDir) {
    Write-Host "[build] removing $buildDir"
    Remove-Item -Recurse -Force $buildDir
}
if (Test-Path $distDir) {
    Write-Host "[build] removing $distDir"
    Remove-Item -Recurse -Force $distDir
}

# --- Run PyInstaller ------------------------------------------------------

$spec = Join-Path $repoRoot 'packaging\radiant_content_gui.spec'
Write-Host "[build] freezing with $spec"
& $PythonExe -m PyInstaller $spec --noconfirm --clean --log-level WARN
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller failed.'
}

# --- Verify artifact ------------------------------------------------------

$exePath = Join-Path $distDir 'RadiantContentGUI.exe'
if (-not (Test-Path $exePath)) {
    throw "Expected exe not found at $exePath"
}

$size = (Get-Item $exePath).Length
Write-Host ''
Write-Host "[build] SUCCESS"
Write-Host "[build] exe   : $exePath"
Write-Host ("[build] size  : {0:N0} bytes" -f $size)
Write-Host "[build] bundle: $distDir"
Write-Host ''
Write-Host '[build] Tip: run the selftest to verify hidden imports:'
Write-Host "    & '$exePath' --selftest"
