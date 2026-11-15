"""Instruction-checked low-level callers that draw two meshes themselves (RENDER-ITEMS-002AB).

RenderObjDraw's low-level type chain (glow level below three, 0x017de3e4) continues after the nine
RENDER-ITEMS-002AA callers with four cases at 0x017deb61..0x017dee71. Each draws mesh 0 twice through
0x00966e4a and joins at 0x017e16fa; it calls no body helper and writes no model field. The cases differ
only in the second draw's texture. From glow level three on these types take the ordinary helper chain.
"""
import capstone

# Dispatch start, body start, next dispatch, members, second-draw texture.
GROUPS = (
    (0x017deb61, 0x017deb7d, 0x017dec28, (0x27ef, 0x286e), 0x81d4),
    (0x017dec28, 0x017dec44, 0x017decef, (0x27f0, 0x2874), 0x81d5),
    (0x017decef, 0x017decff, 0x017dedaa, (0x27f1,), 0x81d6),
    (0x017dedaa, 0x017dedc6, 0x017dee71, (0x27f2, 0x286f), 0x81d7),
)
# Two further cases copy the light argument into the model, call the body helper (flags argument 3, level
# word -1) and then draw meshes 0 and 1 (0x017dee71, 0x017defc1): dispatch start, end, type, and whether the
# second draw swaps the OBJECT u and v words.
HELPER_GROUPS = (
    (0x017dee71, 0x017defc1, 0x2406, False),
    (0x017defc1, 0x017df111, 0x2477, True),
)
HELPER_TYPES = tuple(t for _, _, t, _ in HELPER_GROUPS)
TYPES = tuple(sorted(t for *_, members, _ in GROUPS for t in members))
JOIN = 0x017e16fa
LEVEL_GATE = (0x017de3e4, ['cmp dword ptr [ebp - 0xa8], 3', 'jl 0x17de3fd'])


def body_program(texture):
    """Both draws, every pushed argument: (mesh 0, flags 2, OBJECT alpha, OBJECT blend mesh, OBJECT blend
    light, 0.0, 0.0, -1) and (mesh 0, flags 2, OBJECT alpha, -2, OBJECT blend light, OBJECT u, OBJECT v, texture)."""
    def field(offset):
        return ['mov eax, dword ptr [ebp + 8]', 'push ecx', f'movss xmm0, dword ptr [eax + {offset:#x}]',
                'movss dword ptr [esp], xmm0']
    zero = ['push ecx', 'xorps xmm0, xmm0', 'movss dword ptr [esp], xmm0']
    call = ['push 2', 'push 0', 'mov ecx, dword ptr [ebp - 0xb0]', 'call 0x966e4a']
    return (['push -1'] + zero + zero + field(0xa8) +
            ['mov eax, dword ptr [ebp + 8]', 'push dword ptr [eax + 0x74]'] + field(0xdc) + call +
            [f'push {texture:#x}'] + field(0xb0) + field(0xac) + field(0xa8) + ['push -2'] + field(0xdc) + call +
            [f'jmp {JOIN:#x}'])


def helper_program(swap):
    """Light copy, helper call and both draws of a HELPER_GROUPS case, every instruction."""
    def field(offset):
        return ['mov eax, dword ptr [ebp + 8]', 'push ecx', f'movss xmm0, dword ptr [eax + {offset:#x}]',
                'movss dword ptr [esp], xmm0']
    out = []
    for channel in range(3):
        out += ['push 4', 'pop eax' if channel == 0 else 'pop esi',
                'imul esi, eax, 0' if channel == 0 else f'shl esi, {channel - 1}',
                'add esi, dword ptr [ebp + 0x10]', f'push {channel}', 'mov ecx, dword ptr [ebp - 0xb0]',
                'add ecx, 0x54', 'call 0xcfc922', 'mov ecx, dword ptr [esi]', 'mov dword ptr [eax], ecx']
    out += ['push -1', 'push 3', 'push dword ptr [ebp + 0x30]', 'push dword ptr [ebp + 0x2c]',
            'push dword ptr [ebp + 0x28]', 'push ecx', 'movss xmm0, dword ptr [ebp + 0x14]',
            'movss dword ptr [esp], xmm0', 'push dword ptr [ebp + 0xc]', 'push dword ptr [ebp + 8]',
            'push dword ptr [ebp - 0xb0]', 'call 0x16e036c', 'add esp, 0x24']
    hidden = ['mov eax, dword ptr [ebp + 8]', 'push dword ptr [eax + 0x68]']
    blend = ['mov eax, dword ptr [ebp + 8]', 'push dword ptr [eax + 0x74]']
    out += (hidden + field(0xb0) + field(0xac) + field(0xa8) + blend + field(0xdc) +
            ['push 2', 'push 0', 'mov ecx, dword ptr [ebp - 0xb0]', 'call 0x966e4a'])
    first, second = (0xac, 0xb0) if swap else (0xb0, 0xac)
    out += (hidden + field(first) + field(second) + field(0xa8) + blend +
            ['push ecx', 'movss xmm0, dword ptr [0x1a7e918]', 'movss dword ptr [esp], xmm0',
             'push 0x46', 'push 1', 'mov ecx, dword ptr [ebp - 0xb0]', 'call 0x966e4a', f'jmp {JOIN:#x}'])
    return out


