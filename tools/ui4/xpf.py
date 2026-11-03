"""Shattered Galaxy .xpf sprite decoder (reverse engineered from SG.exe FUN_005f2540 loader + FUN_005eebe0 blitter).
Header (14 bytes, LE): u16 type, u16 w, u16 h, u16 cx, u16 cy, u8 x3 (flags), u8 rows.  Then u32 offsets (rows*24+1
of them, +4 bytes), then frames.  A frame = u8 top_skip, u8 bottom_skip, then for each row between them:
repeat { u8 skip; if x+skip<w: u8 count, count x u16 RGB565 pixels; x += skip+count } while x < w.
Frames of 2 bytes or less are empty.  Returns RGBA images (PIL)."""
import struct
from PIL import Image
COLS = 24
def info(b):
    t, w, h, cx, cy = struct.unpack('<5H', b[:10]); rows = b[13]
    return dict(type=t, w=w, h=h, cx=cx, cy=cy, rows=rows, flags=b[10:13])
def offsets(b):
    rows = b[13]; o0 = struct.unpack_from('<I', b, 14)[0]
    n = rows * COLS + 1
    if 14 + 4 * n > o0: n = rows + 1          # single-direction sprites (UI): one offset per frame
    return struct.unpack('<%dI' % n, b[14:14 + 4 * n])
def frame(b, idx):
    i = info(b); w, h = i['w'], i['h']; offs = offsets(b)
    f = b[offs[idx]:]
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); px = im.load()
    if len(f) < 3: return im
    top, bot = f[0], f[1]; p = 2
    for y in range(top, h - bot):
        x = 0
        while x < w and p < len(f):
            x += f[p]; p += 1
            if x >= w: break
            n = f[p]; p += 1
            for k in range(n):
                v = f[p] | (f[p + 1] << 8); p += 2
                if x + k < w:
                    px[x + k, y] = (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255)
            x += n
    return im
