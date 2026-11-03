# One-shot, re-runnable setup: Node 24 + JDK 21 + Ghidra 12.1.x + rea (main). No admin. Keeps your Java 8.
# Run:  powershell -ExecutionPolicy Bypass -File setup-rea.ps1
# Optional proxy first:  $env:HTTPS_PROXY="http://127.0.0.1:7890"
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$T = 'C:\tools'
$Work = "$env:USERPROFILE\Documents\GitHub"
New-Item -ItemType Directory -Force -Path $T, $Work | Out-Null
function Step($m) { Write-Host "`n=== $m ===" -ForegroundColor Cyan }

# Download with curl.exe: retries + resume, tries each URL in order.
function Get-File($urls, $out) {
  foreach ($u in $urls) {
    Write-Host "Downloading $u"
    & curl.exe -L --fail --retry 5 --retry-delay 3 --connect-timeout 20 -C - -o $out $u
    if ($LASTEXITCODE -eq 0 -and (Test-Path $out) -and (Get-Item $out).Length -gt 1MB) { return }
    Write-Host "  failed, trying next source..." -ForegroundColor Yellow
  }
  throw "All download sources failed for $out"
}
# Read a directory listing (HTML or JSON) and return the first matching file name.
function Find-Name($listUrls, $regex) {
  foreach ($u in $listUrls) {
    try {
      $c = (Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 30).Content
      $m = [regex]::Matches($c, $regex) | ForEach-Object { $_.Value } | Sort-Object -Unique
      if ($m) { return @{ Base = $u; Name = ($m | Select-Object -Last 1) } }
    } catch { Write-Host "  list failed: $u" -ForegroundColor Yellow }
  }
  return $null
}

Step 'Check git'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git not found. Install Git for Windows: https://git-scm.com/download/win' }
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) { throw 'curl.exe missing (needs Windows 10 1803+)' }

# ---- Node 24
Step 'Node 24'
$nodeDir = "$T\node"
$ok = (Test-Path "$nodeDir\node.exe") -and ((& "$nodeDir\node.exe" -v) -match '^v24\.(1[1-9]|[2-9]\d)')
if (-not $ok) {
  $hit = Find-Name @('https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt','https://npmmirror.com/mirrors/node/latest-v24.x/SHASUMS256.txt','https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/latest-v24.x/SHASUMS256.txt') 'node-v24[\d\.]+-win-x64\.zip'
  if (-not $hit) { throw 'Cannot find Node 24 zip' }
  $name = $hit.Name
  $zip = "$T\$name"
  Get-File @("https://nodejs.org/dist/latest-v24.x/$name","https://npmmirror.com/mirrors/node/latest-v24.x/$name","https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/latest-v24.x/$name") $zip
  if (Test-Path $nodeDir) { Remove-Item $nodeDir -Recurse -Force }
  Expand-Archive $zip -DestinationPath $T -Force
  Rename-Item "$T\$($name -replace '\.zip$','')" $nodeDir
  Remove-Item $zip
}
$env:Path = "$nodeDir;$env:Path"
node -v

# ---- JDK 21
Step 'JDK 21'
$jdkDir = "$T\jdk-21"
if (-not (Test-Path "$jdkDir\bin\javac.exe")) {
  $zip = "$T\jdk21.zip"
  $tuna = 'https://mirrors.tuna.tsinghua.edu.cn/Adoptium/21/jdk/x64/windows/'
  $hit = Find-Name @($tuna,'https://mirrors.ustc.edu.cn/adoptium/releases/temurin21-binaries/') 'OpenJDK21U-jdk_x64_windows_hotspot_[\d\._+]+\.zip'
  $urls = @()
  if ($hit -and $hit.Base -eq $tuna) { $urls += ($tuna + $hit.Name) }
  $urls += 'https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jdk/hotspot/normal/eclipse'
  $urls += 'https://github.com/adoptium/temurin21-binaries/releases/latest/download/OpenJDK21U-jdk_x64_windows_hotspot.zip'
  Get-File $urls $zip
  $tmp = "$T\jdk-tmp"; if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
  Expand-Archive $zip -DestinationPath $tmp -Force
  $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
  if (Test-Path $jdkDir) { Remove-Item $jdkDir -Recurse -Force }
  Move-Item $inner.FullName $jdkDir
  Remove-Item $tmp -Recurse -Force; Remove-Item $zip
}
& "$jdkDir\bin\java.exe" -version

