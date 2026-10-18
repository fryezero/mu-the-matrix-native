# NATIVE-GFX-001 prototype window.  Not part of the default build: it needs a
# Rust toolchain and the pinned Ruffle (fetch-ruffle.sh, build-mugfx.sh).
CC := clang
SDL_CONFIG ?= sdl2-config
BUILD := ../build
MUGFX := mugfx/target/release
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
GL_LIBS := -framework OpenGL
MUGFX_LIB := $(MUGFX)/libmugfx.dylib
else
GL_LIBS := -lGL
MUGFX_LIB := $(MUGFX)/libmugfx.so
endif
CFLAGS := -std=c11 -O2 -Wall -Wextra -Wno-unused-parameter -I mugfx/include -I ../../reconstructed/hud -I ../core
SRC := mu_gfx_window.c ../../reconstructed/hud/inv_grid.c ../../reconstructed/hud/item_slots.c ../core/mu_png.c

window: $(BUILD)/mu-gfx-window

$(BUILD)/mu-gfx-window: $(SRC) mugfx/include/mugfx.h $(MUGFX_LIB)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $$($(SDL_CONFIG) --cflags) $(SRC) -L$(MUGFX) -lmugfx -Wl,-rpath,$(abspath $(MUGFX)) \
	  $$($(SDL_CONFIG) --libs) $(GL_LIBS) -lm -o $@

.PHONY: window
