#!/usr/bin/env python3
"""Unicorn machine for the client's 2D interface routines (NATIVE-UI-001).

The pinned restored text (0x00401000) and second image section (0x01a7c000)
are mapped as captured.  The uncaptured third section (globals from
0x01ced000) is mapped as zero-filled memory whose bytes count as undefined
until the caller seeds them or emulated code writes them; every read of an
undefined byte there, or on the case heap, is reported.

Calls leave the client in three ways, all explicit:

* import slots: the slot words in the image-data copy are replaced by stub
  addresses.  Each stub records the call (OpenGL, GLU, GDI and a few
  kernel32 routines) and returns with the routine's stdcall cleanup;
* stubbed client functions (operator new, C runtime file and memory helpers,
  STL bookkeeping, the texture-table lookup): an explicit table of
  replacements with the callee's own stack cleanup;
* nothing else: every executed basic block must lie inside the caller's
  allowlist of client function bodies, otherwise the case stops.

Recorded calls are (name, words): 32-bit argument words in call order, with
floats kept as bit patterns, doubles as two words, and texture uploads
replaced by the SHA-256 of the uploaded bytes.
"""
import hashlib
import struct

try:  # Unicorn is needed only to run client code; the constants below stay importable without it
    from unicorn import (Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_BLOCK,
                         UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED, UC_PROT_ALL)
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP,
                                   UC_X86_REG_EBP, UC_X86_REG_EIP, UC_X86_REG_CS, UC_X86_REG_DS,
                                   UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_FS, UC_X86_REG_GS,
                                   UC_X86_REG_GDTR, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI)
except ImportError:  # pragma: no cover - portable test environments
    Uc = None


TEXT_BASE = 0x00401000
DATA_BASE = 0x01a7c000
BSS_BASE = 0x01ced000            # third section: uncaptured globals
BSS_END = 0x0c000000
STACK_BASE, STACK_SIZE = 0x00100000, 0x00200000
HEAP_BASE, HEAP_SIZE = 0x30000000, 0x04000000
STUB_BASE, STUB_SIZE = 0x7f000000, 0x00100000
TEB_BASE = 0x7ff00000
GDT_BASE = 0x7ffe0000
RETURN_SENTINEL = STUB_BASE + STUB_SIZE - 16

# Import slots used by the UI routines, named by scripts/client_frame_static.py
# (Wine 8.0 export RVAs) and docs/research/client-frame-loop.md.  The format
# lists the stdcall argument words: i = 32-bit word, f = float, d = double
# (two words), p = pointer.
SLOTS = {
    0x01a7c6a8: None,
    0x01a7c714: ('glMatrixMode', 'i'), 0x01a7c718: ('glPushMatrix', ''), 0x01a7c72c: ('glPopMatrix', ''),
    0x01a7c6e4: ('glLoadIdentity', ''), 0x01a7c6d4: ('glViewport', 'iiii'),
    0x01a7c750: ('glBegin', 'i'), 0x01a7c760: ('glEnd', ''), 0x01a7c684: ('glVertex2f', 'ff'),
    0x01a7c774: ('glTexCoord2f', 'ff'), 0x01a7c754: ('glColor4f', 'ffff'), 0x01a7c76c: ('glColor3f', 'fff'),
    0x01a7c6c4: ('glColor4ub', 'iiii'), 0x01a7c77c: ('glBindTexture', 'ii'), 0x01a7c75c: ('glEnable', 'i'),
    0x01a7c758: ('glDisable', 'i'), 0x01a7c748: ('glBlendFunc', 'ii'), 0x01a7c740: ('glDepthMask', 'i'),
    0x01a7c788: ('glTexImage2D', 'iiiiiiiip'), 0x01a7c74c: ('glTexParameteri', 'iii'),
    0x01a7c6ac: ('glTexEnvf', 'iif'), 0x01a7c780: ('glGenTextures', 'ip'), 0x01a7c6e8: ('glClear', 'i'),
    0x01a7c6cc: ('glClearColor', 'ffff'), 0x01a7c6d0: ('glAlphaFunc', 'if'),
    0x01a7c174: ('gluPerspective', 'dddd'), 0x01a7c17c: ('gluOrtho2D', 'dddd'),
    0x01a7c128: ('GetTextExtentPointA', 'ppip'), 0x01a7c11c: ('GetTextExtentPoint32A', 'ppip'),
    0x01a7c144: ('TextOutA', 'piipi'), 0x01a7c138: ('SetBkColor', 'pi'), 0x01a7c13c: ('SetTextColor', 'pi'),
    0x01a7c140: ('CreateDIBSection', 'pppppi'), 0x01a7c12c: ('CreateCompatibleDC', 'p'),
    0x01a7c120: ('CreateFontA', 'iiiiiiiiiiiiip'), 0x01a7c134: ('SelectObject', 'pp'), 0x01a7c278: ('lstrlenA', 'p'), 0x01a7c148: ('SwapBuffers', 'p'),
    # NATIVE-UI-002 (window/widget layer): user32 rectangle helpers and the list walk's pointer check
    0x01a7c818: ('PtInRect', 'pii'), 0x01a7c854: ('SetRect', 'piiii'), 0x01a7c488: ('IsBadReadPtr', 'pi'),
}
del SLOTS[0x01a7c6a8]
FORMAT_WORDS = {'i': 1, 'f': 1, 'p': 1, 'd': 2}


