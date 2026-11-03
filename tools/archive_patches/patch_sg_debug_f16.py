#!/usr/bin/env python3
"""SG.exe 1.8.5 MOVEMENT DEBUG patch: the client reports what it does when the hero tries to change province.
usage: patch_sg_debug.py SG.exe SG_debug.exe
New client packets (the server logs them as 'CLIENT DEBUG'):
  0xF1 strategic-map path search (right-click / FIND PATH, 005eac60 after the BFS 005ea8b0):
       [u32 target][u32 start][u8 found][u32 ctx map 0x29bd8][u32 n records in the planet portal list]
       [u32 n type-1 records whose source == start][u32 first source][u32 last source]
  0xF2 hero stands on a field portal (004d17c0, before the confirm dialog):
       [u32 portal index][u32 type][u32 source][u32 target][u8 flag +8][u32 ctx map]
  FOG: a dead unit (simulated HP 0) gives no sight any more (fog returns at once)
  ALIEN CHASE: a server alien whose target is out of weapon range walks toward it instead of firing blanks
  ALIEN DEATH: every client reports lump 0x1e [uid] when a server alien (uid 50001..69999) reaches 0 HP
  0xF3 portal accepted -> precondition 004c6900 (hero has units) result: [u8 ok][u32 ctx map]
"""
import struct, sys
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
ib = struct.unpack_from('<I', d, pe + 52)[0]
sec0 = pe + 24 + opt
secs = [struct.unpack_from('<8sIIII', d, sec0 + 40 * i) for i in range(nsec)]
assert nsec == 4 and secs[-1][0].rstrip(b'\0') == b'.rsrc', 'unexpected SG.exe (already patched?)'
def off(va):
    for name, vs, vaa, rs, ra in secs:
        if vaa <= va - ib < vaa + max(vs, rs):
            return va - ib - vaa + ra
    raise ValueError(hex(va))
def expect(va, hx):
    got = bytes(d[off(va):off(va) + len(bytes.fromhex(hx))])
    assert got == bytes.fromhex(hx), f'{va:#x}: {got.hex()} != {hx}'
expect(0x5eace4, 'a1d8a76b00')            # mov eax,[0x6ba7d8]
expect(0x4d19ba, '807e08008bf8')          # cmp byte [esi+8],0 ; mov edi,eax
expect(0x4d0bdb, '84c00f8479040000')      # test al,al ; je 0x4d105c
expect(0x4cc226, '807e08000f8453100000')  # unit think: cmp byte [esi+8],0 ; je 0x4cd283
expect(0x48ea69, 'f64104010f84f5000000')  # fog: test byte [ecx+4],1 ; je 0x48eb68
expect(0x4e94c3, '0fb786a6e80000')         # unit tick: movzx eax, word [esi+0xe8a6]
expect(0x5d5d67, '8d8e046e0000e84e3fe7ff')  # lab upgrade ok: lea ecx,[esi+0x6e04] ; call 0x449cc0
expect(0x48f340, '83ec145355')              # POC tick: sub esp,0x14 ; push ebx ; push ebp
expect(0x56001e, '8a8659040000')            # Ctrl+F6 TK toggle: mov al,[esi+0x459]
expect(0x4e56dd, '8b178b4214')            # attack: mov edx,[edi] ; mov eax,[edx+0x14]
expect(0x4ad42d, '807e6900740e')          # PUT own unit: cmp byte [esi+0x69],0 ; je 0x4ad441
expect(0x45585c, '8d54240852')            # Lab engine row: lea edx,[esp+8] ; push edx
expect(0x5d4864, '8b4c24106a00')          # Lab resources: mov ecx,[esp+0x10] ; push 0 (cost digits style)
expect(0x52b08a, '0f84b7000000')          # Lab equip page resources: je 0x52b147 (no item selected -> no cost)
expect(0x52b127, '8b4c24146a00')          # Lab equip page: mov ecx,[esp+0x14] ; push 0 (cost digits style)
expect(0x52afad, '833d0c7bd60000895424')   # Lab equip page: cmp [0xd67b0c],0 ; mov [esp+0x14],edx
expect(0x49f061, 'e8ea9e1000')            # keep-alive 0x58 sent: call 0x5a8f50 (packet dtor) - only on the send path

