# SPDX-License-Identifier: MIT
"""Map RVAs to nearest preceding exported symbol in a PE32 file. Usage: pe_nearest_export.py dll rva..."""
import struct, sys
d = open(sys.argv[1], 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]; optsz = struct.unpack_from('<H', d, pe + 20)[0]
opt = pe + 24; exp_rva = struct.unpack_from('<I', d, opt + 96)[0]
secs = [struct.unpack_from('<8sIIII', d, opt + optsz + 40 * i) for i in range(nsec)]
def off(rva):
    for n, vs, va, rs, ro in secs:
        if va <= rva < va + max(vs, rs): return rva - va + ro
names = {}
if exp_rva:
    e = off(exp_rva); nfun, nnames, af, an, ao = struct.unpack_from('<IIIII', d, e + 20)
    funcs = struct.unpack_from('<%dI' % nfun, d, off(af))
    for i in range(nnames):
        nr = struct.unpack_from('<I', d, off(an) + 4 * i)[0]; o = struct.unpack_from('<H', d, off(ao) + 2 * i)[0]
        s = d[off(nr):d.index(b'\0', off(nr))].decode()
        names.setdefault(funcs[o], s)
syms = sorted(names.items())
for a in sys.argv[2:]:
    r = int(a, 16); best = max((x for x in syms if x[0] <= r), default=None)
    print(hex(r), best[1] if best else '?', '+0x%x' % (r - best[0]) if best else '')
