# Read-only live-state readers for the native reconstruction (macOS host tools).
# Each one is built with clang and ad-hoc signed with the debugger entitlement, so task_for_pid works on a
# Wine main.exe process the user started. No signing identity, task attachment or game access happens here.
TOOLS := objread memread lightread langread
all: $(addprefix build/,$(TOOLS))
build:
	mkdir -p $@
build/%: %.c debugger-entitlement.plist | build
	clang -O2 -Wall $< -o $@
	codesign -s - -f --entitlements debugger-entitlement.plist $@
# objread: NATIVE-OBJECTS-001 static-object list (+ NATIVE-LOGIN-001 scene globals)
# memread: NATIVE-PATH-002 fixed static-data ranges
# lightread: NATIVE-LIGHT-001 model lighting inputs
# langread: NATIVE-LANG-001 / NATIVE-QUEST-001 tables main.exe built from Data\Lang.mpr
$(TOOLS): %: build/%
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
