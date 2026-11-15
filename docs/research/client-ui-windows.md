# More original UI windows, UI-WINDOWS-001

## Evidence and scope

Base `d4af71dd`. Static source is the existing restored text pin
`2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`
and data pin `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
Names and registrations below are reviewed summaries of those pins and the existing
189-file movie survey, including 179 OZG entries, in [native-gfx](native-gfx.md). Converted private AS2
movies supply the callback and display-method contracts. No client bytes or
rows are published, no original/live client ran, and no Windows/live-image
comparison is claimed.

Five optional world views are added. They contain authored English labels and
empty fixtures. Command buttons are disabled; the controller also rejects forged
callbacks. Matching requests, Gremory claims and Muun item/sort/book/appearance
changes cannot reach session, item, social or command handlers. Four Gremory tabs
and all five empty Muun pages work locally. Existing compiled movie methods own
the tab selection, layout, drag and close presentation.

## UI-WINDOWS-002 follow-up

UI-WINDOWS-002 starts at UI-WINDOWS-001 `13721b04` and merges the steward's
main `710ac816`. It uses the same restored text/data SHA-256 pins stated
above, existing converted movies and static ActionScript inspection. No
original client, protected module, live memory or service was used.

Eight presentation adapters add seven distinct surveyed movies, plus a
second instance of already-bound StorageInven. The world registry has 44
entries, 43 distinct filenames. Of the historical 134 baseline-absent survey
rows, twelve now have bindings and 122 remain. These counts do not measure
whole-client completion. The original survey below remains the baseline
ledger; the following table supersedes its disposition for these rows.

| Movie | Static route / display evidence | Native fixture and lifecycle |
|---|---|---|
| MacroMain | Z `0x00efd3a4`, getter `0x0095f986`, manager `+0x144`, toggle `0x00aae767`; sound 25 at `0x00efd43a` | Authored base-DK empty options, three local tabs, close. No helper start, persistent config, skills or items |
| MacroSub | MacroMain `btnMenu` comparison `0x00ba7d89` -> `0x00ba6fcf`; class-dependent opener `0x00babb31`, `ShowWindow` at `0x00babb6a` | Potion and skill-condition child previews, same-type toggle, different-type replacement, close with parent. Base-DK has no party-support child |
| HuntRecord | End `0x00efc39a`, getter `0x0095f647`, manager `+0x1d0`; open `0x00b8a5e2`, full-to-mini `0x00b8a8cf`, close `0x00b8a8fc` | Original placed `scene`, `noTest` callback owner `0x00b8b583`, authored zero record, empty history, table/graph/total/per-second, full/mini/closed cycle |
| Expanded StorageInven | Second registration `0x00ac6193`, getter `0x00c08ba8`, manager `+0x104`; H `0x00efc715` requires open warehouse and original `+0xa5` eligibility; sound 25 `0x00efc772`; `SetExtend` reference `0x00c3e180` | Separate empty 120-cell movie instance, fixture eligibility, close and parent teardown. H never acquires a warehouse |
| MatchingParty | Registration/name `0x00ac6b27`; MatchingSelect callback owner `0x00bc04a5`, party comparison `0x00bc04f4`; search tab `0x00bb8fb1`, party-info tab `0x00bbf6df`, recruit tab `0x00bbfaf3` | Selector -> empty catalogue; local search/recruit/party-info tabs and close. Original catalogue requests are replaced by an empty presentation provider; no remote answer is claimed |
| MatchingGuild | Registration/name `0x00ac6aa2`; MatchingSelect guild comparison `0x00bc0700` | Selector -> empty legacy guild catalogue; local search/recruit tabs and close. Original request remains inert; no original response-driven eligibility is reconstructed |
| Guildmatching_2024 | Registration/name `0x00ac88c3`; G/menu 10 `0x00efcb7c` -> `0x00b0aed2`, manager `+0x2b0` | Empty catalogue and three local tabs, close. No search, recruitment, application or mail |
| PlayGuide | Registration/name `0x00ac548a`; Ctrl+T `0x00efc0da` and menu 22 `0x00c71576`, getter `0x00b3b39e`, manager `+0x2ac` -> `0x00aae767` | Original empty guide frame, title and close. Menu release uses sound 25 at `0x00c716f6`. External guide content/provider absent; this is frame presentation only |

Exact original world/class/window predicates remain outside these adapters.
The fixtures supply eligibility and original empty data. Original compiled
movies own tab visuals and their local animations. No lifecycle claim is a
claim about authoritative helper timing, hunt history or remote catalogues.

The callback allowlist is exclusive: saves/resets, helper activation, skill
selection, item/equipment moves, zen operations, storage expansion purchases,
search/refresh/page requests, recruitment, application, join/approval/cancel
and mail refuse before any session/NPC/item/social handler. Disabled controls
also reject forged callbacks. Local tabs, child navigation, close and movie
metadata are the only accepted operations. Unknown callbacks refuse.

Original menu dispatch sound 25 remains at `0x00c716f6`; H and Z use the two
separate direct call sites above. Native input suppresses held/repeated keys.
No guessed tab, child-navigation or close sound is added. The unowned GFx
query `0x00b49b97` and full GFx sound parity remain outside this lane.

### Help and the remaining survey

A new direct-call scan of the pinned restored text again finds exactly one
call to Help getter `0x00b6cba2`, at `0x00b6b744`. That caller reads auxiliary
EventMapHelper rows rather than opening Help. The menu table still has no
Help route: ID 3 is the sound epilogue and ID 8 opens SystemMenu. The main
movie has no Help menu entry. This does not rule out an indirect call or an
unexamined scene. No original Help key/menu route is proved; native Ctrl+H
keeps its explicit native-policy label and F1 gets no new binding.

AutomaticMacro remains left: Home is a helper activation branch, and an
independent presentation-open lifecycle is unproved. ExtensionBagFrame needs
its expansion/grid owner and an exact original child route. The fifth-tree
item viewer needs its card/item lifecycle, with power features excluded.
All other 119 remaining rows retain the per-row untraced-route and missing
provider reasons in the survey. No unused registration/name reference alone
is promoted into an invented key. PlayGuide is the additional proved empty
first-page route admitted here; no claim is made about original external
content or the other 122 first pages.

## Help route investigation

Help is already bound and is not a new missing movie. Registration `0x00ac678a`
stores its controller at manager `+0x120`; constructor `0x00b89588`, getter
`0x00b6cba2`. The sole direct getter call `0x00b6b744` obtains `+0x11090`
through `0x00b6cb91` for EventMapHelper row filtering. It does not open Help.
The menu jump table `0x00c7170d` sends ID 3 straight to the sound epilogue
`0x00c716f0`, and ID 8 to SystemMenu `0x00c7348a`. The recovered main movie
menu has no Help entry. F1 only has the previously documented legacy-close
paths. An indirect/other-scene original Help route remains unproved. Native
Ctrl+H is retained with its explicit native-policy label; no F1/menu route is
invented. Original platform selector preference remains unproved too.

## Routes, safety and sound

The key/menu addresses below are the static INPUT-001 joins, independently
compared at the original key-test blocks by `validate_input`. D is a direct
window toggle with world/state predicates, not menu ID 3. The offline shell
provides demo eligibility; exact original world/class/window predicates are
not reconstructed in this adapter. Missing movies or UIInit paths refuse.
Text focus/preedit/repeat suppression stays in the existing shared router.
Esc closes the most recently raised new view; original movie close callbacks
also close it.

Menu dispatcher `0x00c714bd` calls SND_Play(25, NULL, 0) at `0x00c716f6`
after dispatch. New B/N/Y/K/menu routes emit one immediate sound at that owner;
D, tabs/pages, close and refused actions add no guessed sound. AUDIO-002G's
legacy CButton site `0x0098689e` stays separate. The unowned GFx sound query
`0x00b49b97` is still not wired, per AUDIO-002G. This is no claim of full GFx
button sound parity. Detached/muted audio uses the existing engine policy;
there is no queued replay.

## Ranked missing-movie inventory

Rank is an implementation recommendation based on expected player frequency
and fixture cost, not measured usage. Tier 10 defers movies whose open route or usage frequency is unknown; it does not invent a frequency estimate. The first two need labels only; Pet and
Gens are common empty views; Gremory has simple local tabs. Name references are
string-push instruction addresses when present, otherwise immediate addresses. They are not proof of a complete open route. `Open route untraced`
means exactly that, and is a remaining research task. Data needs on untraced
rows are conservative domain inferences, not decoded server contracts.

There are 134 baseline-absent survey rows, five added here and 129 left. There are 21 separately accounted-for entries.

This lists every movie name in the existing private survey absent from the
baseline FILES set, after separating the already hosted front-end/HUD/library
entries below. It is a survey denominator, not a whole-client window count.
Expanded warehouse shares already bound `StorageInven.swf`: H at `0x00efc715`,
manager `+0x104`, requires the warehouse. It remains left because its additional
grid owner is absent; H must never open a remote warehouse.

| Movie | Rank / data cost | Registration / name reference | Original route evidence | Data need and result |
|---|---|---|---|---|
| `ArkaBattleNotice.swf` | 10 / unknown | 0xac6dbd | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `ArkaBattleProgress.swf` | 10 / unknown | 0xac6d3b | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `ArkaBattleRegister.swf` | 10 / unknown | 0xac6cb6 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `ArkaResultInfo.swf` | 10 / unknown | 0xac6680 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `ArtifactFrame.swf` | 10 / unknown | 0xac5ef3 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `ArtifactInfoPopup.swf` | 10 / unknown | 0xac52f8 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `AutomaticMacro.swf` | 9 / medium | 0xac9217 | Top-menu AutomaticMacroStart 0x00c8d2bc -> 0x00c8dc85, +0x25c | Empty preview; Home/execution refused; opens in 003 |
| `BattleCoreDialog.swf` | 10 / unknown | 0xac7789 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BattleCoreEnter.swf` | 10 / unknown | 0xac7705 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BattleField_BigDialog.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BattleFieldNotify.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BlockedChat.swf` | 9 / low | 0xac7d38 | Chat BlockedUser/F2; 0x00c5fd7d, +0x200 | Empty list; add/delete/input disabled; opens in 003 |
| `BombHunt.swf` | 10 / unknown | 0xac72ec | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BossHpUI.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `BoxOfBlessEvent.swf` | 10 / unknown | 0xac8371 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `CharacterFrame.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `CombinationFrame.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `CommandWindow.swf` | 1 / none | 0xac699b | D, 0x00efcee8, manager +0x134; menu 3 has no dispatch | Labels only; command intents refused; opens here |
| `CursedTempleEnter.swf` | 10 / unknown | 0xac89ca | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `CursedTempleinfo.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `CursedTempleMatchMenu.swf` | 10 / unknown | 0xac8ce8 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `CursedTempleResult.swf` | 10 / unknown | 0xac8d6d | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `CursedTempleScore.swf` | 10 / unknown | 0xac8df2 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `DamageCount.swf` | 10 / unknown | unlocated | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `DeathPenaltyExpRecovery.swf` | 10 / unknown | 0xac8948 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `DivideWindow.swf` | 10 / unknown | 0xac4f82 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `Duel.swf` | 10 / unknown | unlocated | Open route untraced | Social/list records and controller absent; left |
| `DuelWatch.swf` | 10 / unknown | unlocated | Open route untraced | Social/list records and controller absent; left |
| `ElementalMix.swf` | 10 / unknown | 0xac7dbd | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `EnchantEffectTool.swf` | 10 / unknown | 0xafd3d0 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `EnterBloodCastle.swf` | 10 / unknown | 0xac6894 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EnterEmpireGuardian.swf` | 10 / unknown | 0xac6916 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventInfo.swf` | 10 / unknown | 0xac8bde | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventInventoryFrame.swf` | 10 / high | 0xac623b | Getter 0x0095f623, +0x184; 0x00c74f02 is a visibility query | One 8x4 grid; independent open/provider absent; left |
| `EventMapEntranceUI.swf` | 10 / unknown | 0xac883e | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapHelper.swf` | 10 / unknown | 0xac680f | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapProgressInfo.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapRoundCount.swf` | 10 / unknown | 0xac8ef9 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapTutorial.swf` | 10 / unknown | 0xac75fe | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `ExchangeLuckCoin.swf` | 10 / unknown | 0xac931e | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `ExtensionBagFrame.swf` | 9 / medium | 0xac5e6e | Inventory Expanded callback 0x00b977d7; parent 0x00b91950/1d5, +0xa4 | Two empty 8x4 pages; no expansion authority; opens in 003 |
| `GensRanking.swf` | 4 / low | 0xac63ed | B/menu 11, 0x00efcbb6 -> 0x00aae767, +0xbc | Empty family/rank/contribution view; authority absent; opens here |
| `GoldArcher.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `GremoryCase.swf` | 5 / low | 0xac7ba9 | K/menu 15, 0x00efcc2a -> 0x00c73abc | Four empty tabs; claim/expiry records absent; opens here |
| `GuardianMix.swf` | 10 / unknown | 0xac7ec7 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `GuildCreateFrame.swf` | 10 / unknown | 0xac646f | Open route untraced | Social/list records and controller absent; left |
| `GuildInfoFrame.swf` | 10 / unknown | 0xac64f4 | Open route untraced | Social/list records and controller absent; left |
| `Guildmatching_2024.swf` | 6 / high | 0xac88c3 | G/menu 10, 0x00efcb7c -> 0x00b0aed2, +0x2b0 | Guild catalogue, search/application/answer owner absent; left |
| `GuildPosition.swf` | 10 / unknown | 0xac4ff5 | Open route untraced | Social/list records and controller absent; left |
| `HarmonyMix.swf` | 10 / unknown | 0xac7f4c | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `HuntRecord.swf` | 8 / medium | 0xac9003 | End, 0x00efc39a / 0x0095523a -> 0x00b8a5e2/8cf/8fc, +0x1d0 | Custom root lifecycle, timing and historical rows absent; left |
| `ImageNotice.swf` | 10 / unknown | 0xac7aa2 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `IME.swf` | optional / OS | 0xc4068a | 0x00c4068a names IME; input finding has no complete open route | OS owns composition; movie candidate contract absent; left |
| `IngameShop.swf` | deferred / high | 0xac8160 | X/menu 0, 0x00efc9e6 -> 0x00c73193 | Account catalogue and transaction authority excluded; left |
| `JewelBingo.swf` | 10 / unknown | 0xac81e5 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `KanturuEvent.swf` | 10 / unknown | 0xac9192 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `LabyrinthInfo.swf` | 10 / unknown | 0xac736e | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `LabyrinthMinimap.swf` | 10 / unknown | 0xac73f3 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `LabyrinthZoneName.swf` | 10 / unknown | 0xac8b59 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `ListofMatches.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `MacroMain.swf` | 7 / high | 0xac6bac | Z, 0x00efd3a4 -> 0x00aae767, +0x144 | Persistent helper configuration, skills/items and activation absent; left |
| `MacroSub.swf` | 7 / high | 0xac6c31 | MacroMain child; exact open callback untraced | Configuration owner absent; left |
| `MapName.swf` | 10 / unknown | 0xac8ad4 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `MatchingAlarm.swf` | 10 / unknown | unlocated | Open route untraced | Social/list records and controller absent; left |
| `MatchingGuild.swf` | 6 / high | 0xac6aa2 | MatchingSelect guild child; exact callback untraced | Remote guild catalogue/requests absent; left |
| `MatchingParty.swf` | 6 / high | 0xac6b27 | MatchingSelect party child; exact callback untraced | Remote party catalogue/requests absent; left |
| `MatchingSelect.swf` | 2 / none | 0xac6a1d | N/menu 12, 0x00efcbf0 -> 0x00c73aeb, +0x14c | Labels only; catalogue buttons refused; opens here |
| `MBoxShop.swf` | 10 / unknown | 0xac826a | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `MiniGameHelpWindow.swf` | 10 / unknown | 0xac93a0 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `MiniGameRummy.swf` | 10 / unknown | 0xac7267 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `MixAttributeScalp.swf` | 10 / unknown | 0xac50e7 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `MixSel.swf` | 10 / unknown | 0xac5065 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `MixStone.swf` | 10 / unknown | unlocated | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `MonsterCompensation.swf` | 10 / unknown | 0xac7683 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `MonsterInfo.swf` | 10 / unknown | unlocated | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `MonsterSoulReward.swf` | 10 / unknown | 0xac4f0f | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `MUMix.swf` | 10 / unknown | 0xac84fd | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `MuunExchange.swf` | 10 / unknown | 0xac6368 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `NpcGateKeeper.swf` | 10 / unknown | 0xac5c17 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `NumberBaseball.swf` | 10 / unknown | 0xafd40c | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `Option.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `OrdealSquareBattleCnt.swf` | 10 / unknown | 0xac799b | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `OrdealSquareBattleEnter.swf` | 10 / unknown | 0xac7916 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `OrdealSquareEnterMenu.swf` | 10 / unknown | 0xac7478 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `OrdealSquareResult.swf` | 10 / unknown | 0xac757c | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `OrdealSquareScore.swf` | 10 / unknown | 0xac74fa | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `PartyFrame.swf` | 10 / unknown | 0x95faa4 | Open route untraced | Social/list records and controller absent; left |
| `PartySkill.swf` | 10 / unknown | unlocated | Open route untraced | Social/list records and controller absent; left |
| `Pentagram.swf` | 10 / unknown | 0xac6579 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `PersonalShop.swf` | 10 / unknown | 0xac6fce | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `PersonalShopCaution.swf` | 10 / unknown | 0xac4e2f | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `PersonalShopProduct.swf` | 10 / unknown | unlocated | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `PetFrame.swf` | 10 / unknown | 0xaf0ebb | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `PetInfo.swf` | 10 / unknown | unlocated | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `PetInfoPopup.swf` | 10 / unknown | 0xac5273 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `PetInventoryFrame.swf` | 3 / low | 0xac62e3 | Y/menu 13, 0x00efc559 -> 0x00c739e3, +0x1a8 | Five empty pages; real Muun records/slots/appearance absent; opens here |
| `PlayGuide.swf` | deferred / medium | 0xac548a | Ctrl+T, 0x00efc0da; exact movie lifecycle untraced | Guide provider and controller absent; left |
| `PlayTimeEvent.swf` | 10 / unknown | 0xac83f3 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `PrivateStoreFrame.swf` | 10 / unknown | unlocated | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `ProgressFrame.swf` | 10 / unknown | 0xac8f7e | Open route untraced | Domain fixture/controller contract not recovered; left |
| `PurchaseInven.swf` | 10 / unknown | unlocated | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `QuestSummary.swf` | 10 / unknown | 0xafd42a | Open route untraced | Domain fixture/controller contract not recovered; left |
| `QuickCommand.swf` | 10 / unknown | 0xac569e | Open route untraced | Domain fixture/controller contract not recovered; left |
| `RebuyList.swf` | 10 / unknown | 0xac7c2e | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `ResistPopup.swf` | 10 / unknown | 0xac5619 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `RewardItemExchange.swf` | 10 / unknown | 0xac8478 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `RuudShopFrame.swf` | 10 / unknown | 0xac7cb3 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `SearchPrivateStore.swf` | 10 / unknown | unlocated | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `SeasonalEvent.swf` | 10 / unknown | 0xac82ef | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `SeasonPass.swf` | 10 / unknown | 0xac94aa | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `SelectMenu.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `ServerSelect.swf` | 10 / unknown | 0xac4b7d | Open route untraced | Domain fixture/controller contract not recovered; left |
| `SimpleUI.swf` | 10 / unknown | 0xac929c | Open route untraced | Domain fixture/controller contract not recovered; left |
| `SimpleUISubWin.swf` | 10 / unknown | 0xac4e9f | Open route untraced | Domain fixture/controller contract not recovered; left |
| `SkillTree5thInventory.swf` | 10 / high | 0xac862a | Getter 0x00b105ed, +0x29c; viewer 0x00b15541 iterates its item pages | Independent empty opener unproved; card/item owner absent; left |
| `SkillTree5thItemViewer.swf` | 9 / low | 0xac86af | Ctrl+J pair / Ctrl+I, 0x00efc104/1ad, +0x2a0 | One empty book/list page; no cards/power; opens in 003 |
| `SkillTree5thLevelUpPopup.swf` | 10 / unknown | 0xac8734 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `SkillTree5thSlotClickPopup.swf` | 10 / unknown | 0xac87b9 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `SlottedWingInfo.swf` | 10 / unknown | 0xac65fe | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `SnsWindow.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `SocketMix.swf` | 10 / unknown | 0xac7e42 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `SpeedserverPlus.swf` | 10 / unknown | 0xac8a4f | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `StrongestMatchMenu.swf` | 10 / unknown | 0xac6e42 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `StrongestMatchRank.swf` | 10 / unknown | 0xac6ec4 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `StrongestMatchResult.swf` | 10 / unknown | 0xac6f49 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `SwitchMode.swf` | 10 / unknown | 0xac4cd6 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `SystemMenu.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `TimeCounter.swf` | 10 / unknown | 0xac7b24 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `Trainer.swf` | 10 / unknown | unlocated | Open route untraced | Domain fixture/controller contract not recovered; left |
| `winEarringUpgrade.swf` | 10 / unknown | 0xc67d77 | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `winEventMuMobile.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `winLabyrinthReboot.swf` | 10 / unknown | 0xacd7f0 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `winLoginSceneBottomUI.swf` | 10 / unknown | 0xafd3f8 | Open route untraced | Domain fixture/controller contract not recovered; left |
| `winPet.swf` | 10 / unknown | 0xc8f575 | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |

## Entries outside the missing-world-view list

| Movie | Reason |
|---|---|
| `AlarmFrame.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `base.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `BuffList.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `Caution.swf` | Existing front-end host, outside the world FILES registry |
| `CharacterSelect.swf` | Existing front-end host, outside the world FILES registry |
| `ExternalBase.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `fonts_all.swf` | Font library, not a player window |
| `fonts_en.swf` | Font library, not a player window |
| `fonts_kr.swf` | Font library, not a player window |
| `fonts_kr_anti.swf` | Font library, not a player window |
| `fonts_kr_noanti.swf` | Font library, not a player window |
| `gfxfontlib.swf` | Font library, not a player window |
| `hudMap.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `hudNotice.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `hudPlayerName.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `Icons.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `ImageData.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `ItemDurability.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `Popups.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `Tooltip.swf` | Loaded HUD/data/library child, outside the FILES window denominator |
| `TopMenu.swf` | Loaded HUD/data/library child, outside the FILES window denominator |

