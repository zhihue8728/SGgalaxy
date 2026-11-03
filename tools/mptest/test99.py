"""test99 (user 2026-10-28 15:18 "下一步" = phase 1: widescreen, see more of the map): client patch F49, x86 emulation
of the real patched release exe (tools/patch_sg_debug_f49.py).
A. without SGRender.dll (TABLE 0): every stub behaves like the original code (800 x 600, no shift);
B. with W = 1060 (DX = 130): the frame is W x 600, every viewport moves DX right (SetViewport's own body runs),
   the mouse is clamped to 0..W-1 and moved back by DX, the whole-screen clip rects are -DX .. 800+DX, TC Main and
   Field count as -DX .. 800+DX for child clipping and hit tests, the quick menu / terrain / card constants are
   800+DX based, the fog of war calls go to the DLL, the cursor clip is widened."""
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
SITES = [0x544d3e, 0x4c0b60, 0x4c0b7e, 0x4c0c5d, 0x438100, 0x5459b2, 0x545a50, 0x5490f0, 0x5487d5, 0x549241, 0x549255,
         0x5487ff, 0x545867, 0x4a4a87, 0x4a4b61, 0x499d79, 0x499d90, 0x4b6120, 0x4afa94, 0x54911a, 0x54ba1e]
bad = [hex(v) for v in SITES if not (jmp_to(v) and 0xeb3f40 <= jmp_to(v) < 0xeb4400)]
chk('F49 hooks jump into the stub area 0xeb3f40..0xeb4400', not bad, str(bad))
chk('quick menu test "map right + left <= 0x24b" left as it was', d[off(0x4a4a75):off(0x4a4a75) + 6].hex() == '81f94b020000')
try:
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
                                   UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_EFLAGS)
except ImportError:
    print('PASS (unicorn not installed - emulation skipped)'); sys.exit(0)
mu = Uc(UC_ARCH_X86, UC_MODE_32)
for _nm, vs, va, rs, ro in secs:
    size = (max(vs, rs) + 0xfff) & ~0xfff
    mu.mem_map(0x400000 + va, size); mu.mem_write(0x400000 + va, d[ro:ro + min(rs, size)])
try:
    mu.mem_map(0xEAF000, 0x1000)
except Exception:
    pass
mu.mem_map(0x100000, 0x20000)        # stack + objects
mu.mem_map(0x200000, 0x1000)         # fake DLL entry points
mu.mem_map(0xdead0000, 0x1000)
T = 0xEAFF80
u32 = lambda a: struct.unpack('<I', mu.mem_read(a, 4))[0]
i32 = lambda a: struct.unpack('<i', mu.mem_read(a, 4))[0]
w32 = lambda a, v: mu.mem_write(a, struct.pack('<I', v & 0xffffffff))
calls, STOP = [], set()
F_FOGD, F_FOGV = 0x200000, 0x200010
def hook(uc, addr, size, ud):
    if addr in STOP:
        uc.emu_stop(); return
    if addr in (F_FOGD, F_FOGV):
        esp = uc.reg_read(UC_X86_REG_ESP)
        calls.append((addr, [u32(esp + 4 + 4 * k) for k in range(3)]))
        uc.reg_write(UC_X86_REG_EAX, 1)
        uc.reg_write(UC_X86_REG_ESP, esp + 4); uc.reg_write(UC_X86_REG_EIP, u32(esp))
mu.hook_add(UC_HOOK_CODE, hook)
def run(start, stops, regs=None, stack=(), raw=False):
    calls.clear(); STOP.clear(); STOP.update(stops)
    esp = 0x110000
    r = {UC_X86_REG_EBX: 0, UC_X86_REG_ESI: 0, UC_X86_REG_EDI: 0, UC_X86_REG_EBP: 0, UC_X86_REG_ECX: 0,
         UC_X86_REG_EDX: 0, UC_X86_REG_EAX: 0}
    r.update(regs or {})
    for k, v in r.items():
        mu.reg_write(k, v & 0xffffffff)
    mu.mem_write(esp - 0x400, bytes(0x800))
    w32(esp, 0xdead0000)
    for i, v in enumerate(stack):
        w32(esp + (0 if raw else 4) + 4 * i, v)
    mu.reg_write(UC_X86_REG_ESP, esp)
    mu.emu_start(start, 0, count=20000)
    out = {k: mu.reg_read(k) for k in r}
    out[UC_X86_REG_ESP] = mu.reg_read(UC_X86_REG_ESP)
    return mu.reg_read(UC_X86_REG_EIP), out, esp

def setup(W):
    mu.mem_write(T, bytes(0x40))
    w32(T + 0x3c, 1)                     # "DLL already loaded" (no LoadLibrary in the emulator)
    w32(T + 0x10, W)
