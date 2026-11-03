"""GO ICON (user 2026-11-02 17:47 "安装文件的图示是否能改成刚刚的地平线背景"): a square crop around the planet horizon
of the login background D (client/sgrender/art/SGHud-login.jpg).  Writes
  launcher/go.ico          16-256 px (PNG entries): GOLauncher.exe / GORelay.exe (launcher.res), the installer (nsi)
  deploy/go_icon32.png     32 x 32: the game exe's own icons (tools/set_exe_icon.py patches them in place)
Small sizes are brighter and sharper (the thin horizon line would vanish).
usage: python tools/make_go_icon.py"""
import io, os, struct, sys
from PIL import Image, ImageEnhance, ImageFilter
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
bg = Image.open(os.path.join(REPO, "client", "sgrender", "art", "SGHud-login.jpg")).convert('RGB')
W, H = bg.size; cx = int(0.6 * W)
src = bg.crop((cx - 200, H - 400, cx + 200, H))
def at(s):
    im = ImageEnhance.Brightness(src).enhance(1.25 if s > 48 else 1.55)
    if s <= 48: im = ImageEnhance.Contrast(im).enhance(1.35)
    im = im.resize((s, s), Image.LANCZOS)
    if s <= 48: im = im.filter(ImageFilter.UnsharpMask(1, 120, 2))
    return im
sizes = [16, 24, 32, 48, 64, 128, 256]
ents, datas = [], []
for s in sizes:
    b = io.BytesIO(); at(s).convert('RGBA').save(b, 'PNG'); datas.append(b.getvalue())
off = 6 + 16 * len(sizes); hdr = struct.pack('<HHH', 0, 1, len(sizes))
for s, d in zip(sizes, datas):
    hdr += struct.pack('<BBBBHHII', s % 256, s % 256, 0, 0, 1, 32, len(d), off); off += len(d)
open(os.path.join(REPO, "launcher", "go.ico"), 'wb').write(hdr + b''.join(datas))
at(32).save(os.path.join(REPO, "deploy", "go_icon32.png"))            # the 32x32 picture for the exe's own icons (24-bit, patched in place)
