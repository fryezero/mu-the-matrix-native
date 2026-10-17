"""Independent Python statement of the mesh-draw rules (second implementation).

Written from mac-play/hotpatch/meshdraw-notes.md and the static reading in
docs/research/client-skinning.md, not from native/core/mu_meshdraw.c. Every
binary32 operation is rounded with f32 in the documented order. Output is the
op stream `mu-render corners` records: (mesh, op, four floats).
"""
import struct

OP_TEXCOORD, OP_COLOR3, OP_COLOR4, OP_VERTEX, OP_BEGIN, OP_END, OP_PREPARE = range(1, 8)
ZERO, ONE, SRC_COLOR, ONE_MINUS_SRC_COLOR, SRC_ALPHA, ONE_MINUS_SRC_ALPHA = range(6)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


K99 = f32(0.99)


def floats(data):
    return list(struct.unpack('<%df' % (len(data)//4), data))


def state(flags, alpha):
    """Fixed-function state reading (client-skinning.md, 'State wrappers')."""
    translucent = not (alpha >= K99)
    blend, src, dst, cull = 0, 0, 0, 0
    if flags & 0x40:
        blend, src, dst = 1, ONE, ONE
    elif flags & 0x80:
        blend, src, dst = 1, ZERO, ONE_MINUS_SRC_COLOR
    elif not flags & 1 and flags & 0x10:
        blend, src, dst = 1, ZERO, SRC_COLOR
    elif not flags & 1 and flags & 0x400000:
        blend, src, dst = 1, ZERO, SRC_ALPHA
    elif translucent:
        blend, src, dst = 1, SRC_ALPHA, ONE_MINUS_SRC_ALPHA
    else:
        cull = 0 if flags & 1 else 1
    if flags & 0x40000:
        cull = 1
    depth_test = 0 if flags & 0x2000 else 1
    return blend, depth_test, 1, cull, 0, 1, src, dst


def pack_state(s, alpha_test=0, cull_override=-1):
    blend, depth_test, depth_mask, cull, a_test, texture, src, dst = s
    if alpha_test:
        a_test = 1
    if cull_override >= 0:
        cull = cull_override
    return float(blend | depth_test << 1 | depth_mask << 2 | cull << 3 | a_test << 4 | texture << 5 | src << 8 | dst << 12)


def corner_stream(mesh_index, polygons, uvs, vertices, light_colours, normal_table, colour, origin, mode, flags,
                  alpha, uoff, voff, apply_uv, light):
    """Per-corner ops of one mesh. polygons: [(corners, v[4], n[4], t[4])]; returns (ops, refused)."""
    if mode == 0x8000 or (flags & 0x420) == 0x400:
        return [], True
    ops = []
    col3 = alpha >= K99

    def colour_op(c):
        if col3:
            ops.append((mesh_index, OP_COLOR3, f32(c[0]), f32(c[1]), f32(c[2]), 0.0))
        else:
            ops.append((mesh_index, OP_COLOR4, f32(c[0]), f32(c[1]), f32(c[2]), f32(alpha)))

    for corners, vi, ni, ti in polygons:
        for j in range(corners):
            if mode == 2:
                u, v = uvs[ti[j]]
                if apply_uv:
                    ops.append((mesh_index, OP_TEXCOORD, f32(u+uoff), f32(v+voff), 0.0, 0.0))
                else:
                    ops.append((mesh_index, OP_TEXCOORD, u, v, 0.0, 0.0))
                if light:
                    colour_op(light_colours[ni[j]])
            elif mode == 4:
                colour_op(colour)
                u, v = normal_table[ni[j]]
                ops.append((mesh_index, OP_TEXCOORD, u, v, 0.0, 0.0))
            elif mode in (0x1000, 0x80000, 0x100000):
                colour_op(colour)
                u, v = normal_table[ni[j]]
                ops.append((mesh_index, OP_TEXCOORD, f32(u+uoff), f32(v+voff), 0.0, 0.0))
            p = vertices[vi[j]]
            if flags & 0x20:
                l0, l1, l2 = f32(p[0]-origin[0]), f32(p[1]-origin[1]), f32(p[2]-origin[2])
                l0 = f32(f32(f32(f32(l0+2000.0)*l2)/f32(l2-4000.0))+l0)
                l2 = 5.0
                ops.append((mesh_index, OP_VERTEX, f32(l0+origin[0]), f32(l1+origin[1]), f32(l2+origin[2]), 0.0))
            elif flags & 0x200000:
                z = [vertices[vi[k]][2] for k in range(3)]
                if voff > z[0] and voff > z[1] and voff > z[2]:
                    continue
                ops.append((mesh_index, OP_VERTEX, p[0], p[1], p[2], 0.0))
            else:
                ops.append((mesh_index, OP_VERTEX, p[0], p[1], p[2], 0.0))
    return ops, False


def light_colours(lights, secondary, colour, select):
    if select == 1:
        return [[f32(f32(s*c)+f32(0.2)) for c in colour] for s in secondary]
    return [[f32(l*c) for c in colour] for l in lights]


def model_stream(model, dump, options):
    """Expected op stream for a whole model (scene driver order, mu_scene.h)."""
    o = dict(mode=2, flags=0, alpha=1.0, uoff=0.0, voff=0.0, uv_mesh=-1, lighting=1, colour=(1.0, 1.0, 1.0),
             skip=-1, secondary=0, origin=(0.0, 0.0, 0.0), alpha_test=0, cull=-1)
    o.update(options)
    alpha = f32(o['alpha'])
    colour = [f32(c) for c in o['colour']]
    ops = []
    for index, mesh in enumerate(model['meshes']):
        out = dump['meshes'][index]
        vertices = [floats(out['vertices'][12*k:12*k+12]) for k in range(len(out['vertices'])//12)]
        normals = [floats(out['normals'][12*k:12*k+12]) for k in range(len(out['normals'])//12)]
        light = bool(o['lighting']) and index != o['skip']
        colours = light_colours(floats(out['lights']), floats(out['secondary']), colour, o['secondary']) if light else []
        table = [[f32(0.5+f32(0.5*n[0])), f32(0.5+f32(0.5*n[1]))] for n in normals]
        ops.append((index, OP_PREPARE, pack_state(state(o['flags'], alpha), o['alpha_test'], o['cull']), 0.0, 0.0, 0.0))
        if not o['lighting']:
            if alpha >= K99:
                ops.insert(len(ops)-1, (index-1 if index else 0, OP_COLOR3, *colour, 0.0))
            else:
                ops.insert(len(ops)-1, (index-1 if index else 0, OP_COLOR4, *colour, alpha))
        ops.append((index, OP_BEGIN, 0.0, 0.0, 0.0, 0.0))
        polygons = [(p['corners'], p['vertices'], p['normals'], p['uvs']) for p in mesh['polygons']]
        uvs = [[f32(u), f32(v)] for u, v in mesh['uvs']]
        stream, _ = corner_stream(index, polygons, uvs, vertices, colours, table, colour, [f32(x) for x in o['origin']],
                                  o['mode'], o['flags'], alpha, f32(o['uoff']), f32(o['voff']), index == o['uv_mesh'],
                                  light)
        ops += stream
        ops.append((index, OP_END, 0.0, 0.0, 0.0, 0.0))
    return ops


def read_corners(path):
    with open(path, 'rb') as handle:
        data = handle.read()
    return [struct.unpack_from('<II4f', data, offset) for offset in range(0, len(data), 24)]
