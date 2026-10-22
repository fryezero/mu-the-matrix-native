# NATIVE-SKILL-002 progress (WIP, stopped for usage; branch claude/native-skill2, rebased on main 8f659ed)

## Done (committed)
- Smoke on main with MU_GFX_LIB: mu-world bar / U window / tooltip / right-click cast work; mu-client world OK
  (first frame after loading is black: benign). Fixed a duplicated mu-world link line in native/Makefile.
- reconstructed/skill/skill_list.c: skill list A0 20 (0x0126176e), saved hotkeys A0 03 (0x0126f225 skill part),
  stamp manager (reset/add/remove/refresh/slots/save/cancel), hotkey manager, stamp marker 0x0109750c and
  damage-type icon 0x01097601.
- reconstructed/skill/skill_canuse.c: usability 0x010918c7 (all branches), world rules 0x00a9b235, SkillRequire.
- reconstructed/skill/master_tree.c: master tree (class switch, build, accessors, click + checks + confirm/request
  C1 08 01 16, A0 10 / A0 14 answers, SetText, positions, tooltip 0x00bb1183, icons 0x00bb0e2d, skill damage
  0x00a01692, hero upgrade 0x00bb25f3).
- Native: core/mu_skill takes the packets (mu_skill_book_receive), core/mu_skill_demo.c offline demo server
  (login list + saved bar, learn/forget, MU_SKILL_DEMO file), Skill Imprint window on the stamp manager
  (basic/special tabs, Save/Cancel), tests updated (native/tests/test_native_skill.py passes).
- langread `nested:0x6d8` + live_lang_to_plain writes skills_class.tsv; live read done (lang5.bin, 973 class maps).
- docs/research/client-skills.md section 8 (server packets) written.

## Verified (Unicorn, 0 mismatches, planted mutations all detected)
- scripts/validate_skill_server.py: list 300, keys 300, stamp 300 (also 500-case runs), canuse 400, world 50,
  marker 50; mutants 12-15, 19 detected.
- scripts/validate_skill_tree.py --cases 500: class 256, build 120, access 4000, click 500, answer 500, text 500,
  position 500, damage 500, tooltip 500 (after the __isa_available fix), icons 500 = 7,876; mutants 16-18 detected.
  Report: ~/Documents/main-exe-study/evidence/native-skill2/tree-500.{json,log} (tooltip rerun separately: 0).

## Left (next steps)
1. Wire usability (mu_skill_can_use) + mu_master_skill_damage into core/mu_skill (bar isUse, tooltip damage).
2. GFx layer: add MasterSkillTree/SkillTree4th/SkillTree5th movies (enum, FILES, WINDOW_ALIGN 0/0/3, SetScale 90
   for master), forward their callbacks via cfg.quest_call, key 'A', CharacterInfoFrame tree buttons, a window_draw
   hook; host native/world/world_gfx_tree.c (build at UIInit, demo A0 10 at login / A0 14 on request, icons,
   tooltip in SkillInfoPopup, click-twice confirm). Load masterskilltreedata/tooltip via mu_data. Demo class byte 0x81.
3. Skill Imprint window position: send SetWindowSize to SkillStampFrame (align 9) as the client does (0x00acb333);
   draw the stamp marker + damage-type icon in world_gfx_skill (SkillStamp.tga 0x7e26, DamageTypeIcon.tga 0x8313).
4. Docs: client-skills.md sections 9 (usability/damage/marker/position, R2 notes) and 10 (master tree, R1 notes);
   status/roadmap/handoff rows; native README; README in reconstructed/skill.
5. Rebase, scripts/local-macos-ci.sh, PR, merge; rebuild the preview app; copy skills_class.tsv into Native Data
   (already copied locally to Native Data/lang and scratch/lang).

## Local-only artifacts
- Research notes: ~/Documents/mu-mac-tools/native/scratch/skill2/{trees-notes.md,use-notes.md} (+ r1/, r2/, full.dis).
- Live: scratch/skill2/live/lang5.bin, renders/skill2/live/{world,master}.png; renders/skill2/smoke*.
