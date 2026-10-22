# NATIVE-MIX-001 progress

WIP handoff, 2026-10-22. The whole task is unfinished. The owner authorized
this budget fallback: commit, write this file, push claude/native-mix,
and do not open a PR. Do not merge this partial work or rebuild Preview
as though the requested native feature were complete.

## Workspace and scope

- Worktree: `~/Documents/mu-worktrees/native-mix`, branch `claude/native-mix`.
- Main checkout `~/Documents/main-exe-study` was not modified.
- Read `~/Documents/mu-mac-tools/native/BRIEF-wave4.md` and BRIEF-common.md.
  The owner's task overrides the old Claude attribution defaults. No
  Claude co-author trailer; future PR body must end with
  `Generated with Codex (GPT-6.1 Sol)`.
- No live client was launched, no GAME-LOCK acquired, no real item or zen
  changed, no Preview client touched. No protection/encryption work.
- Do not touch parallel NATIVE-SOCIAL-001/NATIVE-POLISH-001 areas.

## Completed slice

Read [docs/research/client-mix.md](docs/research/client-mix.md) and
[reconstructed/mix/README.md](reconstructed/mix/README.md).

`reconstructed/mix` has source-summary conversion without harmony,
ingredient conditions, readiness/repeat counts, optional ingredient
selectors, expressions, rate/A-B-C-cost arithmetic, Bless/Soul/Life
eligibility and the unencrypted jewel request body. No native/GFx code
has been changed. The root Makefile discovers the new portable tests.

Private validation: 52,533 comparisons, zero mismatches, 11/11 planted
mistakes caught, all 3,009 installed Mix.bmd rows over synthetic summaries.
Twelve portable worked examples pass. `bash scripts/local-macos-ci.sh`
exited 0 after resolving the rebase onto `bb27f8a`. Both shared-doc entries
were retained. The tested tree `8149c7ed9d51e2ade48fce2f2ceb9883598d5fa0`
matches the completed rebase commit `39edaba`; only this verification note
and the finding's gate note changed afterward. Implementation is `357066a`.
The gate log is local at `scratch/mix/local-macos-ci.log` under mu-mac-tools/native.

Private report and disassembly:
`~/Documents/mu-mac-tools/native/scratch/mix/validation.json`,
`client_probe.py`, `item.asm`, `state.asm`, `recipes.asm`, `match.asm`.
Private AS exports: `scratch/mix/as/scripts/__Packages/MixInventoryFrame.as`.
Requested render directory `~/Documents/mu-mac-tools/native/renders/mix/`
exists but has no native renders. No PR, merge commit or rebuilt app.

The shared app-polish `tools/.venv` lacks Unicorn. It was left unchanged.
Private validator Python is
`~/Documents/mu-mac-tools/native/scratch/mix/.venv/bin/python`, with the
repo-pinned Unicorn 2.1.4 and Capstone 5.0.9. Portable CI uses the requested
tools/.venv symlink to app-polish.

## Review findings addressed

The first two-axis review found missing provenance docs, malformed formula
acceptance, a token-7 overflow cast and corpus blind spots. Shape validation
and defined CVTTSS2SI overflow were added, along with accepting extra kinds
6..11, division, token 7, nested groups, numeric boundaries and mutations
7..9. Mutant 10 checks the jewel opcode. The actual CRT conversion now
executes in the quote tests. A second review found the kind-0x37 compound
flag error and a non-finite intermediate hidden by token 7. Both are fixed,
with exhaustive byte-kind cases, mutant 11 and portable regressions.
The final standards and correctness rechecks found no actionable P1/P2
issues within this documented WIP slice.

## Suggested skills

- Implementation skill for the next bounded source/native/GFx slice.
- Code-review skill before publishing the completed task.
- Unslop for the concise shared-doc and PR text.

## Exact next action

Read the original owner task and the finding's Next work section. Continue
with the actual recipe-manager selection, not a first-ready-row substitute:

```sh
cd ~/Documents/mu-worktrees/native-mix
tools/.venv/bin/python ~/Documents/mu-mac-tools/native/scratch/mix/client_probe.py 0x00d0b2c6 0x00d0b847
```

Port candidate filtering/ranking `0x00d0b2c6`, tie score `0x00d0b5d7`,
grouping `0x00d08e38` and state aggregation `0x00d09366`/`0x00d096f0`.
Then wire MixGoblinSel/MixInventoryFrame via GFx and the NPC talk-result
dispatch, add offline requests/replies, and update inventory/tooltip/glow
from reply snapshots. Existing glow is already in world_gfx_game.c.
Personal-store registration/results and NPC repair requests/results are
still required. Harmony summaries and cost D remain unsupported.

After the complete feature: fetch/rebase keeping both sides in shared docs,
run `bash scripts/local-macos-ci.sh` to exit 0, push/open/merge the PR,
then rebuild Preview from merged main. Never dispatch hosted CI or kill
a Preview client not started by this task.
