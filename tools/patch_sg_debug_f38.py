"""F38 (2026-10-27, user: "切換到其他頁面無法按下Vote，只有剛進入FHQ的時候才可以"): the VOTE tab in the Domestic Policy and
Foreign Policy windows is clickable again.
1.8.5 removed only the code that CREATES the tab buttons.  Both windows still own an unused xpf button member
(Domestic +0x3c23c between the Foreign tab +0x3bae4 and the Regiment Scroll +0x3c994; Foreign +0x2810 between the
Domestic tab +0x20b8 and +0x2f68), constructed/destroyed with the others, and both click handlers still route the ids:
Domestic 0047c360 id 0x14 -> 0056f040 (jmp 0056ee30 Vote opener) + close self; Foreign 004b9420 id 0x17 -> 0056f0c0
(close Foreign, jmp 0056ee30).  The tab image is "@ fq-b-mb.xpf 3" (frames 0-2 Domestic, 3-5 VOTE, 6-8 Foreign);
it matches the backgrounds fq-dm-bk.jpg / fq-fr-bk.jpg exactly at (264,1), size 268 x 36.
Hooks: Domestic 0047a126 (mov ecx,edi; mov [edi+0x3cc9c],0x58 -- 12 bytes, end of the creator 00479e00);
       Foreign  004b834d 'push 0x652eb0' (5 bytes, right after the Domestic tab of the creator 004b7fe0).
usage: python patch_sg_debug_f38.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
S_TAB = 0xeb4770                           # "@ fq-b-mb.xpf 3"
DOM_VA, DOM_HOOK, DOM_BACK = 0xeb4630, 0x47a126, 0x47a132
FOR_VA, FOR_HOOK, FOR_BACK = 0xeb46d0, 0x4b834d, 0x4b8352
DOM_SRC = f"""
    push {S_TAB}
    lea eax, [esp+0x18]
    push 0x100
    push eax
    call 0x60947e
    add esp, 0xc
    lea ecx, [edi+0x3c23c]
    mov edx, dword ptr [ecx]
    mov edx, dword ptr [edx+0x40]
    lea eax, [esp+0x14]
    push eax
    mov dword ptr [esp+0x118], 0x108
    mov dword ptr [esp+0x11c], 1
    mov dword ptr [esp+0x120], 0x10c
    mov dword ptr [esp+0x124], 0x24
    mov dword ptr [esp+0x128], edi
    mov dword ptr [esp+0x12c], 0xf0
    mov dword ptr [esp+0x130], 0
    mov dword ptr [esp+0x134], 0x14
    call edx
    mov ecx, edi
    mov dword ptr [edi+0x3cc9c], 0x58
    jmp {DOM_BACK}
"""
FOR_SRC = f"""
    push {S_TAB}
    lea eax, [esp+0x14]
    push 0x100
    push eax
    call 0x60947e
    add esp, 0xc
    lea ecx, [esi+0x2810]
    mov edx, dword ptr [ecx]
    mov edx, dword ptr [edx+0x40]
    lea eax, [esp+0x10]
    push eax
    mov dword ptr [esp+0x114], 0x108
    mov dword ptr [esp+0x118], 1
    mov dword ptr [esp+0x11c], 0x10c
    mov dword ptr [esp+0x120], 0x24
    mov dword ptr [esp+0x124], esi
    mov dword ptr [esp+0x128], 0xf0
    mov dword ptr [esp+0x12c], 0
    mov dword ptr [esp+0x130], 0x17
    call edx
    push 0x652eb0
    jmp {FOR_BACK}
"""
DOM_ORIG = bytes.fromhex("8bcfc7879ccc030058000000")
FOR_ORIG = bytes.fromhex("68b02e6500")

def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    return [struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i) for i in range(n)]

def off(d, va):
    for _nm, vs, sva, rs, ro in sections(d):
        if 0x400000 + sva <= va < 0x400000 + sva + min(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit(f"VA {va:#x} not in any section's raw data")

ks = Ks(KS_ARCH_X86, KS_MODE_32)
DOM = bytes(ks.asm(DOM_SRC, DOM_VA)[0])
FOR = bytes(ks.asm(FOR_SRC, FOR_VA)[0])
assert len(DOM) <= FOR_VA - DOM_VA and len(FOR) <= S_TAB - FOR_VA, (len(DOM), len(FOR))
TAB = b"@ fq-b-mb.xpf 3\0"
def jmp(src, dst): return b"\xe9" + struct.pack("<i", dst - (src + 5))
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    hd, hf = off(d, DOM_HOOK), off(d, FOR_HOOK)
    if bytes(d[hd:hd + 5]) == jmp(DOM_HOOK, DOM_VA) and bytes(d[hf:hf + 5]) == jmp(FOR_HOOK, FOR_VA):
        print(f"{fn}: F38 already applied"); continue
    if bytes(d[hd:hd + 12]) != DOM_ORIG or bytes(d[hf:hf + 5]) != FOR_ORIG:
        raise SystemExit(f"{fn}: unexpected bytes at hooks: {d[hd:hd+12].hex()} / {d[hf:hf+5].hex()}")
    s = off(d, DOM_VA)
    assert d[s:s + 0x150] == bytes(0x150), "stub area not free"
    shutil.copy(fn, fn + ".before_f38")
    d[s:s + len(DOM)] = DOM
    d[off(d, FOR_VA):off(d, FOR_VA) + len(FOR)] = FOR
    d[off(d, S_TAB):off(d, S_TAB) + len(TAB)] = TAB
    d[hd:hd + 12] = jmp(DOM_HOOK, DOM_VA) + b"\x90" * 7
    d[hf:hf + 5] = jmp(FOR_HOOK, FOR_VA)
    open(fn, "wb").write(d)
    print(f"{fn}: F38 applied (stubs {len(DOM)}+{len(FOR)} bytes at {DOM_VA:#x}/{FOR_VA:#x})")
