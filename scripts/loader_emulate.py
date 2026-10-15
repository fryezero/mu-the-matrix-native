#!/usr/bin/env python3
"""Bounded CPU-only hypothesis for the recovered entry. No Windows or API layer.

No host calls, target launching, credentials, network, or native game execution.
Stops before environment-sensitive or system instructions, or on unmapped access.
Initial register values are assumptions, not observations of the installed game.
"""
import argparse
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import struct
import time

import capstone
import unicorn
from unicorn import Uc, UcError
from unicorn.x86_const import *

ROOT = Path(__file__).resolve().parents[1]
IMAGE_BASE, IMAGE_SIZE = 0x400000, 260628480
DEST_BASE, ENTRY = 0x0BE3C000, 0x0BE5F280
STACK_BASE, STACK_SIZE, STOP_VA = 0x70000000, 0x200000, 0x60000000
EXPECTED = "3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a"
REGS = {"eax":UC_X86_REG_EAX, "ebx":UC_X86_REG_EBX, "ecx":UC_X86_REG_ECX,
        "edx":UC_X86_REG_EDX, "esi":UC_X86_REG_ESI, "edi":UC_X86_REG_EDI,
        "ebp":UC_X86_REG_EBP, "esp":UC_X86_REG_ESP, "eip":UC_X86_REG_EIP,
        "eflags":UC_X86_REG_EFLAGS}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(directory, budget, synthetic_rdtsc=False, import_traps=False):
    directory.mkdir(parents=True, exist_ok=True)
    source = ROOT / "input/main.exe"
    data = source.read_bytes()
    assert sha(data) == EXPECTED
    recovered = (ROOT / "evidence/loader-recovery/themida-decoded.bin").read_bytes()
    inventory = json.loads((ROOT / "evidence/pe-inventory.json").read_text())
    uc = Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
    uc.mem_map(IMAGE_BASE, IMAGE_SIZE)
    uc.mem_write(IMAGE_BASE, data[:1536])
    for section in inventory["sections"]:
        start, size = section["file_offset"], section["file_size"]
        if size:
            uc.mem_write(section["virtual_address"], data[start:start + size])
    uc.mem_write(DEST_BASE, recovered)
    initialized_ranges = [(IMAGE_BASE, IMAGE_BASE + 1536), (DEST_BASE, DEST_BASE + len(recovered))]
    initialized_ranges.extend((s["virtual_address"],s["virtual_address"]+s["file_size"])
                              for s in inventory["sections"] if s["file_size"])
    uc.mem_map(STACK_BASE, STACK_SIZE)
    uc.mem_map(STOP_VA, 0x2000)
    uc.mem_write(STOP_VA, b"\xcc")
    initial = {name:0 for name in REGS}
    initial.update(esp=STACK_BASE + STACK_SIZE - 0x1000, eip=ENTRY, eflags=0x202)
    for name, val in initial.items():
        uc.reg_write(REGS[name], val)
    uc.mem_write(initial["esp"], struct.pack("<I", STOP_VA))
    trap_imports = {}
    import_slots = []
    if import_traps:
        def read_u32(va):
            return struct.unpack("<I",uc.mem_read(va,4))[0]
        def read_string(va):
            data = bytes(uc.mem_read(va,1024))
            return data.split(b"\0",1)[0].decode("ascii",errors="replace")
        imp_dir = inventory["directories"][1]
        for index in range(min(imp_dir["size"]//20,4096)):
            descriptor = IMAGE_BASE + imp_dir["rva"] + index*20
            original,_,_,name_rva,first_thunk = struct.unpack("<IIIII",uc.mem_read(descriptor,20))
            if not any((original,name_rva,first_thunk)):
                break
            dll = read_string(IMAGE_BASE+name_rva)
            for slot_index in range(65536):
                val = read_u32(IMAGE_BASE+(original or first_thunk)+slot_index*4)
                if not val:
                    break
                function = f"ordinal-{val & 0xffff}" if val & 0x80000000 else read_string(IMAGE_BASE+val+2)
                trap = STOP_VA + 0x1000 + len(import_slots)*16
                if trap >= STOP_VA + 0x2000:
                    raise ValueError("import trap bounds")
                slot_va = IMAGE_BASE+first_thunk+slot_index*4
                record = {"dll":dll,"function":function,"slot_va":slot_va,"original_slot_value":read_u32(slot_va),"trap_va":trap}
                import_slots.append(record)
                trap_imports[trap] = record
                uc.mem_write(slot_va,struct.pack("<I",trap))
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    last = deque(maxlen=128)
    dirty, write_counts = set(), Counter()
    code_pages = set()
    stop = {"reason":None}
    state = {"instructions":0, "blocks":0, "image_writes":0, "stack_writes":0}
    decoded_cache = {}
    block_log = []
    cpu_inputs = []
    forbidden = {"cpuid", "rdtsc", "rdtscp", "int", "int1", "int3", "into", "syscall",
                 "sysenter", "sysexit", "iret", "iretd", "in", "insb", "insd", "insw",
                 "out", "outsb", "outsd", "outsw", "hlt", "cli", "sti", "rdmsr", "wrmsr"}

    def code_hook(engine, address, size, _):
        state["instructions"] += 1
        if address in trap_imports:
            esp = engine.reg_read(UC_X86_REG_ESP)
            stack = struct.unpack("<8I",engine.mem_read(esp,32))
            args = {"return_va":stack[0], "stack_argument_words":list(stack[1:])}
            if trap_imports[address]["function"] == "GetModuleHandleA":
                pointer = stack[1]
                args["argument1_pointer"] = pointer
                if pointer == 0:
                    args["argument1_meaning"] = "NULL, current executable module"
                else:
                    try:
                        raw_arg = bytes(engine.mem_read(pointer,256)).split(b"\0",1)[0]
                        args["argument1_bytes"] = raw_arg.hex()
                        args["argument1_ascii"] = raw_arg.decode("ascii",errors="replace")
                    except UcError:
                        args["argument1_meaning"] = "unmapped pointer"
            stop.update(reason="required Windows or companion DLL import; no API implementation supplied", address=address, required_import=trap_imports[address], call_arguments=args)
            engine.emu_stop()
            return
        if address == STOP_VA:
            stop.update(reason="returned to synthetic caller", address=address)
            engine.emu_stop()
            return
        if not any(start <= address < end for start,end in initialized_ranges) and (address & ~0xfff) not in dirty:
            stop.update(reason="instruction fetch from zero-filled image region without loaded or written code", address=address)
            engine.emu_stop()
            return
        if state["instructions"] >= budget:
            stop.update(reason="instruction budget", address=address)
            engine.emu_stop()
            return
        raw = bytes(engine.mem_read(address, size))
        key = (address, raw)
        ins = decoded_cache.get(key)
        if ins is None:
            item = next(cs.disasm(raw, address, count=1), None)
            ins = (item.mnemonic, item.op_str) if item else ("unparsed", "")
            if len(decoded_cache) < 100000:
                decoded_cache[key] = ins
        last.append({"va":address, "bytes":raw.hex(), "assembly":" ".join(ins)})
        code_pages.add(address & ~0xfff)
        if ins[0] == "rdtsc" and synthetic_rdtsc:
            ticks = 1000000000 + state["instructions"] * 100
            cpu_inputs.append({"va":address, "at_instruction":state["instructions"], "ticks":ticks})
            engine.reg_write(UC_X86_REG_EAX, ticks & 0xffffffff)
            engine.reg_write(UC_X86_REG_EDX, ticks >> 32)
            engine.reg_write(UC_X86_REG_EIP, address + size)
            return
        if ins[0] in forbidden or "fs:" in ins[1] or "gs:" in ins[1]:
            stop.update(reason="environment or system instruction requires real Windows state",
                        address=address, assembly=" ".join(ins))
            engine.emu_stop()

    def block_hook(engine, address, size, _):
        state["blocks"] += 1
        if len(block_log) < 20000:
            block_log.append({"va":address, "size":size})

    def memory_write(engine, access, address, size, value, _):
        if STACK_BASE <= address < STACK_BASE + STACK_SIZE:
            state["stack_writes"] += 1
            return
        state["image_writes"] += 1
        if IMAGE_BASE <= address < IMAGE_BASE + IMAGE_SIZE:
            for page in range(address & ~0xfff, (address + size - 1 & ~0xfff) + 1, 0x1000):
                dirty.add(page)
                write_counts[page] += 1

    def invalid(engine, access, address, size, value, _):
        stop.update(reason="unmapped memory access", access=access, address=address,
                    size=size, eip=engine.reg_read(UC_X86_REG_EIP))
        return False

    uc.hook_add(unicorn.UC_HOOK_CODE, code_hook)
    uc.hook_add(unicorn.UC_HOOK_BLOCK, block_hook)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, memory_write)
    uc.hook_add(unicorn.UC_HOOK_MEM_INVALID, invalid)
    started = time.monotonic()
    error = None
    try:
        uc.emu_start(ENTRY, 0, timeout=30000000, count=budget)
    except UcError as e:
        error = str(e)
        if stop["reason"] is None:
            stop.update(reason="CPU emulator error", eip=uc.reg_read(UC_X86_REG_EIP))
    if stop["reason"] is None:
        stop.update(reason="30-second CPU emulator timeout or instruction budget")
    changed = []
    for page in sorted(dirty):
        raw = bytes(uc.mem_read(page, 0x1000))
        filename = f"page-{page:08x}.bin"
        (directory / filename).write_bytes(raw)
        changed.append({"va":page, "bytes":4096, "writes":write_counts[page],
                        "sha256":sha(raw), "file":filename,
                        "decoded_offset":page-DEST_BASE if DEST_BASE <= page < DEST_BASE+len(recovered) else None})
    report = {
        "method":__doc__, "unicorn_version":unicorn.__version__, "capstone_version":capstone.__version__,
        "input_sha256_before":sha(data), "input_sha256_after":sha(source.read_bytes()),
        "recovered_sha256":sha(recovered), "initial_registers":initial,
        "assumptions":["PE loaded at preferred image base", "no real Windows loader, TLS initialization, PEB, TEB, APIs, or process state",
                       "all general registers zero apart from synthetic stack", "stack initially zero except synthetic return address",
                       "original sections and offline-decoded .themida mapped exactly at static VAs"],
        "image_base":IMAGE_BASE, "image_size":IMAGE_SIZE, "stack_base":STACK_BASE,
        "stack_size":STACK_SIZE, "entry_va":ENTRY, "instruction_budget":budget,
        "seconds":time.monotonic()-started, "counters":state, "stop":stop, "emulator_error":error,
        "synthetic_rdtsc":synthetic_rdtsc, "cpu_inputs":cpu_inputs,
        "stop_only_import_traps":import_slots,
        "synthetic_rdtsc_rule":"ticks = 1000000000 + executed_instruction_count * 100; writes EDX:EAX and advances EIP past RDTSC; target bytes and branches unmodified" if synthetic_rdtsc else None,
        "final_registers":{name:uc.reg_read(reg) for name,reg in REGS.items()},
        "final_stack_va":uc.reg_read(UC_X86_REG_ESP),
        "final_stack_bytes":bytes(uc.mem_read(uc.reg_read(UC_X86_REG_ESP),256)).hex(),
        "written_image_pages":changed, "code_pages":sorted(code_pages),
        "last_instructions":list(last), "first_blocks":block_log,
        "limitations":["Emulator-only hypothesis; not observed game behavior", "No gameplay recovered merely by running a protector stub",
                       "written pages may contain initialization or encrypted protector state rather than gameplay"],
    }
    (directory / "emulation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"stop":stop,"counters":state,"written_pages":len(changed),"seconds":report["seconds"]},indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"evidence/loader-recovery/emulation-01")
    parser.add_argument("--budget",type=int,default=2000000)
    parser.add_argument("--synthetic-rdtsc",action="store_true")
    parser.add_argument("--import-traps",action="store_true")
    args = parser.parse_args()
    run(args.output,args.budget,args.synthetic_rdtsc,args.import_traps)
