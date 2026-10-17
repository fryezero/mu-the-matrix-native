PYTHON ?= python3
MINGW_CC ?= i686-w64-mingw32-gcc
BUILD := build
# SSE is mandatory: default MinGW x87 math is extremely slow under Rosetta.
# --no-insert-timestamp keeps rebuilds byte-identical (setup-mu-mac.sh compares hashes).
CFLAGS := -O2 -msse2 -mfpmath=sse -Wall -Wextra

all: $(BUILD)/opengl32.dll

$(BUILD)/generated: gen.py exports.txt
	$(PYTHON) gen.py --out $(BUILD)
	touch $@

$(BUILD)/opengl32.dll: mugl.c triangles.c triangles.h $(BUILD)/generated
	$(MINGW_CC) $(CFLAGS) -I$(BUILD) -shared mugl.c triangles.c $(BUILD)/stubs.S $(BUILD)/opengl32.def -o $@ -static-libgcc -Wl,--no-insert-timestamp

clean:
	rm -rf $(BUILD)

.PHONY: all clean
