# SYS-MISC-001b checkpoint

WIP, 2026-10-28. Owner hard stop is 14:45 CDT; final pushed handoff is due by
14:40. Keep the worktree for resumption. No merge lock acquired, no PR opened.
Issue #236 owns this slice; #208 remains stopped and is not resumed.

Branch `codex/sys-misc-001b`, worktree `~/Documents/MTM/worktrees/sys-misc-001b`,
created from origin/main `374777c`. `tools/python` and `evidence` are untracked
symlinks to the main checkout's inputs. Never stage them.

## Done

- Read the full common brief, workspace/repo instructions, current status and
  handoff, roadmap, plan/lane ownership, backlog report, SYS-MISC-001a finding,
  input/HUD findings and APP-REFRESH handoff.
- Confirmed the existing helpdata decoder schedule. Added an authored reader
  wrapper in `reconstructed/help`, portable synthetic-file tests and a pinned
  original-instruction validator with six compiled source mutants.
- 56 reader comparisons, zero mismatches: 48 valid synthetic, 6 corrupt, 1
  missing, 1 installed; 25,088 per-row original decode calls. All six mutants
  caught. Five portable tests pass, private test skips by default.
- Recovered static list-selection and row-emitter contracts. Details and
  source addresses are in `docs/research/client-help-window.md`.

## Next

First rerun the reader validator after the strengthened service/import checks.
Then implement and compare provider construction `0x00b89866`, constructor
`0x00b89588`, loader `0x00b89977`, reload `0x00b89c17`, and row emitters
`0x00b89cc0` / `0x00b89e69`. Be explicit about modeled STL/GFx/string/code-page
boundaries. Preserve the independently tested zero-ID stop, category-byte
selection, ID/mode filtering and third-list append behavior.

After controller equality, host HelpWindow.swf with installed rows through
minimal layer hooks. Find an original menu/open route or label the native
binding. F1 has no recorded HelpWindow-open route. Still required: isolated
real-movie view, native window check, final current-main full Mac gate under
the queue/lock, PR and merge. None are claimed by this checkpoint.

## Local artifacts and resume commands

All lane output lives under `mu-mac-tools/native/scratch/sys-misc-001b` and
`mu-mac-tools/native/renders/sys-misc-001b`. Reader JSON contains counts/hashes
only. Remove disposable reports after their summaries are committed. No new
input needs to be retained; original inputs remain in the shared evidence and
installed game directories. No original client was accessed or started.

```sh
./tools/python/bin/python -m unittest discover -s tests -p test_help.py -v
./tools/python/bin/python scripts/validate_help.py --cases 48 --mutants \
  --game-root "<installed-root>" --output "<lane-scratch>/reader.json"
MU_RECOVERY_INTEGRATION=1 ./tools/python/bin/python -m unittest discover \
  -s tests -p test_help.py -v
```

The installed root is recorded as `game_root` in the Preview Native Data
setup.json. Do not copy whole settings or credentials into logs. Existing
movie input is `scratch/gfx/all-bridge/HelpWindow.swf`. System `java` is a
launcher without a runtime; locate the existing local JRE before using JPEXS.
Do not install or regenerate the movie just to work around that path.
