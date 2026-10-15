#!/usr/bin/env python3
"""Follow only direct jumps/calls statically from decoded protector entry.

Does not emulate, execute, resolve indirect calls, or choose conditional paths.
Calls are followed only to expose call/pop position-independent initialization.
No return-stack reconstruction is attempted. All original addresses are retained.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/loader-recovery"
BASE = 0x0BE3C000
PROVIDER = "/opt/homebrew/opt/binutils/bin/gobjdump"


def disassemble(start, size=96):
    proc = subprocess.run([PROVIDER, "-D", "-b", "binary", "-m", "i386", "-Mintel",
                           "--insn-width=16", f"--adjust-vma={BASE:#x}",
                           f"--start-address={start:#x}", f"--stop-address={start + size:#x}",
                           str(OUT / "themida-decoded.bin")], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    result = []
    for line in proc.stdout.splitlines():
        match = re.match(r"\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s+(.+)", line)
        if match and int(match.group(1), 16) < start + size - 16:
            a, raw, text = match.groups()
            result.append({"va": int(a, 16), "decoded_offset": int(a, 16) - BASE,
                           "bytes": raw.strip(), "assembly": text})
    return result


def trace(start, limit=1000):
    cursor = start
    trace, seen = [], set()
    while len(trace) < limit:
        if cursor in seen:
            return trace, "revisited address"
        instructions = disassemble(cursor)
        if not instructions:
            return trace, "no instructions"
        for ins in instructions:
            cursor = ins["va"]
            if cursor in seen:
                return trace, "revisited address"
            seen.add(cursor)
            trace.append(ins)
            asm = ins["assembly"]
            opcode = asm.split()[0]
            direct = re.fullmatch(r"(?:jmp|call)\s+0x([0-9a-f]+)", asm)
            if direct:
                cursor = int(direct.group(1), 16)
                if not BASE <= cursor < BASE + 41984000:
                    return trace, "direct destination outside decoded section"
                break
            if opcode.startswith("j") or opcode.startswith("ret") or opcode in ("int", "int3", "loop", "syscall", "call"):
                return trace, "conditional, indirect, return, or system operation"
            cursor += len(ins["bytes"].split())
        else:
            continue
    return trace, "instruction limit reached"


if __name__ == "__main__":
    instructions, reason = trace(0x0BE5F280)
    (OUT / "entry-direct-flow.json").write_text(json.dumps({"method": __doc__, "stop_reason": reason,
                                                          "instructions": instructions}, indent=2) + "\n")
    lines = ["; Direct-flow static traversal. No target code executed.", "; Stop: " + reason]
    lines.extend(f"{i['va']:08x}  {i['assembly']}" for i in instructions)
    (OUT / "entry-direct-flow.asm").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