CG = 0x104000                            # a CGraph: base +0x34, pitch +0x60, surface h +0xac / w +0xb0
def cg_init(W):
    mu.mem_write(CG, bytes(0x200))
    w32(CG + 0x34, 0x01000000); w32(CG + 0x60, W); w32(CG + 0xac, 600); w32(CG + 0xb0, W)
    w32(0x6ba7d0, CG)
RECT, PRECT = 0x106000, 0x106010
def setvp(rect, prect):
    for i, v in enumerate(rect): w32(RECT + 4 * i, v)
    for i, v in enumerate(prect): w32(PRECT + 4 * i, v)
    eip, out, esp = run(0x438100, {0xdead0000}, {UC_X86_REG_ECX: CG}, (RECT, PRECT))
    return eip, out[UC_X86_REG_ESP] - esp, [i32(CG + o) for o in (0x64, 0x68, 0x6c, 0x70, 0x74, 0x78, 0x7c, 0x80)], u32(CG + 0x5c)

for W, label in ((0, 'no DLL'), (1060, 'W 1060')):
    DX = (max(W, 800) - 800) // 2 if W else 0
    setup(W); cg_init(W or 800)
    WW = W or 800
    # SetDisplayMode push
    eip, out, esp = run(0x4c0c5d, {0x4c0c62}, {UC_X86_REG_EAX: 0x1234})
    chk(f'{label}: SetDisplayMode width {WW}', eip == 0x4c0c62 and u32(out[UC_X86_REG_ESP]) == WW and out[UC_X86_REG_EAX] == 0x1234)
    chk(f'{label}: TABLE+0x14 = W in use', u32(T + 0x14) == WW)
    # CreateWindowEx width
    eip, out, esp = run(0x544d3e, {0x544d43})
    chk(f'{label}: CreateWindowEx width {WW + 2}', u32(out[UC_X86_REG_ESP]) == WW + 2)
    # SetViewport: rect (10,20,110,70) in parent (0,0,800,600)
    eip, popped, vp, base = setvp((10, 20, 110, 70), (-DX, 0, 800 + DX, 600))
    chk(f'{label}: SetViewport viewport moved by {DX}', eip == 0xdead0000 and popped == 12 and vp[:4] == [10 + DX, 20, 110 + DX, 70]
        and vp[4:] == [0, 0, 100, 50] and base == 0x01000000 + (WW * 20 + 10 + DX) * 2, f'{vp} {base:#x}')
    # the wide map: (-DX, 0, 800+DX, 462) in parent (-DX, 0, 800+DX, 600) -> whole frame, clip 0..W
    eip, popped, vp, base = setvp((-DX, 0, 800 + DX, 462), (-DX, 0, 800 + DX, 600))
    chk(f'{label}: the map viewport covers the frame', vp[:4] == [0, 0, WW, 462] and vp[4:] == [0, 0, WW, 462] and base == 0x01000000, str(vp))
    # mouse clamp + translate (005459a0 path): x 1500 -> W-1-DX ; x 300 -> 300-DX
    for x_in, x_want in ((1500, WW - 1 - DX), (300, 300 - DX)):
        eip, out, esp = run(0x5459b2, {0x5459be}, {UC_X86_REG_EAX: x_in, UC_X86_REG_EDX: 77})
        chk(f'{label}: mouse x {x_in} -> {x_want}', eip == 0x5459be and out[UC_X86_REG_EAX] == x_want & 0xffffffff
            and out[UC_X86_REG_EDX] == 77 and out[UC_X86_REG_ESP] == esp)
    eip, out, esp = run(0x545a50, {0x545a5d}, {UC_X86_REG_EDI: 1500, UC_X86_REG_EAX: 5})
    chk(f'{label}: mouse x (second path) clamped and moved', out[UC_X86_REG_EDI] == WW - 1 - DX and out[UC_X86_REG_EAX] == 5)
    # whole-screen clip rect of the frame (005490c0)
    eip, out, esp = run(0x5490f0, {0x549104}, {UC_X86_REG_EBX: 0, UC_X86_REG_EBP: 600})
    chk(f'{label}: frame root clip = {-DX}..{800 + DX}', [i32(esp + 0x24 + 4 * k) for k in range(4)] == [-DX, 0, 800 + DX, 600]
        and out[UC_X86_REG_ESP] == esp)
    # window tree default clip, the cmp flags before it are kept (ZF=1 -> je taken later)
    mu.reg_write(UC_X86_REG_EFLAGS, 0x46)
    eip, out, esp = run(0x5487d5, {0x5487ed}, {UC_X86_REG_EDI: 0})
    chk(f'{label}: window tree clip = {-DX}..{800 + DX}, flags kept', [i32(esp + 0xc + 4 * k) for k in range(4)] == [-DX, 0, 800 + DX, 600]
        and (mu.reg_read(UC_X86_REG_EFLAGS) & 0x40) != 0)
    # child clipping: the parent is Field (TABLE+0x28) -> no parent clip (only with a DLL)
    FIELD, OTHER, WND = 0x108000, 0x108400, 0x108800
    w32(T + 0x28, FIELD if W else 0)
    w32(WND + 0x138, FIELD)
    eip, out, esp = run(0x5487ff, {0x548807, 0x548831}, {UC_X86_REG_ESI: WND, UC_X86_REG_EDI: 0})
    chk(f'{label}: child of Field: {"whole-frame clip" if W else "parent clip as before"}', eip == (0x548831 if W else 0x548807))
    w32(WND + 0x138, OTHER)
    eip, out, esp = run(0x5487ff, {0x548807, 0x548831}, {UC_X86_REG_ESI: WND, UC_X86_REG_EDI: 0})
    chk(f'{label}: child of another window: parent clip', eip == 0x548807 and out[UC_X86_REG_EAX] == OTHER)
    # hit test: Field takes any x; another window only its own rect
    APP = 0x10a000
    w32(APP + 0xc24, -100)
    for wnd, want in ((FIELD, 0x545885 if W else 0x545976), (OTHER, 0x545976)):
        w32(wnd + 0x118, 0); w32(wnd + 0x120, 800)
        eip, out, esp = run(0x545867, {0x545885, 0x545976}, {UC_X86_REG_EDI: APP, UC_X86_REG_ESI: wnd})
        chk(f'{label}: hit test x -100 on {"Field" if wnd == FIELD else "a window"}', eip == want, hex(eip))
    # quick menu: closed x (push) = 800+DX ; terrain columns ; right small unit card x
    eip, out, esp = run(0x4a4b61, {0x4a4b66})
    chk(f'{label}: quick menu closed at {800 + DX}', u32(out[UC_X86_REG_ESP]) == 800 + DX)
    eip, out, esp = run(0x499d79, {0x499d40, 0x499d81}, {UC_X86_REG_EBP: WW + 31})
    chk(f'{label}: terrain column x {WW + 31} drawn', eip == 0x499d40)
    eip, out, esp = run(0x499d79, {0x499d40, 0x499d81}, {UC_X86_REG_EBP: WW + 32})
    chk(f'{label}: terrain stops at {WW + 32}', eip == 0x499d81)
    eip, out, esp = run(0x4afa94, {0x4afa99})
    chk(f'{label}: right small unit cards at {0x2ab + DX}', out[UC_X86_REG_EAX] == 0x2ab + DX)
    # fog of war: DLL slots
    w32(T + 0x2c, F_FOGD if W else 0); w32(T + 0x30, F_FOGV if W else 0)
    eip, out, esp = run(0x499d90, {0x499d99, 0xdead0000}, {UC_X86_REG_ECX: 0x10c000})
    chk(f'{label}: fog draw {"-> DLL" if W else "original"}', (eip == 0xdead0000 and calls == [(F_FOGD, [0x10c000, 0xdead0000, 0])]
        and out[UC_X86_REG_ESP] == esp + 4) if W else eip == 0x499d99, str(calls))
    eip, out, esp = run(0x4b6120, {0x4b6126, 0xdead0000}, {UC_X86_REG_ECX: 0x10c000}, (5, 7))
    chk(f'{label}: fog visibility {"-> DLL" if W else "original"}', (eip == 0xdead0000 and calls[0][0] == F_FOGV
        and calls[0][1] == [0x10c000, 5, 7] and out[UC_X86_REG_ESP] == esp + 12 and out[UC_X86_REG_EAX] & 0xff == 1)
        if W else (eip == 0x4b6126 and out[UC_X86_REG_EDX] == 5))
    # cursor viewport clip widened after its SetViewport (TC Main rect 0..800 in parent -DX..800+DX)
    for i, v in enumerate((0, 0, 800, 600)): w32(RECT + 4 * i, v)
    for i, v in enumerate((-DX, 0, 800 + DX, 600)): w32(PRECT + 4 * i, v)
    eip, out, esp = run(0x549255, {0x54925a}, {UC_X86_REG_ECX: CG}, (RECT, PRECT), raw=True)
    chk(f'{label}: cursor viewport origin {DX}, clip {-DX}..{800 + DX}', eip == 0x54925a and i32(CG + 0x64) == DX
        and i32(CG + 0x74) == -DX and i32(CG + 0x7c) == 800 + DX and out[UC_X86_REG_ESP] == esp + 8)
