"""WIDE (2026-10-27, user 13:37 "宽屏显示更多地图") - EXPERIMENTAL: the client renders WIDTH x 600 instead of 800 x 600
(height unchanged; cnc-ddraw scales the wider picture to the screen).  Analysis: claude/WIDESCREEN.md.

Step 1 (13:45): frame - display mode, window, CGraph screen / clip rects, the present copy, mouse clamps, MapWnd width.
Step 1b (13:55, user: black area on the right of the menus): every UI screen is CENTRED instead of drawn at the left:
  * CWnd::Create (005ecc50) hook: a ROOT window (parent 0) created as (0, 0, 800, 600) - the desktop and the Helper
    roots, 0054b3d0 - starts at x = DX = (WIDTH - 800) / 2.  Every window is placed relative to its parent
    (abs = parent abs + rel, also in the move function 005ed3c0), so all screens, dialogs and HUD pieces move with it.
  * the field's map view MapWnd (CFieldWnd child, 0049fbd0) gets rel x = -DX and width WIDTH -> it still covers the
    whole screen width.
WIDTH must be a multiple of 10 (the 32-bit present loop copies 5 pixels per step; DX must be an integer).
usage: python patch_wide.py IN.exe OUT.exe [WIDTH=1040]"""
import sys, struct
IN, OUT = sys.argv[1], sys.argv[2]
W = int(sys.argv[3]) if len(sys.argv) > 3 else 1040
assert W % 10 == 0 and 800 <= W <= 1600, W
DX = (W - 800) // 2