## UI-WINDOWS-003: four more presentation routes

Base main `b7dfd2ed`. The restored text/data SHA-256 pins above are unchanged.
This section supersedes the earlier remaining-row disposition for four movies.
Registry: 44 entries / 43 filenames -> 48 / 47. Historical baseline-absent
survey: 12 -> 16 bound of 134; 122 -> 118 left. Help was already registered.
These are asset/route counts, not a client-completion percentage.

| Movie | Original route and owner | Admitted fixture |
|---|---|---|
| ExtensionBagFrame | Inventory comparison `0x00b977d7`, getter `0x00abeab8`, manager `+0xa4`, toggle `0x00b97829`; parent open `0x00b91950` / close `0x00b919d5` | Authored two-page eligibility and 64 empty cells; parent auto-open/teardown, Expanded toggle and close |
| SkillTree5thItemViewer | Registration `0x00ac86af`, manager `+0x2a0`, getter `0x0095f5ba`; Ctrl+J `0x00efc104` joins tree `+0x298` and viewer; Ctrl+I `0x00efc1ad` is independent | One empty book/list page. Equal paired visibility toggles both, unequal opens both. Both must be ready before changing either |
| BlockedChat | Registration `0x00ac7d38`, manager `+0x200`, getter `0x00bbfe04`; Chat BlockedUser `0x00c5fd7d` reads requested open state and toggles only if different | Empty list, disabled add/delete/input. Original chat button and movie's F2 listener, Close/Esc. Closing updates the chat button |
| AutomaticMacro | Registration `0x00ac9217`, manager `+0x25c`, getter `0x00bc07fa`; top-menu MacroMenu / AutomaticMacroStart `0x00c8d2bc` -> `0x00c8dc85` | Empty four-member preview, no hunting maps, all execution/configuration controls disabled. Original top-menu icon and local Close/Esc. Home stays refused |

