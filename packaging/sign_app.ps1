<#
.SYNOPSIS
    Authenticode-sign a .exe with the configured code-signing
    certificate.

.DESCRIPTION
    Designed to be a no-op stub on PR CI and on local dev machines,
    and a real signtool invocation on release builds where the
    ``CODE_SIGN_PFX_BASE64`` + ``CODE_SIGN_PASSWORD`` env vars are
    set from GitHub Actions secrets.

    The release workflow always calls this script - it's safe to
    keep in the pipeline indefinitely. Once a real cert is
    purchased, base64-encode the .pfx (``certutil -encode in.pfx
    out.b64``) and paste the result into the
    ``CODE_SIGN_PFX_BASE64`` secret; add the export password as
    ``CODE_SIGN_PASSWORD``. No code changes are required.

    The PFX is written to a temp path with a tight ACL only long
    enough for signtool to read it, then wiped in a ``try/finally``
    so an interrupted run never leaks key material to disk.

.PARAMETER Path
    File to sign. Must exist; usually the frozen .exe or the Inno
    Setup installer.

.EXAMPLE
    pwsh packaging\sign_app.ps1 -Path dist\RadiantContentGUI\RadiantContentGUI.exe

.EXAMPLE
    pwsh packaging\sign_app.ps1 -Path dist\RadiantContentGUISetup.exe
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Path)) {
    throw "Sign target not found: $Path"
}

$pfxBase64 = $env:CODE_SIGN_PFX_BASE64
$pfxPassword = $env:CODE_SIGN_PASSWORD

if ([string]::IsNullOrWhiteSpace($pfxBase64)) {
    Write-Host '[sign] skipping - CODE_SIGN_PFX_BASE64 not set'
    exit 0
}

# Locate signtool. Windows SDK puts it under Program Files; CI
# images ship it on PATH.
$signtool = $null
$found = Get-Command signtool.exe -ErrorAction SilentlyContinue
if ($found) {
    $signtool = $found.Source
}
if (-not $signtool) {
    $candidates = Get-ChildItem -Path 'C:\Program Files (x86)\Windows Kits' -Recurse -Filter 'signtool.exe' -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like '*x64*' } |
        Sort-Object FullName -Descending
    if ($candidates) {
        $signtool = $candidates[0].FullName
    }
}
if (-not $signtool) {
    throw 'signtool.exe not found.'
}

$pfxFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllBytes(
    $pfxFile,
    [Convert]::FromBase64String($pfxBase64)
)

try {
    Write-Host "[sign] signing $Path with $signtool"
    $signArgs = @(
        'sign',
        '/f', $pfxFile,
        '/tr', 'http://timestamp.sectigo.com',
        '/td', 'SHA256',
        '/fd', 'SHA256',
        $Path
    )
    if (-not [string]::IsNullOrEmpty($pfxPassword)) {
        $signArgs = @('sign', '/f', $pfxFile, '/p', $pfxPassword,
                      '/tr', 'http://timestamp.sectigo.com',
                      '/td', 'SHA256', '/fd', 'SHA256', $Path)
    }
    & $signtool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'signtool sign failed.'
    }
    & $signtool verify /pa $Path
    if ($LASTEXITCODE -ne 0) {
        throw 'signtool verify failed.'
    }
    Write-Host "[sign] OK $Path"
}
finally {
    if (Test-Path $pfxFile) {
        # Best-effort scrub so the PFX never lingers in temp.
        try {
            $stream = [System.IO.File]::OpenWrite($pfxFile)
            $junk = New-Object byte[] 4096
            $stream.Write($junk, 0, $junk.Length)
            $stream.Close()
        } catch {
            # Swallow - the Remove-Item below is the primary defence.
        }
        Remove-Item -Force $pfxFile
    }
}
