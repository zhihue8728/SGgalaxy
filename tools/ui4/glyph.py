"""12 px bitmap CJK glyphs from the game's own Unicode fonts (dns.dat NOGUNIT.FNT = Traditional, NOGUNI_.FNT =
Simplified): 32-byte header + 65535 x {u8 width, 18 bytes = 144 bits big-endian, row r = 12 bits}."""
import numpy as np, dat
_D = dat.entries('game/dns.dat')
FONTS = {'tw': _D['NOGUNIT.FNT'], 'cn': _D['NOGUNI_.FNT']}
def glyph(ch, lang):
    f = FONTS[lang]; o = 32 + 19 * ord(ch)
    wd = f[o]; bits = int.from_bytes(f[o + 1:o + 19], 'big')
    m = np.zeros((12, 12), bool)
    for r in range(12):
        row = (bits >> (144 - 12 * (r + 1))) & 0xfff
        for c in range(12): m[r, c] = (row >> (11 - c)) & 1
    return m, wd
