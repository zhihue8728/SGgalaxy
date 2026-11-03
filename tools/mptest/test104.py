"""test104 (user 2026-10-28 21:58 "下方有个黑底是否能去掉"): client patch F52 (tools/patch_sg_debug_f52.py), x86 emulation
of the patched release exe + checks of the DLL source.
The quick menu's slide 004a4a50 narrowed the map to the menu's left edge (black block under / below the open menu).
A. TABLE+0x38 = 0 (no DLL): 004a4a50 runs its own code (the replayed cmp, then 0x4a4a57);
B. TABLE+0x38 set: 004a4a50 calls it with the field (ecx) as its argument and returns (stack balanced);
C. the DLL: qm_slide keeps the map's right edge at 800+DX, slides the menu by its own x (30 in / 50 out, open 587+DX,
   closed 800+DX, hidden when closed) and is installed as TABLE[14]."""
import sys, os, struct
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
o = off(0x4a4a50)
tgt = 0x4a4a50 + 5 + struct.unpack_from('<i', d, o + 1)[0] if d[o] == 0xe9 else None
chk('F52 hook at 004a4a50 jumps to the stub 0xeb4c60', tgt == 0xeb4c60, hex(tgt or 0))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ECX
mu = Uc(UC_ARCH_X86, UC_MODE_32)
for _nm, vs, va, rs, ro in secs:
    size = (max(vs, rs) + 0xfff) & ~0xfff
    mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
try:
    mu.mem_map(0xEAF000, 0x1000)
except Exception:
    pass
mu.mem_map(0x100000, 0x20000)
T, FN, RET = 0xEAFF80, 0x101000, 0x102000
mu.mem_write(FN, b'\xc3'); mu.mem_write(RET, b'\x90')
seen = {}
def hk(uc, a, s, u):
    if a == FN:
        esp = uc.reg_read(UC_X86_REG_ESP)
        seen['arg'] = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
    if a in (0x4a4a57, RET): uc.emu_stop()
mu.hook_add(UC_HOOK_CODE, hk)
def run(fnptr):
    mu.mem_write(T + 0x38, struct.pack('<I', fnptr)); seen.clear()
    mu.reg_write(UC_X86_REG_ESP, 0x118000); mu.mem_write(0x118000, struct.pack('<I', RET))
    mu.reg_write(UC_X86_REG_ECX, 0x105000)
    mu.emu_start(0x4a4a50, 0, count=200)
    return mu.reg_read(UC_X86_REG_EIP), mu.reg_read(UC_X86_REG_ESP)
eip, esp = run(0)
chk('A. no DLL: the original code continues at 0x4a4a57', eip == 0x4a4a57 and esp == 0x118000)
eip, esp = run(FN)
chk('B. DLL: qm_slide(field) called, then returns to the caller', eip == RET and seen.get('arg') == 0x105000 and esp == 0x118004)
r = open(os.path.join(SRC, 'sgrender.c'), encoding='utf-8', errors='replace').read()
chk('C. DLL: qm_slide installed as TABLE[14]', 'table[TBL_QMSLIDE] = (DWORD)qm_slide;' in r and '#define TBL_QMSLIDE    14' in r)
chk('C. DLL: map kept at the right edge, menu open 587+DX / closed 800+DX, 30 in / 50 out',
    'int R = 800 + g_DX, O = 587 + g_DX' in r and 'move(map, mx, 0, R - mx, g_MH);' in r and 'x - 30' in r and 'x += 50;' in r)