Bag registration `0x00ac5e4a` initializes two 8x4 pages with alignment 0.
The movie has four authored pages; the fixture exposes the original registered
two only. Purchased/period expansion state and item actions are absent.

Viewer callback `0x00b17e3f` -> `0x00b1600c` inverts the reported boolean,
sets view-button text, sends SetViewTypeToggleButtonSelected, then rebuilds
the provider at `0x00b17210`. The adapter preserves this inversion with an
empty provider. It does not enumerate card definitions or formulas.

AutomaticMacro's opener calls virtual open/close before `0x00c8dce0`,
the inactive HUD/service boundary. Native presentation updates the inactive
HUD only; no helper service is implemented. Its local Exit calls
SetVisible(false), then inherited LeaveComplete. Native state synchronizes
after dispatch, when visibility readback is available. Current visibility
guards against a delayed notification closing a reopened view.

The exclusive allowlist intercepts the four movies and their parent events
before item, NPC, social or command owners. Saves, start/stop, matching,
hunting-map selection, character entry, block-list edits, item actions,
filters and level-up operations refuse, including forged callbacks.
Labels and expansion eligibility are authored English fixtures.

### Refusals and further leads

- Help's fresh direct-call scan still finds only `0x00b6b744` calling
  `0x00b6cba2`. It supplies EventMapHelper auxiliary rows, not an opener.
  Indirect/other-scene routes remain unproved. No original F1/menu binding
  was added; Ctrl+H keeps its existing native-policy label.
