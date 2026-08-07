<#
.SYNOPSIS
    Builds ScannerCanoScan.exe and, optionally, code-signs it.

.DESCRIPTION
    Runs the headless checks, builds the one-file executable with PyInstaller,
    then signs it with one of three methods (see the parameters below).

    Signing removes the "Unknown publisher" SmartScreen warning and shows
    "Host Service srl" instead. It needs a certificate; there is no way around
    that. Self-signed certificates do NOT work for SmartScreen.

.PARAMETER TrustedSigningMetadata
    Path to the Azure Trusted Signing metadata .json. Cheapest option for a
    registered company (~10 USD/month), no hardware token, works in CI.
    Needs the Trusted Signing dlib: install with
        Install-Module -Name TrustedSigning -Scope CurrentUser

.PARAMETER PfxPath
    Path to a .pfx certificate file (use with -PfxPassword).

.PARAMETER CertSubject
    Subject name of a certificate already in the Windows certificate store,
    e.g. "Host Service srl". This is how OV/EV hardware tokens are used.

.EXAMPLE
    .\build.ps1
    .\build.ps1 -CertSubject "Host Service srl"
    .\build.ps1 -TrustedSigningMetadata .\trusted-signing.json
#>
[CmdletBinding()]
param(
    [string]$TrustedSigningMetadata,
    [string]$PfxPath,
    [string]$PfxPassword,
    [string]$CertSubject,
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$exe = Join-Path $PSScriptRoot "dist\ScannerCanoScan.exe"

function Find-SignTool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "$env:ProgramFiles\Windows Kits\10\bin")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $found = Get-ChildItem -Path $root -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue |
                 Where-Object { $_.FullName -match "x64" } |
                 Sort-Object FullName -Descending |
                 Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

# ---------------------------------------------------------------- tests
if (-not $SkipTests) {
    Write-Host "== Headless checks ==" -ForegroundColor Cyan
    python tools\selftest.py
    if ($LASTEXITCODE -ne 0) { throw "selftest.py failed" }
    python tools\smoketest.py
    if ($LASTEXITCODE -ne 0) { throw "smoketest.py failed" }
}

# ---------------------------------------------------------------- build
Write-Host "== Building ==" -ForegroundColor Cyan
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
python -m PyInstaller --noconfirm ScannerCanoScan.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
if (-not (Test-Path $exe)) { throw "Executable not produced: $exe" }
$sizeMb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "Built $exe ($sizeMb MB)" -ForegroundColor Green

# ---------------------------------------------------------------- sign
$signing = $TrustedSigningMetadata -or $PfxPath -or $CertSubject
if (-not $signing) {
    Write-Host ""
    Write-Host "Not signed. SmartScreen will show 'Unknown publisher'." -ForegroundColor Yellow
    Write-Host "To sign, re-run with -CertSubject, -PfxPath or -TrustedSigningMetadata." -ForegroundColor Yellow
    exit 0
}

$signtool = Find-SignTool
if (-not $signtool) { throw "signtool.exe not found. Install the Windows 10/11 SDK (Signing Tools)." }
Write-Host "== Signing ==" -ForegroundColor Cyan
Write-Host "signtool: $signtool"

$signArgs = @("sign", "/fd", "SHA256", "/tr", $TimestampUrl, "/td", "SHA256", "/v")
if ($TrustedSigningMetadata) {
    $dlib = Get-ChildItem -Path "$env:USERPROFILE\Documents\WindowsPowerShell\Modules\TrustedSigning",
                                "$env:ProgramFiles\WindowsPowerShell\Modules\TrustedSigning" `
                          -Filter "Azure.CodeSigning.Dlib.dll" -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
    if (-not $dlib) { throw "Trusted Signing dlib not found. Run: Install-Module -Name TrustedSigning -Scope CurrentUser" }
    $signArgs += @("/dlib", $dlib.FullName, "/dmdf", (Resolve-Path $TrustedSigningMetadata).Path)
}
elseif ($PfxPath) {
    $signArgs += @("/f", (Resolve-Path $PfxPath).Path)
    if ($PfxPassword) { $signArgs += @("/p", $PfxPassword) }
}
else {
    $signArgs += @("/n", $CertSubject, "/a")
}
$signArgs += $exe

& $signtool @signArgs
if ($LASTEXITCODE -ne 0) { throw "Signing failed" }

& $signtool verify /pa /v $exe
if ($LASTEXITCODE -ne 0) { throw "Signature verification failed" }
Write-Host "Signed and verified: $exe" -ForegroundColor Green
