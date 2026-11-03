"""F52 QUICK MENU OVER THE MAP (2026-10-28, user 21:58 "下方有个黑底是否能去掉").
Needs F51.  The quick menu's slide (004a4a50, every frame from 004aecf0) drives the slide with the map's right edge:
it narrows MapWnd to the quick menu's left edge, so with the menu open nothing was drawn under it and below it
(462..600 since F51) - a black block, and the HUD's see-through glass skin had only black to show.
Now 004a4a50 first calls SGRender.dll (TABLE+0x38, qm_slide(field)) when the DLL set it: the DLL slides the quick
menu by its own x (same steps: 30 px in, 50 px out, open at 587+DX, closed at 800+DX) and leaves the map the whole
frame wide.  Without the DLL (TABLE+0x38 = 0) the original code runs unchanged.
usage: python patch_sg_debug_f52.py SG.exe [more exes]   (F51 first; idempotent)"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
import patch_sg_debug_f51 as F51
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

T = F49.TABLE
STUB_VA = 0xeb4c60                     # F49's area is full (F51 ends 0xeb43fb); free after F48's strings up to 0xeb4d00
STUB_END = 0xeb4d00
SITES = {"qms": (0x4a4a50, "803d6549c30000", 0x4a4a57)}   # cmp byte ptr [0xc34965], 0
SRC = f"""
qms:
    mov eax, dword ptr [{T + 0x38:#x}]
    test eax, eax
    je qms_orig
    push ecx
    call eax
    add esp, 4
    ret
qms_orig:
    cmp byte ptr [0xc34965], 0
    jmp {SITES['qms'][2]:#x}
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, STUB_VA)[0])
assert STUB_VA + len(STUB) <= STUB_END, hex(STUB_VA + len(STUB))
ENTRY = {"qms": STUB_VA}

if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = F49.off(d, STUB_VA)
        if bytes(d[s:s + len(STUB)]) == STUB:
            print(f"{fn}: F52 already applied"); continue
        f51 = F49.off(d, F51.STUB_VA)
        assert bytes(d[f51:f51 + len(F51.STUB)]) == F51.STUB, f"{fn}: apply F51 first"
        assert d[s:s + len(STUB)] == bytes(len(STUB)), f"{fn}: stub area not free"
        for k, (va, orig, back) in SITES.items():
            o = F49.off(d, va); n = len(orig) // 2
            assert va + n == back and bytes(d[o:o + n]).hex() == orig, f"{fn}: unexpected bytes at {va:#x} ({k})"
        shutil.copy(fn, fn + ".before_f52")
        d[s:s + len(STUB)] = STUB
        for k, (va, orig, back) in SITES.items():
            o = F49.off(d, va)
            d[o:o + len(orig) // 2] = F49.jmp(va, ENTRY[k], len(orig) // 2)
        open(fn, "wb").write(d)
        print(f"{fn}: F52 applied ({len(STUB)}-byte stub at {STUB_VA:#x})")