- Home `0x00efd1a7` remains helper activation. The separate top-menu
  configuration opener does not authorize execution, timing, saved options
  or matching. All such callbacks remain inert.
- SkillTree5thInventory is separate at `+0x29c`, getter `0x00b105ed`.
  Viewer construction `0x00b15541` iterates its item pages. An independent
  empty opener is unproved; its card/item owner remains absent.
- EventInventoryFrame is `+0x184`, getter `0x0095f623`, registered as one
  8x4 page at `0x00ac6217`. Caller `0x00c74f02` only tests visibility
  before another operation; it is not an opener. Event/item owner absent.
- Survey names SystemMenu and Option remain unlocated. Proven routes name
  winSystemMenu and winOption. No asset-alias equivalence is assumed.
- The other remaining rows retain their individual route/provider reasons.
  No live events, catalogue, transaction, guide content or stat formula was
  implemented to make an incomplete route appear complete.

Original comparisons execute 26 bounded route/controller decisions: bag
button and eligible parent lifecycle; fifth-tree paired/independent keys;
requested blocked-chat visibility; view-type inversion/invoke order; and
automatic-window toggle before its inactive boundary. These callers add no
direct sound call. Native hosts assert zero guessed sound deliveries. Exact
class/world predicates, nested unowned GFx sound queries and whole-client
sound parity remain unproved.

