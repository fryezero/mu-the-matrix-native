"""Peephole rewriter for MSVC /Od constant idioms in main.exe.
   push imm8 ; pop r32 ; (imul r,r,imm8 | shl r,imm8 | shl r,1)   ->   mov r,const ; nop padding
   shl r,0 keeps flags, so the rewrite is exact. imul/shl-by-nonzero define flags; those sites are only
   rewritten when forward analysis shows the flags are overwritten before any read."""
import re,struct
R32=['eax','ecx','edx','ebx','esp','ebp','esi','edi']
READ_FLAGS=re.compile(r'^(j(?!mp)|set|cmov|adc|sbb|lahf|pushf|rcl|rcr|cmc|into|loop)')
WRITE_ALL=re.compile(r'^(cmp|test|add|sub|and|or|xor|comiss|ucomiss|comisd|ucomisd|neg|sahf|popf|bt\b|imul)')
def parse(lines):
    ins=[]
    for l in lines:
        m=re.match(r'\s*([0-9a-f]+):\t(\S+)\s*(.*)$',l)
        if m: ins.append((int(m.group(1),16),m.group(2),m.group(3)))
    return ins
def flags_dead_after(ins,k):
    # True if, scanning from instruction k on, flags are fully written before read (calls/rets count as writes)
    for j in range(k,min(k+40,len(ins))):
        _,op,args=ins[j]
        if READ_FLAGS.match(op): return False
        if WRITE_ALL.match(op) or op.startswith('call') or op.startswith('ret'): return True
        if op in ('shl','shr','sar') and not args.startswith('$0x0,') and not args.startswith('%cl'): return True
        if op.startswith('jmp') or op in ('int3','hlt','(bad)'): return False
    return False
def find(ins,mem,base):
    out=[]
    for k in range(len(ins)-3):
        s=find_at(ins,k,mem,base)
        if s: out.append(s)
    return out
def find_at(ins,k,mem,base):
    if True:
        a,op,args=ins[k]
        if op!='push' or not args.startswith('$0x'): return None
        b,op2,args2=ins[k+1]
        if op2!='pop' or b!=a+2 or mem[a-base]!=0x6a: return None
        r=args2.lstrip('%')
        if r not in R32 or r in ('esp','ebp'): return None
        v=struct.unpack('b',mem[a+1-base:a+2-base])[0]&0xffffffff
        c,op3,args3=ins[k+2]
        m=re.match(r'\$0x([0-9a-f]+),%(\w+),%(\w+)$',args3)
        if op3=='imul' and m and m.group(2)==r and m.group(3)==r: val=(v*int(m.group(1),16))&0xffffffff; exact=False
        elif op3=='shl' and re.match(r'\$0x([0-9a-f]+),%(\w+)$',args3) and args3.endswith('%'+r):
            n=int(re.match(r'\$0x([0-9a-f]+)',args3).group(1),16); val=(v<<n)&0xffffffff; exact=(n==0)
        elif op3=='shl' and args3 in ('%'+r, '$1,%'+r): val=(v<<1)&0xffffffff; exact=False
        else: return None
        end=ins[k+3][0]; n=end-a
        if not exact and not flags_dead_after(ins,k+3): return None
        new=bytes([0xb8+R32.index(r)])+struct.pack('<I',val)
        if len(new)>n: return None
        new+=NOPS[n-len(new)]
        return (a,mem[a-base:end-base],new)
NOPS={0:b'',1:b'\x90',2:b'\x66\x90',3:b'\x0f\x1f\x00',4:b'\x0f\x1f\x40\x00',5:b'\x0f\x1f\x44\x00\x00'}
