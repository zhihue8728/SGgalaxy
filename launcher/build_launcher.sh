#!/bin/bash
# Build SGLauncher.exe / SGPublish.exe / SGRelay.exe with mono's mcs (Linux / Claude's workspace), same output as
# build_launcher.bat (csc).  launcher.res = the app.manifest (asInvoker + supported OS) and go.ico (the planet horizon,
# user 11-02 17:47) as Win32 resources: i686-w64-mingw32-windres -O res -i launcher.rc -o launcher.res
#   apt-get install -y mono-mcs mono-devel   (once)
set -e
cd "$(dirname "$0")"
R="-r:System.Web.Extensions.dll -r:System.Numerics.dll"
mcs -nologo -langversion:5 -platform:x86 -target:winexe -win32res:launcher.res -out:SGLauncher.exe $R \
    -r:System.Windows.Forms.dll -r:System.Drawing.dll Ota.cs SGLauncher.cs
mcs -nologo -langversion:5 -target:exe -out:SGPublish.exe $R Ota.cs SGPublish.cs
mcs -nologo -langversion:5 -target:winexe -win32res:launcher.res -out:SGRelay.exe SGRelay.cs
echo "built SGLauncher.exe, SGPublish.exe and SGRelay.exe"