The production hosts check 132 forged callbacks per synthetic/real host;
all eight distinct compiled controller mutants are caught. Final proof,
validator rows, timings and limits are in [UI-WINDOWS-003](../handoffs/UI-WINDOWS-003.md).

## UI-WINDOWS-004: bulk lifecycle census and empty NPC frames

This section supersedes the earlier route claims and remaining-row counts.
The same verified text/data pins above are used. The base is UI-WINDOWS-003
c3b29c40 plus main 4babc900, merged at d14d3a67. No live client, protected
module, server, installed app or new data acquisition is involved.

### Census method and limits

`scripts/survey_ui_routes.py` scans the full pinned text for direct relative
calls to toggle, close-all and the open/close targets in the registered
controller vtables. It also lists every register-based virtual call encoding
at +0x40/+0x44, keeping untyped receivers as candidates. Receiver joins start
at a manager getter, follow register/local moves and exact field getters,
and stop at branches or unrelated calls. A matching field offset in an
unrelated object does not establish a manager/window identity.

The registration constructor has 137 entries, including duplicate instances,
front-end resources and aliases. The scan finds 103 direct toggle calls and
1,042 lifecycle sites/candidates, 415 with manager-window receivers and 627
unresolved. Those are scan counts, not whole-client window counts. Dynamic
receivers, other virtual slot encodings, indirect calls through registers,
uncaptured vtables, and paths outside these services remain unresolved.
A no-route-found row means no opener was joined by this bounded scan, not
proof that the original has none. Close and visibility queries are not
openers. No binding is admitted from a registration/name reference alone.
The 23 main-menu constants and legacy manager calls/constant IDs are listed
separately, with dynamic arguments explicitly unresolved. No old NewUI movie
alias or guessed key is promoted into a GFx binding.

The [service candidates](ui-window-services.csv), [menu entries](ui-window-menus.csv)
and [legacy calls and IDs](ui-window-legacy.csv) preserve the supplemental
address ledgers. There are 176 legacy calls and 47 recovered immediate IDs.

The machine-readable [survey](ui-window-route-survey.csv) keeps all 134
historical rows, marks the 118 unresolved on entry and gives each a route /
provider classification and reason. Its classifications apply to empty,
authored presentation only, never original service completeness.
The supplemental lifecycle ledger records addresses and receiver status;
private reports contain no committed client bytes or movie content.

### Corrected PlayGuide route

The fresh registry join proves PlayGuide is +0x1f0, registration 0x00ac548a.
Getter 0x00b3b39e returns +0x2ac, registered as EventMapEntranceUI at
0x00ac883e. Thus Ctrl+T at 0x00efc0da and main-menu 22 at 0x00c71576 do
not establish a PlayGuide opener. The prior lane checked the caller's toggle
and sound instructions but failed to join the getter to the actual movie.
The unsupported native PlayGuide key/menu routing is now refused. It remains
a registered optional movie with no proved original opener. No event entry
or external guide provider replaces it. This withdraws one historical binding.