def read_helpers(wa):
    """{type: swap} of the light/helper/two-mesh cases; ValueError when an instruction or constant differs."""
    import struct
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    result, previous = {}, GROUPS[-1][2]
    for start, end, t, swap in HELPER_GROUPS:
        if previous != start:
            raise ValueError('helper mesh caller groups are not contiguous')
        raw = wa[0][start - 0x401000:end - 0x401000]
        decoded = list(md.disasm(raw, start))
        actual = [f'{i.mnemonic} {i.op_str}'.strip() for i in decoded if i.mnemonic != 'nop']
        expected = [f'cmp dword ptr [ebp + 0xc], {t:#x}', f'jne {end:#x}'] + helper_program(swap)
        if sum(i.size for i in decoded) != len(raw) or actual != expected:
            raise ValueError(f'unreviewed helper mesh caller instructions at {start:#x}')
        result[t] = swap
        previous = end
    if struct.unpack_from('<I', wa[1], 0x1a7e918 - 0x1a7c000)[0] != 0x3f333333:
        raise ValueError('unreviewed helper mesh caller constant')
    return result


def read(wa):
    """{type: texture}; ValueError when a dispatch, a draw argument or the level gate differs."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

    def check(start, end, expected):
        raw = wa[0][start - 0x401000:end - 0x401000]
        decoded = list(md.disasm(raw, start))
        actual = [f'{i.mnemonic} {i.op_str}'.strip() for i in decoded if i.mnemonic != 'nop']
        if sum(i.size for i in decoded) != len(raw) or actual != expected:
            raise ValueError(f'unreviewed mesh caller instructions at {start:#x}')
    check(LEVEL_GATE[0], LEVEL_GATE[0] + 9, LEVEL_GATE[1])
    result, previous = {}, None
    for start, body, end, members, texture in GROUPS:
        if previous is not None and previous != start:
            raise ValueError('mesh caller groups are not contiguous')
        expected = []
        for index, t in enumerate(members):
            expected += ['mov eax, dword ptr [ebp + 8]', f'cmp dword ptr [eax + 0x5c], {t:#x}',
                         f'je {body:#x}' if index < len(members) - 1 else f'jne {end:#x}']
        check(start, body, expected)
        check(body, end, body_program(texture))
        for t in members:
            result[t] = texture
        previous = end
    return result


def render(rows, helpers):
    return ('/* Generated by item_mesh_callers.read; RenderObjDraw low-level two-mesh callers. */\n'
            'static const struct { int32_t type; int32_t texture; } mu_rc_mesh_callers[] = {\n' +
            ''.join(f'    {{0x{t:04x}, 0x{texture:04x}}},\n' for t, texture in sorted(rows.items())) + '};\n'
            '/* Light copy, body helper, then meshes 0 and 1; swap exchanges the second draw\'s u and v. */\n'
            'static const struct { int32_t type; int32_t swap; } mu_rc_helper_mesh_callers[] = {\n' +
            ''.join(f'    {{0x{t:04x}, {int(swap)}}},\n' for t, swap in sorted(helpers.items())) + '};\n')


def main():
    import argparse
    from pathlib import Path
    import pins
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    wa = tuple(p.read() for p in (pins.TEXT, pins.DATA))
    result = render(read(wa), read_helpers(wa))
    if args.check:
        if args.output.read_text() != result:
            raise SystemExit('item mesh callers differ from pinned instructions')
    else:
        args.output.write_text(result)


if __name__ == '__main__':
    main()