SEC_VA = ib + 0xab3000; SEC_SIZE = 0x2000; CODE_VA = SEC_VA + 0x100

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
def u8(src): return f'''
    push {src}
    lea ecx, [esp+4]
    call 0x5a8fc0
'''
PKT_END = '''
    lea ecx, [esp]
    call 0x5aa1e0
    lea ecx, [esp]
    call 0x5a8f50
    add esp, 0x60
'''
# --- F1: path search result.  Entry esp = frame of 005eac60 at 005eace4: target [esp+0x60], start [esp+0x64], found [esp+0x70]
f1 = '''
    pushfd
    pushad
    mov ebx, dword ptr [esp+0x84]
    mov ebp, dword ptr [esp+0x88]
    movzx edi, byte ptr [esp+0x94]
    sub esp, 0x20
    mov dword ptr [esp], 0
    mov dword ptr [esp+4], 0
    mov dword ptr [esp+8], 0
    mov dword ptr [esp+12], 0
    mov esi, dword ptr [0xc34618]
    mov ecx, dword ptr [esi+0x20]
    mov edx, dword ptr [esi+0x24]
    test ecx, ecx
    je f1_done
    mov eax, dword ptr [ecx+4]
    mov dword ptr [esp+8], eax
f1_loop:
    cmp ecx, edx
    jae f1_done
    inc dword ptr [esp]
    mov eax, dword ptr [ecx+4]
    mov dword ptr [esp+12], eax
    cmp dword ptr [ecx], 1
    jne f1_next
    cmp eax, ebp
    jne f1_next
    inc dword ptr [esp+4]
f1_next:
    add ecx, 0x2c
    jmp f1_loop
f1_done:
    mov eax, dword ptr [0x6ba7cc]
    mov eax, dword ptr [eax+0x29bd8]
    mov dword ptr [esp+16], eax
''' + pkt_begin(0xF1) + u32('ebx') + u32('ebp') + u8('edi') + \
    u32('dword ptr [esp+0x70]') + u32('dword ptr [esp+0x60]') + u32('dword ptr [esp+0x64]') + \
    u32('dword ptr [esp+0x68]') + u32('dword ptr [esp+0x6c]') + PKT_END + '''
    add esp, 0x20
    popad
    popfd
    mov eax, dword ptr [0x6ba7d8]
    jmp 0x5eace9
'''
# --- F2: hero on a portal.  eax = portal record (may be 0), ebx = index, esi = this
f2 = '''
    pushfd
    pushad
    mov edi, eax
    sub esp, 0x20
    mov dword ptr [esp], 0
    mov dword ptr [esp+4], 0
    mov dword ptr [esp+8], 0
    test edi, edi
    je f2_nr
    mov eax, dword ptr [edi]
    mov dword ptr [esp], eax
    mov eax, dword ptr [edi+4]
    mov dword ptr [esp+4], eax
    mov eax, dword ptr [edi+0x1c]
    mov dword ptr [esp+8], eax
f2_nr:
    movzx eax, byte ptr [esi+8]
    mov dword ptr [esp+12], eax
    mov eax, dword ptr [0x6ba7cc]
    mov eax, dword ptr [eax+0x29bd8]
    mov dword ptr [esp+16], eax
''' + pkt_begin(0xF2) + u32('ebx') + u32('dword ptr [esp+0x60]') + u32('dword ptr [esp+0x64]') + \
    u32('dword ptr [esp+0x68]') + u8('dword ptr [esp+0x6c]') + u32('dword ptr [esp+0x70]') + PKT_END + '''
    add esp, 0x20
    popad
    popfd
    cmp byte ptr [esi+8], 0
    mov edi, eax
    jmp 0x4d19c0
'''
# --- F3: 004c6900 result in al
f3 = '''
    pushfd
    pushad
    movzx edi, al
    mov eax, dword ptr [0x6ba7cc]
    mov ebp, dword ptr [eax+0x29bd8]
''' + pkt_begin(0xF3) + u8('edi') + u32('ebp') + PKT_END + '''
    popad
    popfd
    test al, al
    je 0x4d105c
    jmp 0x4d0be3
'''
# --- F4 ALIEN DEATH REPORT (2026-10-21): the unit think 004cc220 only runs for units this client controls
# ([unit+8] != 0), and only that path reports a death (jmp 004de930 -> lump 0x1e [uid] once per unit).  Server
# aliens (uid 50001..69999, owner "Alien") are controlled by nobody, so nobody reported their death and the server
# had to guess the HP.  Now every client reports an alien whose SIMULATED HP reached 0 (lock-step: all clients agree,
# the server takes the first report).  Entry: 004cc226, esp = after `sub esp,0x2c ; push esi`.
f4 = """
    cmp byte ptr [esi+8], 0
    jne f4_local
    mov eax, dword ptr [esi+4]
    cmp eax, 50001
    jb f4_skip
    cmp eax, 70000
    jae f4_skip
    movzx eax, word ptr [esi+0xa866]
    mov ecx, dword ptr [esi+eax*4+0xa464]
    cmp dword ptr [ecx+4], 0
    jne f4_skip
    mov ecx, esi
    pop esi
    add esp, 0x2c
    jmp 0x4de930
f4_skip:
    jmp 0x4cd283
f4_local:
    jmp 0x4cc230
"""
# --- F5 FOG AFTER DEATH (2026-10-21, user: the fog should come back at once when a unit dies): the fog painter
# 0048ea50 still gave a dead own unit its sight radius until its body was removed; now a unit with simulated HP 0
# reveals nothing.  Entry 0048ea69: esi = unit, ecx = its flag history record.
f5 = """
    test byte ptr [ecx+4], 1
    je 0x48eb68
    push eax
    movzx eax, word ptr [esi+0xa866]
    mov eax, dword ptr [esi+eax*4+0xa464]
    cmp dword ptr [eax+4], 0
    pop eax
    jle 0x48eb68
    jmp 0x48ea73
"""
# --- F6 ALIEN CHASE (2026-10-21): an attack order (lump 0x2b -> command 1, 004d6e30) puts a unit straight into the
# fire state 5 whatever the distance; 004e55b0 then plays the attack animation every cooldown but 004d0420 gives
# 0 damage when the target is farther than weapon range + target radius.  Player units never notice because their
# OWNER's think (004cc220, local units only) walks them into range first; server aliens have no owner.  Now in the
# deterministic attack tick (004e55b0 at 004e56dd: edi = attacker, esi = live target), an alien (uid 50001..69999)
# whose target is out of range does not fire: it re-plans a path to the target every 32 ticks (004c9a50) and takes
# one movement step (004e42b0), staying in the attack state; once in range it fires as before.
f6 = """
    mov eax, dword ptr [edi+4]
    cmp eax, 50001
    jb f6_orig
    cmp eax, 70000
    jae f6_orig
    mov edx, dword ptr [esi]
    mov ecx, esi
    call dword ptr [edx+0x14]
    mov ebx, dword ptr [eax]
    mov ebp, dword ptr [eax+4]
    cmp byte ptr [esi+8], 2
    jne f6_gr
    mov ecx, dword ptr [edi+0x144]
    jmp f6_rad
f6_gr:
    mov ecx, dword ptr [edi+0x138]
f6_rad:
    movzx edx, word ptr [esi+0xf0ae]
    mov edx, dword ptr [esi+edx*4+0xecac]
    add ecx, dword ptr [edx+4]
    push ecx
    push ebp
    push ebx
    mov edx, dword ptr [edi]
    mov ecx, edi
    call dword ptr [edx+0x14]
    push dword ptr [eax+4]
    push dword ptr [eax]
    call 0x413ac0
    add esp, 0x14
    test al, al
    jne f6_orig
    mov eax, dword ptr [0x6ba7c8]
    mov eax, dword ptr [eax+0x25a0]
    add eax, dword ptr [edi+4]
    and eax, 31
    jne f6_step
    push 0
    push ebp
    push ebx
    mov ecx, edi
    call 0x4c9a50
f6_step:
    mov ecx, edi
    call 0x4e42b0
    movzx eax, word ptr [edi+0xac6a]
    mov eax, dword ptr [edi+eax*4+0xa868]
    mov eax, dword ptr [eax+4]
    cmp eax, 5
    je f6_done
    cmp eax, 4
    je f6_done
    push 5
    mov ecx, edi
    call 0x4cfc00
f6_done:
    jmp 0x4e5b98
f6_orig:
    mov ecx, edi
    mov edx, dword ptr [edi]
    mov eax, dword ptr [edx+0x14]
    jmp 0x4e56e2
"""
# --- F7 ALIEN DEATH REPORT v2 (2026-10-21): F4 never fired in game (13:45 log: no 0x1e for any 600xx alien, server
# fallback kills only) - the think 004cc220 is not even CALLED for units this client does not control.  The per-unit
# simulation tick 004e94c0 runs for every unit on every client: at its entry (004e94c3, esi = unit) an alien
# (uid 50001..69999) whose simulated HP is <= 0 is reported with 004de930 (lump 0x1e [uid], guarded against
# duplicates by the unit's command queue) every 64 ticks until the server's 0x23 removes it.
f7 = """
    mov eax, dword ptr [esi+4]
    cmp eax, 50001
    jb f7_back
    cmp eax, 70000
    jae f7_back
    movzx eax, word ptr [esi+0xa866]
    mov eax, dword ptr [esi+eax*4+0xa464]
    cmp dword ptr [eax+4], 0
    jg f7_back
    mov eax, dword ptr [0x6ba7c8]
    test dword ptr [eax+0x25a0], 63
    jne f7_back
    mov ecx, esi
    call 0x4de930
f7_back:
    movzx eax, word ptr [esi+0xe8a6]
    jmp 0x4e94ca
"""
# --- F8 LAB TREE AFTER UPGRADE (2026-10-21 14:21): after COMPLETE UPGRADE (0x33 01 01 -> 005d5d40) the client only
# runs the light refresh 00449cc0, which neither drops the old unit row (a blank line stays) nor redraws; switching
# chassis tab and back showed the right list.  Now: full rebuild 0044a560 (what opening the Lab does), keeping the
# current tab (+0x398, the rebuild resets it), then select that tab again with 00448750 (= clicking the tab).
f8 = """
    lea ecx, [esi+0x6e04]
    push dword ptr [ecx+0x398]
    call 0x44a560
    pop eax
    lea ecx, [esi+0x6e04]
    push eax
    call 0x448750
    jmp 0x5d5d72
"""
# --- F9 POC STATE REPORT (2026-10-21): the client never completed a capture itself (the server's 3x fallback always
# came first).  Every 128 ticks each POC (0048f340 entry, ecx = POC object) reports
# 0xF4 [u32 id][u32 type][u32 progress][u32 owner][u8 capturing][u32 n on POC][u32 n capturers][u32 first capturer id]
# [u32 strength][u32 tile x][u32 tile y]
f9 = '''
    pushfd
    pushad
    mov esi, ecx
    mov eax, dword ptr [0x6ba7c8]
    test dword ptr [eax+0x25a0], 127
    jne f9_skip
    mov ecx, esi
    call 0x48c430
    mov ebx, eax
    mov ecx, esi
    call 0x48c440
    mov ebp, eax
    mov ecx, esi
    call 0x48c460
    movzx edi, al
    sub esp, 0x20
    mov eax, dword ptr [esi+0xc5c]
    sub eax, dword ptr [esi+0xc58]
    sar eax, 2
    mov dword ptr [esp], eax
    mov eax, dword ptr [esi+0xc6c]
    mov ecx, dword ptr [esi+0xc68]
    sub eax, ecx
    sar eax, 2
    mov dword ptr [esp+4], eax
    mov dword ptr [esp+8], 0
    test eax, eax
    je f9_nocap
    mov ecx, dword ptr [ecx]
    mov ecx, dword ptr [ecx+4]
    mov dword ptr [esp+8], ecx
f9_nocap:
''' + pkt_begin(0xF4) + u32('dword ptr [esi+0x2c]') + u32('dword ptr [esi]') + u32('ebx') + u32('ebp') + u8('edi') + \
    u32('dword ptr [esp+0x60]') + u32('dword ptr [esp+0x64]') + u32('dword ptr [esp+0x68]') + \
    u32('dword ptr [esi+0x38]') + u32('dword ptr [esi+8]') + u32('dword ptr [esi+0xc]') + PKT_END + '''
    add esp, 0x20
f9_skip:
    popad
    popfd
    sub esp, 0x14
    push ebx
    push ebp
    jmp 0x48f345
'''
# --- F10 Ctrl+F6 TK REPORT (2026-10-21): the client only flips a local flag (+0x459, read by nothing else) and
# sends nothing, so the server could not know.  Now the toggle (00560000) also sends 0xF5 [u8 TK on].
f10 = '''
    pushfd
    pushad
    movzx edi, byte ptr [esi+0x459]
''' + pkt_begin(0xF5) + u8('edi') + PKT_END + '''
    popad
    popfd
    mov al, byte ptr [esi+0x459]
    pop esi
    ret
'''
# --- F11 DEPLOY ENABLED IN TOWN (2026-10-21): every PUT of an own unit (004ac800) calls 0049f670 -> 005ba010(0),
# which greys DEPLOYED UNITS / F7 / Deploy Troops (field +0x60cc = 1).  In a battle the flag is recomputed every
# tick (005ba260), but in a town nothing clears it again, so the hero's own 0x18 in the capital disabled Deploy
# for good.  Now 0049f670 / 0049f640 run only in battle mode (field +0x29bdc != 0).
f11 = '''
    cmp byte ptr [esi+0x69], 0
    je skip
    cmp byte ptr [ebp+0x29bdc], 0
    je skip
    push 0x4ad433
    ret
skip:
    push 0x4ad441
    ret
'''
# --- F12 LAB ENGINE ABILITY COLUMN (2026-10-21): the Lab item list builds its columns per item type (00457d80);
# engines (004557d0) only had Health / Power / Energy cost, so the skill of a Cloak / Booster engine was invisible.
# Now a 4th column of type 3 = 'Ability Icon' (drawn by 00453080 through 00428590, like the Misc tab 00455c70) is
# added; its value = item +0x52 (5th u16 of the 0x10 record), which no client code reads for engines.  The server
# puts the engine's ability bit there.  Header row: -999 like the other tabs.
f12 = '''
    mov esi, ecx
    mov dword ptr [esp+8], 0xf
    lea edx, [esp+8]
    push edx
    call 0x455180
    mov eax, dword ptr [esp+0x18]
    mov edi, 0xfffffc19
    test eax, eax
    je hdr
    movzx edi, word ptr [eax+0x52]
hdr:
    mov dword ptr [esp+0xc], edi
    mov dword ptr [esp+8], 3
    lea edx, [esp+8]
    push edx
    mov ecx, esi
    call 0x455180
    push 0x45586e
    ret
'''
# --- F13 LAB RESOURCE SHORTAGE COLOUR (2026-10-21): the Lab bottom panel (005d4640) draws each resource as
# 'cost / owned' with the digit font font-f.xpf (004c39a0, last arg = colour variant: 0 green, 1 cyan; the font also
# has variant 2 = ORANGE).  The original only flashed the resource icon (ft-resNR.bik) for the first missing one.
# Now the COST digits use variant 2 when the commander owns less (cost in EBP, resource index in EDI).
f13 = '''
    mov ecx, dword ptr [esp+0x10]
    mov eax, dword ptr [0x6ba7d8]
    cmp ebp, dword ptr [eax+edi*4+0x458]
    jle enough
    push 2
    push 0x5d486a
    ret
enough:
    push 0
    push 0x5d486a
    ret
'''
# --- F14 / F15 LAB EQUIP PAGE DESIGN COST (2026-10-21): the equip page's resource panel (0052aec0) shows only the price
# of the item under the cursor; the client never sums the design (its 'left' array +0x1f27f.. is just the resources -
# placing items and LOAD 00530cc0 only check each item against it), so a LOADed design looked affordable and the
# server refused it at DONE.  F14: with no item selected the cost column shows the DESIGN TOTAL = sum of the buy prices
# (sale-list entry 0056ffa0(id) +3 + 4*resource) of the items in the design (+0x1069c) that are neither original
# equipment (+0x105b8) nor placed from the inventory (+0x106b0) - the same 'added' list the client sends with op 3.
# F15: the cost digits are ORANGE (font-f.xpf variant 2) when cost > resources (+0x1f27f); EBX keeps the cost, so the
# original red-icon check 0052b2ae (EBX > left) flashes for an unaffordable design too.
f14 = """
    jnz nz
    push edi
    push ebp
    mov ebp, dword ptr [esp+0x20]
    mov edi, dword ptr [esp+0x18]
    xor ebx, ebx
    mov esi, dword ptr [ebp+0x106a4]
lp:
    cmp esi, dword ptr [ebp+0x106a8]
    jae done
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x105b8]
    call 0x5275b0
    test al, al
    jnz nxt
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x106b0]
    call 0x5275b0
    test al, al
    jnz nxt
    movzx eax, word ptr [esi]
    push eax
    mov ecx, dword ptr [ebp+0x1f294]
    call 0x56ffa0
    test eax, eax
    jz nxt
    add ebx, dword ptr [eax+edi*4+3]
nxt:
    add esi, 2
    jmp lp
done:
    mov esi, dword ptr [ebp+0x105c0]
lp2:
    cmp esi, dword ptr [ebp+0x105c4]
    jae done2
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x1069c]
    call 0x5275b0
    test al, al
    jnz nxt2
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x106b0]
    call 0x5275b0
    test al, al
    jnz nxt2
    movzx eax, word ptr [esi]
    push eax
    mov ecx, dword ptr [ebp+0x1f294]
    call 0x56ffa0
    test eax, eax
    jz nxt2
    sub ebx, dword ptr [eax+edi*4+0x17]
nxt2:
    add esi, 2
    jmp lp2
done2:
    pop ebp
    pop edi
    test ebx, ebx
    jz none
    push 0x52afdb
    ret
none:
    or ebx, 0xffffffff
    push 0x52b147
    ret
nz:
    push 0x52b090
    ret
"""
f15 = """
    mov ecx, dword ptr [esp+0x14]
    mov eax, dword ptr [esp+0x10]
    shl eax, 2
    add eax, dword ptr [esp+0x18]
    cmp ebx, dword ptr [eax+0x1f27f]
    jg orange
    push 0
    push 0x52b12d
    ret
orange:
    push 2
    push 0x52b12d
    ret
"""

