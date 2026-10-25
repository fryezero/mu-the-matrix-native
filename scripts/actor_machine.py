"""Unicorn machine for the NATIVE-ACTOR-001 validators.

Runs client routines over the pinned restored text (0x00401000) and the
verified second image section (0x01a7c000) with:

* declared case regions carrying a defined-byte mask (as in
  scripts/validate_skinning.py): a read of an undefined byte, an access outside
  every declared region, an unmapped access, or a write to a read-only region
  stops the case;
* an FS segment over a private thread-information page, because the routines
  use MSVC structured-exception frames (fs:[0] is read in the prologue and
  restored in the epilogue);
* named stubs at callee entry points. A stub reads its stack arguments,
  records the call, sets EAX and returns with the callee's own stack cleanup.
  Stubs replace only engine services named by the caller (model container,
  file and texture loaders, strings, sounds); everything else runs as client
  code.
"""
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pins  # noqa: E402

TEXT_BASE, TEXT_BYTES = 0x401000, pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
DATA_BASE, DATA_BYTES = 0x1a7c000, pins.DATA.size
DATA_SHA256 = pins.DATA.sha256
STACK, STACK_BYTES = 0x31000000, 0x20000
ENTRY_ESP = STACK + 0x1c000
SENTINEL = 0x7ffe0000
TIB, GDT = 0x7ffd0000, 0x7ffc0000
SEH_HEAD = 0x7ffd0f00   # value of fs:[0] on entry (any address; only stored and restored)
FPCW, MXCSR = 0x027f, 0x1f80
PAGE = 0x1000


load_pinned = pins.load_pinned


def align(value, boundary=PAGE):
    return (value+boundary-1) & -boundary


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


def poison(size, salt):
    return bytes(((index*41+salt) & 0x7f) | 0x80 for index in range(size))


class Region:
    """Bytes at a fixed client address with a defined-byte mask."""

    def __init__(self, name, base, data, defined=None, writable=True):
        self.name, self.base, self.data = name, base, bytearray(data)
        self.defined = bytearray(b'\1'*len(data)) if defined is None else bytearray(defined)
        self.writable = writable

    @property
    def end(self):
        return self.base+len(self.data)

    def define(self, address, payload):
        offset = address-self.base
        if offset < 0 or offset+len(payload) > len(self.data):
            raise ValueError(f'{self.name}: {address:#x}+{len(payload)} outside region')
        self.data[offset:offset+len(payload)] = payload
        self.defined[offset:offset+len(payload)] = b'\1'*len(payload)


def defined_region(name, base, payload, writable=True):
    return Region(name, base, payload, None, writable)


def undefined_region(name, base, size, salt=0x5a):
    return Region(name, base, poison(size, salt), bytes(size))


def descriptor(base, limit, access=0x93, flags=0x4):
    return struct.pack('<Q', (limit & 0xffff) | ((base & 0xffffff) << 16) | (access << 40) |
                       (((limit >> 16) & 0xf) << 48) | (flags << 52) | (((base >> 24) & 0xff) << 56))


