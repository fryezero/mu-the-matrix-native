# NATIVE-HELPERS-002 progress (stopped on owner request, 2026-10-22)

Branch `claude/native-helpers2` (pushed, no PR). Local CI (`bash scripts/local-macos-ci.sh`) passed on commit
before this file (merged raven + pets included). Not rebased on origin/main yet.

## Done and verified (Unicorn, reports under evidence/native-helpers2, evidence/native-pets, evidence/native-raven)
- Particle kinds Spark02/1, smoke02 0x7f5b/0, drop01 0x7fcd/0, Spark03 0x7f26/0xf: validate_particles --cases 3000
  --heavy-cases 300 all equal (create/move/render 3000 each), 3 new negatives detected.
- Mount registry functors (24 models, reconstructed/helpers/mount_render.c): validate_mount_visuals --cases 300:
  7,200 cases / 66,129 calls, 0 mismatches; registry pairs match; negatives 40/40/30.
- Later classes' object subtype from state (mount_class section, 53 entries) + full validate_helpers
  --bug-cases 1000 --cases 1000 --negative 60 --mutations: 0 mismatches, 6/6 mutations.
- Shining Tail class visuals 0x01057fb0 + claw steps 0x0105a0bb (mount_class.c): 300 + 300 cases, 0 mismatches.
- Pets (merged claude/native-pets): 62 loader + 1,000 sessions/28,280 steps, 0 mismatches, 3 neg, 6 mutations.
- Dark Raven (merged claude/native-raven): 1,000 sessions/39,093 steps + 3,000 functor cases, 0 mismatches.
- Native: functor passes, extra textures, second shadows, Shining Tail decals/glints, pets, raven; app picker lists
  later mounts, pets, ravens. Docs: docs/research/client-helper-visuals.md, client-pets.md, client-dark-spirit.md.
- Live (game lock, released): Shining Tail +10 ridden by Nighty at Lorencia 138,135 (dismounted again, game closed);
  pandas of other players. Captures local in ~/Documents/mu-mac-tools/native/renders/helpers2/live/.
  Dark Horse white glow = client's breath smoke01 at Bone03 (static + rate check; no Dark Lord on the account).

## Left
1. Merge branch `claude/native-helpers2-fx` (pushed; commit 2780430 joint 0x7f78 verified by its author,
   ca62c4b = WIP effect 0x8012 / Fenrir 0x4ac/0x4ad, unverified) — run validate_joints / validate_skill_fx first.
2. Short edits: docs/status.md paragraph, docs/roadmap.md row (NATIVE-HELPERS-002), docs/handoff.md section.
3. git fetch && git rebase origin/main (union-resolve shared docs/Makefiles), bash scripts/local-macos-ci.sh,
   push, PR, merge; rebuild ~/Applications/Mu The Matrix Native Preview.app (make -C native preview-app;
   make -C native/app install).
4. Gaps: other later mounts' class visuals/moves; particle kinds 0x831d/0x83b3/0x8086/... and effects
   0x6f3/0x6f6/0x8438, eye joint 0x7fd6 0x43/0x44 counted not drawn; Muun pets only surveyed.

Local-only: ~/Documents/mu-mac-tools/native/scratch/helpers2 (tools, ghidra copy, muinput-h2.exe also copied
into the MuMatrix32 bottle C:\mutools), renders under ~/Documents/mu-mac-tools/native/renders/helpers2/.
