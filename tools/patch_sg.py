#!/usr/bin/env python3
"""SG.exe 1.8.5 hit-delay patch (plan A, HIT_DELAY_PLAN.md).
usage: patch_sg.py SG.exe SG_hitdelay.exe [DELAY_TICKS]

Normal attacks (004e55b0) apply their damage DELAY ticks after the shot instead of on the shot tick:
  * the two `call 004cb3d0` (target->Damage(dmg, attackerId, 0, 0)) of 004e55b0 (main target 004e5775,
    flamethrower splash 004e597d) call HIT_QUEUE instead: it stores {tick = now + DELAY, target, attacker, dmg}
    in a table in a new PE section (duplicates ignored, so a re-simulated shot is not queued twice);
  * the per-unit event dispatcher 004c5a70 (runs for every unit, every tick, on every client) first calls
    HIT_APPLY: every entry whose tick == now and whose target is this unit is applied with 004cb3d0.
Deterministic: all clients run the same simulation ticks, so every client applies the hit on the same tick.
"""
import struct, sys
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

src, dst = sys.argv[1], sys.argv[2]
DELAY = int(sys.argv[3]) if len(sys.argv) > 3 else 30
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

# sanity: original bytes at the hook points
def expect(va, hexbytes):
    got = bytes(d[off(va):off(va) + len(bytes.fromhex(hexbytes))])
    assert got == bytes.fromhex(hexbytes), f'{va:#x}: {got.hex()} != {hexbytes}'
expect(0x4e5775, 'e8565cfeff')          # call 004cb3d0 (main target)
expect(0x4e597d, 'e84e5afeff')          # call 004cb3d0 (flamethrower splash)
expect(0x4c5a70, '5153568bf1')          # dispatcher prologue: push ecx; push ebx; push esi; mov esi,ecx

SEC_VA = ib + 0xab3000                  # after .rsrc (0xab0000 + 0x3000)
SEC_SIZE = 0x3000
DELAY_VA = SEC_VA                       # dword: delay in ticks
NENT = 512
TABLE_VA = SEC_VA + 0x1000              # NENT x {tick, target id, attacker id, damage}
CODE_VA = SEC_VA + 0x100
NOW = '[0x6ba7c8]'

asm = f'''
hit_queue:                              ; thiscall: ecx = target, edi = attacker (caller 004e55b0)
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
    mov esi, ecx
    mov eax, dword ptr [0x6ba7c8]
    mov ebx, dword ptr [eax+0x25a0]
    add ebx, dword ptr [{DELAY_VA:#x}]  ; ebx = tick of the hit
    mov ecx, {TABLE_VA:#x}
    xor edx, edx                        ; edx = free slot (0 = none yet)
    mov eax, dword ptr [0x6ba7c8]
    mov eax, dword ptr [eax+0x25a0]
    sub eax, 1000                       ; entries older than now-1000 ticks are free
q_loop:
    cmp ecx, {TABLE_VA + 16 * NENT:#x}
    jae q_end
    cmp dword ptr [ecx], ebx
    jne q_chkfree
    push eax
    mov eax, dword ptr [esi+4]
    cmp dword ptr [ecx+4], eax
    jne q_ne
    mov eax, dword ptr [edi+4]
    cmp dword ptr [ecx+8], eax
    jne q_ne
    mov eax, dword ptr [ebp+8]
    cmp dword ptr [ecx+12], eax
    jne q_ne
    pop eax
    jmp q_done                          ; same hit already queued (re-simulation)
q_ne:
    pop eax
q_chkfree:
    test edx, edx
    jne q_next
    cmp dword ptr [ecx], eax
    ja q_next
    mov edx, ecx
q_next:
    add ecx, 16
    jmp q_loop
q_end:
    test edx, edx
    je q_now                            ; table full: hit immediately (old behaviour)
    mov dword ptr [edx], ebx
    mov eax, dword ptr [esi+4]
    mov dword ptr [edx+4], eax
    mov eax, dword ptr [edi+4]
    mov dword ptr [edx+8], eax
    mov eax, dword ptr [ebp+8]
    mov dword ptr [edx+12], eax
q_done:
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret 0x10
q_now:
    push dword ptr [ebp+0x14]
    push dword ptr [ebp+0x10]
    push dword ptr [ebp+0xc]
    push dword ptr [ebp+8]
    mov ecx, esi
    call 0x4cb3d0
    jmp q_done

disp_entry:                             ; replaces 004c5a70's first 5 bytes
    push ecx
    push ebx
    push esi
    mov esi, ecx
    pushad
    mov eax, dword ptr [0x6ba7c8]
    mov ebx, dword ptr [eax+0x25a0]     ; now
    mov edi, {TABLE_VA:#x}
a_loop:
    cmp edi, {TABLE_VA + 16 * NENT:#x}
    jae a_end
    cmp dword ptr [edi], ebx
    jne a_next
    mov eax, dword ptr [esi+4]
    cmp dword ptr [edi+4], eax
    jne a_next
    push 0
    push 0
    push dword ptr [edi+8]
    push dword ptr [edi+12]
    mov ecx, esi
    call 0x4cb3d0                       ; target->Damage(dmg, attacker, 0, 0)  (preserves ebx/esi/edi)
a_next:
    add edi, 16
    jmp a_loop
a_end:
    popad
    jmp 0x4c5a75
'''
ks = Ks(KS_ARCH_X86, KS_MODE_32)
import re
asm = '\n'.join(re.sub(r';.*$', '', l).rstrip() for l in asm.split('\n'))
part1, part2 = asm.split('disp_entry:')
HIT_QUEUE, DISP = CODE_VA, CODE_VA + 0x400
c1, _ = ks.asm(part1, HIT_QUEUE)
c2, _ = ks.asm(part2, DISP)
c1, c2 = bytes(c1), bytes(c2)
assert len(c1) < 0x300 and len(c2) < 0x300
code = c1 + bytes(0x400 - len(c1)) + c2

# new section
sec = bytearray(SEC_SIZE)
struct.pack_into('<I', sec, 0, DELAY)
sec[0x100:0x100 + len(code)] = code
raw_ptr = len(d)
assert raw_ptr % 0x1000 == 0
d += sec
hdr = sec0 + 40 * nsec
assert hdr + 40 <= secs[0][4], 'no header room'
struct.pack_into('<8sIIIIIIHHI', d, hdr, b'.hitdly\0', SEC_SIZE, SEC_VA - ib, SEC_SIZE, raw_ptr, 0, 0, 0, 0, 0xE0000060)
struct.pack_into('<H', d, pe + 6, nsec + 1)
struct.pack_into('<I', d, pe + 80, SEC_VA - ib + SEC_SIZE)        # SizeOfImage

def rel_call(at, target, op=0xE8):
    d[off(at)] = op
    struct.pack_into('<i', d, off(at) + 1, target - (at + 5))
rel_call(0x4e5775, HIT_QUEUE)
rel_call(0x4e597d, HIT_QUEUE)
rel_call(0x4c5a70, DISP, 0xE9)
open(dst, 'wb').write(d)
print(f'patched -> {dst}: delay {DELAY} ticks, hit_queue {HIT_QUEUE:#x}, dispatcher hook {DISP:#x}, '
      f'table {TABLE_VA:#x} x {NENT}')
