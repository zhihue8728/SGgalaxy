"""F48 SGRender.dll HOOKS (2026-10-28, user: "plan / build the new drawing layer; first the UI architecture").
The exe gets three static stubs that call out through a TABLE in the .data page tail (0xEAFF80, outside the
anti-cheat hash like F26/F28/F40/F42/F46/F47); SGRender.dll fills it.  Nothing in .text changes at run time, so the
code checksum (F16 / F34) stays the release's.  Without SGRender.dll the table stays 0 and the game runs as before.
  LOADER  CGraph init 004c0bd0 'sub esp,0xac' (6 bytes): LoadLibraryA("SGRender.dll") -> GetProcAddress("SGR_Init")
          -> SGR_Init(TABLE) once (flag TABLE+0x3c), then the replayed instruction.
  PRESENT CGraph::EndFrame 004c4a60 'push esi / mov esi,ecx / mov eax,[esi+0x184]' (9 bytes, thiscall, plain ret),
          once per frame from the main loop 005490c0 while the back surface is still locked: if TABLE[1] ->
          eax = TABLE[1](CGraph); eax != 0 -> return (the DLL drew the frame); else unlock + present as before.
          (First try hooked 004c01f0: that is only the WINDOWED copy, [cg+0x31] != 0 - never runs full screen.)
  CREATE  CWnd::Create 005ecc50 'push esi / mov esi,ecx / mov byte [esi+0x156],1' (10 bytes): if TABLE[2] ->
          TABLE[2](wnd, create struct), every register (eax too) kept (the window inventory, later the new UI's window registry).
TABLE: +0 DLL version, +4 on_present, +8 on_create, +0xc..+0x38 reserved for later phases, +0x3c loader done flag.
usage: python patch_sg_debug_f48.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
LOADLIB, GETPROC = 0x64c1b0, 0x64c1ac
TABLE = 0xEAFF80
STUB_VA = 0xeb4b40
STR_VA = 0xeb4c40               # "SGRender.dll\0SGR_Init\0"
STRS = b"SGRender.dll\0SGR_Init\0"
HOOKS = {   # va: (original bytes, back address)
    "loader":  (0x4c0bd0, bytes.fromhex("81ecac000000"), 0x4c0bd6),
    "present": (0x4c4a60, bytes.fromhex("568bf18b8684010000"), 0x4c4a69),
    "create":  (0x5ecc50, bytes.fromhex("568bf1c68656010000" + "01"), 0x5ecc5a),
}
SRC = f"""
loader:
    pushad
    pushfd
    cmp dword ptr [{TABLE + 0x3c:#x}], 0
    jne l_done
    mov dword ptr [{TABLE + 0x3c:#x}], 1
    push {STR_VA:#x}
    call dword ptr [{LOADLIB:#x}]
    test eax, eax
    je l_done
    push {STR_VA + 13:#x}
    push eax
    call dword ptr [{GETPROC:#x}]
    test eax, eax
    je l_done
    push {TABLE:#x}
    call eax
    add esp, 4
l_done:
    popfd
    popad
    sub esp, 0xac
    jmp {HOOKS['loader'][2]:#x}
present:
    mov eax, dword ptr [{TABLE + 4:#x}]
    test eax, eax
    je p_orig
    push ecx
    push ecx
    call eax
    add esp, 4
    pop ecx
    test eax, eax
    je p_orig
    ret
p_orig:
    push esi
    mov esi, ecx
    mov eax, dword ptr [esi + 0x184]
    jmp {HOOKS['present'][2]:#x}
create:
    cmp dword ptr [{TABLE + 8:#x}], 0
    je c_orig
    pushad
    push dword ptr [esp + 0x24]
    push ecx
    call dword ptr [{TABLE + 8:#x}]
    add esp, 8
    popad
c_orig:
    push esi
    mov esi, ecx
    mov byte ptr [esi + 0x156], 1
    jmp {HOOKS['create'][2]:#x}
"""
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
enc, _ = ks.asm(SRC, STUB_VA)
STUB = bytes(enc)
assert len(STUB) <= 0x100, len(STUB)
def label_va(name):
    # assemble up to the label to find its address
    part = SRC.split(name + ":")[0]
    return STUB_VA + len(bytes(ks.asm(part, STUB_VA)[0])) if part.strip() else STUB_VA
ENTRY = {k: label_va(k) for k in HOOKS}
def jmp(at, to, n):
    return b"\xe9" + struct.pack("<i", to - (at + 5)) + b"\x90" * (n - 5)
if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = off(d, STUB_VA)
        if bytes(d[s:s + len(STUB)]) == STUB and bytes(d[off(d, STR_VA):off(d, STR_VA) + len(STRS)]) == STRS:
            print(f"{fn}: F48 already applied"); continue
        assert d[s:s + 0x100] == bytes(0x100), f"{fn}: stub area {STUB_VA:#x} not free"
        so = off(d, STR_VA)
        assert d[so:so + 0x20] == bytes(0x20), f"{fn}: string area {STR_VA:#x} not free"
        for k, (va, orig, back) in HOOKS.items():
            o = off(d, va)
            assert bytes(d[o:o + len(orig)]) == orig, f"{fn}: unexpected bytes at {va:#x} ({k}): {bytes(d[o:o + len(orig)]).hex()}"
        shutil.copy(fn, fn + ".before_f48")
        d[s:s + len(STUB)] = STUB
        d[so:so + len(STRS)] = STRS
        for k, (va, orig, back) in HOOKS.items():
            o = off(d, va)
            d[o:o + len(orig)] = jmp(va, ENTRY[k], len(orig))
        open(fn, "wb").write(d)
        print(f"{fn}: F48 applied ({len(STUB)}-byte stubs at {STUB_VA:#x}: " + ", ".join(f"{k} {v:#x}" for k, v in ENTRY.items()) + ")")
