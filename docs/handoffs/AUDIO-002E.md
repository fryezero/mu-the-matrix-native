# AUDIO-002 part 5

Owned branch `codex/audio-002e`, new worktree `~/Documents/MTM/worktrees/audio-002e` from latest
`origin/main` at `4b21583`. Scope: the three reconstructed scene-5 Enter/Esc sound-25 sites,
`mu_charsel`'s explicit callback, the shell audio hook/table lifetime, and focused tests/provenance.
No original client, launcher, live service, account/session migration or hosted workflow is used.

## Result and provenance

Caller adapters and sound-capable sites advance **73 to 76**. Original tick `0x01856e6c` calls
`SND_Play(25, NULL, 0)` at:

| Site | Branch |
|---|---|
| `0x01857064` | Enter after the input/GFx/selection gates, before the later refusal check |
| `0x01857163` | Esc opens the menu |
| `0x018571e6` | Esc closes the create panel |

`mu_charsel_audio_cue` consumes the existing ordered reconstructed log. The following service identifies
which of the three otherwise identical calls ran. It does not duplicate the branch gates. A borrowed
immediate callback on `mu_charsel_session` delivers `MU_CUE_SOUND` with the original routine/site,
null-object key `-2`, loop 0 and a per-visit sequence. The callback receives the scene logic-step number.
This offline scene has no network session or session ring. In the existing `audio:1` log,
`session_tick` therefore means the charsel logic step for handler `0x01856e6c`, and `cue_seq` is per
charsel visit; host/host-sequence still distinguishes repeated visits.

Detached and disabled events are discarded without later replay. The callback is cleared before shell
close/rebuild and at core free. Mute remains the existing Effect-group mixer policy. The shell loads the
configured installed sound table once for its existing music/audio host and frees it after the host.
The world's separate existing audio host remains unchanged. Standalone charsel tools remain silent
unless a caller installs the callback. The no-GFx Esc-to-server offline shortcut remains unchanged;
it does not execute either reconstructed Esc branch. GFx double-click/CButton/credits sounds are excluded.

The pinned text SHA-256 is `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`,
base `0x00401000`; image data SHA-256 is
`c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`, base `0x01a7c000`.
The tick's existing body pin remains `0ad0e9720d46bc4b09a67af4e6ddd0223f05c7bd4b32bb10d78cb5acab109d88`.

## Verification

- `tools/python/bin/python scripts/validate_audio_charsel.py --mutations --report <local>/original.json`:
  **5,968 complete original-tick cases, zero mismatches/stops**. Families: Enter **5,760**, Escape **64**,
  common gates **144**. Every combination of the selected input/GFx bytes is covered, with selection
  bounds, shown-index substitution, exact refusal value 1, protocol 0x32/0x33/0x35, initialization,
  simultaneous keys, and busy values 0/1/2. The existing recording services remain stubs; no GFx movie,
  account or FMOD implementation is inferred. Original SND_Play return addresses independently supply
  the expected sites. Output also compares initialization, selection and the panel-close byte.
- **11/11 compiled planted mutants caught**: three site swaps, wrong id/object/loop, Enter selection
  bound/panel gate, menu/panel gates, and moving refusal before the sound. Mutants compile the actual
  adapter or a temporary copy of reconstructed C; no mutant or captured byte is committed.
- The owning manifest row passes, **1 pass, zero fail/error/skip**. Six new native tests pass with
  private instruction comparison enabled. They cover real core keyboard/update calls and the host,
  all three sites once per press despite held keys, refused Enter, blocked keys, Effect mute, disabled
  delivery, detach/rebind without replay, callback cleanup, shell table loading and all three shell
  paths through a GFx stand-in. Nonzero decoded synthetic PCM is checked; muted output stays zero.
- Four standalone charsel PNG hashes equal the pre-change binary's hashes. Three shell flows retain
  equal audio-on/off render hashes. Existing render and PCM golden assertions are unchanged.
- Unchanged `validate_charsel.py --cases 1000 --mutations`: **6,000 cases, zero mismatches**, all
  **12/12** historical compiled mutants detected. Six families each have 1,000 cases, including tick
  and render. No reconstructed charsel source or prior validator comparison is changed.

- Unchanged existing audio comparison at `--random 2000`: **13,967/13,967 equal** and **232/232**
  world perturbations detected. Existing shell suite: **23 tests, one explicit private skip**, no failures.
- Installed manifest-bearing APP-REFRESH-001 table smoke: the real installed sound 25 decodes and the
  scene-5 Enter request plays once. The older owner Native Data folder correctly refused its absent
  manifest; it was left unchanged. No new table extraction or private-data copy is needed.

The portable audio collection also passes: **49 tests, six explicit instruction/private skips**.
The existing golden PCM test passes unchanged at SHA-256
`207036b711a07277a68466d736760c9440bab5d325ede5f90ddc298f18232897`.

## Final integration

Pending the fair merge queue and serialized latest-main/full-Mac-gate sequence. This section will record
its actual results before merge. Standards/spec self-review covers callback and table lifetime,
provenance, silent delivery, visual preservation and owned-path scope; no independent review is claimed.

## Limits and cleanup

Credits/CButton and other unmapped owning controllers remain open. Existing dynamic buff/event inputs,
remote magic results, pickup-success routes, original RNG phase, music 43/44, the virtualised
`0x01854279..0x018542c2` gap and LIVE-PLAY FMOD/native parity remain open. No whole-client sound parity
or original-image fidelity score is claimed.

Scratch/reports and a handful of temporary renders are scoped to
`~/Documents/MTM/mu-mac-tools/native/scratch/audio-002e/`. After merge, remove that directory, any lane
render directory, build outputs, worktree and local branch. No new private input is retained.
