#!/bin/sh
# Build SGRender.dll (game hooks, widescreen, own DirectDraw, presenters, HUD overlay) and the ddraw.dll proxy.
# Needs mingw-w64 (i686).  Both DLLs go to the player's game folder via OTA (deploy/ota_files.json).
set -e
cd "$(dirname "$0")"
i686-w64-mingw32-gcc -O2 -Wall -Wno-misleading-indentation -shared -static-libgcc -s -o SGRender.dll \
    sgrender.c sgdraw.c sgwindow.c sgd3d9.c sghud.c -Wl,--kill-at -lgdi32 -luuid -lmsimg32 -lwininet -lm
i686-w64-mingw32-gcc -O2 -shared -static-libgcc -s -o ddraw.dll ddraw_proxy.c ddraw_proxy.def -lwsock32 -ladvapi32
ls -la SGRender.dll ddraw.dll
