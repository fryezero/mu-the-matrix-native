# SYS-MISC-001a investigation

Work in progress. No live client, protected module, dispatch generator, jump-table walk,
wire encryption or keyed transform was used.

## Inputs and evidence boundary

Pinned restored text SHA-256 `2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724`;
pinned image data `c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f`.
These are the existing compatibility-environment captures, not native Windows observations.

Static observations from bounded window registration, constructors and their direct callers:

- HelpWindow: manager +0x120, registration 0x00ac678a, constructor 0x00b89588,
  vtable 0x01a8f180. Loader 0x00b89977 invokes InitText, SetPosCenter,
  ClearDataProvider and help-row loaders. The helpdata.bmd reader is separate from the movie.
- CommandWindow: manager +0x134, registration 0x00ac699b, constructor 0x00b4c867,
  vtable 0x01a8b718. Command actions include trade, purchase, party, whisper, guild,
  union, rival, friend, follow and duel. These actions depend on social/item domains.
- QuickCommand: manager +0xd8, registration 0x00ac569e, constructor 0x00c0a0f4,
  vtable 0x01a97604. Its contextual target checks and command actions are distinct
  from the list window.
- BossHPUI: manager +0x27c, registration 0x00ac9425, constructor 0x00b35935,
  vtable 0x01a8a16c. Two bar states, each five signed integers at +0x78 with stride
  0x14. Initial state is 0,10,10,0,1 at 0x00b360b1. SetBossInfo 0x00b35af9;
  UpdateHpHud 0x00b35dff. Layer count/colour is not a simple HP percentage.
- DivideWindow is excluded from this slice: its visibility participates in item/NPC
  transaction guards, and the requested item-independent condition is not established.

Local ActionScript inspection of the existing converted movies establishes static interfaces:

- MonsterInfo.AddInfoUI takes key, name, HP frame, attribute, visibility, x, y and mark.
  It has no level argument. InitScene cycles identifiers through 0..100. Its retained
  per-key clips need explicit removal. This differs from hudPlayerName.MonsterInfoMC,
  which the port already renders.
- DamageCount is a resizable text/caution dialog with InitText, SetText and Stop/OK/Cancel
  callbacks. It is not a floating damage-number movie or an automatic damage accumulator.
- BossHpUI.swf exports BossHPUI and uses SetBossInfo and UpdateHpHud.

The pinned image strings contain the BossHPUI/HelpWindow/CommandWindow/QuickCommand
registrations. The exact MonsterInfo and DamageCount class registrations and receive/request
paths have not yet been identified. Movie interfaces alone are not instruction validation.
No arbitrary packet route or invented request is justified by these observations.
