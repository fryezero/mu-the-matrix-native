import os
import sys,collections,struct
# chain.py chains.txt <hex-first-retaddr or target> : histogram of the next return addresses (callers)
mem=open(os.environ['MU_MEMORY_DUMP'],'rb').read(); base=0x400000
def tgt(a):
    if mem[a-5-base]==0xE8: return (a+struct.unpack('<i',mem[a-4-base:a-base])[0])&0xffffffff
    return None
want=int(sys.argv[2],16); depth=int(sys.argv[3]) if len(sys.argv)>3 else 4
c=collections.Counter(); tot=0
for ln in open(sys.argv[1]):
    p=ln.split()[1:]
    if not p: continue
    a=[int(x,16) for x in p]
    if tgt(a[0])==want or a[0]==want:
        tot+=1; c[' '.join('%x'%x for x in a[1:1+depth])]+=1
print('samples',tot)
for k,v in c.most_common(15): print(v,k)
