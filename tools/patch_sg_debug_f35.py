"""F35 (2026-10-26): Chinese input in the multi-line edit box (BOARD / MAIL post window; user: cannot type Chinese there).
F22 only covered the single-line edit class (char handler 0043f470).  The multi-line class (vtable 0064f724) takes
WM_CHAR in 00443a30 and rejects everything outside 0x20..0x7e at 00443ad5/00443ade.  A DBCS char arrives as two WM_CHARs:
lead byte (>=0x80) is kept in STASH (0x00EAFF04, free page tail after .data), the trail byte (>=0x40) inserts both bytes with
the box's own routine 00442ec0 (same call sequence as the 'commit 2 bytes' branch 00443c1e).  Everything else unchanged.
Hook: 00443ad5 (9 bytes: cmp edi,0x20 ; jb 00443d01) -> jmp stub + 4 NOP.  Stub at .dbgmov 0xeb4400.
usage: python patch_sg_debug_f35.py SG_debug.exe [more exes]   (idempotent; needs F34 applied first or not - independent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
VA, HOOK, STASH = 0xeb4400, 0x443ad5, 0xeaff04
SRC = f"""
    cmp edi, 0x80
    jae hi
    cmp byte ptr [{STASH}], 0
    je orig
    cmp edi, 0x40
    jb clr
    jmp trail
hi:
    cmp edi, 0xff
    ja orig
    cmp byte ptr [{STASH}], 0
    jne trail
    test byte ptr [esi+0x2bc], 0x10
    jne rt
    mov eax, edi
    mov byte ptr [{STASH}], al
    jmp rt
trail:
    mov al, byte ptr [{STASH}]
    mov byte ptr [{STASH}], 0
    test byte ptr [esi+0x2bc], 0x10
    jne rt
    mov byte ptr [esp+0x18], al
    mov eax, edi
    mov byte ptr [esp+0x19], al
    mov ecx, esi
    call 0x442bc0
    push 1
    push 2
    lea edx, [esp+0x20]
    push edx
    mov ecx, esi
    call 0x442ec0
    mov eax, dword ptr [esi+0x2f8]
    mov ecx, dword ptr [esi+0x2fc]
    mov dword ptr [esi+0x308], eax
    mov dword ptr [esi+0x30c], ecx
    mov dword ptr [esi+0x310], eax
    mov dword ptr [esi+0x314], ecx
    mov byte ptr [esi+0x318], 0
rt:
    push 0x443d01
    ret
clr:
    mov byte ptr [{STASH}], 0
orig:
    mov byte ptr [{STASH}], 0
    cmp edi, 0x20
    jb rt
    cmp edi, 0x7e
    ja rt
    mov al, 0x10
    push 0x443ae7
    ret
"""
STUB = bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(SRC, VA)[0])
def off(d, va):
    pe = struct.unpack_from('<I', d, 0x3c)[0]; n = struct.unpack_from('<H', d, pe + 6)[0]; opt = struct.unpack_from('<H', d, pe + 20)[0]
    for i in range(n):
        nm, vs, sva, rs, ro = struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i)
        if 0x400000 + sva <= va < 0x400000 + sva + max(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit(f'{va:#x} not in the file')
if __name__ == '__main__':
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, 'rb').read())
        h, s = off(d, HOOK), off(d, VA)
        if d[s:s + len(STUB)] == STUB:
            print(fn, 'already F35'); continue
        assert d[h:h + 9].hex() == '83ff200f8223020000', d[h:h + 9].hex()
        assert d[s:s + len(STUB) + 8] == bytes(len(STUB) + 8), 'stub area not free'
        shutil.copy(fn, fn + '.before_f35')
        d[s:s + len(STUB)] = STUB
        d[h] = 0xE9; struct.pack_into('<i', d, h + 1, VA - (HOOK + 5)); d[h + 5:h + 9] = b'\x90' * 4
        open(fn, 'wb').write(d); print(fn, 'patched F35', len(STUB), 'bytes')