### Nine admitted movies, ten manager slots

The existing offline NPC result callback supplies the proved manager slot.
One table admits the following movies, with two Harmony registrations sharing
one empty presentation. No new packet parsing or service path is added.

| Movie | Manager slot | Existing original route | Empty fixture |
|---|---|---|---|
| GuardianMix | +0x20c | NPC presentation result 7, virtual open | No tabs, recipes, materials or result |
| MixAttributeScalp | +0xb4 | Results 8/9, virtual open after flag | Labels, disabled item action, Close |
| HarmonyMix | +0x264 / +0x260 | Results 0x11 / 0x13, virtual open | Empty recipe list, no options or formulas |
| SocketMix | +0x208 | Result 0x17, virtual open | Empty list and default frame |
| MixSel | +0xac | Results 0x18 / 0x26 / 0x27, presentation methods | Empty selector, all recipe buttons disabled |
| ExchangeLuckCoin | +0x270 | Result 0x20, virtual open | No coins, rate, exchange or result |
| ElementalMix | +0x204 | Result 0x29, virtual open | Empty list, materials and result |
| MuunExchange | +0x1ac | Result 0x33, toggle | Empty one-page exchange list |
| RuudShopFrame | +0x1fc | Result 0x35, virtual open | Empty one-page catalogue, no purchases |

Original route owner is 0x01280659. Its existing instruction harness supplies
the oracle, with manager/window and GFx services stubbed explicitly. The
thirteen relevant result paths are compared with the compiled production
adapter. The comparison includes repeated close-all for 8/9, open versus
toggle and the common sound order. Selector-specific helpers are recorded
at their boundary; their recipe and transaction internals are not executed.
The native selector deliberately supplies an inert common first page.
Static helper tails confirm virtual open at 0x00bd73e9, 0x00bd746b and
0x00bd7138. The last has an original eligibility gate before that tail; the
offline fixture supplies eligibility, with no stat computation or authority.

The graphical offline NPC host now opts into close-all, presentation open,
then existing sound 25 followed by 28. The older headless recording callback
contract remains available. Sound counts retain the existing core owner;
new window controllers add no sound. The UI host previously delivered the
sound callbacks before opening the movie. No sound sites outside this UI
ordering correction are changed. Core `not_played` accounting still uses
its historical OTHER-kind classification, so it is not a visible-window
census for the new presentation adapters.

Every movie has an exclusive callback allowlist. Item movement, recipes,
exchange, purchases, paging requests, configuration, stats and unknown
callbacks refuse before foreign NPC/item/social/command owners. Close and
layout metadata stay local. NPC teardown and Esc close the views. English
labels and empty providers are authored fixtures; no authoritative item,
catalogue, currency, reward, option or eligibility data is reconstructed.

Best remaining small-provider leads were reviewed conservatively.
MiniGameHelpWindow needs its original page/content owner, and guide content
is excluded. DivideWindow needs the selected item/count and transaction
owner. GuildCreateFrame needs the emblem/form and create owner. These are
left with precise missing providers rather than invented empty openers.
Help's indirect opener, Home activation, fifth-tree inventory and event
inventory remain refused for the reasons recorded by UI-WINDOWS-003.

### Current counts

Of the 118 unresolved rows on entry: 9 route proved + provider complete,
17 route proved + provider missing, 30 state-dependent and 62 no route
found. Nine become bound, while the incorrect inherited PlayGuide binding
is withdrawn. The historical 134-row survey therefore changes from
16 bound / 118 unresolved to 24 bound / 110 unresolved. The native registry
has 57 entries / 56 filenames, including the unbound optional PlayGuide
movie. Registry presence and original-route admission remain different counts.

The [handoff](../handoffs/UI-WINDOWS-004.md) records compiled mutants,
native journey provenance, check wall times and the exact steward selection.

## UI-WINDOWS-005: provider groups and intermediate routes

Base main `6900914e`; text/data pins at the top of this document are unchanged.
The [17-row provider ledger](ui-window-provider-groups.csv) records the exact
missing piece, reviewed movie methods, refusal and sound boundary for each row.
Groups on entry are two catalogues, six item/detail views, one mix view, two
forms, three HUD/notices, one account shop, one guide and one recovery list.
Labels and lists recovered for admission are authored English empty fixtures.
No original catalogue, option, item, entitlement or server record is published.

### Second static pass

`scripts/survey_ui_indirect.py` retains manager/window identity across branches
and local saves, resolves method loads followed by register calls, and follows
one intermediate UI controller method with its proved receiver. A virtual call
requires the vtable and `this` to identify the same window. Unknown register
writes kill facts; calls clobber volatile registers. Path-local states avoid
joining identities from different branch arms. Search limits are 1,024 bytes,
240 instructions and 2,048 states per manager root; intermediate exploration is
cached by method/slot. This is a bounded static search, not complete call-graph
recovery. Dynamic IDs, untyped callback dispatch, uncaptured function pointers
and script routes without a captured controller join remain unresolved.

The pass also checks captured absolute function-pointer and adjacent register-immediate manager calls. Dynamic table IDs remain unresolved.

The pass starts at 6,708 direct manager calls. It finds 482 lifecycle sites,
67 additional to 004. The [address ledger](ui-window-indirect.csv) records
manager root, terminal site, movie, slot and action. These extra sites prove
open/toggle routes for 20 entry no-route rows. Movie casing differs in some
registrations, so the survey join uses the proved manager slot, never a guessed
filename alias. Registration names alone still do not admit windows.
The original 30 state-dependent rows retain their classification and refusals.

### Admitted providers and boundaries