def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    return [struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i) for i in range(n)]
def off(d, va):
    for _nm, vs, sva, rs, ro in sections(d):
        if 0x400000 + sva <= va < 0x400000 + sva + min(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit(f"VA {va:#x} not in any section")
I = lambda v: struct.pack("<i", v)
def rel(frm, to, n=5):                      # e9 / e8 rel32 from an instruction of length n at frm
    return I(to - (frm + n))

CAVE = 0xeb4900                             # .dbgmov, free after F42's colour table (last byte 0xeb48ec)
CAVE_CREATE = CAVE
CAVE_MAPWND = CAVE + 0x60

# CWnd::Create hook (005ecccc: test eax,eax / mov [esi+0x138],eax / jne 005ecd08 -> jmp cave)
c = bytearray()
def emit(b): c.extend(b)
emit(b"\x89\x86\x38\x01\x00\x00")                       # mov [esi+0x138], eax   (parent)
emit(b"\x85\xc0")                                       # test eax, eax
emit(b"\x0f\x85" + b"\0\0\0\0"); j_child = len(c) - 4   # jne 005ecd08
emit(b"\x83\xbe\x28\x01\x00\x00\x00")                   # cmp dword [esi+0x128], 0      x
emit(b"\x75\x00"); j1 = len(c) - 1
emit(b"\x83\xbe\x2c\x01\x00\x00\x00")                   # cmp dword [esi+0x12c], 0      y
emit(b"\x75\x00"); j2 = len(c) - 1
emit(b"\x81\xbe\x30\x01\x00\x00" + I(800))              # cmp dword [esi+0x130], 800    w
emit(b"\x75\x00"); j3 = len(c) - 1
emit(b"\x81\xbe\x34\x01\x00\x00" + I(600))              # cmp dword [esi+0x134], 600    h
emit(b"\x75\x00"); j4 = len(c) - 1
emit(b"\xc7\x86\x28\x01\x00\x00" + I(DX))               # mov dword [esi+0x128], DX
emit(b"\xc7\x86\x30\x01\x00\x00" + I(DX + 800))         # mov dword [esi+0x130], DX+800 (parent-0 rect = right edge)
done = len(c)
for j in (j1, j2, j3, j4):
    c[j] = done - (j + 1)
emit(b"\xe9" + b"\0\0\0\0")                             # jmp 005eccd6 (root path)
c[len(c) - 4:] = rel(CAVE_CREATE + len(c) - 5, 0x5eccd6)
c[j_child:j_child + 4] = rel(CAVE_CREATE + j_child - 2, 0x5ecd08, 6)
cave_create = bytes(c)
assert len(cave_create) <= 0x60
# MapWnd rel x = -DX (0049fc6b: mov [esp+0x244], ebx -> jmp cave; cave: mov dword [esp+0x244], -DX; jmp 0049fc72)
cave_map = b"\xc7\x84\x24\x44\x02\x00\x00" + I(-DX) + b"\xe9" + rel(CAVE_MAPWND + 11, 0x49fc72)
# Step 1c (13:56, user: stale pictures in the black side bands): after every present (004c0577) the side bands
# x < DX and x >= DX + 800 of the offscreen buffer (+0x5c, pitch +0x60 pixels, 16 bit) are cleared to black; whatever
# draws there (only the field's MapWnd) draws again in the next frame.
CAVE_BANDS = CAVE + 0x80
b = bytearray()
b += b"\x88\x86\x7c\x01\x00\x00"                     # mov [esi+0x17c], al   (the replaced instruction)
b += b"\x60"                                         # pushad
b += b"\x8b\x5e\x5c"                                 # mov ebx, [esi+0x5c]   buffer
b += b"\x8b\x56\x60"                                 # mov edx, [esi+0x60]   pitch (pixels)
b += b"\x01\xd2"                                     # add edx, edx
b += b"\x85\xdb"                                     # test ebx, ebx
b += b"\x74\x00"; jz = len(b) - 1
b += b"\xbd" + I(600)                                # mov ebp, 600
loop = len(b)
b += b"\x89\xdf"                                     # mov edi, ebx
b += b"\x31\xc0"                                     # xor eax, eax
b += b"\xb9" + I(DX)                                 # mov ecx, DX
b += b"\x66\xf3\xab"                                 # rep stosw
b += b"\x8d\xbb" + I((DX + 800) * 2)                 # lea edi, [ebx + (DX+800)*2]
b += b"\xb9" + I(DX)                                 # mov ecx, DX
b += b"\x66\xf3\xab"                                 # rep stosw
b += b"\x01\xd3"                                     # add ebx, edx
b += b"\x4d"                                         # dec ebp
b += b"\x75" + bytes([(loop - (len(b) + 2)) & 0xff])  # jnz loop
b[jz] = len(b) - (jz + 1)
b += b"\x61"                                         # popad
b += b"\xe9" + rel(CAVE_BANDS + len(b), 0x4c057d)    # jmp back
cave_bands = bytes(b)
assert len(cave_bands) <= 0x60

P = [
    (0x4c0c5d, b"\x68" + I(800), b"\x68" + I(W), "SetDisplayMode width"),
    (0x4c0b60, b"\x68" + I(800), b"\x68" + I(W), "CGraph screen rect (+0x38) width"),
    (0x4c0b7e, b"\x68" + I(800), b"\x68" + I(W), "CGraph clip rect (+0x48) width = offscreen surface width"),
    (0x4c04d2, b"\x3d" + I(800), b"\x3d" + I(W), "present 32-bit: columns"),
    (0x4c05c3, b"\x8d\x94\x09" + I(0x640), b"\x8d\x94\x09" + I(2 * W), "present 16-bit: row bytes (x < 0)"),
    (0x4c05e2, b"\x8d\xa9" + I(800), b"\x8d\xa9" + I(W), "present 16-bit: right edge"),
    (0x4c05f2, b"\xba" + I(0x640), b"\xba" + I(2 * W), "present 16-bit: row bytes"),
    (0x544d3e, b"\x68" + I(0x322), b"\x68" + I(W + 2), "CreateWindowEx width"),
    (0x5459b2, b"\x3d" + I(800), b"\x3d" + I(W), "mouse clamp x (1)"),
    (0x5459b9, b"\xb8" + I(799), b"\xb8" + I(W - 1), "mouse clamp x (1) max"),
    (0x545a50, b"\x81\xff" + I(800), b"\x81\xff" + I(W), "mouse clamp x (2)"),
    (0x545a58, b"\xbf" + I(799), b"\xbf" + I(W - 1), "mouse clamp x (2) max"),
    (0x49fc79, b"\xc7\x84\x24\x4c\x02\x00\x00" + I(800), b"\xc7\x84\x24\x4c\x02\x00\x00" + I(W), "field MapWnd width"),
    (0x49fc6b, b"\x89\x9c\x24\x44\x02\x00\x00", b"\xe9" + rel(0x49fc6b, CAVE_MAPWND) + b"\x90\x90", "field MapWnd x -> cave"),
    (0x5ecccc, b"\x85\xc0\x89\x86\x38\x01\x00\x00", b"\xe9" + rel(0x5ecccc, CAVE_CREATE) + b"\x90\x90\x90", "CWnd::Create -> cave (centre the roots)"),
    (CAVE_CREATE, b"\0" * len(cave_create), cave_create, "cave: root windows at x = DX"),
    (CAVE_MAPWND, b"\0" * len(cave_map), cave_map, "cave: MapWnd x = -DX"),
    (0x4c0577, b"\x88\x86\x7c\x01\x00\x00", b"\xe9" + rel(0x4c0577, CAVE_BANDS) + b"\x90", "present end -> cave (clear the side bands)"),
    (CAVE_BANDS, b"\0" * len(cave_bands), cave_bands, "cave: clear the side bands"),
]
d = bytearray(open(IN, "rb").read())
for va, old, new, what in P:
    o = off(d, va)
    if bytes(d[o:o + len(old)]) != old:
        raise SystemExit(f"unexpected bytes at {va:#x} ({what}): {d[o:o + len(old)].hex()} != {old.hex()}")
    d[o:o + len(new)] = new
    print(f"  {va:#x}  {what}")
open(OUT, "wb").write(d)
print(f"{OUT}: WIDE step 1c, width {W}, UI centred at x {DX}")
