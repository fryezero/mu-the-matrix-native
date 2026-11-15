# Remaining learned-skill callers, RENDER-EFFECTS-032

Verified fixture subset. This lane owns combat callers and requests. EFFECTS-031 owns
charge/child, target-ice, Swell Life and Blood Storm consumers. No consumer file
is changed here. The base is main `b7dfd2ed`.

## Evidence and method

Pinned target main.exe SHA-256 is
`3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`.
Text/data identities come from `scripts/pins.py`, with the same captures as
[EFFECTS-030](client-render-effects-030.md). The new validator records body
SHA-256s. Static switch destinations are read from the pinned text. Visual
fragments execute under the existing strict Unicorn machine using authored
CHARACTER/OBJECT records. Receive parsers and network services never execute.

The comparison retains all ordered effect/joint/particle arguments, owner,
key, skill and default words, scale, sound site, AttackTime writes, cutoff and
CRT draw order. Native consumer support and original caller equality are
separate checks. No stopped original case is accepted as a caught mutant.

## Caller inventory

| Skill | Original presentation slices | Recovered request or pose |
|---|---|---|
| 30..36 summons | Start `0x0125594d`, area selector `0x013a90c0`, end `0x013a9449` | Start sound 0x6f at 0x01255962, null owner; generic Elf magic pose; one caster-owned 0x7f84/3 effect, key/default word8 -1, other words and scale zero |
| 18 Defense | Action fragment `0x01222f89..0x01222fb0` | SkillAction(character,18,0xd7,-1), sound 0x6f at 0x01222fa3 with null owner; default step cutoff and end, no effect request |
| 49 Fire Breath | Pose helper `0x0106c453`, step `0x0139a6f8`, end `0x013aba0c` | Mount pose 0xf9; Player + action 0xf9 + frame >=5 sets AttackTime 15; 0x8001/0 owned by caster, OBJECT key +0x54 and authored global word 0x06fca278, word8 -1; sound 0x72 at 0x013aba74, null owner |
| 44 Crescent Moon Slash | Pose `0x01256cf6`, step `0x0139a76f`, end `0x013ad798` | Pose 0x98, start sound 0x71; frame >5 sets AttackTime 15; four ordered joint/particle pairs every active step; final 0x49e/0 plus sound 0x2ad |
| 24 / 51 / 424 | Bow pose `0x013946ee` | Kind 1/2 selects 0x7e/0x7f, wing word != -1 adds two |
| 52 / 416 | Penetration pose `0x013947d8` | Kind 1/2 selects 0x93/0x94, wing word != -1 adds two |

Defense does not use the magic receive branch at 0x0125726a. That branch is
skill 63. The action fragment names skill 18 directly. Its action is 0xd7,
not an inferred neighboring melee pose. The fragment does not start AttackTime;
the bounded native fixture schedules a finite pose with its existing timeline.

Summons' seven learned IDs all select the same end body. Actor construction,
which would give the summon its primary body and lifetime, belongs to the actor
lane. The ground subtype 3 is also absent from the native effect consumer.
The default step ends AttackTime at frame >=5 for Player actions 0x6f..0x132.
The exceptional hero item 0x815 is outside authored admission: native admission
refuses configured weapon 0x12fb for Defense and the seven summons, whose
default step would otherwise emit the separate special-item spark burst.
A neighboring ordinary-item positive control remains admitted. One refused
ground request is counted per cast. No summoned actor is fabricated.

Crescent Moon Slash draws six CRT words per step. The first two jitter x/y by
rand%30 - 15, then z increases by 20. Each of four pairs draws one rand%60 +150
pitch, zero yaw and caster heading. The null-owned joint is 0x7fd5/0, width 10,
key -1, skill 0 and original remaining defaults. The null-owned particle is
0x7f3c/2 at scale 1.5. The ordinary Player context initializes the white MoveCharacter local at
0x013a8847..0x013a887a, static evidence. End 0x49e/0 uses that local rather
than OBJECT Light, caster owner and default key/word8 -1. Its consumer is absent.

## Authored admission and limits

`MU_SKILL32_CONTEXT=bow_kind,wing,shield,mount` supplies decimal appearance-service
answers, for example `1,0,0,0` or `0,-1,1,0`. Default is the configured weapon's
kind, wing -1, shield/mount false. Invalid strings leave the default. A wing
value of zero is present, as in the original comparison with -1. This does not
equip a wing, shield or mount model. No equipment eligibility rule is claimed.

