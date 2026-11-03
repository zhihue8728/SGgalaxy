"""Write frames back into a Shattered Galaxy .xpf (the inverse of tools/xpf.py frame()).
A frame = u8 top_skip, u8 bottom_skip, then per row between them: repeat {u8 skip; u8 count; count x u16 RGB565} until
the row is covered (a trailing transparent run is written as a lone skip).  Runs are split at 255.
replace_frames(xpf_bytes, {index: RGBA image (w x h of the file)}) -> new xpf bytes (other frames kept byte for byte)."""
import struct
from PIL import Image
import xpf
def enc_frame(im, w, h):
    im = im.convert('RGBA')
    if im.size != (w, h):
        c = Image.new('RGBA', (w, h), (0, 0, 0, 0)); c.paste(im, (0, 0)); im = c
    px = im.load()
    op = lambda x, y: px[x, y][3] >= 128
    rows = [y for y in range(h) if any(op(x, y) for x in range(w))]
    if not rows: return b'\0\0'
    top, bot = rows[0], h - 1 - rows[-1]
    out = bytearray([top, bot])
    for y in range(top, h - bot):
        x = 0
        while x < w:
            s = 0
            while x + s < w and not op(x + s, y) and s < 255: s += 1
            if x + s >= w: out += bytes([s]); x += s; break
            if s == 255 and not op(x + s, y): out += bytes([255, 0]); x += 255; continue
            n = 0
            while x + s + n < w and op(x + s + n, y) and n < 255: n += 1
            out += bytes([s, n])
            for k in range(n):
                r, g, b, a = px[x + s + k, y]
                out += struct.pack('<H', ((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | ((b * 31 + 127) // 255))
            x += s + n
    return bytes(out)
def replace_frames(b, frames):
    """the offset table holds rows*24+1 u32 but only the leading increasing ones are real (portraits: 3 = 2 frames);
    the bytes between the header and frame 0 are kept, only the real offsets are rewritten."""
    i = xpf.info(b); w, h = i['w'], i['h']
    offs = list(xpf.offsets(b))
    m = 1
    while m < len(offs) and offs[m - 1] <= offs[m] <= len(b): m += 1
    real = offs[:m]                                   # m offsets = m-1 frames
    base = real[0]
    datas = [b[real[k]:real[k + 1]] for k in range(m - 1)]
    end_extra = b[real[-1]:]
    for k, im in frames.items(): datas[k] = enc_frame(im, w, h)
    new = []; p = base
    for dta in datas: new.append(p); p += len(dta)
    new.append(p)
    hdr = bytearray(b[:base])
    struct.pack_into('<%dI' % m, hdr, 14, *new)
    return bytes(hdr) + b''.join(datas) + end_extra