| Movie | Original route | Native fixture |
|---|---|---|
| PersonalShop | NPC result 0x30; +0x164 toggle; menu 7 -> 0x00c73603 -> 0x00c73688 | Empty shop/item/search lists; authored child headers; two local tabs; search, community, purchases and item actions refuse |
| ArtifactFrame | Inventory `onClickArtifact`, 0x00b97ebe..0x00b97ee4; getter 0x00981423 -> +0x280 toggle | Empty hex slots and option tree; one page; no artifact records, option bonuses, expand/page or slot operations |
| MUMix | Goblin `onClickGoblinMenu` -> 0x00bd0a4b -> 0x00bd06ae; index 1 opens +0x290 at 0x00bd07ff, then closes selector | Empty category tree/default page; no recipes, material slots, chance, currency or results |
| DuelWatch | NPC result 0x21 -> +0xe0 method 0x00b54793 -> original open tail 0x00b548ef..0x00b548f7 | Four authored empty match rows, each watch button disabled; no match list or entry request |

The Goblin branch also corrects the inherited selector inversion: choice value 0 opens
the existing older mix view, choice value 1 the new MUMix preview. The existing legacy
button regression now supplies original index 0; its transaction assertions
are retained. The old view remains a pre-existing fixture, outside the new
empty-provider scope. Competing visible mix views refuse the other opener.

The table-driven production adapter preserves toggle versus open and refuses
missing readiness. Inventory callback consumption happens before foreign item
handlers and requires the inventory to be visible. Close, Esc and NPC teardown
are local. PersonalShop's original movie changes its tab before its callback;
that callback receives only empty lists and cannot request a catalogue.

NPC routes keep the existing close-all, controller, sound 25 then sound 28
order. Menu 7 retains the original common sound-25 site `0x00c716f6`. The
artifact callback arm contains no direct sound. New controllers add none;
unowned nested GFx sounds remain outside the claim.

### Current classifications

The 118 rows classified by 004 change from 9 complete / 17 provider-missing /
30 state-dependent / 62 no-route to 13 / 33 / 30 / 42. Nineteen newly proved
rows remain provider-missing; DuelWatch is the twentieth and is admitted.
The historical survey rises 24 -> 28 bound of 134, unresolved 110 -> 106.
The separately withdrawn PlayGuide row remains no-route and unbound.
Registry entries rise 57 -> 61; distinct filenames 56 -> 60.

Help/F1, Home activation, separate fifth-tree inventory and event-inventory
openers stay refused. No macro timing/configuration, hunting history, matching
catalogue, storage authority, guide content, transactions, stat formulas or
power features are implemented. A proved lifecycle method is not proof of its
upstream request/state, so the new route discoveries retain those missing
providers instead of acquiring invented keys or native triggers.

The final callback audit requires Goblin parent events to be consumed even
when hidden or malformed, before the older integer-cast handler. Twelve
parent controls and a distinct compiled fallthrough mutant cover that limit.
The route scanner also invalidates partial register writes and overlapping
frame stores. Proved object-field writes preserve disjoint frame saves;
unknown memory writes discard them. Eight synthetic provenance controls pass,
including exchanged and implicit memory stores.
This stricter pass withdraws one tentative ResistPopup opener and two close
joins: 482 lifecycle sites / 67 additional, with 20 newly proved entry routes.
The withdrawn candidate remains no-route; no binding is supplied.

The final integrated four-window journeys reproduce all ten inspected proof
frames byte for byte. The rebuilt final binary retains all 230 default
artifacts against the single preserved baseline. The [005 handoff](../handoffs/UI-WINDOWS-005.md)
records source commits, distinct binary hashes, private/portable results,
compiled mutants and the complete timed steward-validator list.

## UI-WINDOWS-006: missing pieces, parameterised opens and the map banner

Base main `c5b9d5ca`; the text/data pins at the top of this document are unchanged.
No original or live client, protected module, server or new data acquisition.

### What each of the 33 provider-missing rows lacks

`scripts/survey_ui_triggers.py` walks direct callers upward from every proved
open site, at most seven functions, and records where a chain ends: the receive
dispatcher `0x01287ead` (a server answer), a function whose address is stored
in the image data (a virtual method or callback table entry) or no caller in
the bound. Function starts are a prologue heuristic and indirect calls are not
followed, so a root kind names an owner class, never a route or a permission.
The [trigger ledger](ui-window-triggers.csv) holds 136 sites. Each row was then
read at its opener; the [missing-piece ledger](ui-window-missing-pieces.csv)
states the exact piece, whether it is static, and the disposition.

| Group on entry (33 rows) | Rows | Piece kind |
|---|---:|---|
| Server-answer trigger with no offline owner | 17 | authoritative state |
| Server-answer trigger whose handlers already have offline owners | 1 | static: MapName |
| A clicked, used or hovered item or slot record of one kind | 8 | authoritative item records |
| World or HUD state (boss target, selected other player, alarm entry) | 3 | authoritative state |
| Parent window that is not bound | 2 | parent has no static route |
| Pending transaction step of a bound parent | 1 | transaction |
| Upstream caller unresolved | 1 | unknown |

The seventeen are ArkaResultInfo, CursedTempleResult, CursedTempleScore, Duel,
EventMapRoundCount, GoldArcher, GuildCreateFrame, ImageNotice, IngameShop,
ListofMatches, ProgressFrame, RebuyList, RewardItemExchange,
StrongestMatchRank, StrongestMatchResult, SwitchMode and TimeCounter. Their
layouts and label tables are static, but the open is the consequence of an
answer nothing offline owns. Inventing such an owner is packet work and is
refused. The eight item rows are ArtifactInfoPopup, PetInfoPopup, DivideWindow,
MonsterSoulReward, Pentagram, SlottedWingInfo, SkillTree5thLevelUpPopup and
SkillTree5thSlotClickPopup. Pentagram and SlottedWingInfo, for example, open
on Alt + left click over an item with attribute `0x2b` / `0x6a`
(`0x00b92dec`), and the window is then filled from that item. The three state
rows are BossHpUI, QuickCommand and DeathPenaltyExpRecovery. QuickCommand's
input handler `0x00efbcc8` needs Alt, the right button and a selected other
player in range; it becomes a candidate once world picking of demo players
exists, with every command button disabled. GuildPosition and
MiniGameHelpWindow hang off GuildInfoFrame and MiniGameRummy.
PersonalShopCaution is the confirmation step of a store registration which the
native item service completes without it. NpcGateKeeper is reached by legacy
open id `0x18`, but none of the 23 direct callers of `0x00f2abcd` pushes that
id; the caller graph through that shared function says nothing about it.

