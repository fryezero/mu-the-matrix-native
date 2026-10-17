"""Claude's trivial-call scanner, using digests instead of published client templates."""
import hashlib
import struct


def matches(data, pattern):
    return len(data) == pattern['length'] and hashlib.sha256(data).hexdigest() == pattern['sha256']


def scan(mem, calls, config):
    base = config['image_base']
    def read(a, n):
        if a < base or a + n > base + len(mem):
            return b''
        return mem[a-base:a-base+n]
    templates = config['inline_templates']
    callees = {}
    # Only direct-call destinations can contribute a site. No need to search data bytes.
    for target in {t for _, t in calls}:
        # Claude scanned after installing these bodies, so they no longer matched.
        if target in {h['address'] for h in config['helpers']}:
            continue
        for name, template in templates.items():
            if name == 'ret4' and target != config['ret4_address']:
                continue
            if matches(read(target, template['length']), template):
                callees[target] = name
    for target in {t for _, t in calls}:
        if matches(read(target, 11), config['wrapper_prefix']) and matches(read(target+15, 2), config['wrapper_suffix']):
            dest = (target + 15 + struct.unpack('<i', read(target+11, 4))[0]) & 0xffffffff
            if callees.get(dest) in ('deref16', 'self', 'empty'):
                callees[target] = 'w_' + callees[dest]
    out = []
    for a, target in calls:
        old = read(a, 5)
        if target not in callees or len(old) != 5 or old[0] != 0xe8:
            continue
        if (a + 5 + struct.unpack('<i', old[1:])[0]) & 0xffffffff != target:
            raise ValueError('Call listing disagrees with dump')
        kind = callees[target].removeprefix('w_')
        out.append((a, old, bytes.fromhex(templates[kind]['replacement'])))
    return sorted(out)
