# NATIVE-GFX-001/002: the GFx layer and its window.  Not part of the default
# build.  The layer loads libmugfx (Rust, pinned patched Ruffle:
# fetch-ruffle.sh, build-mugfx.sh) at run time, so these C targets build
# without Rust; running them needs the library.
CC := clang
SDL_CONFIG ?= sdl2-config
BUILD := ../build
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
GL_LIBS := -framework OpenGL
DL_LIBS :=
else
GL_LIBS := -lGL
DL_LIBS := -ldl
endif
CFLAGS := -std=c11 -O2 -DGL_SILENCE_DEPRECATION -Wall -Wextra -Wno-unused-parameter -I . -I ../../reconstructed/hud -I ../core -I ../viewer
LAYER_SRC := mu_gfx_layer.c ../../reconstructed/hud/inv_grid.c ../../reconstructed/hud/item_slots.c \
             ../../reconstructed/hud/tooltip_html.c
SRC := mu_gfx_window.c $(LAYER_SRC) ../core/mu_png.c ../viewer/gl_headless.c

window: $(BUILD)/mu-gfx-window

$(BUILD)/mu-gfx-window: $(SRC) mu_gfx_layer.h mu_gfx_sdl.h mugfx/include/mugfx.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $$($(SDL_CONFIG) --cflags) $(SRC) $$($(SDL_CONFIG) --libs) $(GL_LIBS) $(DL_LIBS) -lm -o $@

# Layer test host (no GL, no SDL): native/tests/test_native_gfx2.py drives it
# with a stub libmugfx (tests/gfx_stub_mugfx.c) or the real one.
$(BUILD)/mu-gfx-layer-test: ../tests/gfx_layer_host.c $(LAYER_SRC) mu_gfx_layer.h mugfx/include/mugfx.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -DMU_GFX_NO_GL ../tests/gfx_layer_host.c $(LAYER_SRC) $(DL_LIBS) -lm -o $@

.PHONY: window

# DATA-ACQ-003: first-run conversion, no Python/Pillow. The C++ envelope
# reader is linked as an object; only Crypto++ and system zlib are needed.
CXX := clang++
CRYPTOPP_PREFIX ?= $(shell if command -v brew >/dev/null 2>&1; then brew --prefix cryptopp; else echo /usr; fi)
ifneq ($(CRYPTOPP_PREFIX),/usr)
CONVERT_CPPFLAGS := -isystem $(CRYPTOPP_PREFIX)/include
CONVERT_LDFLAGS := -L$(CRYPTOPP_PREFIX)/lib
endif
CONVERT_SRC := gfxconvert.c gfxconvert_image.c gfxconvert_fonts.c gfxconvert_actions.c
CONVERT_OBJ := $(patsubst %.c,$(BUILD)/gfxconvert/%.o,$(CONVERT_SRC))
CONVERT_FLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -ffp-contract=off
converter: $(BUILD)/gfxconvert/gfxconvert
$(BUILD)/gfxconvert/%.o: %.c gfxconvert.h Makefile
	@mkdir -p $(dir $@)
	$(CC) $(CONVERT_FLAGS) $(CONVERT_CPPFLAGS) -c $< -o $@
$(BUILD)/gfxconvert/modulus.o: ../../model-recovery/modulus.cpp
	@mkdir -p $(dir $@)
	$(CXX) -std=c++17 -O2 $(CONVERT_CPPFLAGS) -c $< -o $@
$(BUILD)/gfxconvert/gfxconvert: $(CONVERT_OBJ) $(BUILD)/gfxconvert/modulus.o
	$(CXX) $^ $(CONVERT_LDFLAGS) -lcryptopp -lz -o $@
.PHONY: converter
