#!/usr/bin/env python3
"""Read BMD v12/v14/v15 envelopes into the validated mesh layout.

The static format constants and algorithm were cross-checked with primary
references in SOURCES.md. No original executable code is executed.
"""
import hashlib
import struct
import ctypes
import sys
from functools import lru_cache
from pathlib import Path
from bmd10 import BmdError, MAX_FILE, parse_bytes

MASK = 0xffffffff
DELTA = (0xc3efe9db, 0x44626b02, 0x79e27c8a, 0x78df30ec,
         0x715ea49e, 0xc785da0a, 0xe04ef22a, 0xe5c40957)
ROTATIONS = (1, 3, 6, 11, 13, 17)
# Published asset-format constant. This is not an account/authentication key.
FORMAT_KEY = bytes.fromhex('cc504513c2a6574ed69a4589bf2fbcd939b3b3bd50bdccb68546d1d61654e087')
MAP_KEY = bytes.fromhex('d17352f6d29acb273eaf593137b3e7a2')


def rol(value, bits):
    bits %= 32
    return ((value << bits) | (value >> ((32-bits) % 32))) & MASK


def ror(value, bits):
    return rol(value, 32-bits)


@lru_cache(maxsize=4)
def round_keys(key):
    if len(key) != 32:
        raise BmdError('LEA-256 requires a 32-byte key')
    words = list(struct.unpack('<8I', key))
    keys = []
    for i in range(32):
        delta, start = DELTA[i % 8], (i*6) % 8
        row = []
        for j, rotation in enumerate(ROTATIONS):
            index = (start+j) % 8
            words[index] = rol((words[index]+rol(delta, i+j)) & MASK, rotation)
            row.append(words[index])
        keys.append(tuple(row))
    return tuple(reversed(keys))


def decrypt_lea_python(cipher, key=FORMAT_KEY):
    if len(cipher) % 16:
        raise BmdError('LEA ECB payload must have complete 16-byte blocks')
    keys = round_keys(key)
    output = bytearray(len(cipher))
    for offset in range(0, len(cipher), 16):
        a,b,c,d = struct.unpack_from('<4I', cipher, offset)
        for k0,k1,k2,k3,k4,k5 in keys:
            t0 = d
            t1 = ((ror(a,9)-(t0 ^ k0)) ^ k1) & MASK
            t2 = ((rol(b,5)-(t1 ^ k2)) ^ k3) & MASK
            t3 = ((rol(c,3)-(t2 ^ k4)) ^ k5) & MASK
            a,b,c,d = t0,t1,t2,t3
        struct.pack_into('<4I', output, offset, a,b,c,d)
    return bytes(output)


@lru_cache(maxsize=1)
def native_reader():
    library = Path(__file__).with_name('liblea256.dylib' if sys.platform == 'darwin' else 'liblea256.so')
    if not library.exists():
        return None
    handle = ctypes.CDLL(str(library))
    function = handle.mu_lea256_decrypt
    function.argtypes = [ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,
                         ctypes.c_void_p,ctypes.c_size_t]
    function.restype = ctypes.c_int
    return function


def decrypt_lea(cipher, key=FORMAT_KEY):
    if len(cipher) % 16 or len(key) != 32:
        raise BmdError('LEA ECB requires complete blocks and a 32-byte key')
    function = native_reader()
    if function is None:
        return decrypt_lea_python(cipher,key)
    source = ctypes.create_string_buffer(cipher)
    output = ctypes.create_string_buffer(len(cipher))
    key_buffer = ctypes.create_string_buffer(key)
    if function(source,len(cipher),output,key_buffer,len(key)):
        raise BmdError('Native LEA decoder rejected input')
    return output.raw


def decrypt_map(cipher):
    previous = 0x5e
    output = bytearray(len(cipher))
    for i, value in enumerate(cipher):
        output[i] = ((value ^ MAP_KEY[i % 16])-previous) & 255
        previous = (value+0x3d) & 255
    return bytes(output)


@lru_cache(maxsize=1)
def modulus_reader():
    library = Path(__file__).with_name('libmodulus.dylib' if sys.platform == 'darwin' else 'libmodulus.so')
    try:
        handle = ctypes.CDLL(str(library))
    except OSError as error:
        raise BmdError('BMD v14 needs the Crypto++ reader; run make -C model-recovery') from error
    function = handle.mu_modulus_decrypt
    function.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                         ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
                         ctypes.c_void_p, ctypes.c_size_t]
    function.restype = ctypes.c_int
    return function


def decrypt_modulus(envelope):
    if not 34 <= len(envelope) <= MAX_FILE:
        raise BmdError('BMD v14 requires a complete 34-byte cipher prefix')
    source = ctypes.create_string_buffer(bytes(envelope))
    output = ctypes.create_string_buffer(len(envelope)-34)
    written = ctypes.c_size_t()
    error = ctypes.create_string_buffer(256)
    if modulus_reader()(source, len(envelope), output, len(output),
                        ctypes.byref(written), error, len(error)):
        raise BmdError(error.value.decode('utf-8', errors='replace'))
    if written.value != len(output):
        raise BmdError('BMD v14 decoder returned an inconsistent payload length')
    return output.raw


def parse_model(raw, *, client_layout=False):
    if len(raw) > MAX_FILE or len(raw) < 4 or raw[:3] != b'BMD':
        raise BmdError('Invalid BMD envelope or unsupported file size')
    version = raw[3]
    if version == 10:
        return parse_bytes(raw, client_layout=client_layout)
    if version not in (12,14,15):
        raise BmdError(f'Unsupported model version {version}')
    if len(raw) < 8:
        raise BmdError('Truncated encrypted envelope')
    length, = struct.unpack_from('<I', raw, 4)
    if length != len(raw)-8:
        raise BmdError('Declared encrypted length must match the complete payload')
    if version == 12:
        plain = decrypt_map(raw[8:])
    elif version == 14:
        plain = decrypt_modulus(raw[8:])
    else:
        plain = decrypt_lea(raw[8:])
    model = parse_bytes(b'BMD\x0a'+plain, lea_block_padding=version == 15, client_layout=client_layout)
    model.update(version=version, decoded_layout_version=10,
                 source_bytes=len(raw), source_sha256=hashlib.sha256(raw).hexdigest(),
                 decoded_payload_sha256=hashlib.sha256(plain).hexdigest(),
                 encrypted_payload_bytes=length)
    if version == 14:
        model['modulus'] = {'inner_selector': raw[8], 'outer_selector': raw[9],
                            'inner_algorithm': raw[8] & 7, 'outer_algorithm': raw[9] & 7,
                            'envelope_prefix_bytes': 34, 'decoded_payload_bytes': len(plain)}
    return model


def parse_model_file(path, *, client_layout=False):
    path = Path(path)
    if path.stat().st_size > MAX_FILE:
        raise BmdError('File exceeds supported size limit')
    model = parse_model(path.read_bytes(), client_layout=client_layout)
    model['source_path'] = str(path)
    return model