class CaseError(RuntimeError):
    pass


REDIRECT = object()   # a client stub that moved EIP itself


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def bits_f(word):
    return struct.unpack('<f', struct.pack('<I', word & 0xffffffff))[0]


def page_align(value, up=True):
    return ((value + 0xfff) & ~0xfff) if up else (value & ~0xfff)


class Machine:
    """One emulated client address space; reusable across cases via reset()."""

    def __init__(self, text, data):
        if Uc is None:
            raise RuntimeError('the unicorn module is required to run client routines')
        self.text, self.data = text, data
        uc = self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        uc.mem_map(TEXT_BASE, page_align(len(text)), UC_PROT_ALL)
        uc.mem_write(TEXT_BASE, text)
        self.data_end = DATA_BASE + len(data)
        uc.mem_map(DATA_BASE, BSS_BASE - DATA_BASE, UC_PROT_ALL)
        uc.mem_map(BSS_BASE, BSS_END - BSS_BASE, UC_PROT_ALL)
        uc.mem_map(STACK_BASE, STACK_SIZE, UC_PROT_ALL)
        uc.mem_map(HEAP_BASE, HEAP_SIZE, UC_PROT_ALL)
        uc.mem_map(STUB_BASE, STUB_SIZE, UC_PROT_ALL)
        uc.mem_map(TEB_BASE, 0x2000, UC_PROT_ALL)
        uc.mem_map(GDT_BASE, 0x1000, UC_PROT_ALL)
        self._segments()
        self.stubs = {}           # address -> (handler, cleanup bytes)
        self._hooked = set()
        self._independent_cache = {}
        self.slot_stub = {}       # slot -> stub address
        self.allowed = []         # (start, end) client code ranges
        self.calls = []
        self.errors = []
        self.defined = set()
        self.heap_next = HEAP_BASE
        self.handlers = {}        # import name -> handler(machine, words) -> eax
        uc.hook_add(UC_HOOK_BLOCK, self._block, begin=TEXT_BASE, end=TEXT_BASE + len(text))
        uc.hook_add(UC_HOOK_MEM_READ, self._read, begin=BSS_BASE, end=BSS_END - 1)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._write, begin=BSS_BASE, end=BSS_END - 1)
        self._heap_hooks = []
        self.heap_checks(True)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        uc.hook_add(UC_HOOK_CODE, self._stub_hit, begin=STUB_BASE, end=STUB_BASE + STUB_SIZE - 1)
        self._next_stub = STUB_BASE
        for slot, spec in SLOTS.items():
            address = self._new_stub()
            self.slot_stub[slot] = address
            self.stubs[address] = ('import', spec)
        self.reset()

    def heap_checks(self, enabled):
        """Track definedness of case-heap bytes (slow for pixel loops).  When
        disabled, heap reads are unchecked; globals stay checked."""
        if enabled and not self._heap_hooks:
            self._heap_hooks = [
                self.uc.hook_add(UC_HOOK_MEM_READ, self._read, begin=HEAP_BASE, end=HEAP_BASE + HEAP_SIZE - 1),
                self.uc.hook_add(UC_HOOK_MEM_WRITE, self._write, begin=HEAP_BASE, end=HEAP_BASE + HEAP_SIZE - 1)]
        elif not enabled and self._heap_hooks:
            for handle in self._heap_hooks:
                self.uc.hook_del(handle)
            self._heap_hooks = []
            self._heap_dirty = True

    # ---- setup --------------------------------------------------------
    def _segments(self):
        def entry(base, limit, access, flags=0xc):
            value = limit & 0xffff
            value |= (base & 0xffffff) << 16
            value |= access << 40
            value |= ((limit >> 16) & 0xf) << 48
            value |= flags << 52
            value |= ((base >> 24) & 0xff) << 56
            return struct.pack('<Q', value)
        gdt = bytearray(8*8)
        gdt[8:16] = entry(0, 0xfffff, 0x9b)      # code, ring 0
        gdt[16:24] = entry(0, 0xfffff, 0x93)     # data
        gdt[24:32] = entry(TEB_BASE, 0xfff, 0x93, 0x4)  # fs: TEB
        self.uc.mem_write(GDT_BASE, bytes(gdt))
        self.uc.reg_write(UC_X86_REG_GDTR, (0, GDT_BASE, len(gdt) - 1, 0))
        self.uc.reg_write(UC_X86_REG_CS, 1 << 3)
        self.uc.reg_write(UC_X86_REG_SS, 2 << 3)
        self.uc.reg_write(UC_X86_REG_DS, 2 << 3)
        self.uc.reg_write(UC_X86_REG_ES, 2 << 3)
        self.uc.reg_write(UC_X86_REG_GS, 2 << 3)
        self.uc.reg_write(UC_X86_REG_FS, 3 << 3)

    def _new_stub(self):
        address = self._next_stub
        self._next_stub += 16
        self.uc.mem_write(address, b'\xc3')   # never executed; the hook redirects
        return address

    def reset(self):
        """Restore captured data, clear globals, heap, calls and errors."""
        self.uc.mem_write(DATA_BASE, self.data)
        for slot, address in self.slot_stub.items():
            self.uc.mem_write(slot, struct.pack('<I', address))
        self.uc.mem_write(TEB_BASE, struct.pack('<I', 0xffffffff) + b'\0'*0x1ffc)
        self.uc.mem_write(TEB_BASE + 0x18, struct.pack('<I', TEB_BASE))
        self._zero_touched()
        self.defined = set()
        self.calls = []
        self.errors = []
        self.heap_next = HEAP_BASE
        self.handlers = {}

    def _zero_touched(self):
        # Zero every page that was written in the bss/heap ranges.
        pages = {a & ~0xfff for a in self.defined}
        for page in pages:
            self.uc.mem_write(page, b'\0'*0x1000)
        if getattr(self, '_heap_dirty', False) or self.heap_next > HEAP_BASE:
            used = page_align(self.heap_next - HEAP_BASE)
            if used:
                self.uc.mem_write(HEAP_BASE, b'\0'*used)
            self._heap_dirty = False

    def fail(self, message):
        """Stop the case from inside a stub; call() raises CaseError(message)."""
        self.errors.append(message)
        self.uc.emu_stop()
        return REDIRECT

    def allow(self, *ranges):
        self.allowed.extend(ranges)

    def stub(self, address, handler, cleanup=0):
        """Replace client function `address`; cleanup = callee-popped bytes."""
        if address not in self._hooked:
            self._hooked.add(address)
            self.uc.hook_add(UC_HOOK_CODE, self._client_stub, begin=address, end=address)
        self.stubs[address] = ('client', (handler, cleanup))

    # ---- memory -------------------------------------------------------
    def write(self, address, payload, define=True):
        self.uc.mem_write(address, bytes(payload))
        if define:
            self.defined.update(range(address, address + len(payload)))

    def read(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def put32(self, address, value):
        self.write(address, struct.pack('<I', value & 0xffffffff))

    def putf(self, address, value):
        self.write(address, struct.pack('<f', value))

    def alloc(self, size, define=False, align=16):
        address = (self.heap_next + align - 1) & ~(align - 1)
        self.heap_next = address + max(size, 1)
        if self.heap_next > HEAP_BASE + HEAP_SIZE:
            raise CaseError('case heap exhausted')
        if define:
            self.defined.update(range(address, address + size))
        return address

    def _value_independent(self, eip):
        """and r/m, 0 and or r/m, -1 read memory but do not depend on it."""
        if eip not in self._independent_cache:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32
            engine = Cs(CS_ARCH_X86, CS_MODE_32)
            code = self.read(eip, 16)
            result = False
            for _, _, mnemonic, operands in engine.disasm_lite(code, eip, 1):
                parts = [p.strip() for p in operands.split(',')]
                result = ('ptr [' in operands and len(parts) == 2 and
                          ((mnemonic == 'and' and parts[1] in ('0', '0x0')) or
                           (mnemonic == 'or' and parts[1] in ('0xffffffff', '-1'))))
            self._independent_cache[eip] = result
        return self._independent_cache[eip]

    def _read(self, uc, access, address, size, value, user):
        for byte in range(address, address + size):
            if byte not in self.defined:
                if self._value_independent(uc.reg_read(UC_X86_REG_EIP)):
                    return
                self.errors.append(f'read of undefined byte {byte:#x} at eip {uc.reg_read(UC_X86_REG_EIP):#x}')
                uc.emu_stop()
                return

    def _write(self, uc, access, address, size, value, user):
        self.defined.update(range(address, address + size))

    def _unmapped(self, uc, access, address, size, value, user):
        self.errors.append(f'unmapped access {address:#x} at eip {uc.reg_read(UC_X86_REG_EIP):#x}')
        return False

    def _block(self, uc, address, size, user):
        for start, end in self.allowed:
            if start <= address < end:
                return
        if address in self.stubs:
            return
        esp = uc.reg_read(UC_X86_REG_ESP)
        self.errors.append(f'execution left the allowlist at {address:#x} (return {self.u32(esp):#x})')
        uc.emu_stop()

    # ---- calls --------------------------------------------------------
    def args(self, count, offset=4):
        esp = self.uc.reg_read(UC_X86_REG_ESP)
        return list(struct.unpack(f'<{count}I', self.read(esp + offset, 4*count))) if count else []

    def _return(self, eax, cleanup):
        uc = self.uc
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack('<I', self.read(esp, 4))[0]
        uc.reg_write(UC_X86_REG_EAX, eax & 0xffffffff)
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + cleanup)
        uc.reg_write(UC_X86_REG_EIP, ret)

    def _stub_hit(self, uc, address, size, user):
        if address == RETURN_SENTINEL:
            uc.emu_stop()
            return
        entry = self.stubs.get(address)
        if entry is None or entry[0] != 'import':
            return
        spec = entry[1]
        name, fmt = spec
        count = sum(FORMAT_WORDS[c] for c in fmt)
        words = self.args(count)
        handler = self.handlers.get(name)
        record = list(words)
        if name in ('GetTextExtentPointA', 'GetTextExtentPoint32A'):
            record.append(self.read(words[1], words[2]).decode('latin1'))
        elif name == 'TextOutA':
            record.append(self.read(words[3], words[4]).decode('latin1'))
        if name == 'glTexImage2D':
            target, level, internal, width, height, border, fmt_, type_, pointer = words
            components = {0x1907: 3, 0x1908: 4}.get(fmt_, 4)
            payload = self.read(pointer, width*height*components) if pointer else b''
            record[8] = hashlib.sha256(payload).hexdigest()
        self.calls.append((name, tuple(record)))
        eax = handler(self, words) if handler else 0
        self._return(eax or 0, 4*count)

    def _client_stub(self, uc, address, size, user):
        entry = self.stubs.get(address)
        if entry is None or entry[0] != 'client':
            return
        handler, cleanup = entry[1]
        eax = handler(self)
        if eax is REDIRECT:
            return
        self._return(eax or 0, cleanup)

    def call(self, address, args=(), ecx=None, limit=400_000_000):
        """Run a client function to its return; args are 32-bit words."""
        uc = self.uc
        esp = STACK_BASE + STACK_SIZE - 0x1000
        frame = struct.pack('<I', RETURN_SENTINEL) + b''.join(struct.pack('<I', a & 0xffffffff) for a in args)
        esp -= len(frame)
        uc.mem_write(esp, frame)
        uc.reg_write(UC_X86_REG_ESP, esp)
        uc.reg_write(UC_X86_REG_EBP, 0)
        for register in (UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI):
            uc.reg_write(register, 0)
        uc.reg_write(UC_X86_REG_ECX, 0 if ecx is None else ecx)
        try:
            uc.emu_start(address, RETURN_SENTINEL, count=limit)
        except UcError as error:
            self.errors.append(f'{error} at eip {uc.reg_read(UC_X86_REG_EIP):#x}')
        if uc.reg_read(UC_X86_REG_EIP) != RETURN_SENTINEL and not self.errors:
            self.errors.append(f'stopped at {uc.reg_read(UC_X86_REG_EIP):#x} (instruction limit)')
        if self.errors:
            raise CaseError('; '.join(self.errors[:4]))
        return uc.reg_read(UC_X86_REG_EAX)


def function_extent(text, start, limit=0x40000):
    """Linear-decode a function from `start` to the first return past every
    forward branch target; returns the exclusive end address."""
    import re
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    engine = Cs(CS_ARCH_X86, CS_MODE_32)
    far = start
    offset = start - TEXT_BASE
    for address, size, mnemonic, operands in engine.disasm_lite(text[offset:offset + limit], start):
        if mnemonic.startswith('j'):
            match = re.fullmatch(r'0x([0-9a-f]+)', operands)
            if match:
                far = max(far, int(match.group(1), 16))
        if mnemonic in ('ret', 'retn') and address >= far:
            return address + size
    raise ValueError(f'no return found for {start:#x}')


def stdcall_cleanup(text, start):
    """Bytes popped by the first return of a callee (ret imm16), else 0."""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    engine = Cs(CS_ARCH_X86, CS_MODE_32)
    end = function_extent(text, start)
    offset = start - TEXT_BASE
    for address, size, mnemonic, operands in engine.disasm_lite(text[offset:end - TEXT_BASE], start):
        if mnemonic in ('ret', 'retn'):
            return int(operands, 16) if operands else 0
    return 0
