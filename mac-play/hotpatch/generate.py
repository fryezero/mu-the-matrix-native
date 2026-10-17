"""Generate PRIVATE patch tables from the owner's pinned pristine memory dump.

Never copies client bytes into tracked source. --synthetic creates a compile-only
build with all game hotpatch/Sleep hooks disabled. It does not establish equivalence.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

import inliner
import peep

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(data, spec, label):
    if len(data) != spec['length'] or digest(data) != spec['sha256']:
        raise ValueError(label + ' does not match pinned input')
    return data


def records_digest(records):
    h = hashlib.sha256()
    for address, old, new in records:
        h.update(struct.pack('<II', address, len(old)) + old + new)
    return h.hexdigest()


def validate_records(records):
    end = 0
    for address, old, new in records:
        if not old or len(old) != len(new) or address < end:
            raise ValueError('Empty, overlapping or unequal-length patch')
        end = address + len(old)


def cbytes(data):
    return '{' + ','.join(str(x) for x in data) + '}'


def tables(output, helpers, inline, peephole, prologue, private):
    for records in ([(a, o, n) for _, a, o, n in helpers], inline, peephole):
        validate_records(sorted(records))
    output.mkdir(parents=True, exist_ok=True)
    lines = ['/* PRIVATE generated input. Never publish this file. */',
             'typedef struct { const char *name; unsigned addr; unsigned len; const unsigned char *orig, *repl; } HotPatch;']
    for name, _, old, new in helpers:
        lines += [f'static const unsigned char hpo_{name}[] = {cbytes(old)};',
                  f'static const unsigned char hpr_{name}[] = {cbytes(new)};']
    lines += ['static const HotPatch hot_patches[] = {']
    lines += [f'{{"{name}",0x{address:x},sizeof hpo_{name},hpo_{name},hpr_{name}}},' for name, address, _, _ in helpers]
    (output / 'hotpatches.h').write_text('\n'.join(lines) + '\n};\n')
    for filename, typename, records, width, length in [('inlinesites.h','InlineSite',inline,5,False),('peepsites.h','PeepSite',peephole,9,True)]:
        lines = ['/* PRIVATE generated input. Never publish this file. */',
                 f'typedef struct {{ unsigned addr; ' + ('unsigned char len; ' if length else '') + f'unsigned char orig[{width}], repl[{width}]; }} {typename};',
                 f'static const {typename} ' + ('peep_sites' if length else 'inline_sites') + '[] = {']
        for a, old, new in records:
            if len(old) > width:
                raise ValueError('Patch exceeds table field width')
            lines.append(f'{{0x{a:x},' + (f'{len(old)},' if length else '') + cbytes(old) + ',' + cbytes(new) + '},')
        (output / filename).write_text('\n'.join(lines) + '\n};\n')
    (output / 'xform-prologue.h').write_text('/* PRIVATE generated input. */\nstatic const unsigned char xf_prologue[16] = ' + cbytes(prologue) + ';\n')
    (output / 'private-build.h').write_text(f'#define MUGL_PRIVATE_TABLES {int(private)}\n')


def replacements(config, cc, objcopy, nm):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        subprocess.run([cc, '-c', str(HERE/'hp.S'), '-o', str(td/'hp.o')], check=True)
        subprocess.run([objcopy, '-O', 'binary', '-j', '.text', str(td/'hp.o'), str(td/'hp.bin')], check=True)
        listing = subprocess.check_output([nm, '-n', str(td/'hp.o')], text=True)
        symbols = {name:int(address,16) for address, _, name in (line.split() for line in listing.splitlines() if len(line.split()) == 3)}
        code = (td/'hp.bin').read_bytes()
        return {h['name']:code[symbols['_hp_'+h['symbol']]:symbols['_hp_'+h['symbol']+'_end']] for h in config['helpers']}


def exclude(a, n, config, xform=False):
    spans = [(h['address'], h['address']+h['length']) for h in config['helpers']]
    if xform:
        spans.append((0x12b5bde, 0x12b678d))
    return any(a < hi and a+n > lo for lo, hi in spans)


def derive_listings(mem, config, output, objdump):
    """Regenerate Claude's instruction format locally, without publishing bytes."""
    output.mkdir(parents=True, exist_ok=True)
    text = output / 'text.bin'
    base = config['image_base']
    text.write_bytes(mem[config['text_start']-base:config['text_end']-base])
    disassembly, calls = output/'ptext.dis', output/'calls.txt'
    command = [objdump,'-D','-b','binary','-mi386','--no-show-raw-insn',
               f"--adjust-vma={config['text_start']:#x}",str(text)]
    with disassembly.open('w') as dis, calls.open('w') as direct:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)
        try:
            for line in process.stdout:
                if ':\t' not in line:
                    continue
                dis.write(line)
                match = re.match(r'\s*([0-9a-f]+):\tcall\s+(0x[0-9a-f]+)\s*$',line)
                if match:
                    direct.write(match.group(1)+' '+match.group(2)+'\n')
        finally:
            process.stdout.close()
        if process.wait():
            raise ValueError('objdump failed')
    return calls, disassembly


