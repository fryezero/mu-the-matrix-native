#!/usr/bin/env python3
"""Compare the authored network protocol module with the client's instructions.

Three client routines run in Unicorn over the pinned restored first section and
the verified second image section, and every output is compared byte-for-byte
against the reconstructed C in native/core/mu_protocol.c (built as
native/build/libmuprotocol.<ext>):

  * the packet builder AddData 0x00d51c9b, which appends body bytes and, when
    its encode flag is set, runs the send obfuscation XorData 0x00d52055 over
    exactly the appended range (the 32-byte key lives in XorData as immediates);
  * the receive framing loop nRecv 0x01290792, which accumulates bytes and
    splits them into C1/C2/C3/C4 frames. Its ws2_32 recv/WSAGetLastError and the
    packet-queue push are stubbed to feed synthetic bytes and capture frames; no
    other client instruction is stubbed and the CRT memcpy/memset it calls are
    real client code.

No client bytes are committed. Supply the restored text and image data locally;
the check skips when they are absent, like the other private integration checks.
The C3/C4 payloads carry the client's separate CryptoModule cipher, which this
module treats as a documented boundary and does not reconstruct (see
docs/research/client-net-protocol.md).
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402

TEXT_BASE = 0x401000
TEXT_BYTES = pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
TARGET_SHA256 = pins.TARGET.sha256
DATA_BASE = 0x1a7c000
DATA_BYTES = pins.DATA.size
DATA_SHA256 = pins.DATA.sha256

ADD_DATA = 0xd51c9b
XOR_DATA = 0xd52055
N_RECV = 0x1290792
PIN = {
    ADD_DATA: (115, 'c78a545136f0c12408ca1c67d9e7258ee3a3790d06f239e04eca44b5ae7ce1c9'),
    XOR_DATA: (220, 'c63549d8bdb4b4e068d69abbf8b7c04c4ff4a1ba0d8733134414964423494a6f'),
    N_RECV: (617, '273475659cfbe7e494f18f0e3d9b627c5f884094b90068f4563c2c3b748d930d'),
}

# ws2_32 IAT slots the receive loop reads (restored client import table).
IAT_RECV = 0x1a7c9e8
IAT_SEND = 0x1a7c9ec
IAT_WSAGLE = 0x1a7c9f0
IAT_CLOSE = 0x1a7c9f4
IAT_SHUTDOWN = 0x1a7c9d0

OBJ_SIZE = 0x1460
OBJ_CMP = 0x145c  # size word + 0x145a body; 4 trailing slack bytes are never written
RECV_BUF_OFF = 0x2014
RECV_LEN_OFF = 0x4014
QUEUE_OFF = 0x4020
SOCKET_OFF = 0xc

PUSH_FN = 0x1291777   # CMessageQueue::Push(frame, size), thiscall ecx=queue
FLUSH_FN = 0x129170b  # queue flush, thiscall
OP_NEW = 0x191ba7b


load_pinned = pins.loader(ValueError, '{label} does not match the pinned capture')


class Harness:
    def __init__(self, text, data):
        import unicorn
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE,
                             UC_HOOK_MEM_UNMAPPED, UC_PROT_ALL)
        from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ECX,
                                      UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_FS,
                                      UC_X86_REG_SS, UC_X86_REG_DS, UC_X86_REG_ES,
                                      UC_X86_REG_GDTR)
        self.u = unicorn
        self.C = dict(UC_HOOK_CODE=UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED=UC_HOOK_MEM_UNMAPPED,
                      ESP=UC_X86_REG_ESP, EBP=UC_X86_REG_EBP, ECX=UC_X86_REG_ECX,
                      EIP=UC_X86_REG_EIP, EAX=UC_X86_REG_EAX)
        for addr, (length, digest) in PIN.items():
            body = text[addr - TEXT_BASE:addr - TEXT_BASE + length]
            if hashlib.sha256(body).hexdigest() != digest:
                raise ValueError('pinned routine %#x changed' % addr)

        self.text = text
        self.data = data
        self.RET = 0x7e000000
        self.STUB = 0x7f000000
        self.HEAP = 0x40000000
        self.STACK = 0x30000000
        uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc = uc
        uc.mem_map(TEXT_BASE, (len(text) + 0xfff) & ~0xfff, UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (len(data) + 0xfff) & ~0xfff, UC_PROT_ALL)
        uc.mem_write(DATA_BASE, data)
        uc.mem_map(self.HEAP, 0x4000000)
        uc.mem_map(self.STACK, 0x200000)
        uc.mem_map(self.RET, 0x1000)
        uc.mem_map(self.STUB, 0x10000)
        uc.mem_write(self.STUB, b'\xc3' * 0x10000)
        teb = 0x7ffd0000
        uc.mem_map(teb, 0x10000)
        uc.mem_write(teb + 0x18, struct.pack('<I', teb))
        self._setup_fs(teb, UC_X86_REG_GDTR, UC_X86_REG_FS, UC_X86_REG_SS,
                       UC_X86_REG_DS, UC_X86_REG_ES)
        self.heap_ptr = self.HEAP + 0x1000
        # IAT stubs
        self.stub_names = {}
        for i, slot in enumerate((IAT_RECV, IAT_SEND, IAT_WSAGLE, IAT_CLOSE, IAT_SHUTDOWN)):
            addr = self.STUB + i * 4
            self.stub_names[addr] = slot
            uc.mem_write(slot, struct.pack('<I', addr))
        self.fn_hooks = {}
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        uc.hook_add(UC_HOOK_CODE, self._dispatch)
        self._op_new_hook()

    def _setup_fs(self, teb, GDTR, FS, SS, DS, ES):
        uc = self.uc
        gdt = 0x7ffc0000
        uc.mem_map(gdt, 0x1000)

        def desc(base, limit, access, flags):
            d = limit & 0xffff
            d |= (base & 0xffffff) << 16
            d |= (access & 0xff) << 40
            d |= ((limit >> 16) & 0xf) << 48
            d |= (flags & 0xf) << 52
            d |= ((base >> 24) & 0xff) << 56
            return struct.pack('<Q', d)
        uc.mem_write(gdt + 8, desc(0, 0xfffff, 0x9a, 0xc))
        uc.mem_write(gdt + 16, desc(0, 0xfffff, 0x92, 0xc))
        uc.mem_write(gdt + 24, desc(teb, 0xfff, 0x92, 0x4))
        uc.reg_write(GDTR, (0, gdt, 0x1f, 0))
        uc.reg_write(SS, 2 << 3)
        uc.reg_write(DS, 2 << 3)
        uc.reg_write(ES, 2 << 3)
        uc.reg_write(FS, 3 << 3)

    def _unmapped(self, uc, access, address, size, value, ud):
        if 0x1ced000 <= address < 0xbdd2000:
            page = address & ~0xfff
            try:
                uc.mem_map(page, 0x2000)
            except self.u.UcError:
                uc.mem_map(page, 0x1000)
            return True
        return False

    def _op_new_hook(self):
        def h(hz):
            esp = self.uc.reg_read(self.C['ESP'])
            size = struct.unpack('<I', self.uc.mem_read(esp + 4, 4))[0]
            self.do_ret(self.malloc(size), pop=0)
        self.fn_hooks[OP_NEW] = h

    def _dispatch(self, uc, address, size, ud):
        if address in self.stub_names:
            self._stub(address)
            return
        f = self.fn_hooks.get(address)
        if f:
            f(self)

    def _stub(self, address):
        slot = self.stub_names[address]
        uc = self.uc
        esp = uc.reg_read(self.C['ESP'])
        if slot == IAT_RECV:
            s, bufp, length, flags = struct.unpack('<4I', uc.mem_read(esp + 4, 16))
            if not self.feed:
                self.last_err = 0x2733
                uc.reg_write(self.C['EAX'], 0xffffffff)
            else:
                n = min(length, len(self.feed))
                uc.mem_write(bufp, self.feed[:n])
                self.feed = self.feed[n:]
                uc.reg_write(self.C['EAX'], n)
        elif slot == IAT_WSAGLE:
            uc.reg_write(self.C['EAX'], self.last_err)
        elif slot in (IAT_SEND, IAT_CLOSE, IAT_SHUTDOWN):
            uc.reg_write(self.C['EAX'], 0)

    def malloc(self, n, align=16):
        p = (self.heap_ptr + align - 1) & ~(align - 1)
        self.heap_ptr = p + max(n, 1)
        return p

    def arg(self, i):
        esp = self.uc.reg_read(self.C['ESP'])
        return struct.unpack('<I', self.uc.mem_read(esp + 4 + 4 * i, 4))[0]

    def do_ret(self, value=None, pop=0):
        uc = self.uc
        esp = uc.reg_read(self.C['ESP'])
        ret = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        if value is not None:
            uc.reg_write(self.C['EAX'], value & 0xffffffff)
        uc.reg_write(self.C['ESP'], esp + 4 + pop)
        uc.reg_write(self.C['EIP'], ret)

    def call(self, addr, args=(), ecx=None):
        uc = self.uc
        esp = self.STACK + 0x200000 - 0x2000
        frame = struct.pack('<I', self.RET) + b''.join(struct.pack('<I', a & 0xffffffff) for a in args)
        esp -= len(frame)
        uc.mem_write(esp, frame)
        uc.reg_write(self.C['ESP'], esp)
        uc.reg_write(self.C['EBP'], 0)
        if ecx is not None:
            uc.reg_write(self.C['ECX'], ecx & 0xffffffff)
        uc.emu_start(addr, self.RET, count=20_000_000)
        if uc.reg_read(self.C['EIP']) != self.RET:
            raise RuntimeError('did not return cleanly from %#x' % addr)
        return uc.reg_read(self.C['EAX'])

    def w(self, a, b):
        self.uc.mem_write(a, bytes(b))

    def r(self, a, n):
        return bytes(self.uc.mem_read(a, n))


def load_native(library):
    lib = ctypes.CDLL(str(library))
    lib.mu_packet_begin.argtypes = [ctypes.c_void_p, ctypes.c_uint8, ctypes.c_uint8]
    lib.mu_packet_add.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
    lib.mu_packet_add.restype = ctypes.c_int
    lib.mu_recv_init.argtypes = [ctypes.c_void_p]
    lib.mu_recv_push.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
    lib.mu_recv_push.restype = ctypes.c_int
    return lib


class NativePacket(ctypes.Structure):
    _fields_ = [('obj', ctypes.c_uint8 * 0x145c), ('overflow', ctypes.c_uint32)]


def native_build(lib, chunks):
    """Mirror the client AddData sequence with the C module and return the raw
    0x1460-byte object buffer."""
    p = NativePacket()
    lib.mu_recv_init  # touch to ensure symbol resolves early
    ctypes.memset(ctypes.byref(p), 0, ctypes.sizeof(p))
    for data, encode in chunks:
        lib.mu_packet_add(ctypes.byref(p), data, len(data), 1 if encode else 0)
    return bytes(bytearray(p.obj))


def validate(text_path, data_path, library):
    text = load_pinned(text_path, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(data_path, DATA_BYTES, DATA_SHA256, 'image data')
    lib = load_native(library)
    rng = random.Random(0x4d55)
    failures = []

    # ---- AddData + XorData: build-side framing and send obfuscation ----
    add_cases = 0
    for _ in range(500):
        h = Harness(text, data)
        obj = h.malloc(OBJ_SIZE)
        h.w(obj, b'\x00' * OBJ_SIZE)
        src = h.malloc(512)
        p = NativePacket()
        ctypes.memset(ctypes.byref(p), 0, ctypes.sizeof(p))
        for _ in range(rng.randint(1, 4)):
            length = rng.randint(1, 40)
            encode = rng.randint(0, 1)
            chunk = bytes(rng.randrange(256) for _ in range(length))
            h.w(src, chunk)
            h.call(ADD_DATA, (src, length, encode), ecx=obj)
            lib.mu_packet_add(ctypes.byref(p), chunk, length, encode)
        add_cases += 1
        client = h.r(obj, OBJ_CMP)
        native = bytes(bytearray(p.obj))
        if client != native:
            idx = next(i for i in range(OBJ_CMP) if client[i] != native[i])
            failures.append({'routine': 'AddData', 'first_diff': idx,
                             'client': client[idx], 'native': native[idx]})
            break

    # ---- nRecv: receive framing ----
    recv_cases = 0
    for _ in range(300):
        frames = []
        for _ in range(rng.randint(1, 5)):
            head = rng.choice([0xC1, 0xC2, 0xC3, 0xC4])
            if head in (0xC1, 0xC3):
                size = rng.randint(3, 250)
                frames.append(bytes([head, size]) + bytes(rng.randrange(256) for _ in range(size - 2)))
            else:
                size = rng.randint(3, 900)
                frames.append(bytes([head, (size >> 8) & 0xff, size & 0xff])
                              + bytes(rng.randrange(256) for _ in range(size - 3)))
        stream = b''.join(frames)

        h = Harness(text, data)
        h.feed = stream
        h.last_err = 0
        sock = h.malloc(0x4100)
        h.w(sock, b'\x00' * 0x4100)
        h.w(sock + QUEUE_OFF, struct.pack('<I', 0x11112222))
        captured = []

        def push(hz, cap=captured):
            frame = hz.arg(0)
            size = hz.arg(1)
            cap.append(hz.r(frame, size))
            hz.do_ret(0, pop=8)
        h.fn_hooks[PUSH_FN] = push
        h.fn_hooks[FLUSH_FN] = lambda hz: hz.do_ret(0, pop=0)
        h.call(N_RECV, ecx=sock)

        native_frames = native_dechunk(stream)
        recv_cases += 1
        if captured != native_frames:
            failures.append({'routine': 'nRecv', 'client_frames': len(captured),
                             'native_frames': len(native_frames)})
            break

    return {
        'target_sha256': TARGET_SHA256,
        'text_sha256': TEXT_SHA256,
        'image_data_sha256': DATA_SHA256,
        'pinned_routines': {hex(a): PIN[a][1] for a in PIN},
        'add_data_cases': add_cases,
        'recv_framing_cases': recv_cases,
        'mismatches': len(failures),
        'failures': failures,
        'authored_library_sha256': hashlib.sha256(Path(library).read_bytes()).hexdigest(),
        'scope': ('AddData/XorData build-side framing + send XOR and nRecv receive '
                  'framing over synthetic C1-C4 streams. The C3/C4 CryptoModule '
                  'payload cipher is a documented boundary, not reconstructed here.'),
    }


def native_dechunk(stream):
    """Receive split identical to mu_recv_drain / the client loop."""
    out = []
    off = 0
    rl = len(stream)
    while rl >= 3:
        h = stream[off]
        if h in (0xC1, 0xC3):
            size = stream[off + 1]
        elif h in (0xC2, 0xC4):
            size = (stream[off + 1] << 8) + stream[off + 2]
        else:
            break
        if size <= 0 or size > rl:
            break
        out.append(stream[off:off + size])
        off += size
        rl -= size
    return out


def main():
    ext = 'dylib' if sys.platform == 'darwin' else 'so'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--text', type=Path, default=pins.TEXT08.default())
    parser.add_argument('--data', type=Path, default=pins.DATA.default())
    parser.add_argument('--library', type=Path,
                        default=ROOT / 'native/build' / ('libmuprotocol.' + ext))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    if not args.text.exists() or not args.data.exists():
        print('skip: restored text/image data not present', file=sys.stderr)
        return 0
    if not args.library.exists():
        print('skip: build native/ first (make -C native)', file=sys.stderr)
        return 0
    try:
        import unicorn  # noqa: F401
    except ImportError:
        print('skip: unicorn not installed', file=sys.stderr)
        return 0

    try:
        result = validate(args.text, args.data, args.library)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as fh:
            fh.write(encoded)
    else:
        print(encoded, end='')
    return int(bool(result['mismatches']))


if __name__ == '__main__':
    sys.exit(main())
