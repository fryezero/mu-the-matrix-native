"""Recorded no-owner shield sprite callers and their bone-position boundary."""
import struct
import validate_renderchar as v

TYPES = (0x16f7, 0x16fb)


def original_link(wa, t, values, time, variant=0):
    w = v.link_world(wa, t)
    m = w.m
    sequence, consumed, calls, bone = iter(values), [], [], []
    item_object = v.CHAR + 0x19d0

    def rand(mm):
        value = next(sequence)
        consumed.append(value)
        return value

    def position(mm):
        assert mm.ecx() == v.MODEL
        assert mm.arg(1) == item_object and mm.arg(3) == 0
        bone[:] = [mm.arg(2)]
        mm.write(mm.arg(0), bytes(12))
        return 0

    def sprite(mm):
        assert mm.arg(4) == (v.CHAR + 0x3254 if t == 0x16f7 else item_object)
        assert mm.read(mm.arg(8), 12) == struct.pack('<iif', 1, 1, 1)
        calls.append((mm.arg(0), bone[0], struct.unpack('<3I', mm.read(mm.arg(1), 12)),
                      mm.arg(2), struct.unpack('<3I', mm.read(mm.arg(3), 12)),
                      mm.arg(5), mm.arg(6), mm.arg(7), 0))
        return 0

    m.stub(0x01989721, rand, 0)
    m.stub(0x012b678d, position, 16)
    m.stub(0x01692eb7, sprite, 0)
    m.wf(0x06fce370, time)
    part = v.CHAR + 0x19ac
    m.write(part, struct.pack('<hBBBB', t, variant*4, variant&1, 0, 47))
    result = m.run(0x012bd910, [0, 0, v.f2u(15), v.CHAR, part, t, variant*4,
                              variant&1, variant&1, 1, 0, variant>>1])
    if not result['ok']:
        raise AssertionError((hex(t), result))
    if any(c[0] not in ('rotpos', 'pose', 'tick', 'transform', 'objdraw') for c in w.calls):
        raise AssertionError(('unexpected shield service', w.calls))
    return 0, calls, len(consumed)
