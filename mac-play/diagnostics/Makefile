MINGW_CC ?= i686-w64-mingw32-gcc
# Mandatory SSE math on Rosetta; no x87 in either diagnostic.
CFLAGS := -O2 -msse2 -mfpmath=sse
all: build/glbench.exe build/eipprof.exe build/glcheck.exe
build:
	mkdir -p $@
build/glbench.exe: glbench.c | build
	$(MINGW_CC) $(CFLAGS) $< -o $@ -lopengl32 -lgdi32
build/glcheck.exe: glcheck.c | build
	$(MINGW_CC) $(CFLAGS) $< -o $@ -lopengl32 -lgdi32
build/eipprof.exe: eipprof.c | build
	$(MINGW_CC) $(CFLAGS) $< -o $@
.PHONY: all