class ActorMachine:
    def __init__(self, text, data):
        from unicorn import (Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
                             UC_HOOK_MEM_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED, UC_PROT_READ, UC_PROT_WRITE,
                             UC_PROT_EXEC, UC_MEM_WRITE)
        from unicorn import x86_const as x86
        self.x86, self.UC_MEM_WRITE, self.UC_HOOK_CODE = x86, UC_MEM_WRITE, UC_HOOK_CODE
        self.RW = UC_PROT_READ | UC_PROT_WRITE
        self.ACCESS = UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, TEXT_BYTES, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, align(DATA_BYTES), UC_PROT_READ)
        uc.mem_write(DATA_BASE, data)
        uc.mem_map(STACK, STACK_BYTES, self.RW)
        uc.hook_add(self.ACCESS, self.caller_stack, begin=ENTRY_ESP, end=STACK+STACK_BYTES-1)
        uc.mem_map(TIB, PAGE, self.RW)
        uc.hook_add(self.ACCESS, self.tib_access, begin=TIB, end=TIB+PAGE-1)
        uc.mem_map(GDT, PAGE, UC_PROT_READ)
        # Null, FS over the TIB page, flat 32-bit data (SS/DS/ES). CS keeps Unicorn's flat default.
        gdt = b'\0'*8 + descriptor(TIB, PAGE-1) + descriptor(0, 0xfffff, 0x93, 0xc)
        uc.mem_write(GDT, gdt)
        uc.reg_write(x86.UC_X86_REG_GDTR, (0, GDT, len(gdt)-1, 0))
        uc.reg_write(x86.UC_X86_REG_FS, 0x8)
        for register in (x86.UC_X86_REG_SS, x86.UC_X86_REG_DS, x86.UC_X86_REG_ES):
            uc.reg_write(register, 0x10)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED, self.unmapped)
        self.stub_hooks = {}
        self.dynamic = []
        self.preserved = {x86.UC_X86_REG_EBX: 0x12345678, x86.UC_X86_REG_ESI: 0x3456789a,
                          x86.UC_X86_REG_EDI: 0x456789ab, x86.UC_X86_REG_EBP: 0x56789abc}

    # ------------------------------------------------------------------
    def stop(self, reason):
        if self.state['stopped'] is None:
            self.state['stopped'] = reason
        self.uc.emu_stop()

    def pc(self):
        return self.uc.reg_read(self.x86.UC_X86_REG_EIP)

    def caller_stack(self, uc, access, address, size, value, ignored):
        if address == ENTRY_ESP and size == 4 and access != self.UC_MEM_WRITE:
            return  # the final RET (or a stub return read below)
        if address >= ENTRY_ESP+4 and address+size <= ENTRY_ESP+4+self.argument_bytes and \
                access != self.UC_MEM_WRITE:
            return
        self.stop(('caller-stack', hex(address), size, access == self.UC_MEM_WRITE, hex(self.pc())))

    def tib_access(self, uc, access, address, size, value, ignored):
        if address == TIB and size == 4:
            if access == self.UC_MEM_WRITE:
                self.state['seh_writes'] += 1
            return
        self.stop(('tib-access', hex(address), size, hex(self.pc())))

    def unmapped(self, uc, access, address, size, value, ignored):
        self.stop(('unmapped', hex(address), size, hex(self.pc())))
        return False

    def access(self, uc, access, address, size, value, regions):
        for region in regions:
            if region.base <= address and address+size <= region.end:
                offset = address-region.base
                if access == self.UC_MEM_WRITE:
                    if not region.writable:
                        break
                    region.defined[offset:offset+size] = b'\1'*size
                    return
                if b'\0' in region.defined[offset:offset+size]:
                    self.stop(('undefined-read', region.name, hex(address), size, hex(self.pc())))
                return
        self.stop(('undeclared-access', hex(address), size, access == self.UC_MEM_WRITE, hex(self.pc())))

    def map_regions(self, regions):
        uc = self.uc
        for base, size, hook in self.dynamic:
            uc.hook_del(hook)
            uc.mem_unmap(base, size)
        self.dynamic = []
        pages = sorted({page for r in regions if len(r.data)
                        for page in range(r.base & ~0xfff, align(r.end), PAGE)})
        spans = []
        for page in pages:
            if spans and spans[-1][1] == page:
                spans[-1][1] = page+PAGE
            else:
                spans.append([page, page+PAGE])
        for low, high in spans:
            inside = [r for r in regions if len(r.data) and r.base < high and r.end > low]
            uc.mem_map(low, high-low, self.RW)
            uc.mem_write(low, b'\xcc'*(high-low))
            hook = uc.hook_add(self.ACCESS, self.access, inside, begin=low, end=high-1)
            self.dynamic.append((low, high-low, hook))
        for r in regions:
            if len(r.data):
                uc.mem_write(r.base, bytes(r.data))

    # ------------------------------------------------------------------
    # Memory helpers for stubs.
    def read32(self, address):
        return struct.unpack('<I', self.uc.mem_read(address, 4))[0]

    def write(self, address, payload):
        """Stub-side write: marks the bytes defined in their region."""
        self.uc.mem_write(address, bytes(payload))
        for region in self.regions:
            if region.base <= address and address+len(payload) <= region.end:
                offset = address-region.base
                region.defined[offset:offset+len(payload)] = b'\1'*len(payload)
                return
        raise ValueError(f'stub write outside regions: {address:#x}')

    def cstring(self, address, limit=260):
        raw = bytearray()
        while len(raw) < limit:
            byte = bytes(self.uc.mem_read(address+len(raw), 1))
            if byte == b'\0':
                break
            raw += byte
        return raw.decode('latin1')

    def argument(self, index):
        esp = self.uc.reg_read(self.x86.UC_X86_REG_ESP)
        return self.read32(esp+4+4*index)

    def stub_entry(self, uc, address, size, ignored):
        handler = self.stubs.get(address)
        if handler is None:
            return  # hook left from another routine's stub set: run as client code
        x86 = self.x86
        esp = uc.reg_read(x86.UC_X86_REG_ESP)
        ret = self.read32(esp)
        try:
            result = handler(self)
        except Exception as failure:  # a stub must never fail silently
            self.stop(('stub-error', hex(address), repr(failure)))
            return
        if self.state['stopped'] is not None:
            return
        eax, cleanup = result if isinstance(result, tuple) else (result, 0)
        uc.reg_write(x86.UC_X86_REG_EAX, eax & 0xffffffff)
        uc.reg_write(x86.UC_X86_REG_ESP, esp+4+cleanup)
        uc.reg_write(x86.UC_X86_REG_EIP, ret)

    def execute(self, start, arguments, regions, stubs, *, ecx=0, cleanup=0, count=0, frame=None):
        """Run from start with a sentinel return. With frame=(size, slots), start is inside a
        routine whose standard EBP frame (PUSH EBP; MOV EBP,ESP; SEH registration) is already
        built: EBP = ENTRY_ESP-4 holds the caller's EBP, [EBP-0xc] the saved fs:[0], ESP =
        EBP-size, and slots maps EBP-relative offsets to initial dwords."""
        uc, x86 = self.uc, self.x86
        self.regions = regions
        self.map_regions(regions)
        self.stubs = stubs
        added = False
        for address in stubs:
            if address not in self.stub_hooks:
                self.stub_hooks[address] = uc.hook_add(self.UC_HOOK_CODE, self.stub_entry, begin=address,
                                                       end=address)
                added = True
        if added:
            uc.ctl_flush_tb()  # blocks translated before a hook existed would bypass it
        self.argument_bytes = 4*len(arguments)
        self.state = {'stopped': None, 'seh_writes': 0}
        uc.mem_write(STACK, b'\xa5'*STACK_BYTES)
        uc.mem_write(TIB, struct.pack('<I', SEH_HEAD) + b'\0'*(PAGE-4))
        uc.mem_write(ENTRY_ESP, struct.pack('<I', SENTINEL)+b''.join(struct.pack('<I', a & 0xffffffff)
                                                                      for a in arguments))
        for register, value in self.preserved.items():
            uc.reg_write(register, value)
        uc.reg_write(x86.UC_X86_REG_EAX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_EDX, 0xdeadbeef)
        uc.reg_write(x86.UC_X86_REG_ECX, ecx)
        for index in range(8):
            lane = 0x7ff4dead5eed0000+index*0x0101010101
            uc.reg_write(getattr(x86, f'UC_X86_REG_XMM{index}'), lane | (lane << 64))
        uc.reg_write(x86.UC_X86_REG_ESP, ENTRY_ESP)
        if frame is not None:
            size, slots = frame
            ebp = ENTRY_ESP-4
            uc.mem_write(ebp, struct.pack('<I', self.preserved[x86.UC_X86_REG_EBP]))
            uc.mem_write(ebp-0xc, struct.pack('<I', SEH_HEAD))
            uc.mem_write(TIB, struct.pack('<I', ebp-0x10))
            for offset, value in slots.items():
                uc.mem_write(ebp+offset, struct.pack('<I', value & 0xffffffff))
            uc.reg_write(x86.UC_X86_REG_EBP, ebp)
            uc.reg_write(x86.UC_X86_REG_ESP, ebp-size)
        uc.reg_write(x86.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x86.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x86.UC_X86_REG_FPSW, 0)
        uc.reg_write(x86.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x86.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, SENTINEL, timeout=600000000, count=count)
        except Exception as failure:  # UcError
            error = str(failure)
        state = self.state
        checks = {'returned': self.pc() == SENTINEL and state['stopped'] is None and error is None,
                  'esp': uc.reg_read(x86.UC_X86_REG_ESP) == ENTRY_ESP+4+cleanup,
                  'callee_saved': all(uc.reg_read(r) == v for r, v in self.preserved.items()),
                  'direction_flag': (uc.reg_read(x86.UC_X86_REG_EFLAGS) >> 10) & 1 == 0,
                  'fpcw': uc.reg_read(x86.UC_X86_REG_FPCW) == FPCW,
                  'mxcsr_control': uc.reg_read(x86.UC_X86_REG_MXCSR) & ~0x3f == MXCSR,
                  'x87_top': (uc.reg_read(x86.UC_X86_REG_FPSW) >> 11) & 7 == 0,
                  'seh_restored': self.read32(TIB) == SEH_HEAD}
        return {'checks': checks, 'ok': all(checks.values()), 'error': error, 'stopped': state['stopped'],
                'eax': uc.reg_read(x86.UC_X86_REG_EAX),
                'regions': {r.name: bytes(uc.mem_read(r.base, len(r.data))) for r in regions if len(r.data)}}
