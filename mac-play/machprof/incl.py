# incl.py CHAINS MAINDUMP MUGLDUMP MUGLBASE MUGLDLL [N] [ROOT [DEPTH]] (MAC-PERF-009)
# Self and inclusive sample shares per function from stackprof EBPWALK=1 CHAINS output, for main.exe (private memory
# dump at VA 0x00400000) and a frame-pointer build of mugl (MOD=...; private dump of the loaded module at MUGLBASE,
# symbols from the DLL via i686-w64-mingw32-nm, preferred base 0x71000000). With ROOT, prints the callee tree below it.
# The innermost frame's function is the call target at the first return address. Inputs and outputs stay private.
import sys,struct,collections,subprocess,bisect
mem=open(sys.argv[2],'rb').read(); base=0x400000
mg=open(sys.argv[3],'rb').read(); mbase=int(sys.argv[4],16)
syms=[]
for ln in subprocess.run(['i686-w64-mingw32-nm','-n',sys.argv[5]],capture_output=True,text=True).stdout.split('\n'):
    p=ln.split()
    if len(p)==3 and p[1] in 'tT': syms.append((int(p[0],16)-0x71000000+mbase,p[2]))
sa=[a for a,_ in syms]
def name(a):
    if mbase<=a<mbase+len(mg):
        i=bisect.bisect_right(sa,a)-1; return 'mugl:'+syms[i][1] if i>=0 else 'mugl?%x'%a
    return '%08x'%a
def rd(a,n):
    if base<=a<base+len(mem): return mem[a-base:a-base+n]
    if mbase<=a<mbase+len(mg): return mg[a-mbase:a-mbase+n]
    return b'\0'*n
def tgt(a):
    b=rd(a-6,6)
    if b[1]==0xE8:
        t=(a+struct.unpack('<i',b[2:6])[0])&0xffffffff
        c=rd(t,5)
        if c[0]==0xE9: t=(t+5+struct.unpack('<i',c[1:5])[0])&0xffffffff
        return name(t)
    if b[0]==0xFF and b[1]==0x15:
        slot=struct.unpack('<I',b[2:6])[0]; v=struct.unpack('<I',rd(slot,4))[0]; return name(v)
    return 'ind<'+name(a)+'>'
inc=collections.Counter(); selfc=collections.Counter(); tot=0; chains=[]
cache={}
for ln in open(sys.argv[1]):
    p=ln.split()
    if not p or p[0]!='S': continue
    tot+=1
    ts=[]
    for x in p[1:]:
        a=int(x,16)
        if a not in cache: cache[a]=tgt(a)
        ts.append(cache[a])
    if not ts: continue
    chains.append(ts)
    selfc[ts[0]]+=1
    for t in set(ts): inc[t]+=1
N=int(sys.argv[6]) if len(sys.argv)>6 else 50
print('samples',tot,'with chain',len(chains))
if len(sys.argv)>7:
    root=sys.argv[7]
    def show(f,depth,ind,pool):
        n=len(pool); kids=collections.Counter(); selfn=0
        for c in pool:
            i=c.index(f)
            if i==0: selfn+=1
            else: kids[c[i-1]]+=1
        print('%s%s %.1f%% (self %.1f%%)'%(ind,f,100*n/tot,100*selfn/tot))
        if depth<=0: return
        for k,m in kids.most_common(14):
            if 100*m/tot<0.3: break
            show(k,depth-1,ind+'  ',[c[:c.index(f)] for c in pool if c.index(f)>0 and c[c.index(f)-1]==k])
    show(root,int(sys.argv[8]) if len(sys.argv)>8 else 3,'',[c for c in chains if root in c])
else:
    print('--- by self'); 
    for t,n in selfc.most_common(N): print('%6.1f%% self %6.1f%% incl  %s'%(100*n/tot,100*inc[t]/tot,t))
    print('--- by inclusive')
    for t,n in inc.most_common(N): print('%6.1f%% incl %6.1f%% self  %s'%(100*n/tot,100*selfc[t]/tot,t))
