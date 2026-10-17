import os
import sys,subprocess
mem=open(os.environ['MU_MEMORY_DUMP'],'rb').read(); base=0x400000
a=int(sys.argv[1],16); n=int(sys.argv[2]) if len(sys.argv)>2 else 400
open('/tmp/_f.bin','wb').write(mem[a-base:a-base+n])
out=subprocess.run(['i686-w64-mingw32-objdump','-D','-b','binary','-mi386','--no-show-raw-insn','--adjust-vma=%#x'%a,'/tmp/_f.bin'],capture_output=True).stdout.decode()
lines=[l for l in out.split('\n') if ':\t' in l]
for l in lines:
    print(l)
    if '\tret' in l and len(sys.argv)<=3: break
