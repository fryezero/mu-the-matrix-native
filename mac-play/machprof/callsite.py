import os
import sys,subprocess,struct
mem=open(os.environ['MU_MEMORY_DUMP'],'rb').read(); base=0x400000
def rd(a,n): return mem[a-base:a-base+n]
def dis(a,n=40,before=24):
    st=a-before
    open('/tmp/_cs.bin','wb').write(rd(st,before+n))
    out=subprocess.run(['i686-w64-mingw32-objdump','-D','-b','binary','-mi386','--no-show-raw-insn','--adjust-vma=%#x'%st,'/tmp/_cs.bin'],capture_output=True).stdout.decode()
    return '\n'.join(l for l in out.split('\n') if ':\t' in l)
for x in sys.argv[1:]:
    a=int(x,16); print('=== ret',x)
    print(dis(a,8,16))
