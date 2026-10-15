#!/usr/bin/env python3
"""Repeat independent aPLib validation using the reviewed, pinned reference."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/loader-recovery"


def main():
    reference = OUT / "reference/aplib.py"
    provenance = json.loads((OUT / "reference/source.json").read_text())
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == provenance["aplib_py_sha256"]
    spec = importlib.util.spec_from_file_location("reference_aplib", reference)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    source = (ROOT / "input/main.exe").read_bytes()
    report = json.loads((OUT / "recovery.json").read_text())
    assert hashlib.sha256(source).hexdigest() == report["input_sha256_before"]
    chunks = []
    for record in report["chunks"]:
        start, end = record["compressed_file_start"], record["compressed_file_end_exclusive"]
        decoder = module.APLib(source[start:end], strict=True)
        output = decoder.depack()
        digest = hashlib.sha256(output).hexdigest()
        assert digest == record["sha256"]
        assert len(output) == record["decoded_bytes"]
        assert decoder.source.tell() == end - start
        chunks.append({"chunk":record["index"], "sha256":digest, "bytes":len(output),
                       "compressed_bytes_consumed":decoder.source.tell(), "matches":True})
    result = {"reference":provenance, "reference_self_test_passed":True, "chunks":chunks}
    (OUT / "independent-validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(f"Independent aPLib validation passed for {len(chunks)} chunks")


if __name__ == "__main__":
    main()
