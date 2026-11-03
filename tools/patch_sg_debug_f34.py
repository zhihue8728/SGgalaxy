"""F34 (2026-10-25): code CHALLENGE for the anti-cheat checksum.
Server class 0xF7 [u32 nonce][u32 start dword][u32 count] -> client 0xF8 [u32 nonce][u32 answer]
answer: h = nonce; h = rol(h,5) ^ dword over .text dwords [start, start+count) (start >= 0x928EF -> 0; count 0 or past
the end -> to the end), then over the whole .dbgmov (0x800 dwords).  Server: sgs/client_ota.py challenge_answer().
Hook: 0054a1d0 (global packet switch, stdcall 2 args, ret 8) first 7 bytes -> jmp stub + 2 NOP; the stub replays
mov eax,[esp+4] / movzx edx,byte [eax] for every other type and goes on at 0054a1d7.
Stub at .dbgmov 0xeb3e70 (built with keystone, see the source in claude/ANTI_CHEAT.md), ends with the marker "SGCH34".
Verified in an x86 emulator against the server formula (tools/mptest/test65.py).
usage: python patch_sg_debug_f34.py SG_debug.exe [more exes]   (idempotent: already patched files are skipped)"""
import sys, struct, shutil
STUB = bytes.fromhex(
    "8b4424048038f774090fb61068d7a15400c3837c24080d0f82a20000009c6089c78b5f010fcb8b4f050fc98b57090fca81f9ef280900"
    "720231c9b8ef28090029c885d2740439c2760289c28d348d0010400089d8c1c005330683c6044a75f5be0030eb00b900080000c1c005"
    "330683c6044975f589c583ec608d0c24e8ef4f6fffc7042438c7640068f80000008d4c2404e87a506fff538d4c2404e860516fff558d4c"
    "2404e856516fff8d0c24e8be626fff8d0c24e826506fff83c460619db001c208005347434833340000")
VA, HOOK = 0xeb3e70, 0x54a1d0
def off(d, va):
    pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
    for i in range(n):
        nm, vs, sva, rs, ro = struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i)
        if 0x400000 + sva <= va < 0x400000 + sva + max(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit(f'{va:#x} not in the file')
for fn in sys.argv[1:]:
    d = bytearray(open(fn, 'rb').read())
    h, s = off(d, HOOK), off(d, VA)
    if d[s:s + len(STUB)] == STUB:
        print(fn, 'already F34'); continue
    assert d[h:h + 7].hex() == '8b4424040fb610', d[h:h + 7].hex()
    assert d[s:s + len(STUB)] == bytes(len(STUB)), 'stub area not free'
    shutil.copy(fn, fn + '.before_f34')
    d[s:s + len(STUB)] = STUB
    d[h] = 0xE9; struct.pack_into('<i', d, h + 1, VA - (HOOK + 5)); d[h + 5:h + 7] = b'\x90\x90'
    open(fn, 'wb').write(d); print(fn, 'patched F34')
