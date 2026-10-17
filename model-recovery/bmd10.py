#!/usr/bin/env python3
"""Strict read-only BMD v10 parser and recorded-pose geometry exporter.

Independent implementation of layouts cross-checked with xulek's ISC-declared
bmd-loader.ts at 3f11bf89f3702261174d8efa1436d56a15c7d97a. See SOURCES.md.
No decryption, game execution, frame-rate inference, or server access.

``client_layout=True`` follows the client's model reader 0x012b3812 instead
(docs/research/model-edge.md): the same stream walk, but no index, bone,
parent, flag or floating-point check. Every value the strict reader would
reject is kept raw and listed in ``client_semantics`` with its layout offset,
because its meaning depends on client memory state. Structural limits stay:
truncation (the client would read past its decoded buffer), negative or
oversized counts, and the size limits.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

MAX_FILE = 128 * 1024 * 1024
MAX_COUNT = 4096


class BmdError(ValueError):
    def __init__(self, message, *, offset=None):
        # Offsets refer to the decoded v10 layout including its four-byte header.
        # Encrypted file offsets cannot be obtained by adding the envelope size.
        self.offset = offset
        super().__init__(message if offset is None else f'{message} at layout offset {offset}')


class Reader:
    def __init__(self, data, issues=None):
        # issues: client-layout mode collects non-finite values instead of raising.
        self.data, self.offset, self.issues = data, 0, issues

    def take(self, size):
        if size < 0 or self.offset + size > len(self.data):
            raise BmdError(f'Truncated read at offset {self.offset}: need {size} bytes')
        value = self.data[self.offset:self.offset+size]
        self.offset += size
        return value

    def unpack(self, fmt):
        start = self.offset
        values = struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt)))
        # Reader formats are sequences of scalar fields, with no repeat counts.
        for index, value in enumerate(values):
            if isinstance(value, float) and not math.isfinite(value):
                offset = start+struct.calcsize('<'+fmt[:index])
                if self.issues is None:
                    raise BmdError('Non-finite numeric data', offset=offset)
                self.issues.append({'kind': 'nonfinite', 'strict': True, 'offset': offset,
                                    'binary32_hex': self.data[offset:offset+4][::-1].hex()})
        return values

    def string(self):
        raw = self.take(32)
        # latin-1 preserves every input byte; raw fixed-width bytes retained too.
        return {'text': raw.split(b'\0', 1)[0].decode('latin-1'), 'raw_hex': raw.hex()}

    def flag(self):
        value, = self.unpack('B')
        if value not in (0, 1):
            if self.issues is None:
                raise BmdError(f'Non-boolean flag {value} near offset {self.offset}')
            # The client tests the byte for nonzero.
            self.issues.append({'kind': 'flag-nonboolean', 'strict': True, 'offset': self.offset-1, 'value': value})
        return bool(value)


def count(value, label, maximum=MAX_COUNT):
    if not 0 <= value <= maximum:
        raise BmdError(f'Invalid {label} count {value}')
    return value


def parse_bytes(raw, *, lea_block_padding=False, client_layout=False):
    if len(raw) > MAX_FILE or len(raw) < 42:
        raise BmdError('File outside supported size limits')
    issues = [] if client_layout else None

    def issue(kind, message, offset=None, strict=True, **detail):
        if issues is None:
            raise BmdError(message, offset=offset)
        issues.append(dict({'kind': kind, 'strict': strict, 'offset': offset, 'message': message}, **detail))
    r = Reader(raw, issues)
    if r.take(4) != b'BMD\x0a':
        raise BmdError('Only plaintext BMD version 10 is supported')
    name = r.string()
    nm, nb, na = r.unpack('HHH')
    for n, label in [(nm, 'mesh'), (nb, 'bone'), (na, 'action')]:
        count(n, label)
    result = {'version': 10, 'name': name, 'source_bytes': len(raw),
              'source_sha256': hashlib.sha256(raw).hexdigest(), 'meshes': [], 'actions': [], 'bones': []}
    for mi in range(nm):
        start = r.offset
        nv, nn, nt, nf, texture_index = r.unpack('hhhhh')
        for n, label in [(nv, 'vertex'), (nn, 'normal'), (nt, 'texcoord'), (nf, 'polygon')]:
            count(n, label, 32767)
        # Reject counts exceeding remaining physical file capacity before allocating.
        minimum = nv*16+nn*20+nt*8+nf*64+32
        if minimum > len(raw)-r.offset:
            raise BmdError(f'Mesh {mi} arrays exceed file bounds')
        mesh = {'source_offset': start, 'texture_index': texture_index,
                'vertices': [], 'normals': [], 'uvs': [], 'polygons': []}
        for _ in range(nv):
            node, pad, x, y, z = r.unpack('hhfff')
            mesh['vertices'].append({'node': node, 'position': [x,y,z], 'padding_hex': struct.pack('<h',pad).hex()})
        for _ in range(nn):
            node, pad0, x, y, z, bind_vertex, pad1 = r.unpack('hhfffhh')
            mesh['normals'].append({'node': node, 'normal': [x,y,z], 'bind_vertex': bind_vertex,
                                    'padding_hex': struct.pack('<hh',pad0,pad1).hex()})
        for _ in range(nt):
            mesh['uvs'].append(list(r.unpack('ff')))
        for fi in range(nf):
            face_offset = r.offset
            block = r.take(64)
            corners = block[0]
            if corners not in (3, 4):
                issue('corner-count', f'Mesh {mi} polygon {fi}: unsupported corner count {corners}',
                      offset=face_offset, mesh=mi, polygon=fi, value=corners)
            arrays = [list(struct.unpack_from('<4h', block, off)) for off in (2,10,18)]
            # The mesh draw reads corners 0..(int8)count-1; only the four stored corners are checked here.
            active = min(max(struct.unpack_from('<b', block, 0)[0], 0), 4) if client_layout else corners
            for indices, upper, kind, field in zip(arrays, (nv,nn,nt), ('vertex','normal','UV'), (2,10,18)):
                for corner, index in enumerate(indices[:active]):
                    if index < 0 or index >= upper:
                        issue(f'{kind.lower()}-index',
                              f'Mesh {mi} polygon {fi}: invalid active {kind} index {index} at corner {corner}',
                              offset=face_offset+field+2*corner, mesh=mi, polygon=fi, corner=corner, value=index,
                              count=upper)
            mesh['polygons'].append({'corners': corners, 'vertices': arrays[0], 'normals': arrays[1],
                                      'uvs': arrays[2], 'raw_hex': block.hex()})
        mesh['texture'] = r.string()
        mesh['source_end'] = r.offset
        result['meshes'].append(mesh)
    for ai in range(na):
        keys, = r.unpack('h')
        count(keys, 'animation key', 32767)
        locked = r.flag()
        result['actions'].append({'keys': keys, 'lock_positions': locked,
                                   'positions': [list(r.unpack('fff')) for _ in range(keys)] if locked else []})
    for bi in range(nb):
        offset = r.offset
        dummy = r.flag()
        bone = {'source_offset': offset, 'dummy': dummy, 'tracks': []}
        if not dummy:
            bone['name'] = r.string()
            parent, = r.unpack('h')
            if not -1 <= parent < nb:
                issue('parent', f'Bone {bi}: invalid parent {parent}', offset=r.offset-2, bone=bi, value=parent)
            bone['parent'] = parent
            for action in result['actions']:
                keys = action['keys']
                if keys*24 > len(raw)-r.offset:
                    raise BmdError(f'Bone {bi}: animation arrays exceed file bounds')
                bone['tracks'].append({'positions': [list(r.unpack('fff')) for _ in range(keys)],
                                       'rotations': [list(r.unpack('fff')) for _ in range(keys)]})
        result['bones'].append(bone)
    trailer = raw[r.offset:]
    if trailer:
        if not lea_block_padding or len(trailer) > 16 or (len(raw)-4) % 16:
            # The client reader never looks at bytes after the last bone record.
            issue('trailer', f'{len(raw)-r.offset} unparsed trailing bytes at offset {r.offset}', offset=r.offset)
        # Explicit decrypted ECB envelope: retain every unused block-alignment
        # byte. No padding convention or semantic meaning is inferred.
        result['cipher_block_trailer_hex'] = trailer.hex()
    for mi, mesh in enumerate(result['meshes']):
        vertex_start = mesh['source_offset']+10
        normal_start = vertex_start+16*len(mesh['vertices'])
        for vi, vertex in enumerate(mesh['vertices']):
            if not 0 <= vertex['node'] < nb or result['bones'][vertex['node']]['dummy']:
                issue('vertex-bone', f'Mesh {mi} vertex {vi}: unsupported vertex bone {vertex["node"]}',
                      offset=vertex_start+16*vi, mesh=mi, vertex=vi, value=vertex['node'])
        for ni, normal in enumerate(mesh['normals']):
            if not 0 <= normal['node'] < nb or result['bones'][normal['node']]['dummy']:
                issue('normal-bone', f'Mesh {mi} normal {ni}: unsupported normal bone {normal["node"]}',
                      offset=normal_start+20*ni, mesh=mi, normal=ni, value=normal['node'])
            # BindVertex can be -1 in some files; preserve it but reject other invalid indices.
            if not -1 <= normal['bind_vertex'] < len(mesh['vertices']):
                issue('bind-vertex', f'Mesh {mi}: invalid normal bind vertex {normal["bind_vertex"]}',
                      offset=normal_start+20*ni+16, mesh=mi, normal=ni, value=normal['bind_vertex'])
    for bi, bone in enumerate(result['bones']):
        seen = set()
        current = bi
        parent_owner = bi
        while current != -1:
            if issues is not None and not 0 <= current < nb:
                bone['client_unresolved'] = True   # out-of-range parent, listed above
                break
            if current in seen:
                issue('parent-cycle', 'Bone parent cycle', bone=bi)
                break
            seen.add(current)
            ancestor = result['bones'][current]
            if ancestor['dummy']:
                if current != bi:
                    if issues is None or parent_owner == bi:
                        # Client mode lists each direct edge once, from its own bone.
                        issue('dummy-parent', f'Bone {parent_owner}: parent {current} references dummy bone',
                              offset=result['bones'][parent_owner]['source_offset']+33, bone=parent_owner,
                              value=current)
                    bone['client_unresolved'] = True
                break
            parent_owner = current
            current = ancestor['parent']
    if issues is not None:
        for bi, bone in enumerate(result['bones']):
            if not bone['dummy'] and bone['parent'] > bi:
                # Not rejected by the strict reader; the client's pose loop reads that slot
                # before writing it in the same call (previous contents).
                issue('parent-forward', f'Bone {bi}: parent {bone["parent"]} follows it', strict=False,
                      offset=bone['source_offset']+33, bone=bi, value=bone['parent'])
        result['client_semantics'] = issues
    result['parsed_bytes'] = r.offset
    return result


def parse_file(path):
    if path.stat().st_size > MAX_FILE:
        raise BmdError('File exceeds supported size limit')
    model = parse_bytes(path.read_bytes())
    model['source_path'] = str(path)
    return model


def local_matrix(position, rotation):
    # Rz * Ry * Rx, corroborated with the reference's Euler-to-quaternion formula.
    x,y,z = rotation
    cx,sx,cy,sy,cz,sz = math.cos(x),math.sin(x),math.cos(y),math.sin(y),math.cos(z),math.sin(z)
    return [[cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx, position[0]],
            [sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx, position[1]],
            [-sy, cy*sx, cy*cx, position[2]], [0,0,0,1]]


def multiply(a,b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def pose_matrices(model, action=0, frame=0):
    if not 0 <= action < len(model['actions']) or not 0 <= frame < model['actions'][action]['keys']:
        raise BmdError('Requested action/frame is not recorded in model')
    matrices = {}
    # Iterative hierarchy evaluation avoids recursion-depth failure for malformed long chains.
    # Client-layout bones below a dummy record compose a pose slot the client does not
    # write in that call; no matrix is invented for them.
    pending = {i for i,b in enumerate(model['bones']) if not b['dummy'] and not b.get('client_unresolved')}
    while pending:
        progress = False
        for i in sorted(pending):
            bone = model['bones'][i]
            parent = bone['parent']
            if parent >= 0 and parent not in matrices:
                continue
            track = bone['tracks'][action]
            matrix = local_matrix(track['positions'][frame], track['rotations'][frame])
            matrices[i] = multiply(matrices[parent], matrix) if parent >= 0 else matrix
            pending.remove(i)
            progress = True
        if not progress:
            raise BmdError('Cannot resolve bone hierarchy')
    return matrices


def transform(matrix, vector, point):
    result = [sum(matrix[i][j]*vector[j] for j in range(3))+(matrix[i][3] if point else 0) for i in range(3)]
    if not all(math.isfinite(x) for x in result):
        raise BmdError('Non-finite transformed vector')
    return result


def bone_matrix(matrices, node, label):
    if node not in matrices:
        raise BmdError(f'{label} uses bone {node}, whose matrix comes from client memory outside the '
                       'pose (state-dependent); no geometry exported')
    return matrices[node]


def obj_text(model, action=0, frame=0):
    matrices = pose_matrices(model, action, frame)
    lines = [f'# Real installed BMD v{model["version"]} geometry; recorded bone action/frame applied',
             f'# Source SHA-256: {model["source_sha256"]}', f'# Action {action}, frame {frame}; source axes and UVs preserved',
             '# Original materials are listed in JSON; no material behavior inferred']
    vo=no=to=0
    for i, mesh in enumerate(model['meshes']):
        lines.append(f'o mesh_{i}')
        for v in mesh['vertices']:
            coords = transform(bone_matrix(matrices, v['node'], f'Mesh {i} vertex'), v['position'], True)
            lines.append('v '+' '.join(format(x,'.9g') for x in coords))
        for uv in mesh['uvs']:
            lines.append('vt '+' '.join(format(x,'.9g') for x in uv))
        for n in mesh['normals']:
            coords = transform(bone_matrix(matrices, n['node'], f'Mesh {i} normal'), n['normal'], False)
            lines.append('vn '+' '.join(format(x,'.9g') for x in coords))
        for face in mesh['polygons']:
            for k in range(face['corners']):
                for name, upper in (('vertices', len(mesh['vertices'])), ('uvs', len(mesh['uvs'])),
                                    ('normals', len(mesh['normals']))):
                    if not 0 <= face[name][k] < upper:
                        raise BmdError(f'Mesh {i} polygon corner reads {name} entry {face[name][k]} past its '
                                       'array (client memory state); no geometry exported')
            lines.append('f '+' '.join(f'{face["vertices"][k]+vo+1}/{face["uvs"][k]+to+1}/{face["normals"][k]+no+1}' for k in range(face['corners'])))
        vo += len(mesh['vertices']); no += len(mesh['normals']); to += len(mesh['uvs'])
    return '\n'.join(lines)+'\n'


def summarize(model):
    return {'name': model['name']['text'], 'meshes':len(model['meshes']), 'bones':len(model['bones']),
            'actions':len(model['actions']), 'keys_per_action':[a['keys'] for a in model['actions']],
            'vertices':sum(len(m['vertices']) for m in model['meshes']),
            'polygons':sum(len(m['polygons']) for m in model['meshes']),
            'textures':[m['texture']['text'] for m in model['meshes']],
            'source_sha256':model['source_sha256'], 'source_bytes':model['source_bytes']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--asset',action='append',default=[])
    p.add_argument('--validate-all',action='store_true')
    a=p.parse_args();root=a.root.resolve(strict=True);out=a.output.resolve()
    if out.exists() or root==out or root in out.parents:
        p.error('Output must be a new directory outside original installation')
    selected=set()
    for rel in a.asset:
        path=(root/rel).resolve(strict=True)
        if root not in path.parents:p.error('Asset outside installation')
        selected.add(path)
    paths=set(selected)
    if a.validate_all:
        for path in root.rglob('*'):
            if path.is_file() and path.suffix.lower()=='.bmd' and root in path.resolve().parents:
                with path.open('rb') as f:
                    if f.read(4)==b'BMD\x0a':paths.add(path.resolve())
    if not paths:p.error('Select assets or --validate-all')
    out.mkdir(parents=True);records=[]
    for path in sorted(paths):
        record={'path':str(path.relative_to(root))}
        try:
            model=parse_file(path);record.update(summarize(model),status='parsed')
            if path in selected:
                dest=out/path.relative_to(root)
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.with_suffix('.json').write_text(json.dumps(model,indent=2,allow_nan=False)+'\n')
                record['json']=str(dest.with_suffix('.json').relative_to(out))
                try:
                    obj=obj_text(model)
                    dest.with_suffix('.obj').write_text(obj)
                    record['obj']=str(dest.with_suffix('.obj').relative_to(out))
                except BmdError as exc:record['pose_error']=str(exc)
        except (BmdError,OSError) as exc:record.update(status='rejected',error=str(exc))
        records.append(record)
    good=sum(r['status']=='parsed' for r in records)
    summary={'total':len(records),'parsed':good,'rejected':len(records)-good,'json_exports':sum('json' in r for r in records),'obj_exports':sum('obj' in r for r in records)}
    (out/'manifest.json').write_text(json.dumps({'summary':summary,'files':records},indent=2)+'\n')
    print(json.dumps(summary))
    return 0 if good==len(records) else 1

if __name__=='__main__':raise SystemExit(main())
