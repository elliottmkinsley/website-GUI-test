<#
.SYNOPSIS
    Build a Windows installer (RadiantContentGUISetup.exe) from the
    frozen PyInstaller bundle.

.DESCRIPTION
    Wraps Inno Setup's compiler (``iscc.exe``) so local maintainers
    and CI run the same single command. The default is the "online"
    single-exe installer (``/DSingleFile=1``); a future offline build
    would omit ``-SkipVendor`` and ship the multi-disk variant.

    Sequence:

      1. Resolve ``AppVersion`` from ``gui/__version__.py`` if not
         explicitly passed.
      2. Unless ``-SkipAppBuild`` is set, run ``build_app.ps1`` so
         the frozen bundle exists before iscc tries to read from it.
      3. Locate ``iscc.exe`` (PATH first, then the Inno Setup 6
         default install path).
      4. Invoke iscc with ``/DAppVersion=`` and ``/DSingleFile=1``.
      5. Verify ``dist\RadiantContentGUISetup*.exe`` exists and
         print its path + SHA-256 hash.

.PARAMETER AppVersion
    Override the version. CI passes this from the git tag.

.PARAMETER SkipAppBuild
    Do not run ``build_app.ps1`` first. CI uses this because the
    frozen bundle was already produced in an earlier step.

.PARAMETER SkipVendor
    Future-proofing for offline installer payloads. Present for
    parity with the playbook; currently a no-op other than confirming
    the build is the online variant.

.PARAMETER IsccPath
    Explicit path to ``iscc.exe`` if the autodetection fails.

.EXAMPLE
    pwsh packaging\build_installer.ps1 -SkipVendor

.EXAMPLE
    pwsh packaging\build_installer.ps1 -SkipAppBuild -SkipVendor -AppVersion 1.0.0
#>

[CmdletBinding()]
param(
    [string]$AppVersion,
    [switch]$SkipAppBuild,
    [switch]$SkipVendor,
    [string]$IsccPath
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

# --- Resolve AppVersion ---------------------------------------------------

if (-not $AppVersion) {
    $versionPy = Join-Path $repoRoot 'gui\__version__.py'
    if (-not (Test-Path $versionPy)) {
        throw "$versionPy not found; pass -AppVersion explicitly."
    }
    $match = Select-String -Path $versionPy -Pattern '__version__\s*:\s*str\s*=\s*"([^"]+)"' -List
    if (-not $match) {
        $match = Select-String -Path $versionPy -Pattern '__version__\s*=\s*"([^"]+)"' -List
    }
    if (-not $match) {
        throw "Could not parse __version__ from $versionPy."
    }
    $AppVersion = $match.Matches[0].Groups[1].Value
    Write-Host "[installer] derived AppVersion=$AppVersion from $versionPy"
}

# Normalise: strip leading v if the caller passed a tag name.
$AppVersion = $AppVersion.TrimStart('v', 'V')

# --- Optional app build ---------------------------------------------------

if (-not $SkipAppBuild) {
    Write-Host '[installer] running build_app.ps1 ...'
    $buildAppScript = Join-Path $repoRoot 'packaging\build_app.ps1'
    & $buildAppScript -SkipTests
    if ($LASTEXITCODE -ne 0) {
        throw 'build_app.ps1 failed.'
    }
}

$bundleDir = Join-Path $repoRoot 'dist\RadiantContentGUI'
$bundleExe = Join-Path $bundleDir 'RadiantContentGUI.exe'
if (-not (Test-Path $bundleExe)) {
    throw "Frozen bundle not found at $bundleExe. Run packaging\build_app.ps1 first or omit -SkipAppBuild."
}

# --- Locate iscc.exe ------------------------------------------------------

if (-not $IsccPath) {
    $candidate = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($candidate) {
        $IsccPath = $candidate.Source
    } else {
        $fallback = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
        if (Test-Path $fallback) {
            $IsccPath = $fallback
        }
    }
}

if (-not $IsccPath -or -not (Test-Path $IsccPath)) {
    throw 'iscc.exe not found. Install Inno Setup 6 or pass -IsccPath.'
}

Write-Host "[installer] using iscc at $IsccPath"

# --- Invoke iscc ----------------------------------------------------------

$iss = Join-Path $repoRoot 'packaging\installer.iss'
$iscArgs = @(
    "/DAppVersion=$AppVersion"
)

if ($SkipVendor) {
    # Online installer: emit a single .exe rather than spanning into
    # .bin slices (see packaging/installer.iss preamble and playbook
    # gotcha #2).
    $iscArgs += '/DSingleFile=1'
}

Write-Host "[installer] iscc $($iscArgs -join ' ') $iss"
& $IsccPath @iscArgs $iss
if ($LASTEXITCODE -ne 0) {
    throw 'iscc.exe failed.'
}

# --- Verify artifact ------------------------------------------------------

$outputs = Get-ChildItem -Path (Join-Path $repoRoot 'dist') -Filter 'RadiantContentGUISetup*.exe' -ErrorAction SilentlyContinue
if (-not $outputs) {
    throw 'No RadiantContentGUISetup*.exe was produced.'
}

foreach ($file in $outputs) {
    $sha = (Get-FileHash -Algorithm SHA256 $file.FullName).Hash
    $sizeMb = [Math]::Round($file.Length / 1MB, 2)
    Write-Host ''
    Write-Host "[installer] SUCCESS"
    Write-Host "[installer] file  : $($file.FullName)"
    Write-Host "[installer] size  : $sizeMb MB"
    Write-Host "[installer] sha256: $sha"
}
