# DATA-ACQ-003, first run without Python

Implemented 2026-10-27 on `codex/data-acq-003` in its assigned isolated worktree.
Finding and repeat commands: [native-gfx-converter.md](../research/native-gfx-converter.md).

- C converter replaces the Python/Pillow runtime dependency. The Python converter
  stays unchanged as a development oracle. App first-run invokes the bundled,
  signed executable; no Python files ship in the app.
- Full installed corpus, default and app options separately: 261/261 file hashes
  equal, including 179 movies and 82 NaviMaps; 9,166/9,166 embedded bitmap assets
  equal in each mode. Zero converter mismatches.
- Existing Native Data is read-only. One pre-existing difference,
  `winQuestSummary.swf`, differs from both new converters; 260/261 existing files
  agree. No installed data was changed.
- Clean environment simulation: signed app `--setup`, temporary HOME and
  CFFIXED_USER_HOME, `env -i`, PATH without Python. 179 movies, all 261 output
  hashes equal, plus 31 text files, 33 object files and one sound table copied.
- Portable converter: 11 tests; ASan/UBSan: 11 tests; planted mistakes: 3/3 caught.
  App: 12 tests, 11 pass, one explicit private smoke skip. Repeat/force and failed
  conversion preservation are covered.
- Local gate: `bash scripts/local-macos-ci.sh tools/python/bin/python` passes on
  latest integrated main `15962e9`: 1,297 tests, 1,142 pass and 155 explicit skips;
  viewer/readers build and repository audit pass, zero rejected files.

Scratch, logs and per-file hashes:
`~/Documents/MTM/mu-mac-tools/native/scratch/data-acq-003/`.
No original client, launcher or live service used. No network/protection changes.

Remaining: a real second macOS user was not available, so its account/consent and
permissions remain unverified. Guided capture for other users is DATA-ACQ-002;
distribution signing/notarization remains deferred. No claim of full gate-5 or
cross-machine installation completion.
