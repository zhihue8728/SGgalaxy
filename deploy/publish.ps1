# SGalaxy client release (OTA): build a signed release from out\ and upload it; the players' SGLauncher installs it.
# (claude/OTA_PLAN.md)  Run from anywhere:
#   deploy\publish.bat -Keygen                                       first time only: create the signing key
#   deploy\publish.bat -Version 1.0.1 -Notes "修正地图编号"            new release (only changed files are uploaded)
#        [-NotesTw "..."] [-NotesEn "..."]                            notes per language (default: the -Notes text)
#        [-Min 1.0.0]                                                 versions below this cannot log in at once
#        [-DeadlineHours 48]                                          older versions cannot log in after 48 h
#        [-Full]                                                      upload every file again (new / wiped server)
#   deploy\publish.bat -Rollback 1.0.0                               make an older published release current again
#   deploy\publish.bat -Status                                       what the server has
# Build the client files first as usual (patch_sg_debug_fNN.py, build_i18n_exe.py, ...); this script only publishes
# what is in out\ (deploy\ota_files.json lists the files).  Server code changes: deploy\deploy.bat.
param([string]$Version = "", [string]$Notes = "", [string]$NotesTw = "", [string]$NotesEn = "", [string]$Min = "",
      [double]$DeadlineHours = 0, [string]$Rollback = "", [switch]$Keygen, [switch]$Full, [switch]$Force, [switch]$Status)
$ErrorActionPreference = "Stop"

# ---- settings (same server as deploy.ps1) ----------------------------------------------------------------------
$HostIP     = "43.135.15.91"
$User       = "ubuntu"
$UpdatePort = 3001                     # launcher downloads (open TCP 3001 in the Lighthouse firewall)
$Key        = "$HOME\.ssh\game.pem"
$Urls       = "http://${HostIP}:$UpdatePort"   # more mirrors: "http://a:3001,https://cdn.example.com/sg"
# ---------------------------------------------------------------------------------------------------------------

$Repo = Split-Path -Parent $PSScriptRoot
$Tool = Join-Path $Repo "launcher\SGPublish.exe"
$Target = "$User@$HostIP"
$SshOpt = @("-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=15", "-o", "ConnectTimeout=20")
if (Test-Path $Key) { icacls $Key /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null; $SshOpt += @("-i", $Key) }
function Remote([string]$cmd) {
    # -n: no console input (Windows ssh can otherwise wait for a key after the command finished)
    ssh -n @SshOpt $Target $cmd
    if ($LASTEXITCODE -ne 0) { throw "server command failed ($LASTEXITCODE)" }
}
function SendRemoteScript {
    Write-Host "[1/3] sending the install script..."
    scp @SshOpt "$PSScriptRoot\ota_remote.sh" "${Target}:/tmp/ota_remote.sh"
    if ($LASTEXITCODE -ne 0) { throw "upload failed" }
    Remote "sed -i 's/\r$//' /tmp/ota_remote.sh"
}

Push-Location $Repo
try {
    if ($Keygen) { & $Tool keygen; exit $LASTEXITCODE }
    if ($Status) { SendRemoteScript; Remote "sudo bash /tmp/ota_remote.sh status"; exit 0 }
    if ($Rollback) {
        SendRemoteScript
        Remote "sudo bash /tmp/ota_remote.sh rollback $Rollback"
        Write-Host "Rolled back to $Rollback (launchers install it at their next start)." -ForegroundColor Green
        exit 0
    }
    if (-not $Version) { throw "use -Version 1.0.1 -Notes `"...`"  (or -Keygen / -Rollback V / -Status)" }

    # 0. the HUD art pack must match client\sgrender\art (tools\make_hud_pack.py; skipped when python is missing)
    $Py = Get-Command python -ErrorAction SilentlyContinue
    if ($Py) {
        Push-Location $Repo
        try { & $Py.Source "tools\make_hud_pack.py" "--check" } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) { throw "SGHud.pak is out of date: run  python tools\make_hud_pack.py  first" }
    }

    # 0b. (2026-11-02) the .dat files and SGHud.pak are shipped ENCRYPTED: out\enc\... from deploy\encrypt_files.json
    #     (tools\sgcrypt_files.py; needs python + cryptography + numpy, installed here the first time)
    if (-not $Py) { throw "python is needed to encrypt the game files (tools\sgcrypt_files.py)" }
    foreach ($m in @("cryptography", "numpy")) {          # numpy: fast cutting into chunks (format 2)
        & $Py.Source -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$m') else 1)"
        if ($LASTEXITCODE -ne 0) { & $Py.Source -m pip install --user $m; if ($LASTEXITCODE -ne 0) { throw "pip install $m failed" } }
    }
    & $Py.Source "tools\sgcrypt_files.py"
    if ($LASTEXITCODE -ne 0) { throw "encrypting the game files failed (tools\sgcrypt_files.py)" }

    # 1. signed release in out\ota\stage (only objects the server does not have yet)
    $a = @("build", "--version", $Version, "--url", $Urls, "--server-ip", $HostIP, "--notes", $Notes)
    if ($NotesTw) { $a += @("--notes-tw", $NotesTw) }
    if ($NotesEn) { $a += @("--notes-en", $NotesEn) }
    if ($Min) { $a += @("--min", $Min) }
    if ($DeadlineHours -gt 0) { $a += @("--deadline-hours", "$DeadlineHours") }
    if ($Full) { $a += "--all" }
    if ($Force) { $a += "--force" }
    & $Tool @a
    if ($LASTEXITCODE -ne 0) { throw "build failed" }

    # 2. upload + install on the server (objects first, manifests and release.json last)
    $Tar = Join-Path $env:TEMP "sgota.tgz"
    Remove-Item $Tar -ErrorAction SilentlyContinue
    tar -czf $Tar -C "out\ota\stage" .
    Write-Host ("Upload: {0:N1} MB" -f ((Get-Item $Tar).Length / 1MB))
    SendRemoteScript
    Write-Host "[2/3] uploading the release (this takes a while the first time)..."
    scp @SshOpt $Tar "${Target}:/tmp/sgota.tgz"
    if ($LASTEXITCODE -ne 0) { throw "upload failed" }
    Write-Host "[3/3] installing on the server..."
    Remote "rm -rf /tmp/sgota && mkdir -p /tmp/sgota && tar -xzf /tmp/sgota.tgz -C /tmp/sgota && sudo bash /tmp/ota_remote.sh install /tmp/sgota && rm -rf /tmp/sgota /tmp/sgota.tgz"

    # 3. remember what the server has; the stamped launcher for new players
    Copy-Item "out\ota\stage\launcher\GOLauncher.exe" "out\ota\GOLauncher.exe" -Force
    & $Tool commit
    # zip for new players: the stamped launcher + simplified Chinese instructions (2026-10-27)
    $Zip = Join-Path $Repo "out\GOLauncher_$Version.zip"
    Remove-Item $Zip -ErrorAction SilentlyContinue
    Compress-Archive -Path "out\ota\GOLauncher.exe", "launcher\使用说明.txt" -DestinationPath $Zip
    Write-Host "New-player download: $Zip"
    Write-Host "Release $Version is live. Online players get a notice within 15 s." -ForegroundColor Green
    Write-Host "New players: give them the installer (python tools\make_installer.py) or out\ota\GOLauncher.exe (http://${HostIP}:$UpdatePort/launcher/GOLauncher.exe)."
} catch {
    Write-Host "PUBLISH FAILED: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
