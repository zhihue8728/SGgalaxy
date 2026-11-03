"""F37 (2026-10-26, user: presidential elections): the FHQ hall (CPreCityHallWnd) VOTE button is back.
1.8.5 removed only the code that CREATES the button: the window still owns a BinkButton member at +0xd04 (constructed /
destroyed with the others, shown / hidden by 0056e830, highlight frame for id 0x10 at 0056e7e8 = (350, 300, 101 x 97)),
the click handler 0056efc0 maps id 0x10 -> [+0x5da0] = 1 -> 0056ee30 opens "Vote Wnd" (+0x5da4), and the videos
fq-vt-n.bik / fq-vt-h.bik / fq-vt-mk.xpf are still in odv.dat.  The stub re-creates it exactly like Domestic Policy
(0056eb17..0056eb17+0x9a): 0041c710(normal bik, hit bik, mask, mask, 1, 0) and vtable+0x40 create with the rectangle
350,300,101,97, parent = the hall, style 0xf0, id 0x10.
Hook: 0056ece5 'push 0x65a94c' (5 bytes, after the Exit button) -> jmp stub; the stub ends with that push and jumps back.
usage: python patch_sg_debug_f37.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
VA, HOOK, BACK = 0xeb4500, 0x56ece5, 0x56ecea
S_N, S_NAME = 0xeb4600, 0xeb4610          # "fq-vt-n.bik", "BkButtonVote"
SRC = f"""
    push edi
    push 1
    push 0x65a8f8
    push 0x65a8f8
    push 0x65a8ec
    lea ebp, [esi+0xd04]
    push {S_N}
    mov ecx, ebp
    call 0x41c710
    push {S_NAME}
    lea eax, [esp+0x14]
    push 0x100
    push eax
    call 0x60947e
    mov edx, dword ptr [ebp]
    mov edx, dword ptr [edx+0x40]
    add esp, 0xc
    lea eax, [esp+0x10]
    push eax
    mov ecx, ebp
    mov dword ptr [esp+0x114], 0x15e
    mov dword ptr [esp+0x118], 0x12c
    mov dword ptr [esp+0x11c], 0x65
    mov dword ptr [esp+0x120], 0x61
    mov dword ptr [esp+0x124], esi
    mov dword ptr [esp+0x128], 0xf0
    mov dword ptr [esp+0x12c], edi
    mov dword ptr [esp+0x130], 0x10
    call edx
    push 0x65a94c
    jmp {BACK}
"""
ORIG = bytes.fromhex("684ca96500")

def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    return [struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i) for i in range(n)]

def off(d, va):
    for _nm, vs, sva, rs, ro in sections(d):
        if 0x400000 + sva <= va < 0x400000 + sva + max(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit("VA not in any section")

ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, VA)[0])
assert len(STUB) < S_N - VA, len(STUB)
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    h = off(d, HOOK)
    if d[h] == 0xE9 and struct.unpack_from("<i", d, h + 1)[0] == VA - (HOOK + 5):
        print(f"{fn}: F37 already applied"); continue
    if bytes(d[h:h + 5]) != ORIG:
        raise SystemExit(f"{fn}: unexpected bytes at {HOOK:#x}: {d[h:h + 5].hex()}")
    s = off(d, VA)
    assert d[s:s + 0x120] == bytes(0x120), "stub area not free"
    shutil.copy(fn, fn + ".before_f37")
    d[s:s + len(STUB)] = STUB
    d[off(d, S_N):off(d, S_N) + 12] = b"fq-vt-n.bik\0"
    d[off(d, S_NAME):off(d, S_NAME) + 13] = b"BkButtonVote\0"
    d[h:h + 5] = b"\xe9" + struct.pack("<i", VA - (HOOK + 5))
    open(fn, "wb").write(d)
    print(f"{fn}: F37 applied (stub {len(STUB)} bytes at {VA:#x})")
