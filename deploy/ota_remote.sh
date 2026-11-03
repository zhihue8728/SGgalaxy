#!/bin/bash
# Runs ON the server (called by publish.ps1 with sudo).  install STAGE_DIR | rollback VERSION | status
set -e
U=${OTA_DIR:-/opt/sgserver/updates}
mkdir -p "$U/objects" "$U/versions" "$U/launcher"
case "$1" in
install)
  S="$2"
  # 1. new objects (content-addressed: the name must be the sha256 of the content)
  for f in "$S"/objects/*; do
    [ -f "$f" ] || continue
    n=$(basename "$f")
    [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$n" ] || { echo "corrupt upload: $n"; exit 1; }
    [ -f "$U/objects/$n" ] || mv "$f" "$U/objects/$n"
  done
  # 2. every object a new manifest needs must be on the server before the manifest goes live
  missing=0
  for m in "$S"/manifest-*.json; do
    for h in $(python3 -c "import json,sys; m=json.load(open(sys.argv[1])); print(' '.join([f['sha256'] for f in m['files']]+[m['launcher']['sha256']]))" "$m"); do
      [ -f "$U/objects/$h" ] || { echo "missing object $h ($(basename "$m"))"; missing=1; }
    done
  done
  [ $missing = 0 ] || { echo "-> run publish again with -Full"; exit 2; }
  cp -r "$S/versions/." "$U/versions/"
  cp "$S/launcher/GOLauncher.exe" "$U/launcher/GOLauncher.exe.tmp" && mv "$U/launcher/GOLauncher.exe.tmp" "$U/launcher/GOLauncher.exe"
  # 3. manifests (+ signatures), then release.json last: the game server announces the release when it changes
  for f in "$S"/manifest-*; do cp "$f" "$U/.tmp" && mv "$U/.tmp" "$U/$(basename "$f")"; done
  cp "$S/release.json" "$U/.tmp" && mv "$U/.tmp" "$U/release.json"
  ;;
rollback)
  V="$2"
  [ -d "$U/versions/$V" ] || { echo "no published version $V: $(ls "$U/versions")"; exit 1; }
  for f in "$U/versions/$V"/manifest-*; do cp "$f" "$U/.tmp" && mv "$U/.tmp" "$U/$(basename "$f")"; done
  cp "$U/versions/$V/release.json" "$U/.tmp" && mv "$U/.tmp" "$U/release.json"
  echo "current release is now $V"
  ;;
status)
  echo "current: $(cat "$U/release.json" 2>/dev/null)"
  echo "versions: $(ls "$U/versions" | tr '\n' ' ')"
  echo "objects: $(ls "$U/objects" | wc -l) files, $(du -sh "$U/objects" | cut -f1)"
  ;;
esac
id sg >/dev/null 2>&1 && chown -R sg:sg "$U"; true
