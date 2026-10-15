# Contributing

Read [AGENTS.md](AGENTS.md) for the current mission and [the roadmap](docs/roadmap.md) for bounded work. Contributions can improve code recovery, validated formats, test coverage, reproducibility, or documentation.

## Before changing code

1. Choose or open a focused issue with an observable question or behavior.
2. State its input identity, expected output, relevant evidence and completion check.
3. Claim the issue and use a branch or worktree. Independent agents should own separate modules or output paths; dependent work waits for a shared interface.

## Deliver a reviewable change

A PR should explain the concrete result, method, tests actually run, and remaining uncertainty. For reverse engineering, include original addresses/offsets and digests in a reviewed summary. Describe reused source and retain its license. Synthetic fixtures should exercise bounds, reference validity, malformed input, and meaningful expected behavior.

Run the portable checks in [setup](docs/setup.md). Run private integration when the changed behavior needs original files, and state the tested build. Passing synthetic tests alone does not establish game compatibility. Keep raw private inputs and generated exports out of commits, issues and workflow artifacts.

Update the module's findings and current handoff whenever a result changes the next recovery step. Attach a short task-specific continuation note, not a full conversation transcript.

## Completion language

Use "implemented", "structurally validated", "compared with the reference", or "observed at runtime" only for the corresponding evidence. A code export is not a playable client. Native macOS play is a later milestone with its own behavioral and packaging checks.