# --- F16 ANTI-CHEAT (2026-10-21): after every keep-alive 0x58 (every 5 s, 0049eff0) the client sends
#     0xF6 [u32 checksum of its own CODE in memory: .text + this patch section][u32 patch version 0x16]
#     checksum: h = 0; for every dword w: h = rol(h, 5) ^ w   (server/sgserver.py client_code_hash, same formula)
f16 = """
    call 0x5a8f50
    pushfd
    pushad
    xor eax, eax
    mov esi, 0x401000
    mov ecx, 0x928ef
h1:
    rol eax, 5
    xor eax, dword ptr [esi]
    add esi, 4
    dec ecx
    jnz h1
    mov esi, 0xeb3000
    mov ecx, 0x800
h2:
    rol eax, 5
    xor eax, dword ptr [esi]
    add esi, 4
    dec ecx
    jnz h2
    mov ebx, eax
""" + pkt_begin(0xF6) + u32('ebx') + u32('0x16') + PKT_END + """
    popad
    popfd
    push 0x49f066
    ret
"""

# --- F17 (2026-10-21 22:45): Lab equip page shows the NET DESIGN COST even while an item is hovered/selected (after
#     LOAD the last hovered item stayed in 0xd67b0c and only its own price was shown).  Hook at 0052afad (start of
#     the per-resource cost text): design total != 0 -> draw the total; == 0 -> original behaviour.
f17 = """
    mov dword ptr [esp+0x14], edx
    cmp dword ptr [esp+0x12c], 0
    jne q_orig
    push edi
    push ebp
    mov ebp, dword ptr [esp+0x20]
    mov edi, dword ptr [esp+0x18]
    xor ebx, ebx
    mov esi, dword ptr [ebp+0x106a4]
q_lp:
    cmp esi, dword ptr [ebp+0x106a8]
    jae q_done
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x105b8]
    call 0x5275b0
    test al, al
    jnz q_nxt
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x106b0]
    call 0x5275b0
    test al, al
    jnz q_nxt
    movzx eax, word ptr [esi]
    push eax
    mov ecx, dword ptr [ebp+0x1f294]
    call 0x56ffa0
    test eax, eax
    jz q_nxt
    add ebx, dword ptr [eax+edi*4+3]
q_nxt:
    add esi, 2
    jmp q_lp
q_done:
    mov esi, dword ptr [ebp+0x105c0]
q_lp2:
    cmp esi, dword ptr [ebp+0x105c4]
    jae q_done2
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x1069c]
    call 0x5275b0
    test al, al
    jnz q_nxt2
    movzx eax, word ptr [esi]
    push eax
    lea ecx, [ebp+0x106b0]
    call 0x5275b0
    test al, al
    jnz q_nxt2
    movzx eax, word ptr [esi]
    push eax
    mov ecx, dword ptr [ebp+0x1f294]
    call 0x56ffa0
    test eax, eax
    jz q_nxt2
    sub ebx, dword ptr [eax+edi*4+0x17]
q_nxt2:
    add esi, 2
    jmp q_lp2
q_done2:
    pop ebp
    pop edi
    test ebx, ebx
    jz q_orig
    push 0x52afdb
    ret
q_orig:
    mov ebx, dword ptr [esp+0x10]
    cmp dword ptr [0xd67b0c], 0
    je q_none
    push 0x52afbe
    ret
q_none:
    push 0x52b07f
    ret
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
code = bytearray(); addrs = {}
for name, src_ in (('f1', f1), ('f2', f2), ('f3', f3), ('f4', f4), ('f5', f5), ('f6', f6), ('f7', f7), ('f8', f8), ('f9', f9), ('f10', f10), ('f11', f11), ('f12', f12), ('f13', f13), ('f14', f14), ('f15', f15), ('f16', f16), ('f17', f17)):
    va = CODE_VA + len(code); addrs[name] = va
    c, _ = ks.asm(src_, va); code += bytes(c); code += bytes((-len(code)) % 16)
assert len(code) < SEC_SIZE - 0x100
sec = bytearray(SEC_SIZE); sec[0x100:0x100 + len(code)] = code
raw_ptr = len(d); assert raw_ptr % 0x1000 == 0
d += sec
hdr = sec0 + 40 * nsec
assert hdr + 40 <= secs[0][4], 'no header room'
struct.pack_into('<8sIIIIIIHHI', d, hdr, b'.dbgmov\0', SEC_SIZE, SEC_VA - ib, SEC_SIZE, raw_ptr, 0, 0, 0, 0, 0xE0000060)
struct.pack_into('<H', d, pe + 6, nsec + 1)
struct.pack_into('<I', d, pe + 80, SEC_VA - ib + SEC_SIZE)
def jmp(at, target, nops=0):
    d[off(at)] = 0xE9; struct.pack_into('<i', d, off(at) + 1, target - (at + 5))
    for i in range(nops): d[off(at) + 5 + i] = 0x90
jmp(0x5eace4, addrs['f1'])
jmp(0x4d19ba, addrs['f2'], 1)
jmp(0x4d0bdb, addrs['f3'], 3)
jmp(0x4cc226, addrs['f4'], 5)
jmp(0x48ea69, addrs['f5'], 5)
jmp(0x4e56dd, addrs['f6'])
jmp(0x4e94c3, addrs['f7'], 2)
jmp(0x5d5d67, addrs['f8'], 6)
jmp(0x48f340, addrs['f9'])
jmp(0x56001e, addrs['f10'], 1)
jmp(0x4ad42d, addrs['f11'], 1)
jmp(0x45585c, addrs['f12'])
jmp(0x5d4864, addrs['f13'], 1)
jmp(0x52b08a, addrs['f14'], 1)
jmp(0x52b127, addrs['f15'], 1)
jmp(0x49f061, addrs['f16'])
jmp(0x52afad, addrs['f17'], 6)
open(dst, 'wb').write(d)
print('patched ->', dst, {k: hex(v) for k, v in addrs.items()})
