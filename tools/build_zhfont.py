#!/usr/bin/env python3
"""Chinese text for the 1.8.5 client (2026-10-21).  The client's bitmap text renderer (004bfe10) only knows the
Korean NOG.fnt (2402 hangul glyphs, 12 x 12, 24 bytes = 12 rows x u16 big-endian, MSB = left).  The game data
also ships complete 12 px UNICODE fonts that the exe never uses (dns.dat NOGUNIT.FNT = Traditional Chinese glyph
forms, NOGUNI_.FNT = Simplified; header 32 bytes, 65535 x {u8 width, 18 bytes = 12 rows x 12 bits}).
This tool builds out/NOG.fnt = original bytes up to the glyph block end (0xd38 + 0xe130) + 65536 TC glyphs + 65536
SC glyphs (24-byte format) + the original tail (unused), and writes out/dns_zh.dat with it.  Client patch F18
(patch_sg_debug_f18.py) reads 0x30e130 glyph bytes instead of 0xe130 and maps DBCS text through
MultiByteToWideChar(GetACP()): code page 950 -> glyph 2402 + unicode (TC), 936 -> 2402 + 65536 + unicode (SC),
anything else -> the original Korean mapping.
usage: build_zhfont.py GAMEDIR"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, sgdat_add
GLYPH_OFF, GLYPH_LEN = 0xd38, 0xe130
def conv(uni):
    out = bytearray()
    for cp in range(65536):
        g = bytearray(24)
        if cp < 65535:
            rec = uni[32 + cp * 19 + 1: 32 + cp * 19 + 19]
            bits = int.from_bytes(rec, 'big')          # 144 bits, row r = bits 143-12r .. 132-12r
            for r in range(12):
                row = (bits >> (144 - 12 * (r + 1))) & 0xFFF
                struct.pack_into('>H', g, 2 * r, row << 4)
        out += g
    return bytes(out)
def main():
    gd = sys.argv[1]
    src = os.path.join(gd, 'dns.dat.orig') if os.path.exists(os.path.join(gd, 'dns.dat.orig')) else os.path.join(gd, 'dns.dat')
    d = open(src, 'rb').read()
    F = {n.upper(): d[o:o + s] for n, o, s in sgdat.read_index(d)}
    nog = F['NOG.FNT']
    end = GLYPH_OFF + GLYPH_LEN
    new = nog[:end] + conv(F['NOGUNIT.FNT']) + conv(F['NOGUNI_.FNT']) + nog[end:]
    here = os.path.dirname(os.path.abspath(__file__))
    outd = os.path.join(here, '..', 'out')
    os.makedirs(os.path.join(outd, 'zh'), exist_ok=True)
    fn = os.path.join(outd, 'zh', 'NOG.fnt')
    open(fn, 'wb').write(new)
    print(sgdat_add.add(src, os.path.join(outd, 'dns_zh.dat'), [fn]), len(nog), '->', len(new))
main()