def private_tables(args, config):
    mem = args.dump.read_bytes()
    if len(mem) != config['dump_bytes'] or digest(mem) != config['dump_sha256']:
        raise ValueError('Dump identity mismatch. Requires the documented pristine image, not the on-disk PE or a patched dump')
    if args.calls is None:
        args.calls, args.disassembly = derive_listings(mem, config, args.out/'inputs', args.objdump)
    for path, key in [(args.calls,'calls_sha256'),(args.disassembly,'disassembly_sha256')]:
        if digest(path.read_bytes()) not in {config[key],config.get('derived_'+key)}:
            raise ValueError('Offline listing identity mismatch')
    base = config['image_base']
    helpers = []
    repls = replacements(config, args.cc, args.objcopy, args.nm)
    originals = {}
    for h in config['helpers']:
        a, n = h['address'], h['length']
        old = checked(mem[a-base:a-base+n], h, h['name'])
        new = repls[h['name']]
        if len(new) > n:
            raise ValueError('Replacement larger than original')
        helpers.append((h['name'], a, old, new + b'\xcc' * (n-len(new))))
        originals[h['name']] = old
    xf = config['xform']; a = xf['address']
    prologue = checked(mem[a-base:a-base+xf['length']], xf, 'xform prologue')
    with args.calls.open() as f:
        calls = [tuple(int(v,16) for v in line.split()) for line in f if line.strip()]
    inline = [r for r in inliner.scan(mem, calls, config) if not exclude(r[0],len(r[1]),config)]
    # Claude's bounded sliding window and flags-dead check, with the fixed end-base slice.
    window = deque(); peephole = []
    with args.disassembly.open() as f:
        for line in f:
            ins = peep.parse([line])
            if not ins:
                continue
            window.append(ins[0])
            if len(window) >= 48:
                record = peep.find_at(list(window),0,mem,base)
                if record and not exclude(record[0],len(record[1]),config,xform=True):
                    peephole.append(record)
                window.popleft()
    for name, records in [('inline',inline),('peephole',peephole)]:
        expected = config['generated'][name]
        if len(records) != expected['count'] or records_digest(records) != expected['sha256']:
            raise ValueError(f'{name} result differs from Claude v7.0: {len(records)} records, {records_digest(records)}')
    tables(args.out,helpers,inline,peephole,prologue,True)
    mapping = {'vrot':'vrot','vtrans':'vtrans','self':'self','index':'index','deref16':'deref16','eq':'eq','store8a':'st_a','store8b':'st_b','store8c':'st_c'}
    (args.out/'orig.h').write_text('/* PRIVATE harness input. */\n'+'\n'.join(f'static const unsigned char orig_{mapping[n]}[] = {cbytes(o)};' for n,o in originals.items())+'\n')
    return {'inline':len(inline),'peephole':len(peephole),'helpers':len(helpers),'dump_sha256':digest(mem)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--synthetic',action='store_true')
    p.add_argument('--dump',type=Path)
    p.add_argument('--calls',type=Path)
    p.add_argument('--disassembly',type=Path)
    p.add_argument('--cc',default='i686-w64-mingw32-gcc')
    p.add_argument('--objcopy',default='i686-w64-mingw32-objcopy')
    p.add_argument('--nm',default='i686-w64-mingw32-nm')
    p.add_argument('--objdump',default='i686-w64-mingw32-objdump')
    args = p.parse_args()
    # Restrict generated game material to the repository's explicitly ignored build directory.
    allowed = HERE/'build'
    if not args.out.resolve().is_relative_to(allowed.resolve()):
        p.error('Output must be under mac-play/hotpatch/build (ignored)')
    if args.synthetic:
        if args.dump or args.calls or args.disassembly:
            p.error('--synthetic cannot be combined with private inputs')
        tables(args.out,[],[],[],bytes(16),False)
        return
    if args.dump is None or bool(args.calls) != bool(args.disassembly):
        p.error('Supply --dump; optional --calls and --disassembly must be paired')
    result = private_tables(args,json.loads((HERE/'targets.json').read_text()))
    (args.out/'generation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
