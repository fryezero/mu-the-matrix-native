#!/usr/bin/env python3
"""Offline translation of the entry decoder at 0x0e64605d, never runs target code.

MIT licensed original analysis code. The recovered bytes retain their original
ownership. Addresses below are specific to the SHA-256 in EXPECTED_SHA256.
"""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SHA256 = "3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a"
BOOT_VA = 0x0E646000
BOOT_FILE = 0x876400
STREAM_FILE = 0x876606
DEST_VA = 0x0BE3C000
JUMP_OFFSET = 0x23280
MAX_TOTAL = 0x280A000


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Decoder:
    def __init__(self, data, start, limit):
        self.data, self.start, self.pos, self.limit = data, start, start, limit
        self.out = bytearray()
        self.bits = 0x80
        self.stats = {"literal": 0, "single": 0, "short": 0,
                      "long": 0, "repeat": 0, "zero": 0}

    def byte(self):
        if self.pos >= len(self.data):
            raise ValueError("compressed source exhausted")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def bit(self):
        # ADD DL,DL; refill MOV DL,[ESI] / ADC DL,DL on zero.
        carry = self.bits >> 7
        self.bits = (self.bits << 1) & 255
        if not self.bits:
            b = self.byte()
            self.bits = ((b << 1) | carry) & 255
            carry = b >> 7
        return carry

    def gamma(self):
        n = 1
        while True:
            n = (n << 1) | self.bit()
            if n > 0xffffffff:
                raise ValueError("gamma value overflow")
            if not self.bit():
                return n

    def append(self, b):
        if len(self.out) >= self.limit:
            raise ValueError("decompressed output exceeds static destination bound")
        self.out.append(b)

    def copy(self, offset, count):
        if not 0 < offset <= len(self.out):
            raise ValueError(f"invalid backward offset {offset:#x} at output {len(self.out):#x}")
        if count > self.limit - len(self.out):
            raise ValueError("copy exceeds static destination bound")
        for _ in range(count):
            self.out.append(self.out[-offset])

    def run(self):
        r0 = None
        state = 2
        self.append(self.byte())
        self.stats["literal"] += 1
        while True:
            if not self.bit():
                self.append(self.byte())
                self.stats["literal"] += 1
                state = 2
            elif not self.bit():
                offset = self.gamma() - state
                state = 1
                if offset == 0:
                    if r0 is None:
                        raise ValueError("repeat before previous offset")
                    self.copy(r0, self.gamma())
                    self.stats["repeat"] += 1
                else:
                    offset = ((offset - 1) << 8) | self.byte()
                    r0 = offset
                    count = self.gamma()
                    if offset >= 0x7D00:
                        count += 2
                    elif offset >= 0x500:
                        count += 1
                    elif offset <= 0x7f:
                        count += 2
                    self.copy(offset, count)
                    self.stats["long"] += 1
            elif not self.bit():
                b = self.byte()
                offset = b >> 1
                if not offset:
                    return bytes(self.out)
                self.copy(offset, 2 + (b & 1))
                r0, state = offset, 1
                self.stats["short"] += 1
            else:
                offset = 0
                for _ in range(4):
                    offset = (offset << 1) | self.bit()
                if offset:
                    self.copy(offset, 1)
                    self.stats["single"] += 1
                else:
                    self.append(0)
                    self.stats["zero"] += 1
                state = 2


def recover(source, directory):
    data = source.read_bytes()
    digest = sha(data)
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Unexpected input SHA-256 {digest}")
    directory.mkdir(parents=True, exist_ok=True)
    cursor = STREAM_FILE
    output = bytearray()
    records, groups = [], []
    while True:
        group_offset = cursor
        count = data[cursor]
        cursor += 1
        groups.append({"file_offset": group_offset, "count": count})
        if count == 0:
            break
        if len(groups) > 128:
            raise ValueError("Too many groups")
        for _ in range(count):
            decoder = Decoder(data, cursor, MAX_TOTAL - len(output))
            decoded = decoder.run()
            index = len(records)
            filename = f"chunk-{index:02d}.bin"
            (directory / filename).write_bytes(decoded)
            records.append({
                "index": index, "file": filename,
                "compressed_file_start": cursor,
                "compressed_file_end_exclusive": decoder.pos,
                "compressed_va_start": BOOT_VA + cursor - BOOT_FILE,
                "compressed_bytes": decoder.pos - cursor,
                "decoded_offset": len(output),
                "decoded_va": DEST_VA + len(output),
                "decoded_bytes": len(decoded),
                "sha256": sha(decoded), "operations": decoder.stats,
            })
            output.extend(decoded)
            cursor = decoder.pos
    (directory / "themida-decoded.bin").write_bytes(output)
    report = {
        "input": str(source.resolve()), "input_sha256_before": digest,
        "input_sha256_after": sha(source.read_bytes()),
        "method": "Offline Python translation of disassembled first-stage decoder; target not executed",
        "decoder_va_start": 0x0E64605D, "decoder_va_end_exclusive": 0x0E6461A8,
        "driver_va_start": 0x0E6461A8, "stream_file_offset": STREAM_FILE,
        "groups": groups, "chunks": records,
        "compressed_end_exclusive": cursor,
        "decoded_file": "themida-decoded.bin", "decoded_bytes": len(output),
        "decoded_base_va": DEST_VA, "decoded_sha256": sha(output),
        "first_stage_jump_offset": JUMP_OFFSET,
        "first_stage_jump_va": DEST_VA + JUMP_OFFSET,
        "limitations": ["First-stage decoded data only; not a runnable PE or game source",
                        "Virtual mapping follows observed loader arithmetic, not runtime observation",
                        "Compressed-source mapping is per chunk; LZ backreferences prevent a simple byte-to-byte mapping"],
    }
    (directory / "recovery.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("input/main.exe"))
    parser.add_argument("--output", type=Path, default=Path("evidence/loader-recovery"))
    args = parser.parse_args()
    result = recover(args.input, args.output)
    print(json.dumps({k: result[k] for k in ("decoded_bytes", "decoded_sha256", "groups", "first_stage_jump_va")}, indent=2))
