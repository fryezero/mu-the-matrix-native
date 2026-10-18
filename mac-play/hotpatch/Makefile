PYTHON ?= python3
MINGW_CC ?= i686-w64-mingw32-gcc
BUILD := build
# Mandatory for Claude v7.0's binary32 operation order under Rosetta.
CFLAGS := -O2 -msse2 -mfpmath=sse -ffp-contract=off -Wall

# The default cross-build has no game patch tables and cannot apply game hooks.
all: $(BUILD)/synthetic/opengl32.dll diagnostics modes

$(BUILD)/exports/generated: gen_exports.py ../mugl/exports.txt
	$(PYTHON) gen_exports.py --out $(BUILD)/exports
	touch $@

$(BUILD)/synthetic/generated: generate.py targets.json
	$(PYTHON) generate.py --synthetic --out $(BUILD)/synthetic
	touch $@

$(BUILD)/synthetic/opengl32.dll: mugl.c xform.c meshdraw.c stall.c terrain.c gpudiag.c ../mumodes/modehook.c $(BUILD)/exports/generated $(BUILD)/synthetic/generated
	$(MINGW_CC) $(CFLAGS) -I$(BUILD)/exports -I$(BUILD)/synthetic -shared mugl.c $(BUILD)/exports/stubs.S $(BUILD)/exports/opengl32.def -o $@ -Wl,--enable-stdcall-fixup -static-libgcc

# Explicit opt-in, using private tables already generated and checked by generate.py.
private: $(BUILD)/exports/generated
	test -f $(BUILD)/private/generation.json
	$(MINGW_CC) $(CFLAGS) -I$(BUILD)/exports -I$(BUILD)/private -shared mugl.c $(BUILD)/exports/stubs.S $(BUILD)/exports/opengl32.def -o $(BUILD)/private/opengl32.dll -Wl,--enable-stdcall-fixup -static-libgcc
	$(MINGW_CC) $(CFLAGS) -I$(BUILD)/private hptest.c hp.S thunks.S -o $(BUILD)/private/hptest.exe

diagnostics:
	mkdir -p $(BUILD)/diagnostics
	$(MINGW_CC) $(CFLAGS) meshbench.c -o $(BUILD)/diagnostics/meshbench.exe -lopengl32 -lgdi32
	$(MINGW_CC) $(CFLAGS) callbench.c loops.S -o $(BUILD)/diagnostics/callbench.exe
	$(MINGW_CC) $(CFLAGS) ../automation/muinput.c -o $(BUILD)/diagnostics/muinput.exe -luser32

modes:
	mkdir -p $(BUILD)/modes
	$(MINGW_CC) $(CFLAGS) -shared ../mumodes/mscoree_proxy.c ../mumodes/mstubs.S ../mumodes/mscoree.def -o $(BUILD)/modes/mscoree.dll -Wl,--enable-stdcall-fixup -static-libgcc

clean:
	rm -rf $(BUILD)

.PHONY: all private diagnostics modes clean
