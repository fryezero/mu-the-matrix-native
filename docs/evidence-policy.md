# Repository and local evidence

Commit original source, synthetic regression fixtures, public mathematical test vectors, reviewed findings, target digests and source references. Keep binaries, game data, recovered geometry, decompiler payloads, memory captures, raw REA ledgers and machine-specific logs in ignored local directories.

The repository is public; its tracked tree must stay suitable for review without shipping the game. Privacy is not a reason to mix raw process data into source control. Game files and recovered outputs retain their original ownership; the project license covers authored implementations and documentation.

## README screenshots

At the owner's request, `docs/images/` holds the README's screenshots and renders (since 2026-10-21; the earlier
`docs/media/` set is in the history). They are window-only captures and offline native renders, resized for the
web, visually reviewed (no account names, passwords, emails or private paths) and pinned by exact path and SHA-256
in the publication audit. This exception covers only those documentation images, not game asset packs, model or
texture exports, executable bytes or process dumps. All other binary and generated files remain subject to the
existing audit. Replacing an image means reviewing it again and updating its pin. The game imagery retains its
owners' rights and is not covered by this repository's MIT license.

## Record a finding

Each substantive finding needs an input hash, a bounded question, its original address/file offset where applicable, the method/tool identity, the observation, any inference, tested coverage and remaining uncertainty. A summary may link relative paths to ignored evidence, but should state when a fresh clone cannot open that evidence.

`evidence-index.json` is the shared index. Local raw manifests are the detailed source, not remote hidden attachments. Reproduction instructions must identify which inputs the contributor supplies. Synthetic unit tests and private corpus scans answer different questions.

## Publication check

Run `python3 scripts/audit_repository.py` before committing. Review staged filenames and diffs. The audit rejects generated/binary formats, acquisition directories, oversized files and local-machine paths. It is a useful boundary check, not a substitute for reading changed content.

Memory-capture helpers and analysis should stay within the selected game and the owner's authorized environment. Keep game-account credentials out of reports and do not upload process captures as GitHub issue attachments or workflow artifacts.

Session recordings (journals of native or original-client sessions, NET-CONTRACT-001 permits recording the owner's
own sessions) are local evidence like memory captures: ignored directories only, never committed or uploaded. They
carry the client build digest. Login and delete payloads are written as their length only, and nothing the launcher
or IGC.dll produces is recorded.
