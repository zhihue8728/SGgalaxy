from keystone import Ks, KS_ARCH_X86, KS_MODE_32
import capstone
VA = 0xeb3e70
TEXT_DW = 0x928ef
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
PKT_END = '''
    lea ecx, [esp]
    call 0x5aa1e0
    lea ecx, [esp]
    call 0x5a8f50
    add esp, 0x60
'''
# F34 (2026-10-25): server challenge 0xF7 [u32 nonce][u32 start dword][u32 count] -> client 0xF8 [u32 nonce][u32 answer]
# answer: h = nonce; rol5/xor over .text dwords [start, start+count) (clamped), then over the whole .dbgmov (0x800 dwords)
src = f'''
    mov eax, dword ptr [esp+4]
    cmp byte ptr [eax], 0xF7
    je chal
    movzx edx, byte ptr [eax]
    push 0x54a1d7
    ret
chal:
    cmp dword ptr [esp+8], 13
    jb done0
    pushfd
    pushad
    mov edi, eax
    mov ebx, dword ptr [edi+1]
    bswap ebx
    mov ecx, dword ptr [edi+5]
    bswap ecx
    mov edx, dword ptr [edi+9]
    bswap edx
    cmp ecx, {TEXT_DW}
    jb c1
    xor ecx, ecx
c1:
    mov eax, {TEXT_DW}
    sub eax, ecx
    test edx, edx
    je c2
    cmp edx, eax
    jbe c3
c2:
    mov edx, eax
c3:
    lea esi, [ecx*4 + 0x401000]
    mov eax, ebx
h1:
    rol eax, 5
    xor eax, dword ptr [esi]
    add esi, 4
    dec edx
    jnz h1
    mov esi, 0xeb3000
    mov ecx, 0x800
h2:
    rol eax, 5
    xor eax, dword ptr [esi]
    add esi, 4
    dec ecx
    jnz h2
    mov ebp, eax
''' + pkt_begin(0xF8) + u32('ebx') + u32('ebp') + PKT_END + '''
    popad
    popfd
done0:
    mov al, 1
    ret 8
'''
ks = Ks(KS_ARCH_X86, KS_MODE_32)
c, _ = ks.asm(src, VA)
code = bytes(c) + b"SGCH34\0\0"          # marker the server looks for (challenge-capable build)
open('stub.bin', 'wb').write(code)
print(len(code), code.hex())
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for i in md.disasm(bytes(c), VA):
    pass
