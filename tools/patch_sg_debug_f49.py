"""F49 WIDESCREEN FRAME (2026-10-28, user: "看到更多地图, 支持宽屏"; phase 1 of claude/RENDER_UI_REDESIGN_PLAN.md).
Needs F48 (SGRender.dll call-out TABLE 0xEAFF80).  The client draws a W x 600 frame instead of 800 x 600; W comes
from SGRender.dll (TABLE+0x10, from the monitor's aspect ratio).  Without the DLL (or W = 0) every stub uses 800 and
DX = 0, i.e. the game behaves exactly as before.  cnc-ddraw scales the W x 600 frame to the screen.

DESIGN - the game keeps its 800 x 600 world ("800-space"): every window keeps the position it has always had.  The
frame shows 800-space x = -DX .. 800+DX (DX = (W-800)/2), so every screen and dialog is centred automatically, and
only the field's map view is made wider (the DLL creates MapWnd at x = -DX, width W).  Done in 5 places:
  1. SetViewport (00438100) moves every viewport DX to the right (all drawing goes through it);
  2. the mouse is translated back (x_screen - DX) after the clamp to 0..W-1;
  3. the "whole screen" clip rects (frame roots, window tree default, cursor, fade) are -DX .. 800+DX; the mouse
     cursor / drag icon keep their viewport (the main window: origin x 0 = screen DX) with the clip widened to
     -DX .. 800+DX, so the cursor can be drawn over the side bands;
  4. the main window (TC Main) and the field window (Field) count as -DX .. 800+DX for the window tree's clipping
     of their children and for mouse hit tests (their children: the wide map, the quick menu at the right edge);
  5. field code: the quick menu's slide edges (800 -> 800+DX; its "map right + map left <= 0x24b" test needs no
     change: the map's left is -DX), terrain columns (800+32 -> W+32), the right small unit cards (+DX), and the
     fog of war: its draw (00499d90) and visibility test (004b6120) call the DLL, which keeps a W+32 wide copy of
     the exe's 832-pixel fog window (same softening; the exe's window buffer cannot grow inside its object).
(First try 10-28 15:3x moved the windows instead - "centre the 800-wide screens inside a full-frame main window";
controls that draw as if their parent were at x 0 (the strategic map's frame) ended up DX off.  10-27's
tools/patch_wide.py moved windows too; its "the login box cannot be clicked" = the mouse cursor was drawn in the main
window's viewport, DX away from the real mouse.)

getw: loads SGRender.dll once if not done yet (same flag TABLE+0x3c as F48's loader - the CGraph constructor and
CreateWindowEx run BEFORE F48's loader in CGraph::Init), eax = W (800 when TABLE+0x10 is 0 or outside 800..2000,
made even), also written to TABLE+0x14.  getdx: eax = DX.  getr: eax = 800 + DX (the frame's right edge in 800-space).
TABLE: +0xc on_frame(CGraph, app), +0x10 W (DLL), +0x14 W in use, +0x24 TC Main, +0x28 Field (the DLL stores them at
creation), +0x2c fog_draw(MapWnd), +0x30 fog_vis(fog, x, y) (both only set when W > 800).
usage: python patch_sg_debug_f49.py SG.exe [more exes]   (F48 first; idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
LOADLIB, GETPROC = 0x64c1b0, 0x64c1ac
TABLE = T = 0xEAFF80
STR_VA = 0xeb4c40               # F48's "SGRender.dll\0SGR_Init\0"
STUB_VA = 0xeb3f40              # free up to 0xeb4400 (.dbgmov, inside the F34 challenge range = static code only)
STUB_END = 0xeb4400
SITES = {   # name: (va, original bytes, back address)
    # the frame: W x 600
    "cw":      (0x544d3e, "6822030000", 0x544d43),                       # CreateWindowEx width 0x322 -> W+2
    "ctor1":   (0x4c0b60, "6820030000", 0x4c0b65),                       # CGraph screen rect +0x38
    "ctor2":   (0x4c0b7e, "6820030000", 0x4c0b83),                       # CGraph clip rect +0x48 = back surface
    "mode":    (0x4c0c5d, "6820030000", 0x4c0c62),                       # SetDisplayMode(800, 600, 16)
    "win32":   (0x4c04d2, "3d200300000f8c1afeffff", 0x4c04dd),           # windowed present 32-bit: columns
    "win16a":  (0x4c05c3, "8d940940060000", 0x4c05ca),                   # windowed present 16-bit: row bytes
    "win16b":  (0x4c05e2, "8da920030000", 0x4c05e8),                     #   right edge
    "win16c":  (0x4c05f2, "ba40060000", 0x4c05f7),                       #   row bytes
    "clear":   (0x4bae00, "6840060000", 0x4bae05),                       # ClearPrimary: row bytes
    "clipc":   (0x54ba1e, "681e030000", 0x54ba23),                       # ClipCursor right 798 -> W-2
    "frame":   (0x54911a, "8b860c0c0000", 0x549120),                     # frame begin -> TABLE[3] on_frame
    # 1. viewports
    "vp":      (0x438100, "8b4424048b10", 0x438106),                     # SetViewport(rect, parent clip)
    # 2. the mouse
    "mouse1":  (0x5459b2, "3d200300007c05b81f030000", 0x5459be),
    "mouse2":  (0x545a50, "81ff200300007c05bf1f030000", 0x545a5d),
    # 3. whole-screen clip rects (0,0,800,600) -> (-DX,0,800+DX,600)
    "frclip":  (0x5490f0, "895c2424895c2428c744242c20030000896c2430", 0x549104),
    "trclip":  (0x5487d5, "897c240c897c2410c744241420030000c744241858020000", 0x5487ed),
    "curclip": (0x549241, "895c2418895c241cc744242020030000896c2424", 0x549255),
    "curfix":  (0x549255, "e8a6eeeeff", 0x54925a),                       # cursor viewport: clip -DX .. 800+DX
    "fade":    (0x4c499e, "c744241020030000", 0x4c49a6),                 # FadeScreen rect
    # 4. TC Main / Field = -DX .. 800+DX for child clipping and mouse hit tests
    "pclip":   (0x5487ff, "8b86380100003bc7", 0x548807),
    "hit":     (0x545867, "8b87240c0000398618010000" "0f8ffd000000" "3b86200100000f8df1000000", 0x545885),
    # 5. field code: quick menu (right, 0xd5 wide) slide edges 004a4a50, terrain, right small unit cards
    "qm2":     (0x4a4a87, "81b91801000020030000751d", 0x4a4a93),
    "qm3":     (0x4a4abb, "81ff5d0200007d05bf5d020000", 0x4a4ac8),
    "qm4":     (0x4a4b49, "81b9180100000e030000751b", 0x4a4b55),
    "qm5":     (0x4a4b61, "6820030000", 0x4a4b66),
    "qm6":     (0x4a4b7c, "3d200300007dbb", 0x4a4b83),
    "qm7":     (0x4a4b86, "81ff200300007e05bf20030000", 0x4a4b93),
    "qm8":     (0x4a4bd8, "81ff200300000f8c3fffffff", 0x4a4be4),
    "terr":    (0x499d79, "81fd400300007cbf", 0x499d81),
    "fogdraw": (0x499d90, "83ec188b8134050000", 0x499d99),               # fog of war draw (MapWnd) -> TABLE[11]
    "fogvis":  (0x4b6120, "8b54240485d2", 0x4b6126),                     # fog visibility (fog, x, y) -> TABLE[12]
    "card":    (0x4afa94, "b8ab020000", 0x4afa99),
}
B = {k: v[2] for k, v in SITES.items()}
SRC = f"""
load_once:
    pushad
    pushfd
    cmp dword ptr [{T + 0x3c:#x}], 0
    jne lo_done
    mov dword ptr [{T + 0x3c:#x}], 1
    push {STR_VA:#x}
    call dword ptr [{LOADLIB:#x}]
    test eax, eax
    je lo_done
    push {STR_VA + 13:#x}
    push eax
    call dword ptr [{GETPROC:#x}]
    test eax, eax
    je lo_done
    push {T:#x}
    call eax
    add esp, 4
lo_done:
    popfd
    popad
    ret
getw:
    call load_once
    mov eax, dword ptr [{T + 0x10:#x}]
    cmp eax, 800
    jl gw_def
    cmp eax, 2000
    jle gw_ok
gw_def:
    mov eax, 800
gw_ok:
    and eax, 0xfffffffe
    mov dword ptr [{T + 0x14:#x}], eax
    ret
getdx:
    call getw
    sub eax, 800
    sar eax, 1
    ret
getr:
    call getdx
    add eax, 800
    ret
cw:
    push eax
    call getw
    add eax, 2
    xchg eax, dword ptr [esp]
    jmp {B['cw']:#x}
ctor1:
    push eax
    call getw
    xchg eax, dword ptr [esp]
    jmp {B['ctor1']:#x}
ctor2:
    push eax
    call getw
    xchg eax, dword ptr [esp]
    jmp {B['ctor2']:#x}
mode:
    push eax
    call getw
    xchg eax, dword ptr [esp]
    jmp {B['mode']:#x}
win32:
    push eax
    call getw
    xchg eax, dword ptr [esp]
    cmp eax, dword ptr [esp]
    lea esp, [esp + 4]
    jl 0x4c02f7
    jmp {B['win32']:#x}
win16a:
    push eax
    call getw
    lea edx, [ecx + ecx]
    lea edx, [edx + eax * 2]
    pop eax
    jmp {B['win16a']:#x}
win16b:
    push eax
    call getw
    lea ebp, [ecx + eax]
    pop eax
    jmp {B['win16b']:#x}
win16c:
    push eax
    call getw
    lea edx, [eax + eax]
    pop eax
    jmp {B['win16c']:#x}
clear:
    push eax
    call getw
    add eax, eax
    xchg eax, dword ptr [esp]
    jmp {B['clear']:#x}
clipc:
    push eax
    call getw
    sub eax, 2
    xchg eax, dword ptr [esp]
    jmp {B['clipc']:#x}
frame:
    mov eax, dword ptr [{T + 0xc:#x}]
    test eax, eax
    je fr_orig
    pushad
    push esi
    push edi
    call eax
    add esp, 8
    popad
fr_orig:
    mov eax, dword ptr [esi + 0xc0c]
    jmp {B['frame']:#x}
vp:
    call getdx
    test eax, eax
    jne vp_shift
vp_orig:
    mov eax, dword ptr [esp + 4]
    mov edx, dword ptr [eax]
    jmp {B['vp']:#x}
vp_shift:
    push ebx
    push esi
    sub esp, 32
    mov esi, dword ptr [esp + 44]
    mov ebx, dword ptr [esi]
    add ebx, eax
    mov dword ptr [esp], ebx
    mov ebx, dword ptr [esi + 4]
    mov dword ptr [esp + 4], ebx
    mov ebx, dword ptr [esi + 8]
    add ebx, eax
    mov dword ptr [esp + 8], ebx
    mov ebx, dword ptr [esi + 12]
    mov dword ptr [esp + 12], ebx
    mov esi, dword ptr [esp + 48]
    mov ebx, dword ptr [esi]
    add ebx, eax
    mov dword ptr [esp + 16], ebx
    mov ebx, dword ptr [esi + 4]
    mov dword ptr [esp + 20], ebx
    mov ebx, dword ptr [esi + 8]
    add ebx, eax
    mov dword ptr [esp + 24], ebx
    mov ebx, dword ptr [esi + 12]
    mov dword ptr [esp + 28], ebx
    lea ebx, [esp + 16]
    push ebx
    lea ebx, [esp + 4]
    push ebx
    call vp_orig
    add esp, 32
    pop esi
    pop ebx
    ret 8
mouse1:
    push eax
    call getw
    cmp dword ptr [esp], eax
    jl m1_keep
    dec eax
    mov dword ptr [esp], eax
m1_keep:
    call getdx
    sub dword ptr [esp], eax
    pop eax
    jmp {B['mouse1']:#x}
mouse2:
    push eax
    call getw
    cmp edi, eax
    jl m2_keep
    lea edi, [eax - 1]
m2_keep:
    call getdx
    sub edi, eax
    pop eax
    jmp {B['mouse2']:#x}
frclip:
    push eax
    call getdx
    neg eax
    mov dword ptr [esp + 0x28], eax
    mov dword ptr [esp + 0x2c], ebx
    call getr
    mov dword ptr [esp + 0x30], eax
    mov dword ptr [esp + 0x34], ebp
    pop eax
    jmp {B['frclip']:#x}
trclip:
    pushfd
    push eax
    call getdx
    neg eax
    mov dword ptr [esp + 0x14], eax
    mov dword ptr [esp + 0x18], edi
    call getr
    mov dword ptr [esp + 0x1c], eax
    mov dword ptr [esp + 0x20], 600
    pop eax
    popfd
    jmp {B['trclip']:#x}
curclip:
    push eax
    call getdx
    neg eax
    mov dword ptr [esp + 0x1c], eax
    mov dword ptr [esp + 0x20], ebx
    call getr
    mov dword ptr [esp + 0x24], eax
    mov dword ptr [esp + 0x28], ebp
    pop eax
    jmp {B['curclip']:#x}
curfix:
    call 0x438100
    push eax
    call getdx
    mov ecx, dword ptr [0x6ba7d0]
    neg eax
    mov dword ptr [ecx + 0x74], eax
    neg eax
    add eax, 800
    mov dword ptr [ecx + 0x7c], eax
    pop eax
    jmp {B['curfix']:#x}
fade:
    push eax
    call getdx
    neg eax
    mov dword ptr [esp + 0xc], eax
    call getr
    mov dword ptr [esp + 0x14], eax
    pop eax
    jmp {B['fade']:#x}
pclip:
    mov eax, dword ptr [esi + 0x138]
    test eax, eax
    je pc_orig
    cmp eax, dword ptr [{T + 0x24:#x}]
    je 0x548831
    cmp eax, dword ptr [{T + 0x28:#x}]
    je 0x548831
pc_orig:
    cmp eax, edi
    jmp {B['pclip']:#x}
hit:
    mov eax, dword ptr [edi + 0xc24]
    cmp esi, dword ptr [{T + 0x24:#x}]
    je hit_in
    cmp esi, dword ptr [{T + 0x28:#x}]
    je hit_in
    cmp dword ptr [esi + 0x118], eax
    jg 0x545976
    cmp eax, dword ptr [esi + 0x120]
    jge 0x545976
hit_in:
    jmp {B['hit']:#x}
qm2:
    push eax
    call getr
    cmp dword ptr [ecx + 0x118], eax
    pop eax
    jne 0x4a4ab0
    jmp {B['qm2']:#x}
qm3:
    push eax
    call getdx
    add eax, 0x25d
    cmp edi, eax
    jge qm3_k
    mov edi, eax
qm3_k:
    pop eax
    jmp {B['qm3']:#x}
qm4:
    push eax
    call getdx
    add eax, 0x30e
    cmp dword ptr [ecx + 0x118], eax
    pop eax
    jne 0x4a4b70
    jmp {B['qm4']:#x}
qm5:
    push eax
    call getr
    xchg eax, dword ptr [esp]
    jmp {B['qm5']:#x}
qm6:
    push eax
    call getr
    xchg eax, dword ptr [esp]
    cmp eax, dword ptr [esp]
    lea esp, [esp + 4]
    jge 0x4a4b3e
    jmp {B['qm6']:#x}
qm7:
    push eax
    call getr
    cmp edi, eax
    jle qm7_k
    mov edi, eax
qm7_k:
    pop eax
    jmp {B['qm7']:#x}
qm8:
    push eax
    call getr
    cmp edi, eax
    pop eax
    jl 0x4a4b23
    jmp {B['qm8']:#x}
terr:
    push eax
    call getw
    add eax, 0x20
    cmp ebp, eax
    pop eax
    jl 0x499d40
    jmp {B['terr']:#x}
fogdraw:
    mov eax, dword ptr [{T + 0x2c:#x}]
    test eax, eax
    je fd_orig
    push ecx
    call eax
    add esp, 4
    ret
fd_orig:
    sub esp, 0x18
    mov eax, dword ptr [ecx + 0x534]
    jmp {B['fogdraw']:#x}
fogvis:
    mov eax, dword ptr [{T + 0x30:#x}]
    test eax, eax
    je fv_orig
    push dword ptr [esp + 8]
    push dword ptr [esp + 8]
    push ecx
    call eax
    add esp, 12
    ret 8
fv_orig:
    mov edx, dword ptr [esp + 4]
    test edx, edx
    jmp {B['fogvis']:#x}
card:
    call getdx
    add eax, 0x2ab
    jmp {B['card']:#x}
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, STUB_VA)[0])
assert STUB_VA + len(STUB) <= STUB_END, hex(len(STUB))
def label_va(name):
    part = SRC.split("\n" + name + ":")[0]
    return STUB_VA + len(bytes(ks.asm(part, STUB_VA)[0]))
ENTRY = {k: label_va(k) for k in SITES}
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
def jmp(at, to, n):
    return b"\xe9" + struct.pack("<i", to - (at + 5)) + b"\x90" * (n - 5)
if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = off(d, STUB_VA)
        if bytes(d[s:s + len(STUB)]) == STUB:
            print(f"{fn}: F49 already applied"); continue
        assert bytes(d[off(d, STR_VA):off(d, STR_VA) + 22]) == b"SGRender.dll\0SGR_Init\0", f"{fn}: apply F48 first"
        assert d[s:s + (STUB_END - STUB_VA)] == bytes(STUB_END - STUB_VA), f"{fn}: stub area not free"
        for k, (va, orig, back) in SITES.items():
            o = off(d, va)
            n = len(orig) // 2
            assert va + n == back, (k, hex(va + n), hex(back))
            assert bytes(d[o:o + n]).hex() == orig, f"{fn}: unexpected bytes at {va:#x} ({k}): {bytes(d[o:o + n]).hex()}"
        shutil.copy(fn, fn + ".before_f49")
        d[s:s + len(STUB)] = STUB
        for k, (va, orig, back) in SITES.items():
            o = off(d, va)
            d[o:o + len(orig) // 2] = jmp(va, ENTRY[k], len(orig) // 2)
        open(fn, "wb").write(d)
        print(f"{fn}: F49 applied ({len(STUB)}-byte stubs at {STUB_VA:#x}, {len(SITES)} sites)")
