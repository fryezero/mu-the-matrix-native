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
| `AutomaticMacro.swf` | 7 / high | 0xac9217 | Home helper branch 0x00efd1a7; exact movie-open call untraced | Helper start/stop and answers excluded; left |
| `BattleCoreDialog.swf` | 10 / unknown | 0xac7789 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BattleCoreEnter.swf` | 10 / unknown | 0xac7705 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BattleField_BigDialog.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BattleFieldNotify.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `BlockedChat.swf` | 10 / unknown | 0xac7d38 | Open route untraced | Social/list records and controller absent; left |
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
| `EventInventoryFrame.swf` | 10 / unknown | 0xac623b | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapEntranceUI.swf` | 10 / unknown | 0xac883e | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapHelper.swf` | 10 / unknown | 0xac680f | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapProgressInfo.swf` | 10 / unknown | unlocated | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapRoundCount.swf` | 10 / unknown | 0xac8ef9 | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `EventMapTutorial.swf` | 10 / unknown | 0xac75fe | Open route untraced | Event/round/score fixture and lifecycle absent; live event state excluded; left |
| `ExchangeLuckCoin.swf` | 10 / unknown | 0xac931e | Open route untraced | Item/currency/recipe/reward fixture and transaction owner absent; left |
| `ExtensionBagFrame.swf` | 9 / medium | 0xac5e6e | Inventory child; exact open callback untraced | Item grids and expansion state absent; left |
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
| `SkillTree5thInventory.swf` | 10 / unknown | 0xac862a | Open route untraced | Domain-specific records/controller absent; no stat/power work; left |
| `SkillTree5thItemViewer.swf` | deferred / medium | 0xac86af | Ctrl+J/I branch 0x00efc104/1ad; child lifecycle untraced | Card/item fixture owner absent; no stat/power work; left |
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
