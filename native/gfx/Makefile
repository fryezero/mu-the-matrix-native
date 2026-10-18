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
