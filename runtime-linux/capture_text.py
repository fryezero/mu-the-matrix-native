#!/usr/bin/env python3
"""Capture the pinned client's first executable image section under Linux Wine."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys

TARGET_SHA256 = '3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a'
IMAGE_BASE = 0x400000
TEXT_START = 0x401000
TEXT_BYTES = 23572480
IMAGE_BYTES = 260628480


def check_image_header(header):
    if len(header) < 64 or header[:2] != b'MZ':
        raise ValueError('Selected image has no DOS header')
    pe_offset, = struct.unpack_from('<I', header, 60)
    if pe_offset > len(header) - 24 - 60:
        raise ValueError('Selected PE header is outside the captured header page')
    optional = pe_offset + 24
    if (header[pe_offset:pe_offset+4] != b'PE\0\0' or
            struct.unpack_from('<H', header, pe_offset+4)[0] != 0x14c or
            struct.unpack_from('<H', header, optional)[0] != 0x10b or
            struct.unpack_from('<I', header, optional+28)[0] != IMAGE_BASE or
            struct.unpack_from('<I', header, optional+56)[0] != IMAGE_BYTES):
        raise ValueError('Mapped PE header does not match the pinned x86 image layout')


def process_identity(stat):
    """Names in /proc/PID/stat can contain spaces and closing parentheses."""
    fields = stat.rsplit(')', 1)[1].split()
    pid = int(stat.split(' ', 1)[0])
    if len(fields) < 20 or not fields[19].isdigit():
        raise ValueError('Invalid process identity record')
    return pid, int(fields[19]), fields[0]


def image_ranges(maps, start, length):
    """Require complete readable/executable coverage of the selected image range."""
    if start < 0 or length <= 0:
        raise ValueError('Invalid image range')
    limit = start + length
    ranges = []
    for line in maps.splitlines():
        match = re.match(r'^([0-9a-f]+)-([0-9a-f]+) ([rwxps-]{4}) ', line)
        if match is None:
            raise ValueError('Invalid process mapping record')
        low, high = (int(match[i], 16) for i in (1, 2))
        low, high = max(start, low), min(limit, high)
        if low < high:
            if 'r' not in match[3] or 'x' not in match[3]:
                raise ValueError('Selected image range is not readable executable memory')
            ranges.append((low, high, match[3]))
    cursor = start
    for low, high, _ in sorted(ranges):
        if low != cursor:
            raise ValueError('Selected image range has a gap or overlap')
        cursor = high
    if cursor != limit:
        raise ValueError('Selected image range is not completely mapped')
    return sorted(ranges)


def mapped_image_identity(maps, target_stat):
    """Bind the mapped PE header to the selected file, not its display name."""
    for line in maps.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5:
            raise ValueError('Invalid process mapping record')
        low, high = (int(value, 16) for value in fields[0].split('-'))
        if low <= IMAGE_BASE < high:
            major, minor = (int(value, 16) for value in fields[3].split(':'))
            identity = (major, minor, int(fields[4]))
            expected = (os.major(target_stat.st_dev), os.minor(target_stat.st_dev), target_stat.st_ino)
            if (identity != expected or int(fields[2], 16) + IMAGE_BASE - low != 0 or
                    high < IMAGE_BASE + 4096 or 'r' not in fields[1]):
                raise ValueError('Mapped image header does not belong to the pinned target file')
            return identity
    raise ValueError('No file-backed image header mapping')


def copy_ranges(memory_fd, destination, ranges):
    digest = hashlib.sha256()
    written = 0
    with destination.open('xb') as output:
        for low, high, _ in ranges:
            while low < high:
                size = min(1024 * 1024, high - low)
                data = os.pread(memory_fd, size, low)
                if len(data) != size:
                    raise OSError('Short process-memory read')
                output.write(data)
                digest.update(data)
                low += size
                written += size
        output.flush()
        os.fsync(output.fileno())
    return written, digest.hexdigest()


def capture(pid, target, output):
    proc = Path('/proc') / str(pid)
    target = target.resolve(strict=True)
    output = output.resolve()
    if output == target.parent or target.parent in output.parents:
        raise ValueError('Output must be outside the client directory')
    if pid <= 0 or target.name.lower() != 'main.exe':
        raise ValueError('Select the exact main.exe process and file')
    source_stat = target.stat()
    source_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    if source_hash != TARGET_SHA256:
        raise ValueError('Target file does not match the pinned client')
    before = process_identity((proc / 'stat').read_text())
    argv0 = (proc / 'cmdline').read_bytes().split(b'\0', 1)[0]
    if (before[0] != pid or before[2] in ('Z', 'X') or
            argv0.rsplit(b'/', 1)[-1].lower() != b'main.exe' or
            (proc / 'cwd').resolve() != target.parent):
        raise ValueError('Process identity does not match the selected client directory')
    maps = (proc / 'maps').read_text()
    image_identity = mapped_image_identity(maps, source_stat)
    ranges = image_ranges(maps, TEXT_START, TEXT_BYTES)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'format': 'mu-linux-wine-text-capture-v1', 'pid': pid,
                'process_start_ticks': before[1], 'target_sha256': source_hash,
                'mapped_image_device_inode': list(image_identity),
                'started_utc': datetime.now(timezone.utc).isoformat(),
                'address': hex(TEXT_START), 'expected_bytes': TEXT_BYTES,
                'complete_within_scope': False,
                'limitations': ['Wine compatibility environment, not native Windows.',
                                'Unsuspended reads are not an atomic snapshot.',
                                'Only the pinned first executable image section is selected.',
                                'No other modules, stacks or private allocations are selected.',
                                'Captured bytes do not establish gameplay or behavior equivalence.']}
    try:
        with (proc / 'mem').open('rb', buffering=0) as memory:
            check_image_header(os.pread(memory.fileno(), 4096, IMAGE_BASE))
            size, digest = copy_ranges(memory.fileno(), output / 'client-text.bin', ranges)
        after = process_identity((proc / 'stat').read_text())
        after_maps = (proc / 'maps').read_text()
        after_image_identity = mapped_image_identity(after_maps, target.stat())
        manifest.update(file='client-text.bin', bytes=size, sha256=digest,
                        same_process=before[:2] == after[:2],
                        process_still_running=after[2] not in ('Z', 'X'),
                        same_mapping_plan=ranges == image_ranges(after_maps, TEXT_START, TEXT_BYTES),
                        same_image_file=image_identity == after_image_identity,
                        target_file_unchanged=hashlib.sha256(target.read_bytes()).hexdigest() == source_hash)
        manifest['complete_within_scope'] = all(manifest[k] for k in
            ('same_process', 'process_still_running', 'same_mapping_plan', 'same_image_file', 'target_file_unchanged')) and size == TEXT_BYTES
    except (OSError, ValueError, IndexError) as error:
        manifest['error'] = str(error)
    finally:
        manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with (output / 'capture.json').open('x') as record:
            json.dump(manifest, record, indent=2)
            record.write('\n')
            record.flush()
            os.fsync(record.fileno())
        directory_fd = os.open(output, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not sys.platform.startswith('linux'):
        parser.error('Run this inside the isolated Linux guest')
    try:
        result = capture(args.pid, args.target, args.output)
    except (OSError, ValueError, IndexError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['complete_within_scope'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
