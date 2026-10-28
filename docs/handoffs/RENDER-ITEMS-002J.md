# RENDER-ITEMS-002 part 10

Checkpoint in progress on base 9e0cceb, branch codex/render-items-002j, issue #234.
Own item-render rules, item validators/tests and survey membership. No live client,
launcher, perf/mesh/scene, particle/world or audio implementation is edited.

The six requested types 0x2322..0x2327 and 105 further bodies pass the bounded
initial comparison after the atlas ancient-light correction: 111 additions,
880/1,674 bodies and 17/17 skins. Two new shield targets are wired.
Strict final validator, native gallery and serialized release remain pending.

The survey's wing label is model-index inference. The installed Item.bmd model
getter resolves all six requested types to s30_seed.bmd, the elemental seeds.
The real native inventory gallery exposed the inherited OBJECT hidden-mesh-zero
boundary: it hides the seed model's only mesh. Extend this six-type boundary with
recorded hidden mesh inputs and compare again before claiming a visible gallery.
The initial arbitrary wing-model pairings are discarded and are not evidence of
actual equipment/model mappings.

The full-function screen rejects 55 further probe-fitting candidates. Fourteen
atlas armour types retain preceding body light, separately from model shade,
in their ancient meshes. Rank-5 owner effects, Muun and nested map-object tables
remain excluded. No per-frame allocation or shared caller/build hook is added.
