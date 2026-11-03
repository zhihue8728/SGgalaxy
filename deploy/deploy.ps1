# SGalaxy one-click deploy: local Windows PC -> Tencent Cloud server (Ubuntu 24.04)
# Usage (from the repo folder):  deploy\deploy.bat                  = upload the code and restart the server
#                                 deploy\deploy.bat -Account SG001    = create a GM account on the server (asks the password)
#                                 deploy\deploy.bat -Countdown 5     = players get a 5-minute in-game countdown, then restart
#                                 deploy\deploy.bat -Password SG001  = change an account's password (asks it, max 8 chars)
#                                 deploy\deploy.bat -Setup           = only without a cloud key pair: install an SSH key
# Client updates for the players: deploy\publish.bat (claude/OTA_PLAN.md).
# Player data on the server (accounts, world, NPCs, regiments, GM list, backups, logs) is NEVER overwritten.
param([switch]$Setup, [string]$Account = "", [double]$Countdown = 0, [string]$Password = "")
$ErrorActionPreference = "Stop"

# ---- settings -------------------------------------------------------------------------------------------------
$HostIP = "43.135.15.91"     # server public IP
$User   = "ubuntu"           # Lighthouse Ubuntu images log in as ubuntu (sudo without password)
$Port   = 3000               # game port (open TCP 3000 in the Lighthouse console firewall)
$UpdatePort = 3001           # launcher downloads (open TCP 3001 too)
$Key    = "$HOME\.ssh\game.pem"   # key pair bound to the server in the Tencent Cloud console
# ---------------------------------------------------------------------------------------------------------------

$Repo = Split-Path -Parent $PSScriptRoot
$Target = "$User@$HostIP"
$SshOpt = @("-o", "StrictHostKeyChecking=accept-new")
if (Test-Path $Key) {
    # Windows OpenSSH refuses a private key other users can read ("UNPROTECTED PRIVATE KEY FILE")
    icacls $Key /inheritance:r /grant:r "${env:USERNAME}:(R)" | Out-Null
    $SshOpt += @("-i", $Key)
}

if ($Setup) {
    if (-not (Test-Path $Key)) { ssh-keygen -t ed25519 -N '""' -f $Key | Out-Null }
    $pub = Get-Content "$Key.pub"
    Write-Host "Installing the SSH key on $Target (enter the server password once)..."
    ssh -o StrictHostKeyChecking=accept-new $Target "mkdir -p ~/.ssh && chmod 700 ~/.ssh && grep -qxF '$pub' ~/.ssh/authorized_keys 2>/dev/null || echo '$pub' >> ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys"
    Write-Host "Done. Now run deploy\deploy.bat without -Setup."
    exit 0
}

if ($Password) {
    # new password typed here; only its salted hash is stored on the server.  The login box takes max 8 characters.
    $sec = Read-Host "New password for $Password (max 8 characters)" -AsSecureString
    $pw = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    if ($pw.Length -lt 1 -or $pw.Length -gt 8) { Write-Host "The password must be 1-8 characters." -ForegroundColor Red; exit 1 }
    $pw64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pw))
    ssh -n @SshOpt $Target "cd /opt/sgserver && sudo -u sg python3 tools/acct.py setpw $Password `"`$(echo $pw64 | base64 -d)`""
    exit $LASTEXITCODE
}

if ($Account) {
    # the password is typed here and only its salted hash is stored on the server (never in a file or the repo)
    $sec = Read-Host "Password for $Account" -AsSecureString
    $pw = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    $pw64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pw))
    ssh -n @SshOpt $Target "cd /opt/sgserver && sudo -u sg python3 tools/acct.py create $Account `"`$(echo $pw64 | base64 -d)`" --gm"
    exit $LASTEXITCODE
}

# 0. the keys (2026-11-02, encrypted connection + encrypted game.db): from %USERPROFILE%\.sgota, NEVER in the repo.
#    net_key.json = the connection key (tools\sgnet.py keygen; its public half is built into ddraw.dll)
#    db_key       = the game.db key (made here the first time).  The server keeps its copies in /opt/sgserver/.netkey and
#    .dbkey; remote.sh never replaces a different key there (the database would become unreadable).
$KeyDir = "$HOME\.sgota"
$NetKey = "$KeyDir\net_key.json"
$DbKey  = "$KeyDir\db_key"
if (-not (Test-Path $NetKey)) {
    Write-Host "Missing $NetKey (the connection key: python tools\sgnet.py keygen, then rebuild ddraw.dll)." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $DbKey)) {
    $b = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    Set-Content -Path $DbKey -Value (($b | ForEach-Object { $_.ToString("x2") }) -join "") -NoNewline -Encoding ascii
    Write-Host "New database key: $DbKey  -- BACK UP the folder $KeyDir (without it game.db cannot be read)." -ForegroundColor Yellow
}

# 1. package: code + static data only (runtime data stays on the server)
$Stage = Join-Path $env:TEMP "sgdeploy"
Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "$Stage\server", "$Stage\tools", "$Stage\deploy" | Out-Null
$Runtime = @("accounts.json", "world.json", "npcs.json", "regiments.json", "board.json", "gm_accounts.json", "restart_request.json")
Get-ChildItem "$Repo\server" -File | Where-Object {
    ($_.Extension -in ".py", ".json", ".tsv", ".txt") -and ($_.Name -notin $Runtime) -and ($_.Name -notmatch "\.(bak|before_)")
} | Copy-Item -Destination "$Stage\server"
New-Item -ItemType Directory -Force "$Stage\server\sgs" | Out-Null      # server parts (sgserver.py loads them)
Copy-Item "$Repo\server\sgs\*.py" "$Stage\server\sgs\"
Copy-Item "$Repo\tools\sgproto.py", "$Repo\tools\sgnet.py", "$Repo\tools\acct.py" "$Stage\tools\"
Copy-Item "$Repo\SG_debug.exe" "$Stage\"                      # the server checks the client checksum against it
Copy-Item "$PSScriptRoot\remote.sh", "$PSScriptRoot\sgserver.service" "$Stage\deploy\"
$Tar = Join-Path $env:TEMP "sgdeploy.tgz"
Remove-Item $Tar -ErrorAction SilentlyContinue
tar -czf $Tar -C $Stage .
Write-Host ("Package: {0:N1} MB" -f ((Get-Item $Tar).Length / 1MB))

# 2. upload + install + restart (the keys go separately into a folder only the login user can read)
ssh -n @SshOpt $Target "rm -rf /tmp/sgkeys && mkdir -m 700 /tmp/sgkeys"
scp @SshOpt $NetKey $DbKey "${Target}:/tmp/sgkeys/"
if ($LASTEXITCODE -ne 0) { Write-Host "KEY UPLOAD FAILED" -ForegroundColor Red; exit 1 }
scp @SshOpt $Tar "${Target}:/tmp/sgdeploy.tgz"
ssh -n @SshOpt $Target "rm -rf /tmp/sgdeploy && mkdir -p /tmp/sgdeploy && tar -xzf /tmp/sgdeploy.tgz -C /tmp/sgdeploy && sed -i 's/\r$//' /tmp/sgdeploy/deploy/remote.sh && sudo bash /tmp/sgdeploy/deploy/remote.sh $HostIP $Port $([int]($Countdown * 60)) $UpdatePort"
if ($LASTEXITCODE -ne 0) { Write-Host "DEPLOY FAILED" -ForegroundColor Red; exit 1 }
Write-Host "Deployed to ${HostIP}:$Port" -ForegroundColor Green
