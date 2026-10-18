"""Generate pass-through stubs (stubs.S), real-pointer table and .def for the mugl opengl32 proxy."""
CUSTOM = {  # export -> internal stdcall symbol with arg bytes
 'glBegin':4,'glEnd':0,
 'glVertex2f':8,'glVertex2fv':4,'glVertex3f':12,'glVertex3fv':4,'glVertex2i':8,'glVertex3i':12,'glVertex2d':16,'glVertex3d':24,'glVertex3dv':4,'glVertex2iv':4,'glVertex3iv':4,
 'glTexCoord2f':8,'glTexCoord2fv':4,'glTexCoord2d':16,'glTexCoord2i':8,
 'glColor3f':12,'glColor3fv':4,'glColor4f':16,'glColor4fv':4,'glColor3ub':12,'glColor3ubv':4,'glColor4ub':16,'glColor4ubv':4,'glColor3d':24,'glColor4d':32,
 'glNormal3f':12,'glNormal3fv':4,
 'glPopAttrib':0,'glCallList':4,'glCallLists':12,
 'wglGetProcAddress':4,'wglSwapBuffers':4,'glShadeModel':4,'glEnable':4,'glDisable':4,'glBindTexture':8,'glBlendFunc':8,'glDepthMask':4,'glMatrixMode':4,'glAlphaFunc':8,'glDepthFunc':4,'glDeleteTextures':8,'glGetFloatv':8,'glGetDoublev':8,'glGetIntegerv':8,'glGetBooleanv':8,'glVertexPointer':16,'glNormalPointer':12,'glColorPointer':16,'glTexCoordPointer':16,'glIndexPointer':12,'glEdgeFlagPointer':8,'glInterleavedArrays':12,'glDrawElements':16,'glPushClientAttrib':4,'glPopClientAttrib':0,'glDrawArrays':12,'glTranslatef':12,'glRotatef':16,'glRotated':32,'glScalef':12,'glScaled':24,'glMultMatrixf':4,'glMultMatrixd':4,'glLoadMatrixf':4,'glLoadMatrixd':4,'glOrtho':48,'glFrustum':48,'glRenderMode':4,'glEnableClientState':4,'glDisableClientState':4,'glPushMatrix':0,'glPopMatrix':0,'glLoadIdentity':0,
 'glTexParameteri':12,'glTexParameterf':12,'glTexParameteriv':12,'glTexParameterfv':12,'glNewList':8,'glEndList':0,'glViewport':16,
}
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
names = (Path(__file__).resolve().parents[1] / 'mugl/exports.txt').read_text().splitlines()
if len(names) != len(set(names)) or not CUSTOM.keys() <= set(names):
    raise ValueError('Invalid export manifest')
with (args.out / 'stubs.S').open('w') as s:
    s.write('    .text\n')
    for idx, n in enumerate(names):
        if n in CUSTOM: continue
        s.write(f'    .globl _stub_{n}\n_stub_{n}:\n    cmpb $0, _mugl_busy\n    jne 1f\n    jmp *_real_{n}\n1:  pushal\n    pushfl\n    pushl ${idx}\n    call _mugl_sync_from\n    addl $4, %esp\n    popfl\n    popal\n    jmp *_real_{n}\n')
    s.write('    .data\n')
    for n in names:
        s.write(f'    .globl _real_{n}\n_real_{n}: .long 0\n')
import re
def flags(n):
    f = 0
    consume = (n.startswith('wgl') or n.startswith('glGet') or n.startswith('glRasterPos') or n.startswith('glEval')
               or n in ('glPushAttrib','glNewList','glEndList','glArrayElement','glDrawArrays','glDrawElements','glCallList','glCallLists'))
    release = (n.startswith('wgl') or n.startswith('glGet') or n in ('glArrayElement','glColorPointer','glDisableClientState','glDrawArrays',
               'glDrawElements','glEdgeFlagPointer','glEnableClientState','glIndexPointer','glInterleavedArrays','glNormalPointer',
               'glPopClientAttrib','glPushClientAttrib','glTexCoordPointer','glVertexPointer','glIsEnabled'))
    invalidate = n in ('glArrayElement','glDrawArrays','glDrawElements','glEvalMesh1','glEvalMesh2','glEvalCoord1d','glEvalCoord1f','glEvalCoord2d','glEvalCoord2f','glEvalPoint1','glEvalPoint2')
    return (1 if consume else 0) | (2 if release else 0) | (4 if invalidate else 0)
with (args.out / 'names.h').open('w') as h:
    h.write(''.join(f'extern void *real_{n};\n' for n in names))
    h.write('static const char *const mugl_names[] = {\n' + ''.join(f'  "{n}",\n' for n in names) + '};\n')
    h.write('static const unsigned char mugl_flags[] = {' + ','.join(str(flags(n)) for n in names) + '};\n')
    h.write('static void **const mugl_slots[] = {\n' + ''.join(f'  (void **)&real_{n},\n' for n in names) + '};\n')
with (args.out / 'opengl32.def').open('w') as d:
    d.write('LIBRARY opengl32.dll\nEXPORTS\n')
    for n in names:
        d.write(f'    {n} = mugl_{n}@{CUSTOM[n]}\n' if n in CUSTOM else f'    {n} = stub_{n}\n')
print(len(names), 'exports;', len(CUSTOM), 'custom')
