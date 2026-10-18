"""Unicorn machine for the NATIVE-RENDERCHAR-001 validators.

Runs the client's world render routines (RenderCharacter 0x01363260 and what
it reaches) over the pinned restored text (0x00401000) and second image
section (0x01a7c000).

Memory model (all of it declared, nothing guessed silently):

* the text and the data section are mapped from the pinned captures;
* case regions (models, objects, the character record, item records) are
  written by the case builder;
* any other read or write between 0x01ced000 and 0x0c000000 (the image's
  uninitialised data) maps a zero page on first touch and is recorded; that is
  the state of a freshly loaded image before the game fills it. The list of
  touched pages is part of every report;
* MSVC thread-safe statics run their own constructors on first use: the TLS
  init epoch starts at INT_MIN (as in the CRT), _Init_thread_header/footer
  (0x0191c511/0x0191c4c0) are replaced by single-thread equivalents,
  malloc (0x01983110) is a bump allocator, free and atexit do nothing;
* named engine services are replaced by recorders (see SERVICES in the
  validator); every replacement is listed in the report.

Any other unmapped access stops the case.
"""
import collections
import hashlib
import struct
from pathlib import Path

TEXT_BASE, TEXT_BYTES = 0x401000, 23572480
TEXT_SHA256 = '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724'
DATA_BASE, DATA_BYTES = 0x1a7c000, 2557764
DATA_SHA256 = 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f'
PAGE = 0x1000
BSS_LOW, BSS_HIGH = 0x01ced000, 0x0c000000
STACK, STACK_BYTES = 0x30000000, 0x400000
ENTRY_ESP = STACK + STACK_BYTES - 0x1000
SENTINEL = 0x7ffe0000
TIB, GDT = 0x7ffd0000, 0x7ffc0000
SEH_HEAD = 0x7ffd0f00
HEAP, HEAP_BYTES = 0x40000000, 0x4000000
FPCW, MXCSR = 0x027f, 0x1f80
INIT_EPOCH = 0x80000000


def align(value, boundary=PAGE):
    return (value + boundary - 1) & -boundary


