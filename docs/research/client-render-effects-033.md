# Learned-skill presentation, RENDER-EFFECTS-033

Offline authored fixtures only. Baseline combines EFFECTS-032 b8ef0051 with
main 6900914e, including EFFECTS-031. No actor, app, UI or power work.
Target/text/data identities use scripts/pins.py and the EFFECTS-032 captures.

## Initial classification

The inherited 29-row table is 11 P / 7 L / 11 M. All eighteen L/M rows
are listed below before implementation. P means bounded primary presentation,
L means visible subset, M means missing primary presentation. These labels
never grant eligibility or claim authoritative input.

| Skill | Before | Exact missing part |
|---|---|---|
| 344 Blood Storm | M | Effect 0x583/0 emitter and 0x584/0 body; emitter also requests 0x585/0 and 0x586/0; body requests particle 0x8145/1. Full lifecycle, owner +0x3b and draw dispatch unproved |
| 52 Penetration | L | Effect 0x46c/0 follows the arrow owner action/live/position; charge is now supported by 031 |
| 51 Ice Arrow | L | Optional target-side ice presentation input/caller; primary arrow already supported |
| 18 Defense | L | Original held-input lifetime and shield body context; current finite pose is supported |
| 48 Swell Life | M inherited | Requests recovered by 030, consumers now supplied by 031; reassess combined fixture; persistent presence remains separate |
| 44 Crescent Moon Slash | L | Final effect 0x49e/0 create/move/draw consumer |
| 49 Fire Breath | M | Effect 0x8001/0 consumer; mount body/lifetime unavailable in current fixture |
| 30 Summon Goblin | M | Shared ground effect 0x7f84/3; summon actor selector/body and lifetime |
| 31 Summon Stone Golem | M | Same shared ground request; actor selector/body and lifetime |
| 32 Summon Assassin | M | Same shared ground request; actor selector/body and lifetime |
| 33 Summon Elite Yeti | M | Same shared ground request; actor selector/body and lifetime |
| 34 Summon Dark Knight | M | Same shared ground request; actor selector/body and lifetime |
| 35 Summon Bali | M | Same shared ground request; actor selector/body and lifetime |
| 36 Summon Soldier | M | Same shared ground request; actor selector/body and lifetime |
| 43 Death Stab | L | General equipment/link selector, outside current base-DK bone-33 proof |
| 27 Greater Defense | L | General equipment links and authored presence lifecycle beyond bounded aura fixture |
| 28 Greater Damage | L | Same shared link/presence boundary |
| 47 stale entry | M | Absent record, always refused; capacity entries past learned count excluded |

Uniform groups: seven summon rows share one ground consumer and actor contract;
two aura rows share link/presence services; the other nine rows each have the
specific gap above. All ordinary request forms are already recovered by 030/032.
There is no request-only M group left on this combined base. No alias is admitted
by sharing a consumer.

Frozen Native Data lacks exact names DarkLordSkill.bmd, Flame01.OZJ and water.OZJ.
No refresh is permitted. Rows requiring these assets stay refused with frozen
input even if separate full read-only game data can demonstrate a component.
Effect 0x47a is reserved for MUUN-VISUAL-005 and is not changed here.
