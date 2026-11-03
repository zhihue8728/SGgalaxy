"""F51 TALL FIELD MAP (2026-10-28, user 20:41 "戰場畫面應該要再拉高一點").
Needs F50.  The field map (MapWnd) was 462 high, the old lower panel CStatusLowerWnd filled 462..600.  The new HUD
(SGRender.dll) hides that panel and floats its own panels over the map, so the map can use the whole frame height.
The DLL creates MapWnd MH high (TABLE+0x34, 462..600; 0 / outside = 462 = unchanged without the DLL) and the exe:
  - draws enough terrain rows: 00499d10 loops 16 rows (16 * 32 = 512 >= 462 + 32) -> (MH + 63) / 32 (600 -> 20);
  - the quick menu (004a4a50) and the left strategic map (004a6a50) slide code re-sizes MapWnd with height 462 at
    4 places -> MH (their own panels stay 462 high);
  - wrecks: the draw loop over destroyed units (sorted by y) in 0049ba40 stops below scroll row + 0x11 -> + 0x16.
Everything else follows MapWnd's own rect (+0x130 / +0x134): unit / object culling, the camera clamp 0049ab30.
The fog of war (exe window 0x40 rows = 512 px) is drawn and tested by the DLL (F49's TABLE+0x2c / +0x30), which
builds its window MH + 32 pixels high.
getmh: eax = MH.  usage: python patch_sg_debug_f51.py SG.exe [more exes]   (F50 first; idempotent)"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
import patch_sg_debug_f50 as F50
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

T = F49.TABLE
STUB_VA = (F50.STUB_VA + len(F50.STUB) + 0xf) & ~0xf
SITES = {   # name: (va, original bytes, back address)
    "rows": (0x499d84, "83fb107c97", 0x499d89),      # cmp ebx, 0x10 / jl 0x499d20
    "mq1":  (0x4a4af0, "68ce010000", 0x4a4af5),      # MapWnd Move(.., 462): quick menu slides out
    "mq2":  (0x4a4bbb, "68ce010000", 0x4a4bc0),      #   quick menu slides in
    "ms1":  (0x4a6af0, "68ce010000", 0x4a6af5),      #   strategic map slides out
    "ms2":  (0x4a6bb3, "68ce010000", 0x4a6bb8),      #   strategic map slides in
}
WRECK = (0x49c29c, "83c211", "83c216")                # add edx, 0x11 -> 0x16 (in place)
SRC = f"""
getmh:
    mov eax, dword ptr [{T + 0x34:#x}]
    cmp eax, 462
    jl gm_def
    cmp eax, 600
    jle gm_ok
gm_def:
    mov eax, 462
gm_ok:
    ret
rows:
    push eax
    call getmh
    add eax, 63
    shr eax, 5
    cmp ebx, eax
    pop eax
    jl 0x499d20
    jmp {SITES['rows'][2]:#x}
mq1:
    push eax
    call getmh
    xchg eax, dword ptr [esp]
    jmp {SITES['mq1'][2]:#x}
mq2:
    push eax
    call getmh
    xchg eax, dword ptr [esp]
    jmp {SITES['mq2'][2]:#x}
ms1:
    push eax
    call getmh
    xchg eax, dword ptr [esp]
    jmp {SITES['ms1'][2]:#x}
ms2:
    push eax
    call getmh
    xchg eax, dword ptr [esp]
    jmp {SITES['ms2'][2]:#x}
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, STUB_VA)[0])
assert STUB_VA + len(STUB) <= F49.STUB_END, hex(STUB_VA + len(STUB))
def label_va(name):
    part = SRC.split("\n" + name + ":")[0]
    return STUB_VA + len(bytes(ks.asm(part, STUB_VA)[0])) if part.strip() else STUB_VA
ENTRY = {k: label_va(k) for k in SITES}

if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = F49.off(d, STUB_VA)
        if bytes(d[s:s + len(STUB)]) == STUB:
            print(f"{fn}: F51 already applied"); continue
        f50 = F49.off(d, F50.STUB_VA)
        assert bytes(d[f50:f50 + len(F50.STUB)]) == F50.STUB, f"{fn}: apply F50 first"
        assert d[s:s + len(STUB)] == bytes(len(STUB)), f"{fn}: stub area not free"
        for k, (va, orig, back) in SITES.items():
            o = F49.off(d, va); n = len(orig) // 2
            assert va + n == back and bytes(d[o:o + n]).hex() == orig, f"{fn}: unexpected bytes at {va:#x} ({k})"
        w = F49.off(d, WRECK[0])
        assert bytes(d[w:w + 3]).hex() == WRECK[1], f"{fn}: unexpected bytes at {WRECK[0]:#x}"
        shutil.copy(fn, fn + ".before_f51")
        d[s:s + len(STUB)] = STUB
        for k, (va, orig, back) in SITES.items():
            o = F49.off(d, va)
            d[o:o + len(orig) // 2] = F49.jmp(va, ENTRY[k], len(orig) // 2)
        d[w:w + 3] = bytes.fromhex(WRECK[2])
        open(fn, "wb").write(d)
        print(f"{fn}: F51 applied ({len(STUB)}-byte stubs at {STUB_VA:#x}, {len(SITES)} sites + wreck rows)")
