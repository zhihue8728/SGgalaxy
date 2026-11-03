"""test102 (user 2026-10-28 19:17 "闪退, 鼠标在HUD下面"; crash dump: 005f5f01 wrote 88 bytes before the canvas):
client patch F50, x86 emulation of the patched release exe (tools/patch_sg_debug_f50.py).
The pixel-pick routines (004bf400, 005f0d70, 005f4320, 005f5ed0) write a marker at mouse - viewport; F49 keeps the
mouse in 800-space but moves viewports DX right, so the marker was DX left of the mouse (wrong picks; negative index =
write before the canvas = the crash).  F50 adds DX to the mouse x there.
A. without the DLL (W 0): mouse x unchanged;  B. W 900 (DX 50): mouse x + 50;  C. the crash case: mouse (-44, 0) in
800-space, viewport (0, 0) frame -> index 6, inside the canvas (was -44)."""
import sys, os, struct
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
REPO = os.path.expanduser('~/mnt/SGgalaxy')
EXE = os.environ.get('SG_EXE', os.path.join(REPO, 'out/SG_cn.exe'))
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
SITES = {0x4bf40e: 0x4bf414, 0x5f0d8e: 0x5f0d94, 0x5f433e: 0x5f4344, 0x5f5ede: 0x5f5ee4}
bad = [hex(v) for v in SITES if not (jmp_to(v) and 0xeb4340 <= jmp_to(v) < 0xeb4400)]
chk('F50 hooks jump into the stub area 0xeb4340..0xeb4400', not bad, str(bad))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDX
mu = Uc(UC_ARCH_X86, UC_MODE_32)
for _nm, vs, va, rs, ro in secs:
    size = (max(vs, rs) + 0xfff) & ~0xfff
    mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
try:
    mu.mem_map(0xEAF000, 0x1000)
except Exception:
    pass
mu.mem_map(0x100000, 0x20000)
w32 = lambda a, v: mu.mem_write(a, struct.pack('<I', v & 0xffffffff))
T, MAIN, CG = 0xEAFF80, 0x108000, 0x10c000
STOP = set()
mu.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: uc.emu_stop() if a in STOP else None)
def run(start, stop, regs):
    STOP.clear(); STOP.add(stop)
    for k, v in regs.items(): mu.reg_write(k, v)
    mu.reg_write(UC_X86_REG_ESP, 0x118000)
    mu.emu_start(start, 0, count=5000)
    return mu.reg_read(UC_X86_REG_EIP)
for W, dx in ((0, 0), (900, 50), (1060, 130)):
    mu.mem_write(T, bytes(0x40)); w32(T + 0x3c, 1); w32(T + 0x10, W)
    w32(MAIN + 0x2578, -44); w32(MAIN + 0x257c, 0)
    w32(0x6ba7c8, MAIN); w32(0x6ba7d0, CG)
    w32(CG + 0x5c, 0x10e000); w32(CG + 0x60, 900); w32(CG + 0x64, 0); w32(CG + 0x68, 0)
    eip = run(0x4bf40e, 0x4bf414, {UC_X86_REG_ECX: MAIN})
    chk(f'W {W}: 004bf400 mouse x + DX', eip == 0x4bf414 and struct.unpack('<i', struct.pack('<I', mu.reg_read(UC_X86_REG_EAX)))[0] == -44 + dx)
    for va, back in ((0x5f0d8e, 0x5f0d94), (0x5f433e, 0x5f4344)):
        eip = run(va, back, {UC_X86_REG_EAX: MAIN})
        esi = struct.unpack('<i', struct.pack('<I', mu.reg_read(UC_X86_REG_ESI)))[0]
        chk(f'W {W}: {va:#x} mouse x + DX, eax kept', eip == back and esi == -44 + dx and mu.reg_read(UC_X86_REG_EAX) == MAIN)
    eip = run(0x5f5ed0, 0x5f5f01, {})                       # the crash site: index computed into edx
    idx = struct.unpack('<i', struct.pack('<I', mu.reg_read(UC_X86_REG_EDX)))[0]
    chk(f'W {W}: 005f5ed0 marker index = mouse_x + DX - viewport_left', eip == 0x5f5f01 and idx == -44 + dx, str(idx))
