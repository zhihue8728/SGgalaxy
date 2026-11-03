"""F42 (2026-10-27, user: "头上的星星就按转生次数吧, 铜星/银星/金星来分配"): the title line over a commander's name gets
its colour from the server: a first byte 1/2/3 in the 0x20 title selects copper / silver / gold and is not printed;
without it the line stays F41's teal.  Needs F41 (title printed as "%s").
  hook 1: 004cf0f5 'push esi; push 0x65348c' (6 bytes, esi = unit +0xc6 title) -> stub: tier = [esi] if 1..3 (saved
          at 0xEAFF48, page tail after .data, outside the checksum) and the text starts after it; else tier 0.
  hook 2: 004cf11e 'push B; push G; push R' (15 bytes, args of 00402f40 colour) -> stub pushes the tier's colour.
usage: python patch_sg_debug_f42.py SG_debug.exe [more exes]   (after F41; idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
TIER = 0xEAFF48
H1, H1_BACK, H2, H2_BACK = 0x4cf0f5, 0x4cf0fb, 0x4cf11e, 0x4cf12d
S1, S2, TABLE = 0xeb4840, 0xeb4880, 0xeb48c0
#            tier 0 teal (F41)   1 copper         2 silver          3 gold        as (B, G, R)
COLOURS = [(0xc8, 0xe6, 0x50), (50, 127, 205), (225, 215, 210), (40, 210, 255)]
SRC1 = f"""
    movzx eax, byte ptr [esi]
    cmp eax, 1
    jb none
    cmp eax, 3
    ja none
    mov dword ptr [{TIER}], eax
    lea eax, [esi+1]
    push eax
    jmp cont
none:
    mov dword ptr [{TIER}], 0
    push esi
cont:
    push 0x65348c
    jmp {H1_BACK}
"""
SRC2 = f"""
    mov eax, dword ptr [{TIER}]
    lea eax, [eax+eax*2]
    push dword ptr [{TABLE}+eax*4]
    push dword ptr [{TABLE}+4+eax*4]
    push dword ptr [{TABLE}+8+eax*4]
    jmp {H2_BACK}
"""
H1_ORIG = bytes.fromhex("56688c346500")
H2_ORIG = bytes.fromhex("68c800000068e60000006850000000")       # F41 colours
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
def jmp(src, dst, size): return b"\xe9" + struct.pack("<i", dst - (src + 5)) + b"\x90" * (size - 5)
ks = Ks(KS_ARCH_X86, KS_MODE_32)
C1 = bytes(ks.asm(SRC1, S1)[0]); C2 = bytes(ks.asm(SRC2, S2)[0])
assert len(C1) <= S2 - S1 and len(C2) <= TABLE - S2, (len(C1), len(C2))
TAB = b"".join(struct.pack("<III", *c) for c in COLOURS)
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    a, b = off(d, H1), off(d, H2)
    if bytes(d[a:a + 6]) == jmp(H1, S1, 6):
        print(f"{fn}: F42 already applied"); continue
    if bytes(d[a:a + 6]) != H1_ORIG or bytes(d[b:b + 15]) != H2_ORIG:
        raise SystemExit(f"{fn}: needs F41 first ({d[a:a+6].hex()} / {d[b:b+15].hex()})")
    s = off(d, S1)
    assert d[s:s + 0xb0] == bytes(0xb0), "stub area not free"
    shutil.copy(fn, fn + ".before_f42")
    d[s:s + len(C1)] = C1
    d[off(d, S2):off(d, S2) + len(C2)] = C2
    d[off(d, TABLE):off(d, TABLE) + len(TAB)] = TAB
    d[a:a + 6] = jmp(H1, S1, 6)
    d[b:b + 15] = jmp(H2, S2, 15)
    open(fn, "wb").write(d)
    print(f"{fn}: F42 applied (stubs {len(C1)}+{len(C2)} bytes)")
