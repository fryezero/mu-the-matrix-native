# Main world call order, WORLD-ORDER-001

Implementation checkpoint. Full branch coverage, final local macOS gate and delivery results follow in the
milestone handoff before merge.

**Verified so far:** the compiled C order-only reconstruction of MoveMainScene `0x0185613e..0x01856e6c` and
RenderMainScene `0x0185916b..0x01859d8a` matches pinned original control flow in Unicorn on 1,200 cases each,
zero mismatches and zero stopped cases. Nine compiled planted mistakes are detected. The source calls the
existing scene-manager host with routine/import identities and virtual-call slots. It is a validation family,
not a replacement native runtime. The first-tick packet-building interval is one opaque event.

`reconstructed/world-order/parts_order.py` projects the compiled record stream onto native `parts.def` tick,
GL draw and software draw columns. Its native adapters state every grouping, moved part and added native
step. `test_world_parts.py` no longer holds a literal expected tick/draw list. Open, pre-tick, frame and report
keep their separate native baseline checks. No executable runtime code or order numbers changed.

**Limits:** this is call order and draw success evidence, not callee-body, call-argument, ECX, general-write,
exception-unwinding or image-equality evidence. The ordinary recorded stream supplies the part projection;
world/guard variants are separately compared with original instructions. Existing native aggregated passes,
demo work and GL/software differences remain explicit adapters, not claims of full original ordering.