def f2u(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def u2f(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


def load_pinned(path, size, digest, label):
    payload = Path(path).read_bytes()
    if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
        raise SystemExit(f'{label}: unexpected size or SHA-256 ({path})')
    return payload


def descriptor(base, limit, access=0x93, flags=0x4):
    return struct.pack('<Q', (limit & 0xffff) | ((base & 0xffffff) << 16) | (access << 40) |
                       (((limit >> 16) & 0xf) << 48) | (flags << 52) | (((base >> 24) & 0xff) << 56))


class RenderMachine:
    def __init__(self, text, data):
        from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_UNMAPPED, UC_PROT_READ, UC_PROT_WRITE, \
            UC_PROT_EXEC, UC_HOOK_CODE
        from unicorn import x86_const as x86
        self.x86, self.UC_HOOK_CODE = x86, UC_HOOK_CODE
        self.RW = UC_PROT_READ | UC_PROT_WRITE
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, align(TEXT_BYTES), UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, align(DATA_BYTES), self.RW)
        uc.mem_write(DATA_BASE, data)
        uc.mem_map(STACK, STACK_BYTES, self.RW)
        uc.mem_map(TIB, PAGE, self.RW)
        uc.mem_map(GDT, PAGE, UC_PROT_READ)
        gdt = b'\0' * 8 + descriptor(TIB, PAGE - 1) + descriptor(0, 0xfffff, 0x93, 0xc)
        uc.mem_write(GDT, gdt)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, GDT, len(gdt) - 1, 0))
        uc.reg_write(x86.UC_X86_REG_FS, 0x8)
        for register in (x86.UC_X86_REG_SS, x86.UC_X86_REG_DS, x86.UC_X86_REG_ES):
            uc.reg_write(register, 0x10)
        uc.mem_map(HEAP, HEAP_BYTES, self.RW)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        self.lazy = collections.OrderedDict()
        self.stubs, self.hooks = {}, {}
        self.calls = []
        self.stopped = None
        self.heap = HEAP
        self.epoch = INIT_EPOCH
        self.mapped = []
        self._crt_services()

    # -- memory -----------------------------------------------------------
    def _unmapped(self, uc, access, address, size, value, ignored):
        if BSS_LOW <= address < BSS_HIGH:
            page = address & ~(PAGE - 1)
            uc.mem_map(page, PAGE, self.RW)
            self.lazy[page] = self.pc()
            if address + size > page + PAGE and (page + PAGE) < BSS_HIGH:
                pass
            return True
        self.stopped = ('unmapped', hex(address), size, hex(self.pc()))
        return False

    def map(self, base, size, payload=b'', executable=False):
        self.uc.mem_map(base, align(size), self.RW | (4 if executable else 0))   # 4 = UC_PROT_EXEC
        self.mapped.append((base, align(size)))
        if payload:
            self.uc.mem_write(base, bytes(payload))

    def ensure(self, base, size):
        """Map zero pages covering [base, base+size) inside the uninitialised range (declared)."""
        for page in range(base & ~(PAGE - 1), align(base + size), PAGE):
            if page not in self.lazy:
                try:
                    self.uc.mem_map(page, PAGE, self.RW)
                except Exception:
                    continue
                self.lazy[page] = 'declared'

    def pc(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_EIP)

    def read(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def r32(self, address):
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def rf(self, address):
        return u2f(self.r32(address))

    def w32(self, address, value):
        self.uc.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def wf(self, address, value):
        self.uc.mem_write(address, struct.pack('<f', value))

    def write(self, address, payload):
        self.uc.mem_write(address, bytes(payload))

    # -- stubs ------------------------------------------------------------
    def arg(self, index):
        esp = self.uc.reg_read(self.x86.UC_X86_REG_ESP)
        return self.r32(esp + 4 + 4 * index)

    def ecx(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_ECX)

    def stub(self, address, handler, cleanup):
        self.stubs[address] = (handler, cleanup)
        if address not in self.hooks:
            self.hooks[address] = self.uc.hook_add(self.UC_HOOK_CODE, self._stub, begin=address, end=address)

    def _stub(self, uc, address, size, ignored):
        handler, cleanup = self.stubs[address]
        esp = uc.reg_read(self.x86.UC_X86_REG_ESP)
        ret = self.r32(esp)
        try:
            value = handler(self)
        except Exception as failure:  # a stub must never fail silently
            self.stopped = ('stub-error', hex(address), repr(failure))
            uc.emu_stop()
            return
        if self.stopped:
            uc.emu_stop()
            return
        uc.reg_write(self.x86.UC_X86_REG_EAX, (value or 0) & 0xffffffff)
        uc.reg_write(self.x86.UC_X86_REG_ESP, esp + 4 + cleanup)
        uc.reg_write(self.x86.UC_X86_REG_EIP, ret)

    def _crt_services(self):
        def malloc(m):
            size = max((m.arg(0) + 15) & ~15, 16)
            address = m.heap
            m.heap += size
            if m.heap > HEAP + HEAP_BYTES:
                m.stopped = ('heap-exhausted',)
            m.uc.mem_write(address, b'\0' * size)
            return address
        self.stub(0x01983110, malloc, 0)
        self.stub(0x019a4d50, lambda m: 0, 0)          # free
        self.stub(0x0191be48, lambda m: 0, 0)          # atexit

        def header(m):                                  # _Init_thread_header, one thread
            guard = m.arg(0)
            if m.r32(guard) == 0:
                m.w32(guard, 0xffffffff)
            return 0
        self.stub(0x0191c511, header, 0)

        def footer(m):                                  # _Init_thread_footer
            m.epoch = (m.epoch + 1) & 0xffffffff
            m.w32(m.arg(0), m.epoch)
            m.w32(TIB + 0xc04, m.epoch)
            return 0
        self.stub(0x0191c4c0, footer, 0)

    # -- run --------------------------------------------------------------
    def run(self, start, arguments, ecx=0):
        uc, x86 = self.uc, self.x86
        uc.ctl_flush_tb()
        uc.mem_write(TIB, struct.pack('<I', SEH_HEAD) + b'\0' * (PAGE - 4))
        uc.mem_write(TIB + 0x2c, struct.pack('<I', TIB + 0x800))      # TLS slot array
        for slot in range(16):
            uc.mem_write(TIB + 0x800 + 4 * slot, struct.pack('<I', TIB + 0xc00))
        uc.mem_write(TIB + 0xc04, struct.pack('<I', self.epoch))     # thread init epoch
        uc.mem_write(ENTRY_ESP, struct.pack('<I', SENTINEL) +
                     b''.join(struct.pack('<I', a & 0xffffffff) for a in arguments))
        preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a,
                     x86.UC_X86_REG_EDI: 0x456789ab, x86.UC_X86_REG_EBP: 0x56789abc}
        for register, value in preserved.items():
            uc.reg_write(register, value)
        uc.reg_write(x86.UC_X86_REG_ESP, ENTRY_ESP)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, SENTINEL, timeout=0)
        except Exception as failure:
            error = str(failure)
        ok = self.pc() == SENTINEL and error is None and self.stopped is None
        checks = {'returned': ok,
                  'esp': uc.reg_read(x86.UC_X86_REG_ESP) == ENTRY_ESP + 4,
                  'callee_saved': all(uc.reg_read(r) == v for r, v in preserved.items()),
                  'seh_restored': self.r32(TIB) == SEH_HEAD,
                  'fpcw': uc.reg_read(x86.UC_X86_REG_FPCW) == FPCW}
        return {'ok': ok and all(checks.values()), 'checks': checks, 'error': error, 'stopped': self.stopped,
                'pc': hex(self.pc())}

    def run_inside(self, start, stop, frame_bytes, slots):
        """Run from start (inside a routine whose EBP frame is built) until stop.
        slots: EBP-relative offsets -> dwords (arguments at +8.., locals below)."""
        uc, x86 = self.uc, self.x86
        uc.ctl_flush_tb()
        uc.mem_write(TIB, struct.pack('<I', SEH_HEAD) + b'\0' * (PAGE - 4))
        uc.mem_write(TIB + 0x2c, struct.pack('<I', TIB + 0x800))
        for slot in range(16):
            uc.mem_write(TIB + 0x800 + 4 * slot, struct.pack('<I', TIB + 0xc00))
        uc.mem_write(TIB + 0xc04, struct.pack('<I', self.epoch))
        ebp = ENTRY_ESP - 4
        for offset, value in slots.items():
            uc.mem_write(ebp + offset, struct.pack('<I', value & 0xffffffff))
        uc.reg_write(x86.UC_X86_REG_EBP, ebp)
        uc.reg_write(x86.UC_X86_REG_ESP, ebp - frame_bytes)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, stop, timeout=0)
        except Exception as failure:
            error = str(failure)
        ok = self.pc() == stop and error is None and self.stopped is None
        return {'ok': ok, 'error': error, 'stopped': self.stopped, 'pc': hex(self.pc())}

    def backtrace(self, limit=16):
        out = [hex(self.pc())]
        ebp = self.uc.reg_read(self.x86.UC_X86_REG_EBP)
        for _ in range(limit):
            try:
                ret, ebp = self.r32(ebp + 4), self.r32(ebp)
            except Exception:
                break
            out.append(hex(ret))
            if ret == SENTINEL:
                break
        return out
