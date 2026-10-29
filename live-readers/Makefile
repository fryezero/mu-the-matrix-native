# Read-only live-state readers for the native reconstruction (macOS host tools).
# Each one is built with clang and ad-hoc signed with the debugger entitlement, so task_for_pid works on a
# Wine main.exe process the user started. No signing identity, task attachment or game access happens here.
TOOLS := objread memread lightread langread rtsample
all: $(addprefix build/,$(TOOLS))
build:
	mkdir -p $@
build/%: %.c debugger-entitlement.plist | build
	clang -O2 -Wall -MMD -MP -MT $@ $< -o $@
	codesign -s - -f --entitlements debugger-entitlement.plist $@
# objread: NATIVE-OBJECTS-001 static-object list (+ NATIVE-LOGIN-001 scene globals)
# memread: NATIVE-PATH-002 fixed static-data ranges
# lightread: NATIVE-LIGHT-001 model lighting inputs
# langread: NATIVE-LANG-001 / NATIVE-QUEST-001 tables main.exe built from Data\Lang.mpr
# rtsample: RENDER-TIME-002 post-draw temporal summaries (rtinput/ holds its Wine-side input replay, built separately)
$(TOOLS): %: build/%
# BUILD-DEPS-001: -MMD lists each tool's headers in build/<tool>.d.
-include $(wildcard build/*.d)
clean:
	rm -rf build
.PHONY: all clean $(TOOLS)

# LAYOUT-001: build objread's constants from the shared JSON, never pasted offsets.
PYTHON ?= python3
.PHONY: layout-json
layout-json:
	$(MAKE) -C ../native layout PYTHON="$(PYTHON)"
build/layout_reader.h: ../scripts/layout_manifest.py layout-json | build
	$(PYTHON) ../scripts/layout_manifest.py --manifest ../native/build/gen/layout.json --reader-header $@
build/objread: build/layout_reader.h