# ---- Ghidra
Step 'Ghidra'
$ghDir = Get-ChildItem $T -Directory -Filter 'ghidra_12.1*_PUBLIC' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $ghDir) {
  $zip = Get-ChildItem $T -File -Filter 'ghidra_12.1*_PUBLIC_*.zip' -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $zip) {
    # find the asset URL using curl.exe (more tolerant than .NET web cmdlets)
    $url = $null
    $tmpJ = "$T\gh-releases.json"
    & curl.exe -sSL --retry 3 --connect-timeout 20 -H 'User-Agent: setup-rea' -o $tmpJ 'https://api.github.com/repos/NationalSecurityAgency/ghidra/releases?per_page=30'
    if (Test-Path $tmpJ) {
      $m = [regex]::Matches((Get-Content $tmpJ -Raw), 'https://github\.com/NationalSecurityAgency/ghidra/releases/download/[^"]+/ghidra_12\.1\.\d+_PUBLIC_\d+\.zip')
      if ($m.Count) { $url = $m[0].Value }
    }
    if (-not $url) {
      foreach ($v in '12.1.4','12.1.3','12.1.2','12.1.1','12.1') {
        & curl.exe -sSL --retry 2 --connect-timeout 20 -o $tmpJ "https://github.com/NationalSecurityAgency/ghidra/releases/expanded_assets/Ghidra_$($v)_build"
        if (Test-Path $tmpJ) {
          $m = [regex]::Match((Get-Content $tmpJ -Raw), '/NationalSecurityAgency/ghidra/releases/download/[^"]+/ghidra_12\.1[\.\d]*_PUBLIC_\d+\.zip')
          if ($m.Success) { $url = 'https://github.com' + $m.Value; break }
        }
      }
    }
    if (-not $url) {
      Write-Host "`nCannot reach GitHub from this shell." -ForegroundColor Red
      Write-Host 'Manual fix: in your browser download ghidra_12.1.x_PUBLIC_*.zip from' -ForegroundColor Yellow
      Write-Host 'https://github.com/NationalSecurityAgency/ghidra/releases , put the zip in C:\tools , then re-run this script.' -ForegroundColor Yellow
      throw 'Ghidra download unavailable'
    }
    Write-Host "Found $url"
    $zipPath = Join-Path $T ($url.Split("/")[-1])
    Get-File @($url, ("https://ghfast.top/" + $url)) $zipPath
    $zip = Get-Item $zipPath
  }
  Expand-Archive $zip.FullName -DestinationPath $T -Force
  Remove-Item $zip.FullName
  $ghDir = Get-ChildItem $T -Directory -Filter 'ghidra_12.1*_PUBLIC' | Select-Object -First 1
}
$ghidra = $ghDir.FullName
Write-Host $ghidra

# ---- Env vars
Step 'Environment variables'
[Environment]::SetEnvironmentVariable('GHIDRA_INSTALL_DIR', $ghidra, 'User')
[Environment]::SetEnvironmentVariable('REA_ANALYSIS_PROVIDER', 'ghidra', 'User')
[Environment]::SetEnvironmentVariable('REA_GHIDRA_STARTUP_TIMEOUT_MS', '600000', 'User')
$env:GHIDRA_INSTALL_DIR = $ghidra; $env:REA_ANALYSIS_PROVIDER = 'ghidra'; $env:REA_GHIDRA_STARTUP_TIMEOUT_MS = '600000'
$env:JAVA_HOME = $jdkDir; $env:Path = "$jdkDir\bin;$env:Path"

# ---- rea
Step 'Clone and build rea'
$reaDir = "$Work\rea"
if (-not (Test-Path "$reaDir\.git")) { git clone https://github.com/morluto/rea $reaDir } else { git -C $reaDir pull --ff-only }
Set-Location $reaDir
$helper = "$reaDir\rea-env.ps1"
@"
`$env:Path = 'C:\tools\node;C:\tools\jdk-21\bin;' + `$env:Path
`$env:JAVA_HOME = 'C:\tools\jdk-21'
`$env:GHIDRA_INSTALL_DIR = '$ghidra'
`$env:REA_ANALYSIS_PROVIDER = 'ghidra'
`$env:REA_GHIDRA_STARTUP_TIMEOUT_MS = '600000'
Set-Location '$reaDir'
"@ | Set-Content $helper -Encoding ASCII

# use npm mirror if npmjs is unreachable
try { Invoke-WebRequest 'https://registry.npmjs.org/' -UseBasicParsing -TimeoutSec 15 | Out-Null }
catch { Write-Host 'npmjs unreachable, using npmmirror' -ForegroundColor Yellow; $env:npm_config_registry = 'https://registry.npmmirror.com' }
npm ci
npm run build

Step 'rea doctor'
npx rea doctor --json
Write-Host "`nDone. New shell: . `"$helper`"  then: npx rea ..." -ForegroundColor Green