No sound-only, label-only or layout-only deficit exists in the 33 rows. Only
one group is static, so the table-driven pass admits one movie.

### MapName, the arrival banner

MapName is `+0x128`, registration `0x00ac8aec` (alignment 9, registrar group
3, the group of InfoPopup). Its open method `0x00baee4a` is self-contained:

1. nothing when the current world is `0x28`;
2. `InitText`, then the lifetime timer starts (`0x011865d8` on `+0x78`);
3. `SetMapName` with the map-name function `0x016baaa6`. The letter loop
   before it calls `rand()` once per letter and its store was removed, so the
   name is unchanged;
4. `SetStrife(GlobalText 0xbac)` only when the strife predicate `0x016bec9f`
   holds; `SetOccupyGuild` only for a non-empty occupying guild (`+0xac`);
5. base open `0x00aae420`.

The update method `0x00baf120` closes it once 5000 ms (the double at
`0x01a90948`) have passed while it is loaded and open, and restarts the timer.
Three handlers open it: the join answer `0x0124cc64` at `0x0124e15e`
(unconditional; the preceding conditional was replaced by a jump), the respawn
answer `0x0127bd9e` at `0x0127c567` (unconditional on its tail) and the
teleport answer `0x0128136d` at `0x01281ea7`, after the manager and legacy
close-all, only when the packet's number word `[4]` is not zero.

All three handlers already have offline owners: the hero join, the demo
respawn and the map session's teleport answer. The native banner therefore
needs no new owner. `mu_gfx_layer_map_arrival` applies the open contract with
the name the top menu already uses; the first location feed is the join, the
respawn part and the travel report the other two. The strife predicate depends
on a server-mode flag (its entry is outside the readable text) and the guild
on a server answer, so both stay as `InitText` clears them. A world the
map-name function names from runtime state gets no banner. Native load order
differs: the offline join precedes the movie's UIInit, so that one open is
held until the movie is ready. The banner takes no pointer input, is not
closed by Esc or by the NPC close-all, and adds no sound. Whether the
original close-all list contains a group-3 movie is unproved; no claim is made.

Instruction comparisons run the whole open method (ten cases over world,
strife and guild), the update method (24 cases around 5000 ms) and the three
owner tails with every service stubbed. The native invoke trace of the
provider equals the original's for the fixture case. Seventeen compiled
mutants are caught; the [handoff](../handoffs/UI-WINDOWS-006.md) lists them.

### Third pass: parameterised opens

004 and 005 treated only vtable `+0x40` / `+0x44` as lifecycle slots. A window
class can have another virtual method that opens its own window through `this`
after taking arguments. `self_open_slots` in `scripts/survey_ui_indirect.py`
walks every other vtable method of each registered class (2,048 bytes, 400
steps, no helper calls) and keeps those that reach the base open, the class's
own open, the toggle or `call [vtable + 0x40]` with the entry `this`. The
existing manager-rooted pass then also accepts a virtual call through exactly
those offsets. The default pass is unchanged: 482 sites, identical ledger.

Two classes have such a method, both at `+0x4c`:
EventMapHelper `0x00b6b656` and MiniGameRummy `0x00bca125`. Five
manager-qualified callers follow ([ledger](ui-window-parameterised.csv)).
EventMapHelper opens from the NpcDialogue callbacks `onClickbtnEnterTime` /
`onClickbtnEnterLevel` (`0x00be5405`, `0x00be5453`, argument 1 or 2) and from
an EventMapEntranceUI method (`0x00b04ba3`). MiniGameRummy opens twice in a
server-answer handler (`0x0126f12c`, `0x0126f203`). As a control, naming
`+0x4c` for the already-bound NpcQuestProgress (`0x00bedfb4`) rediscovers its
known owners, among them the quest-progress answer at `0x01222a4c`. The strict
walk itself does not prove that control method, because an unknown store
precedes its open; it is named by hand and only used as a control.

Both rows move from no-route to route proved + provider missing.
EventMapHelper's missing piece is static in kind but not recovered: its row
table (reached through the Help controller field `+0x11090`) and an NPC
dialogue page that shows the two buttons. MiniGameRummy needs card-game
answers. The other 40 no-route rows are unchanged; no further sweep idea was
tried. Of those, eight have a manager slot but no joined opener
(EnterBloodCastle, EventMapTutorial, GuildInfoFrame, MBoxShop, ResistPopup,
SimpleUI, SimpleUISubWin, SkillTree5thInventory) and 32 have no manager slot
joined to a registration in the world constructor. The separately withdrawn
PlayGuide row (`+0x1f0`) remains no-route and outside the 118-row denominator.

### State-dependent rows

The 30 rows stay refused. The [state ledger](ui-window-state-needs.csv) gives
one line per row. Sixteen are opened only by server answers and five more by
server answers among other owners. The remaining nine are reached from
controller callbacks, the input handler or the NPC-click path, which are
static but only meaningful inside an event (for example EventMapEntranceUI by
Ctrl+T and menu 22, CursedTempleEnter and EnterEmpireGuardian by an NPC
click). OrdealSquareBattleEnter's opener is NPC
talk result `0x34`, already reconstructed in `npc_talk.c`; what it lacks is
the event schedule, entry count and party eligibility its page shows. These
are owner decisions, not missing evidence.

### Current counts

The 118 rows classified by 004 change from 13 complete / 33 provider-missing /
30 state-dependent / 42 no-route to 14 / 34 / 30 / 40: MapName is admitted and
two no-route rows gain a proved route. The historical survey rises 28 -> 29
bound of 134, unresolved 106 -> 105. Registry entries rise 61 -> 62, distinct
filenames 60 -> 61. Help/F1, Home activation, the separate fifth-tree
inventory and the event-inventory openers stay refused.
