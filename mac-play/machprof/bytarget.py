import os
import sys,struct,collections
mem=open(os.environ['MU_MEMORY_DUMP'],'rb').read(); base=0x400000
def b(a): return mem[a-base]
tot=0; tg=collections.Counter(); ex=collections.defaultdict(list)
for ln in open(sys.argv[1]):
    k,a,n=ln.split()
    if k!='L': continue
    a=int(a,16); n=int(n); tot+=n
    if b(a-5)==0xE8:
        t=(a+struct.unpack('<i',mem[a-4-base:a-base])[0])&0xffffffff
        # follow jmp thunks (E9 rel32 / FF25 [abs])
        if 0x400000<=t<0x3000000 and b(t)==0xE9: t=(t+5+struct.unpack('<i',mem[t+1-base:t+5-base])[0])&0xffffffff
        if 0x400000<=t<0x3000000 and b(t)==0xFF and b(t+1)==0x25:
            slot=struct.unpack('<I',mem[t+2-base:t+6-base])[0]
            v=struct.unpack('<I',mem[slot-base:slot+4-base])[0] if 0x400000<=slot<0x3000000 else 0
            t=('IAT[%x]->%x'%(slot,v))
        key=t if isinstance(t,str) else '%08x'%t
    else:
        # indirect call: show the call bytes
        if b(a-6)==0xFF and b(a-5)==0x15:
            slot=struct.unpack('<I',mem[a-4-base:a-base])[0]
            v=struct.unpack('<I',mem[slot-base:slot+4-base])[0] if 0x400000<=slot<0x3000000 else 0
            key='IAT[%x]->%x'%(slot,v)
        else: key='indirect'
    tg[key]+=n; ex[key].append('%x:%d'%(a,n))
print('total',tot)
for k,v in tg.most_common(40): print('%5d %5.1f%% %-28s %s'%(v,100*v/tot,k,' '.join(ex[k][:6])))
