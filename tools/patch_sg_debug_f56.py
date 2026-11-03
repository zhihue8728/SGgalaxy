"""F56 COUNCIL OK (2026-11-03, user: FHQ council "勾選後點擊離開出現無效" - ticking a power and leaving always says invalid).
The council screen (Domestic Policy) keeps 100 records (this+0x3ce98, rows of 0x5c: +4 regiment, +0x20 title,
+0x3c name, +0x58 powers - the client pads the server's list to 100) but creates only 13 edit boxes (479e00) that show
records off..off+12 while scrolling (479be0).  Its OK check 47b7e0 reads edit box i for record i, for all 100 records:
edit boxes 13..99 were never created and are empty -> "invalid" every time, and after a scroll the 13 boxes hold
other records' text.  The three edit reads (thiscall 43e490(buf, 0xff), ret 8) now copy record i's own text instead,
so the check and the packet see the server's rows (and what the user typed or deleted in a box is ignored: names
and titles are the server's, see server/sgs/social.py council_save).  Not battle code: no lock-step concern.
usage: python patch_sg_debug_f56.py SG.exe [more exes]   (idempotent; checks the bytes first)"""
import sys, os, shutil, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

GETTEXT = 0x43e490
CAVE_VA = 0xeb4cb0                     # after F55's stub (0xeb4c90..0xeb4ca0), free to the end of .dbgmov (0xeb5000)
CAVE_END = 0xeb4d80
# call site -> the record string's offset in the row (regiment / title / name)
CALLS = {0x47b9d2: 0x04, 0x47bae5: 0x20, 0x47bb76: 0x3c}
# in 47b7e0's loop: esi = &records (vector: +4 begin, +8 end), caller [esp+0x40] = row * 0x5c;
# in the cave (return address + 2 args above the caller's esp) that is [esp+0x4c]
SRC = """
c_reg:
    mov eax, 0x04
    jmp common
c_title:
    mov eax, 0x20
    jmp common
c_name:
    mov eax, 0x3c
common:
    mov edx, dword ptr [esi + 4]
    test edx, edx
    je empty
    add edx, dword ptr [esp + 0x4c]
    cmp edx, dword ptr [esi + 8]
    jae empty
    add edx, eax
    cmp dword ptr [edx + 0x18], 0x10
    jb inl
    mov edx, dword ptr [edx + 4]
    jmp copy
inl:
    add edx, 4
copy:
    push edi
    mov edi, dword ptr [esp + 8]
    mov ecx, 0xfe
lp:
    mov al, byte ptr [edx]
    mov byte ptr [edi], al
    test al, al
    je done
    inc edx
    inc edi
    dec ecx
    jne lp
    mov byte ptr [edi], 0
done:
    pop edi
    ret 8
empty:
    mov edx, dword ptr [esp + 4]
    mov byte ptr [edx], 0
    ret 8
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
CAVE = bytes(ks.asm(SRC, CAVE_VA)[0])
assert CAVE_VA + len(CAVE) <= CAVE_END, hex(CAVE_VA + len(CAVE))
ENTRY = {0x04: CAVE_VA, 0x20: CAVE_VA + 7, 0x3c: CAVE_VA + 14}     # mov eax,imm32 (5) + jmp short (2)
assert CAVE[0] == 0xb8 and CAVE[7] == 0xb8 and CAVE[14] == 0xb8


def call_bytes(at, to):
    return b"\xe8" + struct.pack("<i", to - (at + 5))


if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = F49.off(d, CAVE_VA)
        if bytes(d[s:s + len(CAVE)]) == CAVE and all(bytes(d[F49.off(d, c):F49.off(d, c) + 5]) == call_bytes(c, ENTRY[k]) for c, k in CALLS.items()):
            print(f"{fn}: F56 already applied"); continue
        assert d[s:s + len(CAVE)] == bytes(len(CAVE)), f"{fn}: cave area not free"
        for c in CALLS:
            o = F49.off(d, c)
            assert bytes(d[o:o + 5]) == call_bytes(c, GETTEXT), f"{fn}: unexpected bytes at {c:#x}"
        shutil.copy(fn, fn + ".before_f56")
        d[s:s + len(CAVE)] = CAVE
        for c, k in CALLS.items():
            o = F49.off(d, c)
            d[o:o + 5] = call_bytes(c, ENTRY[k])
        open(fn, "wb").write(d)
        print(f"{fn}: F56 applied ({len(CAVE)}-byte cave at {CAVE_VA:#x}, {len(CALLS)} calls)")
