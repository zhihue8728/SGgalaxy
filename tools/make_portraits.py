"""Render the missing organic unit portraits (<id>.jpg 276x344 for tc.dat, <id>s.jpg 80x100 for tc2.dat) from the
unit's st.xpf sprite (row 0 / frame 0), since the original dats have no portrait jpg for organic units."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xpf, xpf_probe as X
from PIL import Image, ImageFilter
GD = os.path.expanduser('~/mnt/Shattered Galaxy/')
UNITS = ['g011', 'g015', 'g024', 'g025', 'a006', 'a010', 'a017', 'g051', 'g059']   # + Quorg, Wight (2026-10-22)
def get(n):
    for dat in ('tc.dat', 'tc2.dat', 'NTF2.dat', 'tc3.dat'):
        p = GD + dat
        if os.path.exists(p):
            b = X.load(p, n)
            if b: return b
def background(w, h):
    bg = Image.new('RGB', (w, h))
    px = bg.load()
    for y in range(h):
        for x in range(w):
            d = ((x - w / 2) ** 2 / (w / 2) ** 2 + (y - h * 0.55) ** 2 / (h / 2) ** 2) ** 0.5
            v = max(0, int(46 - 40 * min(d, 1.1)))
            px[x, y] = (v // 2, v // 2 + 2, v + 6)
    return bg
def portrait(uid, w, h):
    b = get(uid + 'st.xpf')
    im = xpf.frame(b, 0)
    bb = im.getchannel('A').getbbox()
    im = im.crop(bb)
    s = min(w * 0.86 / im.width, h * 0.72 / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    bg = background(w, h).convert('RGBA')
    bg.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2 + int(h * 0.04)))
    return bg.convert('RGB')
def jpg_bytes(img):
    o = io.BytesIO(); img.save(o, 'JPEG', quality=88); return o.getvalue()
if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_scratch', 'portraits')
    os.makedirs(out, exist_ok=True)
    sheet = Image.new('RGB', (276 * 4, 344 * 2))
    for i, u in enumerate(UNITS):
        big = portrait(u, 276, 344); big.save(os.path.join(out, u + '.jpg'), quality=88)
        portrait(u, 80, 100).save(os.path.join(out, u + 's.jpg'), quality=88)
        sheet.paste(big, ((i % 4) * 276, (i // 4) * 344))
    sheet.save(os.path.join(out, 'sheet.png'))
