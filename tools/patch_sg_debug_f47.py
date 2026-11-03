"""F47 BATTLE CLOCK BUFFER + LATE-COMMAND REPORT (2026-10-28, user: "packets get lost, units teleport and snap back -
can it be smoothed?").
Client clock controller 00548f00 (claude/CLIENT_CLOCK.md): every relayed command carries its execution time L; the
client keeps its clock T so that d = L - T stays between 10 ticks (brake below) and w (catch up above; w starts at 20,
+10 after each late command, -5 every (55-w)*6 s down to 20; ticks = 1/100 s).  A command that arrives with L below
the current simulation tick is LATE: the client rolls every unit back to L and re-simulates (the teleport + stop).
So any extra one-way delay above ~100 ms (a lost / resent packet, a jitter spike) is a visible jump.
F47:
 1. bigger minimum buffer: brake below d = 20 (was 10), w starts at 30 and never decays below 30 (was 20).  A command
    may now arrive ~200 ms later than usual before it is late.  Own units still move at once (the owner's client walks
    them first, 004e32a0); only the other players' / server units start their moves ~100 ms later.
 2. every late command is reported to the server: 0xF9 [u32 L][u32 tick][u32 w] (once per simulation tick), logged
    and summed per player ("late commands" in the server log) - the first real measurement of how often it happens.
Hooks:
  00548f29 'sub eax,edi / add eax,5' (5 bytes)          -> jmp STUB (report, then replays the 2 instructions)
  00549037 'cmp eax,0xa'   -> 'cmp eax,0x14'           (brake threshold)
  00548fe6 'cmp cx,0x19'   -> 'cmp cx,0x23'            (w decays only while >= 35 -> floor 30)
  .data 006a5394 w = 20    -> 30
  3. SMOOTH instead of "snap back + stop" (user 01:13 "can the snap-back be smoothed?"): the original pushes the
     clock back by the whole lateness at once (base += tick - L + 5): every unit is drawn back at time L (snap back)
     and the game stands still until real time catches up (stop).  Now only 5 ticks go back at once (like F36); the
     rest is put in PENDING and given back 1 tick every 2nd frame from the frame limiter (F46 stub tail -> FRAME
     STUB): the battle runs ~30 % slower for a moment instead of jumping back and freezing, and the buffer still
     grows by the same amount (F36 alone kept the clock at the edge -> more late commands; here it does not).
     The rolled-back simulation catches up to "now" in the same frame, so only the units the late command touched
     shift (forward, by the time it was late), nothing jumps back.  PENDING is capped at 200 ticks (the original
     ignores push-backs > 500) and cleared outside a battle.
  4. client freeze report 0xFA (frame gap >= 150 ms in a battle), see FREEZE_MS below.
Variables (page tail after .data, outside the checksum like F26/F28/F40/F42/F46): 0xEAFF64 last reported tick,
0xEAFF68 PENDING ticks, 0xEAFF6C frame parity, 0xEAFF70 previous frame time (ms).
usage: python patch_sg_debug_f47.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
HOOK, BACK, VA, LASTT = 0x548f29, 0x548f2e, 0xeb49a0, 0xEAFF64
PENDING, PARITY, FRAME_VA = 0xEAFF68, 0xEAFF6C, 0xeb4a40
F46_STUB, F46_BACK = 0xeb4940, 0x549646
GAME, BATTLE, BASE = 0x6ba7c8, 0x6ba7cc, 0x1c54
SPREAD_MAX = 200
# 4. CLIENT FREEZE report (2026-10-28, rollbacks with commands 0.3-1.6 s late although the network was fine?): the
#    frame stub measures the time since the previous frame; a frame gap >= FREEZE_MS in a battle (the client was busy:
#    loading sprites, a long re-simulation ...) is reported 0xFA [u32 gap ms][u32 tick] - the server logs it next to
#    the LATE lines, so a late command can be told apart: network / relay late (relay ACK stats) or client frozen.
PREVF, TIMEGETTIME, TICK, FREEZE_MS = 0xEAFF70, 0x64c30c, 0x25a0, 150
ORIG_HOOK = bytes.fromhex("2bc783c005")
BRAKE_AT, BRAKE_OLD, BRAKE_NEW = 0x549037, bytes.fromhex("83f80a"), bytes.fromhex("83f814")
FLOOR_AT, FLOOR_OLD, FLOOR_NEW = 0x548fe6, bytes.fromhex("6683f919"), bytes.fromhex("6683f923")
W_AT, W_OLD, W_NEW = 0x6a5394, bytes.fromhex("1400"), bytes.fromhex("1e00")
def pkt_begin(t):
    return f'''
    sub esp, 0x60
    lea ecx, [esp]
    call 0x5a8ee0
    mov dword ptr [esp], 0x64c738
    push {t}
    lea ecx, [esp+4]
    call 0x5a8f80
'''
def u32(src): return f'''
    push {src}
    lea ecx, [esp+4]
    call 0x5a9070
'''
def u16(src): return f'''
    push {src}
    lea ecx, [esp+4]
    call 0x5a9020
'''
PKT_END = '''
    lea ecx, [esp]
    call 0x5aa1e0
    lea ecx, [esp]
    call 0x5a8f50
    add esp, 0x60
'''
SRC = f"""
    pushfd
    pushad
    cmp eax, dword ptr [{LASTT:#x}]
    je skip
    mov dword ptr [{LASTT:#x}], eax
    mov ebx, edi
    mov esi, eax
    movzx ebp, word ptr [{W_AT:#x}]
""" + pkt_begin(0xF9) + u32("ebx") + u32("esi") + u32("ebp") + PKT_END + f"""
skip:
    popad
    popfd
    sub eax, edi
    add eax, 5
    cmp eax, 5
    jle keep
    sub eax, 5
    add dword ptr [{PENDING:#x}], eax
    cmp dword ptr [{PENDING:#x}], {SPREAD_MAX}
    jle capped
    mov dword ptr [{PENDING:#x}], {SPREAD_MAX}
capped:
    mov eax, 5
keep:
    jmp {BACK:#x}
"""
FRAME_SRC = f"""
    pushfd
    push eax
    push ecx
    push edx
    call dword ptr [{TIMEGETTIME:#x}]
    mov ecx, dword ptr [{PREVF:#x}]
    mov dword ptr [{PREVF:#x}], eax
    test ecx, ecx
    je pend
    sub eax, ecx
    cmp eax, {FREEZE_MS}
    jb pend
    cmp dword ptr [{BATTLE:#x}], 0
    je pend
    mov ecx, dword ptr [{GAME:#x}]
    test ecx, ecx
    je pend
    pushad
    mov ebx, eax
    mov esi, dword ptr [ecx+{TICK:#x}]
""" + pkt_begin(0xFA) + u32("ebx") + u32("esi") + PKT_END + f"""
    popad
pend:
    mov eax, dword ptr [{PENDING:#x}]
    test eax, eax
    jle out
    mov ecx, dword ptr [{BATTLE:#x}]
    test ecx, ecx
    je clr
    mov ecx, dword ptr [{GAME:#x}]
    test ecx, ecx
    je clr
    xor dword ptr [{PARITY:#x}], 1
    je out
    dec dword ptr [{PENDING:#x}]
    inc dword ptr [ecx+{BASE:#x}]
    jmp out
clr:
    mov dword ptr [{PENDING:#x}], 0
out:
    pop edx
    pop ecx
    pop eax
    popfd
    jmp {F46_BACK:#x}
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
STUB = bytes(ks.asm(SRC, VA)[0])
assert len(STUB) <= FRAME_VA - VA, len(STUB)
FSTUB = bytes(ks.asm(FRAME_SRC, FRAME_VA)[0])
assert len(FSTUB) <= 0x100, len(FSTUB)
JMP = b"\xe9" + struct.pack("<i", VA - (HOOK + 5))
def f46_tail(d):
    """offset of the F46 stub's final 'jmp 0x549646' (-> redirected to the FRAME STUB)."""
    s0 = off(d, F46_STUB)
    for i in range(0x5b, -1, -1):
        if d[s0 + i] == 0xe9 and struct.unpack_from("<i", d, s0 + i + 1)[0] == F46_BACK - (F46_STUB + i + 5):
            return s0 + i, F46_STUB + i
        if d[s0 + i] == 0xe9 and struct.unpack_from("<i", d, s0 + i + 1)[0] == FRAME_VA - (F46_STUB + i + 5):
            return s0 + i, F46_STUB + i
    raise SystemExit("F46 stub tail not found (apply F46 first)")
if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        h, s = off(d, HOOK), off(d, VA)
        b, f, w = off(d, BRAKE_AT), off(d, FLOOR_AT), off(d, W_AT)
        if bytes(d[h:h + 5]) == JMP and bytes(d[s:s + len(STUB)]) == STUB:
            print(f"{fn}: F47 already applied"); continue
        t_off, t_va = f46_tail(d)
        fs = off(d, FRAME_VA)
        assert bytes(d[h:h + 5]) == ORIG_HOOK, f"{fn}: unexpected bytes at {HOOK:#x}: {bytes(d[h:h + 5]).hex()}"
        assert bytes(d[b:b + 3]) == BRAKE_OLD and bytes(d[f:f + 4]) == FLOOR_OLD and bytes(d[w:w + 2]) == W_OLD, fn
        assert d[s:s + 0x100] == bytes(0x100), f"{fn}: stub area {VA:#x} not free"
        assert d[fs:fs + 0x100] == bytes(0x100), f"{fn}: frame stub area {FRAME_VA:#x} not free"
        shutil.copy(fn, fn + ".before_f47")
        d[s:s + len(STUB)] = STUB
        d[h:h + 5] = JMP
        d[b:b + 3] = BRAKE_NEW
        d[f:f + 4] = FLOOR_NEW
        d[w:w + 2] = W_NEW
        d[fs:fs + len(FSTUB)] = FSTUB
        d[t_off:t_off + 5] = b"\xe9" + struct.pack("<i", FRAME_VA - (t_va + 5))
        open(fn, "wb").write(d)
        print(f"{fn}: F47 applied ({len(STUB)}-byte stub at {VA:#x}; brake 20, w floor/start 30, late report 0xF9; smooth push-back via {FRAME_VA:#x})")