New requests require the exact class family and an active learned-list match
within min(count,150). Shield and mount rows also require their authored context.
Skill 47 and unseen aliases remain refused. The global skill word for Fire
Breath is explicitly authored as 49 in native fixture runs, not acquired state.
No power, mana, damage, cooldown or target-side state is synthesized.

General Death Stab weapon-link selection, Greater Defense/Damage equipment links
and presence feeds remain open. These L rows need original owner/link services;
no guessed bone or unrestricted owner admission is added. Swell Life and Blood
Storm remain entirely with EFFECTS-031. Target ice is also that lane's work.

## Learned inventory after this lane

The original caller/mutant proof, native tests and fixture renders pass.
The 29 rows are the same denominator
as EFFECTS-030, 28 learned entries plus ordinary attack. P means a bounded primary
visual, L a visible subset with a named missing context, and M missing primary
visuals. Request recovery alone does not promote an M row.

| Skill | Before -> after | Remaining boundary |
|---|---|---|
| 18 Defense | M -> L | Recovered pose/sound in a finite authored schedule; original held-input lifetime and shield equipment rendering are not established |
| 44 Crescent Moon Slash | M -> L | Step sparks/ribbons; 0x49e/0 end consumer refused |
| 49 Fire Breath | M -> M | Recovered mount pose/cutoff/request; primary 0x8001/0 consumer refused; mount body/lifetime not supplied |
| 30 Summon Goblin | M -> M | One ground request refused, actor construction/lifetime absent |
| 31 Summon Stone Golem | M -> M | Same explicit boundaries |
| 32 Summon Assassin | M -> M | Same explicit boundaries |
| 33 Summon Elite Yeti | M -> M | Same explicit boundaries |
| 34 Summon Dark Knight | M -> M | Same explicit boundaries |
| 35 Summon Bali | M -> M | Same explicit boundaries |
| 36 Summon Soldier | M -> M | Same explicit boundaries |
| 24 Triple Shot | P -> P | Wing/kind action context now explicit; original two requests retained |
| 51 / 52 | L -> L | Broader wing/kind action context; target/consumer boundaries belong to EFFECTS-031 |
| 43 Death Stab | L -> L | General equipment link selection still absent |
| 27 / 28 | L -> L | General links and presence input still absent |
| 47 | M -> M | Stale, no admission |
| 48 / 344 | M -> M here | Consumer-only rows skipped, owned by EFFECTS-031 |
| 0,19,20,21,22,23,26,41,42,2044 | P -> P each | Unchanged bounded primary presentation |

This lane alone moves 11 P / 5 L / 13 M to 11 P / 7 L / 11 M. Individual
synthetic 416/424 aliases remain L, outside the 29-row denominator. Unlearned
catalogue and other aliases retain the complete separate inventory in 030;
none are admitted by their icon, class nibble or shared consumer.

## Completed focused comparison

At compiled caller inputs `8965554f`, the final proof passes 4,433 checks,
zero mismatches, with 31/31 compiled production-C mutants caught and zero
original-machine stops, 71.71 s command wall. It includes 1,000 step, 1,000 end,
900 start, 117 original pose and 200 interleaving cases, plus 810 authored
admission controls, 276 active-count/cap controls and 130 exact-selector controls.
Thus 3,217 checks execute original instructions; 1,216 are native policy controls.
The combat dylib SHA-256 is
`62936052baf3718000d820c5060f981e2d6def34b127932f6b55e5348e57fbb7`.
AUDIO-004 main integration changes no compiled inputs of this caller comparator.

The interleaving family gives each joint/particle service a varying declared
number of CRT draws. Original and C share the same independently maintained
input sequence. It compares the resulting ordered requests and total RNG use.
The production streaming adapter emits each pair before drawing the next pitch.
It reuses the compared scalar planner for that pair, without duplicating its
jitter/angle arithmetic. The legacy particle constructor borrows the combat
CRT state and returns its resulting state; the world pool's separate native
movement stream is restored. This fixes constructor/caller order without
claiming a whole-client shared RNG phase, pool allocation phase or time alignment.

