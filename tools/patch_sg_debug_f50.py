"""F50 PIXEL PICK IN THE WIDE FRAME (2026-10-28, user 19:17 "闪退"; crash dump SG.exe.19700.dmp).
Needs F49.  The game picks the unit under the mouse by drawing: before a sprite is drawn it writes a marker pixel at
the mouse position in the canvas and reads it back afterwards (004bf400, 005f0d70, 005f4320, 005f5ed0).  The pixel
address is  viewport origin + ((mouse_y - viewport_top) * pitch + (mouse_x - viewport_left)) * 2.
F49 moves every viewport DX to the right (frame coordinates) but keeps the mouse in 800-space (x - DX), so the
marker landed DX pixels left of the mouse: clicks picked the wrong spot, and with the mouse in the top rows of the
frame and less than DX from its left edge the index went negative and the write landed before the canvas
(crash 005f5f01, mouse_x - viewport_left = -44, row 0, frame 900 wide = DX 50).
Fix: these four reads of the mouse x (CMainSystem +0x2578) add DX (F49's getdx; 0 without the DLL = unchanged).
usage: python patch_sg_debug_f50.py SG.exe [more exes]   (F49 first; idempotent)"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

GETDX = F49.label_va("getdx")
STUB_VA = 0xeb4340                     # after F49's stubs (they end at 0xeb433f), free up to F49.STUB_END
SITES = {   # name: (va, original bytes, back address)
    "pk1": (0x4bf40e, "8b8178250000", 0x4bf414),   # 004bf400: mov eax, [ecx+0x2578]
    "pk2": (0x5f0d8e, "8bb078250000", 0x5f0d94),   # 005f0d70: mov esi, [eax+0x2578]
    "pk3": (0x5f433e, "8bb078250000", 0x5f4344),   # 005f4320
    "pk4": (0x5f5ede, "8bb078250000", 0x5f5ee4),   # 005f5ed0
}
SRC = f"""
pk1:
    call {GETDX:#x}
    add eax, dword ptr [ecx + 0x2578]
    jmp {SITES['pk1'][2]:#x}
pk2:
    push eax
    call {GETDX:#x}
    mov esi, eax
    pop eax
    add esi, dword ptr [eax + 0x2578]
    jmp {SITES['pk2'][2]:#x}
pk3:
    push eax
    call {GETDX:#x}
    mov esi, eax
    pop eax
    add esi, dword ptr [eax + 0x2578]
    jmp {SITES['pk3'][2]:#x}
pk4:
    push eax
    call {GETDX:#x}
    mov esi, eax
    pop eax
    add esi, dword ptr [eax + 0x2578]
    jmp {SITES['pk4'][2]:#x}
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, STUB_VA)[0])
assert F49.STUB_VA + len(F49.STUB) <= STUB_VA and STUB_VA + len(STUB) <= F49.STUB_END, hex(len(STUB))
def label_va(name):
    part = SRC.split("\n" + name + ":")[0]
    return STUB_VA + len(bytes(ks.asm(part, STUB_VA)[0])) if part.strip() else STUB_VA
ENTRY = {k: label_va(k) for k in SITES}

if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = F49.off(d, STUB_VA)
        if bytes(d[s:s + len(STUB)]) == STUB:
            print(f"{fn}: F50 already applied"); continue
        f49 = F49.off(d, F49.STUB_VA)
        assert bytes(d[f49:f49 + len(F49.STUB)]) == F49.STUB, f"{fn}: apply F49 first"
        assert d[s:s + len(STUB)] == bytes(len(STUB)), f"{fn}: stub area not free"
        for k, (va, orig, back) in SITES.items():
            o = F49.off(d, va); n = len(orig) // 2
            assert va + n == back and bytes(d[o:o + n]).hex() == orig, f"{fn}: unexpected bytes at {va:#x} ({k})"
        shutil.copy(fn, fn + ".before_f50")
        d[s:s + len(STUB)] = STUB
        for k, (va, orig, back) in SITES.items():
            o = F49.off(d, va)
            d[o:o + len(orig) // 2] = F49.jmp(va, ENTRY[k], len(orig) // 2)
        open(fn, "wb").write(d)
        print(f"{fn}: F50 applied ({len(STUB)}-byte stubs at {STUB_VA:#x}, {len(SITES)} sites)")
