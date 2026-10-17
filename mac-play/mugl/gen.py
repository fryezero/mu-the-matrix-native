# SPDX-License-Identifier: MIT
"""Generate pass-through stubs (stubs.S), real-pointer table and .def for the mugl opengl32 proxy."""
from pathlib import Path
import argparse
import re

CUSTOM = {  # export -> internal stdcall symbol with arg bytes
 'glBegin':4,'glEnd':0,
 'glVertex2f':8,'glVertex2fv':4,'glVertex3f':12,'glVertex3fv':4,'glVertex2i':8,'glVertex3i':12,'glVertex2d':16,'glVertex3d':24,'glVertex3dv':4,'glVertex2iv':4,'glVertex3iv':4,
 'glTexCoord2f':8,'glTexCoord2fv':4,'glTexCoord2d':16,'glTexCoord2i':8,
 'glColor3f':12,'glColor3fv':4,'glColor4f':16,'glColor4fv':4,'glColor3ub':12,'glColor3ubv':4,'glColor4ub':16,'glColor4ubv':4,'glColor3d':24,'glColor4d':32,
 'glNormal3f':12,'glNormal3fv':4,
 'glNewList':8,'glEndList':0,'glPolygonMode':8,'glRenderMode':4,
 'glPopAttrib':0,'glCallList':4,'glCallLists':12,
 'wglGetProcAddress':4,'wglSwapBuffers':4,'glShadeModel':4,
}

# These pass-through calls may replace values cached by the buffered entry points.
def invalidates(name):
    return name in {'glPopClientAttrib', 'glInterleavedArrays', 'glEnableClientState', 'glDisableClientState'} or name.startswith(('glColor', 'glTexCoord', 'glNormal', 'glEval', 'glArrayElement', 'wglMake'))


def generate(exports, output):
    names = [line.strip() for line in Path(exports).read_text().splitlines() if line.strip()]
    if len(names) != len(set(names)) or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', n) for n in names):
        raise ValueError('Invalid or duplicate export')
    if not CUSTOM.keys() <= set(names):
        raise ValueError('Custom entry point missing from export list')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'stubs.S').open('w') as s:
        s.write('    .text\n')
        for idx, n in enumerate(names):
            if n in CUSTOM:
                continue
            s.write(f'    .globl _stub_{n}\n_stub_{n}:\n')
            if not invalidates(n):
                s.write(f'    cmpb $0, _mugl_busy\n    jne 1f\n    jmp *_real_{n}\n')
            s.write(f'1:  pushal\n    pushfl\n    pushl ${idx}\n    call _mugl_sync_from\n    addl $4, %esp\n    popfl\n    popal\n    jmp *_real_{n}\n')
        s.write('    .data\n')
        for n in names:
            s.write(f'    .globl _real_{n}\n_real_{n}: .long 0\n')
    with (output / 'names.h').open('w') as h:
        h.write(''.join(f'extern void *real_{n};\n' for n in names))
        h.write('static const char *const mugl_names[] = {\n' + ''.join(f'  "{n}",\n' for n in names) + '};\n')
        h.write('static const unsigned char mugl_invalidates[] = {\n' + ''.join(f'  {int(invalidates(n))},\n' for n in names) + '};\n')
        h.write('static void **const mugl_slots[] = {\n' + ''.join(f'  (void **)&real_{n},\n' for n in names) + '};\n')
    with (output / 'opengl32.def').open('w') as d:
        d.write('LIBRARY opengl32.dll\nEXPORTS\n')
        for n in names:
            d.write(f'    {n} = mugl_{n}@{CUSTOM[n]}\n' if n in CUSTOM else f'    {n} = stub_{n}\n')
    return len(names)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', type=Path, default=Path(__file__).with_name('exports.txt'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(generate(args.exports, args.out), 'exports;', len(CUSTOM), 'custom')