An initial 4,233-check/28-mutant proof covered caller stubs without consumer RNG.
Self-review found the integration gap after that run. The final proof above
supersedes it and adds three streaming mutants. The repeat mutant run is due
to this changed production path and new check, not a rerun of unchanged consumers.
The first small comparison also exposed the default frame cutoff and a missing
synthetic hero-item region in the harness. No stopped exploratory case counts
as evidence or a caught mutant. Deterministic edges cover frame 1/5, both sides
of each action/model range and NaN.

The first native run passes six initial fixture tests, 7.77 s. The final private
run additionally includes malformed-context admission and the original stream
family. Portable skips are not private evidence.

## Installed-data fixture proof

Twelve scenes, before/after/repeat, pass in 63.47 s. Each uses one cast at frame
2, stop at frame 3, Lorencia tile 182,127, a DemoTarget placement at 184,127,
960x600 GL, 60 logic frames, save every 12 and draw every logic frame. Names
are DemoKnight/DemoArcher. Items, other players and audio output are disabled.
All 72 after/repeat PNG pairs are byte-identical. No cast sends a request,
hits/kills stay zero and target HP remains constant. Models/bitmaps stay 29/39.
An initial local invocation used the native-data directory as a game-root and
failed before producing an image. The successful run uses canonical private-env
with MU_GAME_ROOT, leaving MU_NATIVE_DATA_DIR as the separate read-only input.

| Scene | Visual requests | Refused | Native result |
|---|---:|---:|---|
| Each of 30,31,32,33,34,35,36 | 1 | 1 | Caster magic pose and start sound, no summon body or ground effect |
| 18, shield context | 0 | 0 | Recovered defense pose and sound |
| 44 | 89 | 1 | Eleven steps of four spark joints plus four particles, then refused 0x49e/0; two sounds |
| 49, mount context | 1 | 1 | Recovered mount action/cutoff and end sound, no fire body |
| 51, wing/kind context | One arrow caller | 0 | Existing Ice Arrow projectile |
| 52, wing/kind context | Charge plus one arrow caller | 2 | Existing Penetration arrow; charge and child still refused |

Early-flight wing-context scenes for 51 and 52 use target 187,127 and frames
0..11, saved at 0/3/6/9/11. All ten after/repeat PNG pairs match, 9.39 s.
Four Ice Arrow captures and two Penetration captures change from the unwinged
baseline. Visual inspection confirms the floating bow pose and frame-6
projectile. The longer Penetration sample captures its idle pose after the
projectile has retired and therefore has no changed saved PNG; the early scene
covers the omitted interval. Crescent's frame-12 sparks and Defense's frame-12
pose were also inspected. This is native repeatability and caller/consumer
proof, not original GPU-image equivalence.


## Final replay and default identity

Post-RNG-correction after/repeat refresh passes all 82 PNG pairs in 59.08 s.
The baseline is not rerun. Request/refusal totals above remain unchanged; active
Crescent scatter changes as intended. The final frame-12 Crescent proof is
visually inspected again after the correction.

Both world versions are explicitly rebuilt. Baseline main b7dfd2ed has SHA-256
`e341fc2000d2e7f035f1e1814ca5384231389c8e7409ed20557643b0485108d7`.
The final binary is
`bb5470bf11a199bc3d6a241da9206d2548e39ed28ef874dfcb779b99fa45368c`.
The final script rebuilds before its sweep and checks the hash again afterward.
Across 14 October and 32 DATA-ACQ-002 default views, all 92 PNGs, 92 OBJECT/light
dumps and 46 reports match. Only output-directory prefixes are normalized in
JSON. No default view changes because the new callers are inactive. Incoming
AUDIO-004 likewise preserves these defaults. Before 74.61 s; after 69.74 s.
No whole-client GPU or performance equivalence follows.

Final reduced private checks pass 15/15, zero skips, 25.75 s. The native-only
selection is 174 work items, requiring 8d reduced under the 40-item cap.
Portable affected execution passes 1,803 tests, 1,490 passed / 313 expected
skips, zero failures/errors, 500.74 s command wall and 412.7 s runner wall.
It runs 170 affected items with two workers. The only excluded module is
native/tests/test_native_app.py, whose packaging is explicitly forbidden by
this session's owner brief. No committed test or expectation is changed to
make that exclusion; a local driver filters its runner work item. No app bundle
or installed-app journey is produced. The handoff records validator/audit timing
and the final publication state.
