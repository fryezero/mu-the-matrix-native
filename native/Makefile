# Native viewer (NATIVE-VIEW-001).
#
#   make -C native            core library and the portable headless tool build/mu-render
#   make -C native viewer     windowed SDL2 + OpenGL 2.1 viewer build/mu-viewer (needs sdl2-config)
#
# The core builds on macOS and Linux with clang and Crypto++ (already required by
# model-recovery for BMD v14). libjpeg is optional; without it JPEG textures are
# reported missing. Every C file is built with -ffp-contract=off: the
# reconstructed record-math, pose and skinning sources require binary32
# operations in source order, and the software rasterizer relies on it for
# host-independent hashes.

CC := clang
CXX := clang++
BUILD := build
UNAME := $(shell uname -s)

WARN := -Wall -Wextra -Werror -Wconversion
CFLAGS := -std=c11 -O2 -ffp-contract=off -fno-fast-math $(WARN)
CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -Werror -Wconversion

CRYPTOPP_PREFIX ?= $(shell if command -v brew >/dev/null 2>&1; then brew --prefix cryptopp; else echo /usr; fi)
ifneq ($(CRYPTOPP_PREFIX),/usr)
CRYPTOPP_CFLAGS := -isystem $(CRYPTOPP_PREFIX)/include
CRYPTOPP_LIBS := -L$(CRYPTOPP_PREFIX)/lib
endif
CRYPTOPP_LIBS += -lcryptopp

# Optional libjpeg (libjpeg-turbo on Homebrew, libjpeg-dev on Debian/Ubuntu).
JPEG_PREFIX ?= $(shell if command -v brew >/dev/null 2>&1; then brew --prefix jpeg-turbo 2>/dev/null; fi)
ifneq ($(wildcard $(JPEG_PREFIX)/include/jpeglib.h),)
JPEG_CFLAGS := -DMU_HAVE_JPEG=1 -isystem $(JPEG_PREFIX)/include
JPEG_LIBS := -L$(JPEG_PREFIX)/lib -ljpeg
else ifneq ($(wildcard /usr/include/jpeglib.h),)
JPEG_CFLAGS := -DMU_HAVE_JPEG=1
JPEG_LIBS := -ljpeg
else
JPEG_CFLAGS := -DMU_HAVE_JPEG=0
JPEG_LIBS :=
endif
ifeq ($(MU_NO_JPEG),1)
JPEG_CFLAGS := -DMU_HAVE_JPEG=0
JPEG_LIBS :=
endif

RECON := ../reconstructed
CORE_SRC := core/mu_bmd.c core/mu_model.c core/mu_meshdraw.c core/mu_image.c core/mu_png.c core/mu_camera.c \
            core/mu_raster.c core/mu_scene.c core/mu_textures.c core/mu_options.c core/mu_character.c \
            core/mu_terrain.c
RECON_SRC := $(RECON)/model-codec/model_codec.c $(RECON)/model-codec/client_lea.c \
             $(RECON)/model-codec/bone_tracks.c $(RECON)/model-codec/pose_builder.c \
             $(RECON)/model-codec/skinning.c $(RECON)/model-codec/character.c $(RECON)/record-math/record_math.c \
             $(RECON)/terrain/terrain.c
CORE_OBJ := $(patsubst core/%.c,$(BUILD)/core/%.o,$(CORE_SRC))
RECON_OBJ := $(patsubst $(RECON)/%.c,$(BUILD)/recon/%.o,$(RECON_SRC))
MODULUS_OBJ := $(BUILD)/modulus.o
LIB := $(BUILD)/libmunative.a
HEADERS := $(wildcard core/*.h) $(wildcard $(RECON)/model-codec/*.h) $(RECON)/record-math/record_math.h \
           $(RECON)/terrain/terrain.h

all: $(BUILD)/mu-render $(BUILD)/mu-terrain $(BUILD)/libmumeshdraw.$(if $(filter Darwin,$(UNAME)),dylib,so)

$(BUILD)/core/%.o: core/%.c $(HEADERS)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $@

# Reconstructed sources are compiled unchanged with their own module's flags.
$(BUILD)/recon/%.o: $(RECON)/%.c $(HEADERS)
	@mkdir -p $(dir $@)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -ffp-contract=off -c $< -o $@

$(MODULUS_OBJ): ../model-recovery/modulus.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CRYPTOPP_CFLAGS) -c $< -o $@

$(LIB): $(CORE_OBJ) $(RECON_OBJ) $(MODULUS_OBJ)
	rm -f $@
	ar rcs $@ $^

$(BUILD)/mu-render: tools/mu_render.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render.c -o $(BUILD)/mu_render.o
	$(CXX) $(BUILD)/mu_render.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

$(BUILD)/mu-terrain: tools/mu_terrain.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_terrain.c -o $(BUILD)/mu_terrain.o
	$(CXX) $(BUILD)/mu_terrain.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

# The mesh-draw module alone, for the Python equivalence tests (ctypes).
$(BUILD)/libmumeshdraw.dylib $(BUILD)/libmumeshdraw.so: core/mu_meshdraw.c core/mu_meshdraw.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared core/mu_meshdraw.c -o $@

# ---- windowed viewer ----
SDL_CONFIG ?= sdl2-config
ifeq ($(UNAME),Darwin)
GL_LIBS := -framework OpenGL
GL_CFLAGS := -DGL_SILENCE_DEPRECATION
else
GL_LIBS := -lGL
GL_CFLAGS :=
endif
VIEWER_SRC := viewer/main.c viewer/gl_backend.c viewer/gl_headless.c

viewer: $(BUILD)/mu-viewer

$(BUILD)/mu-viewer: $(VIEWER_SRC) viewer/gl_backend.h $(LIB)
	@mkdir -p $(BUILD)/viewer
	for f in $(VIEWER_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/viewer/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/viewer/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) $(GL_LIBS) -lm -o $@

clean:
	rm -rf $(BUILD)

.PHONY: all viewer clean
