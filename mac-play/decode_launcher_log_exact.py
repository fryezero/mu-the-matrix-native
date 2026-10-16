"""Exact decoder for Mu The Matrix (IGCN launcher) Data/Launcher/Log.txt.

Launcher code (cu.a/cu.b -> cn.c) XORs the UTF-16LE bytes of each message with a
fixed 5-byte key, then writes it with File.AppendAllText (UTF-8). Key bytes are
derived from a known plaintext crib (a standard .NET exception message).
"""
import re, sys
CRIB = "Attempted to read or write protected memory. This is often an indication that other memory is corrupt."
rx = re.compile(r'^(\[[^\]]*\]\s*(?:ERROR:\s*)?)\t?(.*)$')
def units(s): return list(s.encode('utf-16-le'))
def derive_key(bodies):
    for b in bodies:
        bb = units(b)
        cb = CRIB.encode('utf-16-le')
        for off in range(0, len(bb) - len(cb) + 1, 2):
            key = [None] * 5; ok = True
            for j in range(len(cb)):
                k = bb[off + j] ^ cb[j]; idx = (off + j) % 5
                if key[idx] is None: key[idx] = k
                elif key[idx] != k: ok = False; break
            if ok and None not in key: return bytes(key)
    return None
text = open(sys.argv[1], encoding='utf-8', errors='surrogatepass').read()
entries = []
for ln in text.split('\n'):
    m = rx.match(ln)
    if m or not entries: entries.append([m.group(1) if m else '', m.group(2) if m else ln])
    else: entries[-1][1] += '\n' + ln
key = derive_key([b for _, b in entries]) if len(sys.argv) < 3 else bytes.fromhex(sys.argv[2])
if key is None: sys.exit('no crib match; pass key hex as 2nd arg')
print('# key', key.hex(), file=sys.stderr)
for p, b in entries:
    bb = units(b)
    dec = bytes(c ^ key[i % 5] for i, c in enumerate(bb)).decode('utf-16-le', errors='replace')
    print(p + dec)
