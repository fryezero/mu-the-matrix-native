#!/usr/bin/env python3
"""Inspect first-stage bytes and extract embedded PE files without execution."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/loader-recovery"
BASE = 0x0BE3C000


def main():
    data = (OUT / "themida-decoded.bin").read_bytes()
    original = (ROOT / "input/main.exe").read_bytes()
    patterns = {"decoder_prefix":original[0x87645d:0x87645d+32],
                "getbit_inline":bytes.fromhex("00d275058a164610d2"),
                "AP32":b"AP32", "MZ":b"MZ", "kernel32":b"kernel32",
                "VirtualAlloc":b"VirtualAlloc", "GetProcAddress":b"GetProcAddress",
                "zlib_789c":bytes.fromhex("789c"), "aPLib_name":b"aPLib", "Themida_name":b"Themida"}
    signatures = {}
    for name,pattern in patterns.items():
        found = [m.start() for m in re.finditer(re.escape(pattern),data)]
        signatures[name] = {"count":len(found), "first_offsets":found[:50]}
    strings = []
    for match in re.finditer(rb"[ -~]{8,}",data):
        text = match.group().decode("ascii")
        if any(word in text.lower() for word in ("dll","virtual","import","version","memory","error","compress","protect","debug","load","getproc","themida","weapon","muonline","webzen")):
            strings.append({"offset":match.start(),"va":BASE+match.start(),"text":text})
    (OUT / "signature-scan.json").write_text(json.dumps({"patterns":signatures,"selected_strings":strings},indent=2)+"\n")
    embedded = []
    for match in re.finditer(b"MZ",data):
        off = match.start()
        if off+64 > len(data):
            continue
        pe = off + struct.unpack_from("<I",data,off+60)[0]
        if pe+24 > len(data) or data[pe:pe+4] != b"PE\0\0":
            continue
        machine,count = struct.unpack_from("<HH",data,pe+4)
        optsize = struct.unpack_from("<H",data,pe+20)[0]
        sectstart = pe+24+optsize
        if sectstart+count*40 > len(data):
            continue
        sections,end = [],0
        for index in range(count):
            pos = sectstart+index*40
            name = data[pos:pos+8].split(b"\0")[0].decode("ascii",errors="replace")
            vs,rva,rs,rp = struct.unpack_from("<IIII",data,pos+8)
            end = max(end,rp+rs)
            sections.append({"name":name,"rva":rva,"virtual_size":vs,"raw_offset":rp,"raw_size":rs})
        if end == 0 or off+end > len(data):
            continue
        payload = data[off:off+end]
        filename = f"embedded-pe-{len(embedded):02d}.bin"
        (OUT / filename).write_bytes(payload)
        embedded.append({"offset":off,"va":BASE+off,"bytes":len(payload),
                         "sha256":hashlib.sha256(payload).hexdigest(),"pe_offset":pe-off,
                         "machine":machine,"imagebase":struct.unpack_from("<I",data,pe+24+28)[0],
                         "entry_rva":struct.unpack_from("<I",data,pe+24+16)[0],
                         "sections":sections,"file":filename})
    (OUT / "embedded-pe.json").write_text(json.dumps(embedded,indent=2)+"\n")
    entropy = []
    for offset in range(0,len(data),1048576):
        chunk = data[offset:offset+1048576]
        count = Counter(chunk)
        ent = -sum((n/len(chunk))*math.log2(n/len(chunk)) for n in count.values())
        entropy.append({"offset":offset,"entropy":ent,"zeros":count[0],"e9_jumps":count[233]})
    (OUT / "decoded-entropy.json").write_text(json.dumps(entropy,indent=2)+"\n")
    print(f"Found {len(embedded)} embedded PE files and {len(strings)} selected strings")


if __name__ == "__main__":
    main()
