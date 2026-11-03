#!/bin/sh
# Real client in wine, playing a battle recording (2026-11-03, HD units step 1; the old ck.sh / snap.sh were lost).
# Needs: wine (32-bit), Xvfb, xdotool, imagemagick, python3 (cryptography), mingw-w64 i686 for the test DLLs.
#   GAME=<extracted installer folder, e.g. 7z x GalacticOverlord_Setup_1.0.95.exe>   (the release asset "testdata")
#   REC=<a .rcd recording>
# What it does:
#   1. a TEST connection key (~/.sgota/net_key.json, made once) and test ddraw.dll + SGRender.dll built with its public
#      half in /tmp/sgtb (the repo's sgnet_pub.h and DLLs are not touched); copied into $GAME (also as GORender.dll);
#   2. F58 etc. applied to $GAME/GO_debug.exe (tools/patch_sg_debug_f58.py), copied to $SRV/../SG_debug.exe so the
#      server's anti-cheat allows its checksum;
#   3. a scratch server ($SRV, fresh game.db with a TEST database key) on 127.0.0.1:3000;
#   4. wine with the game's own ddraw.dll (ddraw=n,b: it decrypts the .dat files), REG_SG_IP = 127.0.0.1;
#   5. menu -> BRIEFING ROOM -> the first recording -> PLAY; screenshots shot_*.png in $GAME.
# GORender.ini in $GAME is left as you write it (e.g. [display] hd_debug=1, hd_codes=a008).
set -e
REPO=$(cd "$(dirname "$0")/.." && pwd)
: "${GAME:?set GAME}" "${REC:?set REC}"
SRV=${SRV:-/tmp/sgsrv/srv}; TB=/tmp/sgtb
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine-sg} WINEARCH=win32 WINEDEBUG=-all DISPLAY=${DISPLAY:-:99} WINEDLLOVERRIDES="ddraw=n,b"

# 1. test key + DLLs
[ -f "$HOME/.sgota/net_key.json" ] || python3 "$REPO/tools/sgnet.py" keygen
rm -rf "$TB"; mkdir -p "$TB/tools" "$TB/client"
cp "$REPO/tools/sgnet.py" "$TB/tools/"; cp -r "$REPO/client/sgrender" "$TB/client/"
python3 "$TB/tools/sgnet.py" header >/dev/null
(cd "$TB/client/sgrender" && sh build.sh >/dev/null)
cp "$TB/client/sgrender/ddraw.dll" "$GAME/"; cp "$TB/client/sgrender/SGRender.dll" "$GAME/"; cp "$TB/client/sgrender/SGRender.dll" "$GAME/GORender.dll"

# 2. client patches + allowed checksum
for p in "$REPO"/tools/patch_sg_debug_f58.py; do python3 "$p" "$GAME/GO_debug.exe"; done
mkdir -p "$SRV"; rm -rf "$SRV"; cp -r "$REPO/server" "$SRV"; cp "$REPO/tools/sgnet.py" "$REPO/tools/sgproto.py" "$SRV/"
cp "$GAME/GO_debug.exe" "$SRV/../SG_debug.exe"

# 3. server
[ -f "$SRV/../test.dbkey" ] || python3 -c "import os;print(os.urandom(32).hex())" > "$SRV/../test.dbkey"
rm -f "$SRV"/game.db*
(cd "$SRV" && SG_DBKEY_FILE="$SRV/../test.dbkey" nohup python3 sgserver.py --host 127.0.0.1 --public-ip 127.0.0.1 >out.txt 2>&1 &)

# 4. wine
pgrep -x Xvfb >/dev/null || (Xvfb "$DISPLAY" -screen 0 1280x800x24 >/dev/null 2>&1 &)
sleep 2; wineboot -i >/dev/null 2>&1 || true
wine reg add "HKCU\\SOFTWARE\\Galactic Overlord" /v REG_SG_IP /t REG_SZ /d 127.0.0.1 /f >/dev/null 2>&1
mkdir -p "$GAME/Record"; cp "$REC" "$GAME/Record/"
sleep 8                                                    # server warm-up
(cd "$GAME" && wine GO_debug.exe >wine.out 2>&1 &)
sleep 18; import -window root "$GAME/shot_menu.png"

# 5. briefing room -> play (coordinates for a 1280x800 screen, windowed game)
xdotool mousemove 216 447 click 1; sleep 3
xdotool mousemove 760 219 click 1; sleep 1
xdotool mousemove 746 578 click 1; sleep 25
import -window root "$GAME/shot_replay.png"
echo "playing; log: $GAME/GORender.log, server: $SRV/sgserver.log; stop: wineserver -k"
