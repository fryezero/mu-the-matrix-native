# NATIVE-QUEST-002 progress (WIP, branch claude/native-quest2; not for main)

## Done (committed on this branch)
- libquest (reconstructed/quest): guide quest tab 0 (quest_guide.c: GuideQuest/GuideQuestString data, routines
  0x00d49610..0x00d4bed6, packets F6 0x50/0x51, give-up/box, Go Now, requests F6 51..57), QuestSummary HUD +
  QuestProgressInfo (quest_summary.c), quest-tab Go Now 0x00d5029b (quest_move.c; same-map path walk, F6 7A =
  cross-map hook), the client's text wrap 0x011ff794/0x01193941 (quest_wrap.c; also used for npcdialogue's quest
  list when the host gives a font measure), class-upgrade quests (quest_classic.c: Quest.bmd loader 0x009f4866,
  manager state machine 0x009f4244/436e/43f0/4654/4fc8, packets C1 C0/A1/A4/86, F6 1C, NpcJobChangeQuest window,
  MyQuestInfo tab 1), guide callbacks in mu_quest_info_callback (static reading).
- langread: deep:/ptr: options; live read 2026-10-22 -> ~/Documents/mu-mac-tools/native/scratch/quest2/live/lang5.bin
  (local). live_lang_to_plain.py writes guidequest.tsv, guidestrings.tsv, dialoganswers.tsv (local plaintext in
  ~/Documents/mu-mac-tools/native/scratch/quest2/lang).
- scripts/validate_quest2.py (Unicorn). Latest counts, 0 mismatches unless noted: guide-data 383, guide 852 (one
  later run: 834 with 1 mismatch, not yet looked at: /tmp/full1.json), summary 894, move 90, wrap 600, dialog-wrap
  500, classic-data 400 (client loader + live records vs native), classic 1346 (+ C1 86 op: re-run). QUEST-001
  validator still 0 mismatches on lang5.bin.
- native: mu_quest session demo server (guide/classic lines, rewards, F6 54/7A travel hook via s->travel),
  mu_walk_auto_move_ex, GFx layer movie ids QuestSummary/QuestProgressInfo/NpcJobChangeQuest; native builds.
- NPC 257 (Shadow Phantom Soldier) model found: generic CreateMonster case 0x01384539 = Player model 0xa91 with
  armour set 24 +13 (slots helm..boots 7..11:24, item types 0x18fe..0x20fe level 13), wings 12:3 (0x22e9),
  scale 1.0, joint 0x7f78 x5; class extraction fails only on CreateJoint 0x0153b02c (stub it in
  scripts/validate_actors.py class_case). Not yet wired into mu-world (needs a player-model NPC path, e.g. the
  players demo with those slots).

## Left / next steps
1. Look at the guide mismatch in /tmp/full1.json (re-run: `. ~/Documents/mu-mac-tools/native/scratch/quest2/env.sh;
   $P scripts/validate_quest2.py --snapshot $SNAP`), re-run classic with the r86 op; add --mutations (planted
   MU_QUEST_MUTATION points in the new files).
2. world_gfx glue (not done): quest_movie for the 3 new movies, "call W openWindow/closeWindow" -> show/hide,
   quest_call routing (mu_summary_callback, mu_classic_callback/onload, mu_quest_progress_info_onload), NJCQ keys,
   host callbacks (measure via mu_ui_font, path_reset/path_start/send_move via mu_walk_auto_move_ex,
   item_record_name, item_level_name, money_text), session load_classic(game root), classic NPC talk -> C1 A1.
   NATIVE-MAP-001's travel API is merged (#138): set session->travel to call mu_map_travel_to(world, x, y).
3. Demo lines in native/world/lorencia-demo-npc.txt (guide 11, classic 0:3), tests (test_quest.py synthetic guide/
   classic/wrap; native/tests/test_native_quest.py), renders under ~/Documents/mu-mac-tools/native/renders/quest2/.
4. NPC 257: validate_actors class_case joint stub, regenerate class table (+ wing slot), render it.
5. Docs (client-quests.md section, status/roadmap/handoff), rebase, local CI, PR, merge, rebuild preview app
   (copy guidequest.tsv/guidestrings.tsv/dialoganswers.tsv into its Native Data).
