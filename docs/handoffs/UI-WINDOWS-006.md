# UI-WINDOWS-006

## WIP (checkpoint 1, 2026-11-15 16:25)

Base main `c5b9d5ca` (PR #400 merged). Branch `claude/ui-windows-006`,
worktree `~/Documents/MTM/worktrees/ui-windows-006`. Text/data pins unchanged.

### Done

- Trigger roots of all 33 "route proved, provider missing" rows and of the 30
  state-dependent rows, by bounded direct-call caller chains from every open
  site up to the server-response dispatcher `0x01287ead`, a controller vtable
  entry or the frame loop (lane-local prototype, not yet committed as a script).
- Groups of the 33 rows by missing piece (sizes; ledger not yet committed):
  - 17 server-response trigger with no offline owner (authoritative):
    ArkaResultInfo, CursedTempleResult, CursedTempleScore, Duel,
    EventMapRoundCount, GoldArcher, GuildCreateFrame, ImageNotice, IngameShop,
    ListofMatches, ProgressFrame, RebuyList, RewardItemExchange,
    StrongestMatchRank, StrongestMatchResult, SwitchMode, TimeCounter.
  - 1 server-response trigger whose three handlers already have offline owners
    (static): MapName. Join `0x0124cc64`, respawn `0x0127bd9e`, numbered
    teleport `0x0128136d`. Open method `0x00baee4a` is self-contained: no-op in
    world 0x28, InitText, SetMapName(map-name function `0x016baaa6`), 5000 ms
    lifetime (update `0x00baf120`, constant at `0x01a90948`), then close.
    Strife flag and occupying guild are server-mode/authoritative: left empty.
  - 8 clicked or hovered item/slot record of one kind (authoritative item
    records): ArtifactInfoPopup, PetInfoPopup, DivideWindow, MonsterSoulReward,
    Pentagram, SlottedWingInfo, SkillTree5thLevelUpPopup,
    SkillTree5thSlotClickPopup.
  - 2 unbound parent window: GuildPosition (GuildInfoFrame), MiniGameHelpWindow
    (MiniGameRummy).
  - 3 world/HUD state: BossHpUI (boss target owner), QuickCommand (Alt + right
    button on a selected other player), DeathPenaltyExpRecovery (alarm entry).
  - 1 pending transaction step: PersonalShopCaution (register window OnClickOk).
  - 1 upstream caller unresolved: NpcGateKeeper (legacy open id 0x18 is pushed
    by none of the 23 direct callers of `0x00f2abcd`).
- Third sweep idea (not tried by 004/005): parameterised open methods. A window
  vtable method other than +0x40/+0x44 that opens its own window through
  `this`, then manager-qualified virtual calls through that vtable offset.
  `scripts/survey_ui_indirect.py` gained an optional `extra` argument (default
  behaviour unchanged: 482 sites). With +0x4c for slots 0x124, 0x17c and the
  already-bound control 0x10c it finds 490 sites: EventMapHelper open at
  `0x00b04ba3`, `0x00be5405`, `0x00be5453` (NpcDialogue callbacks
  onClickbtnEnterTime / onClickbtnEnterLevel) and MiniGameRummy open at
  `0x0126f12c`, `0x0126f203` (server response). The control finds the known
  NpcQuestProgress openers.

### Left

- Commit the self-open detection and the trigger-root classifier as scripts
  with synthetic tests; publish the 33-row ledger, the 30 one-line state needs,
  the updated survey and the 42 (then 40) no-route list.
- Admit MapName: layer controller (open contract, 5 s lifetime), arrival hooks
  at the three existing offline owners (added lines only), instruction-checked
  comparison of the open method and of the teleport tail, compiled mutants,
  native journey with captures.
- Checks per TEST BUDGET, identity sweep, handoff, status lines, PR.

### Next step

Add `self_open_slots()` to `scripts/survey_ui_indirect.py`, then
`scripts/survey_ui_triggers.py`, then the MapName controller in a new
`native/gfx/mu_gfx_windows6.inc`.
