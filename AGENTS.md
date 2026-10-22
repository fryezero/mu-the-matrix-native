# Agent entry point

## Mission and current boundary

Reconstruct and understand the exact Mu The Matrix client identified in `docs/evidence-index.json`. Native macOS gameplay is the later destination. First recover code and validate behavior; a viewer, a different MU version, or a partial decompilation does not satisfy the game-rebuild goal.

Start by reading `docs/status.md` and `docs/handoff.md`. Choose the next bounded task from `docs/roadmap.md` and check existing GitHub issues/branches for an owner before editing. Use a separate branch or worktree for independent agent work. Record the claimed scope, files and dependencies in the issue or PR so other agents can avoid collisions.

The owner authorizes merging reviewed changes into `main` once their relevant checks pass. Use PRs to retain the evidence and review record; no additional merge confirmation is needed.

## Read when needed

- Build, CI, missing local inputs, or integration tests: `docs/setup.md`.
- Native/loader recovery, emulation, or Windows startup: `docs/code-recovery.md` and `windows-capture/README.md`.
- Restored client functions, copy semantics, or instruction comparison: `docs/research/client-copy64.md` and `reconstructed/client-memory/README.md`.
- Record arithmetic, x87 precision, cofactors or inverse aliasing: `docs/research/record-math.md` and `reconstructed/record-math/README.md`.
- Image or effect formats: `docs/asset-recovery.md`.
- BMD geometry or encryption: `docs/model-recovery.md` and `model-recovery/SOURCES.md`.
- New module/platform boundaries: `docs/architecture.md`.
- Uploads, evidence, and licensing scope: `docs/evidence-policy.md` and `THIRD_PARTY_NOTICES.md`.

## Evidence and implementation rules

Preserve original files. Put acquired bytes, memory captures, derived payloads and generated assets in ignored local directories. Commit authored source, synthetic fixtures, reviewed summaries and provenance metadata. Before committing, inspect staged paths and run the repository audit described in `docs/setup.md`.

For each reverse-engineering conclusion, record target SHA-256, source address/file offset, method, observation versus inference, coverage and unresolved behavior. Preserve failed hypotheses with their failure cause. Keep generated pseudocode, readable byte patterns, structurally parsed records and runtime-equivalent behavior distinct.

This repository is the native track. Running the original client on macOS through Wine (the Mac app, the
player disk image, the Wine runtime, mugl, the CPU hotpatches, fast x87, the launcher fixes) lives in the separate
repository [fryezero/mu-the-matrix-mac](https://github.com/fryezero/mu-the-matrix-mac) (local checkout
`~/Documents/mu-the-matrix-mac`); put Wine-track work there. The original client is playable on the Mac through
that track, which is also how live client state is observed for comparisons (`live-readers/`, under the shared
game lock). For code capture, full x86 system emulation with Linux Wine (`runtime-linux/README.md`,
`docs/research/restored-client-text.md`) restored a repeatable client-code region. The Windows helper remains
prepared; actual native Windows validation is still open. Distinguish compatibility-environment captures from
native Windows evidence.

Run `make test` with the configured Python. Private integration is opt-in; missing original inputs must produce an explicit skip in portable tests or an error in requested integration checks. Keep synthetic regression fixtures independent of proprietary data. Every behavior claim needs a relevant test or a precise unverified limitation.

At handoff, update `docs/status.md`, the relevant finding document, and `docs/handoff.md` with changes, actual checks, artifact locations and the next concrete step. Keep the broader roadmap honest. A native game build is complete only after the acceptance gates in `docs/roadmap.md` pass.
