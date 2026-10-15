# Repository and local evidence

Commit original source, synthetic regression fixtures, public mathematical test vectors, reviewed findings, target digests and source references. Keep binaries, game data, recovered geometry, decompiler payloads, memory captures, raw REA ledgers and machine-specific logs in ignored local directories.

The repository is private initially, but its tracked tree should remain suitable for future review without shipping the game. Privacy is not a reason to mix raw process data into source control. Game files and recovered outputs retain their original ownership; the project license covers authored implementations and documentation.

## Record a finding

Each substantive finding needs an input hash, a bounded question, its original address/file offset where applicable, the method/tool identity, the observation, any inference, tested coverage and remaining uncertainty. A summary may link relative paths to ignored evidence, but should state when a fresh clone cannot open that evidence.

`evidence-index.json` is the shared index. Local raw manifests are the detailed source, not remote hidden attachments. Reproduction instructions must identify which inputs the contributor supplies. Synthetic unit tests and private corpus scans answer different questions.

## Publication check

Run `python3 scripts/audit_repository.py` before committing. Review staged filenames and diffs. The audit rejects generated/binary formats, acquisition directories, oversized files and local-machine paths. It is a useful boundary check, not a substitute for reading changed content.

Memory-capture helpers and analysis should stay within the selected game and the owner's authorized environment. Keep game-account credentials out of reports and do not upload process captures as GitHub issue attachments or workflow artifacts.
