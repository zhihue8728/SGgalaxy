"""test103 (user 2026-10-28 20:41 "戰場畫面應該要再拉高一點"): client patch F51 (tools/patch_sg_debug_f51.py), x86
emulation of the patched release exe + checks of the DLL source.
The field map (MapWnd) is MH high (TABLE+0x34 from SGRender.dll, 462..600; 0 / outside = 462 = the original).
A. terrain rows 00499d10: (MH + 63) / 32 rows (462 -> 16 = original, 600 -> 20);
B. the 4 MapWnd re-sizes of the quick menu / strategic map slides push MH (eax and the stack kept);
C. the wreck rows (0049ba40): + 0x16;
D. the DLL: MapWnd created MH high, TABLE[13] = MH, the fog of war window (MH + 32) / 8 + 3 rows, its draw / test
   installed for a tall map, the HUD radar's camera frame MH high, the HUD panels float (no full-width band)."""
import sys, os, struct, re
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
REPO = os.path.expanduser('~/mnt/SGgalaxy')
EXE = os.environ.get('SG_EXE', os.path.join(REPO, 'out/SG_cn.exe'))
SRC = os.environ.get('SG_SRC', os.path.join(REPO, 'client/sgrender'))
d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = [struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i) for i in range(n)]
def off(va):
    for _nm, vs, sva, rs, ro in secs:
        if 0x400000 + sva <= va < 0x400000 + sva + min(vs, rs):
            return va - 0x400000 - sva + ro
def jmp_to(va):
    o = off(va)
    return va + 5 + struct.unpack_from('<i', d, o + 1)[0] if d[o] == 0xe9 else None
SITES = {0x499d84: 0x499d89, 0x4a4af0: 0x4a4af5, 0x4a4bbb: 0x4a4bc0, 0x4a6af0: 0x4a6af5, 0x4a6bb3: 0x4a6bb8}
bad = [hex(v) for v in SITES if not (jmp_to(v) and 0xeb4380 <= jmp_to(v) < 0xeb4400)]
chk('F51 hooks jump into the stub area after F50', not bad, str(bad))
chk('C. wreck rows: add edx, 0x16', d[off(0x49c29c):off(0x49c29c) + 3] == b'\x83\xc2\x16')
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_EBX
mu = Uc(UC_ARCH_X86, UC_MODE_32)
for _nm, vs, va, rs, ro in secs:
    size = (max(vs, rs) + 0xfff) & ~0xfff
    mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
try:
    mu.mem_map(0xEAF000, 0x1000)
except Exception:
    pass
mu.mem_map(0x100000, 0x20000)
T = 0xEAFF80
STOP = set()
mu.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: uc.emu_stop() if a in STOP else None)
def run(start, stops, regs):
    STOP.clear(); STOP.update(stops)
    for k, v in regs.items(): mu.reg_write(k, v)
    mu.reg_write(UC_X86_REG_ESP, 0x118000)
    mu.emu_start(start, 0, count=5000)
    return mu.reg_read(UC_X86_REG_EIP)
for tv, mh in ((0, 462), (462, 462), (600, 600), (540, 540), (700, 462), (100, 462)):
    mu.mem_write(T + 0x34, struct.pack('<I', tv))
    rows = (mh + 63) // 32
    ok = all(run(0x499d84, {0x499d20, 0x499d89}, {UC_X86_REG_EBX: k, UC_X86_REG_EAX: 0x1234}) == (0x499d20 if k < rows else 0x499d89)
             and mu.reg_read(UC_X86_REG_EAX) == 0x1234 and mu.reg_read(UC_X86_REG_ESP) == 0x118000 for k in range(rows - 2, rows + 2))
    chk(f'A. TABLE MH {tv}: terrain rows {rows}', ok)
    good = True
    for va, back in list(SITES.items())[1:]:
        eip = run(va, {back}, {UC_X86_REG_EAX: 0x5678})
        top = struct.unpack('<I', mu.mem_read(mu.reg_read(UC_X86_REG_ESP), 4))[0]
        good &= eip == back and top == mh and mu.reg_read(UC_X86_REG_ESP) == 0x118000 - 4 and mu.reg_read(UC_X86_REG_EAX) == 0x5678
    chk(f'B. TABLE MH {tv}: MapWnd re-sizes push {mh}', good)
r = open(os.path.join(SRC, 'sgrender.c'), encoding='utf-8', errors='replace').read()
h = open(os.path.join(SRC, 'sghud.c'), encoding='utf-8', errors='replace').read()
chk('D. DLL: MapWnd created MH high', 'if (r[3] == 462) r[3] = g_MH;' in r)
chk('D. DLL: TABLE[13] = MH, 600 with the HUD, 462 with backend=cnc / [hud] enable=0', 'table[TBL_MAPH] = g_MH;' in r and
    re.search(r'"maph", hud \? 600 : 462', r) is not None and '_stricmp(be, "cnc")' in r)
chk('D. DLL: fog rows (MH + 32) / 8 + 3 (>= 0x40), draw / test installed for a tall map',
    'g_fog_rows = (g_MH + 32) / 8 + 3' in r and 'if (g_DX || g_MH != 462) { table[TBL_FOG_DRAW]' in r)
chk('D. HUD: radar camera frame MH high, floating panels', 's->camh = sgr_map_h();' in h and 'static void panel_bg(' in h
    and 'hit_add(0, yb, C.RW, hb, 0, H_SWALLOW, 0);' not in h)
