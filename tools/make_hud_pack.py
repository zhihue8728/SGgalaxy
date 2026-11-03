#!/usr/bin/env python3
"""Build SGHud.pak, the new HUD's art pack (user 2026-11-01 09:05), read by SGRender.dll (sghud_draw.h, hud_pack_get).
Packs client/sgrender/art/SGHud-*.png / .jpg and client/sgrender/fonts/SGHud-*.ttf, stored as they are (already compressed).
Format: "SGHP", u32 version 1, u32 count, count x { char name[48] NUL padded; u32 offset; u32 size; }, then the files,
each 4-byte aligned, sorted by name (the same input gives the same bytes, so the OTA delta stays small).
Run it after any change to the HUD art, before publish.  The pack goes to the players as SGHud.pak (deploy/ota_files.json).
usage: python tools/make_hud_pack.py [--check]   (from the repo root; --check only verifies the pack is up to date)"""
import os, struct, sys, glob

SRC = ['client/sgrender/art/SGHud-*.png', 'client/sgrender/art/SGHud-*.jpg', 'client/sgrender/fonts/SGHud-*.ttf']
OUT = 'client/sgrender/SGHud.pak'

def build():
    files = sorted({p for g in SRC for p in glob.glob(g)}, key=lambda p: os.path.basename(p).lower())
    names = [os.path.basename(p) for p in files]
    if len(set(n.lower() for n in names)) != len(names): sys.exit('duplicate names: %s' % names)
    for n in names:
        if len(n.encode('ascii')) > 47: sys.exit('name too long (max 47): ' + n)
    pos = 12 + 56 * len(files); table = b''; body = b''
    for p, n in zip(files, names):
        d = open(p, 'rb').read()
        pad = (-(pos + len(body))) % 4; body += b'\0' * pad
        table += n.encode('ascii').ljust(48, b'\0') + struct.pack('<II', pos + len(body), len(d))
        body += d
    return b'SGHP' + struct.pack('<II', 1, len(files)) + table + body, names

def main():
    data, names = build()
    if '--check' in sys.argv:
        ok = os.path.exists(OUT) and open(OUT, 'rb').read() == data
        print(OUT, 'up to date' if ok else 'OUT OF DATE - run python tools/make_hud_pack.py'); sys.exit(0 if ok else 1)
    open(OUT, 'wb').write(data)
    print('%s: %d files, %d bytes' % (OUT, len(names), len(data)))
    for n in names: print('  ' + n)

if __name__ == '__main__':
    main()
