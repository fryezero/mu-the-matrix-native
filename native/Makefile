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
CORE_SRC := core/mu_bmd.c core/mu_model.c core/mu_meshdraw.c core/mu_meshdraw_case.c core/mu_image.c core/mu_png.c \
            core/mu_camera.c core/mu_raster.c core/mu_scene.c core/mu_textures.c core/mu_options.c core/mu_character.c \
            core/mu_terrain.c core/mu_frame.c core/mu_actor.c core/mu_gif.c \
            core/mu_ui_raster.c core/mu_ui_assets.c core/mu_ui_font.c \
            core/mu_effect.c core/mu_edge.c
RECON_SRC := $(RECON)/model-codec/model_codec.c $(RECON)/model-codec/client_lea.c \
             $(RECON)/model-codec/bone_tracks.c $(RECON)/model-codec/pose_builder.c \
             $(RECON)/model-codec/skinning.c $(RECON)/model-codec/character.c $(RECON)/record-math/record_math.c \
             $(RECON)/terrain/terrain.c \
             $(RECON)/camera/client_camera.c $(RECON)/camera/client_world_camera.c \
             $(RECON)/camera/client_input.c $(RECON)/camera/client_frame.c \
             $(RECON)/actors/actors.c \
             $(RECON)/ui/ui2d.c $(RECON)/ui/ui_text.c $(RECON)/ui/ui_texture.c $(RECON)/ui/ui_login.c \
             $(RECON)/effects/effects.c $(RECON)/effects/effects_json.c
CORE_OBJ := $(patsubst core/%.c,$(BUILD)/core/%.o,$(CORE_SRC))
RECON_OBJ := $(patsubst $(RECON)/%.c,$(BUILD)/recon/%.o,$(RECON_SRC))
MODULUS_OBJ := $(BUILD)/modulus.o
LIB := $(BUILD)/libmunative.a
HEADERS := $(wildcard core/*.h) $(wildcard $(RECON)/model-codec/*.h) $(RECON)/record-math/record_math.h \
           $(RECON)/terrain/terrain.h $(wildcard $(RECON)/camera/*.h) $(wildcard $(RECON)/actors/*.h) \
           $(wildcard $(RECON)/ui/*.h) $(RECON)/effects/effects.h

SHLIB_EXT := $(if $(filter Darwin,$(UNAME)),dylib,so)

# The GDI text boundary uses CoreText on macOS (placeholder font elsewhere).
ifeq ($(UNAME),Darwin)
UI_LIBS := -framework CoreText -framework CoreGraphics -framework CoreFoundation
else
UI_LIBS :=
endif

all: $(BUILD)/mu-render $(BUILD)/mu-terrain $(BUILD)/mu-frame $(BUILD)/mu-effect $(BUILD)/libmumeshdraw.$(SHLIB_EXT) \
     $(BUILD)/mu-proto $(BUILD)/libmuprotocol.$(SHLIB_EXT) $(BUILD)/libmuui.$(SHLIB_EXT) \
     $(BUILD)/mu-data audio

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

$(BUILD)/mu-render: tools/mu_render.c tools/mu_render_ui.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render.c -o $(BUILD)/mu_render.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_ui.c -o $(BUILD)/mu_render_ui.o
	$(CXX) $(BUILD)/mu_render.o $(BUILD)/mu_render_ui.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# The 2D layer alone (reconstruction + software GL + assets), for the Python
# validator and tests (ctypes).
UI_LIB_SRC := core/mu_ui_raster.c core/mu_ui_assets.c core/mu_ui_font.c $(RECON)/ui/ui2d.c \
              $(RECON)/ui/ui_text.c $(RECON)/ui/ui_texture.c $(RECON)/ui/ui_login.c core/mu_png.c
$(BUILD)/libmuui.$(SHLIB_EXT): $(UI_LIB_SRC) $(HEADERS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -fPIC -shared $(UI_LIB_SRC) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/mu-terrain: tools/mu_terrain.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_terrain.c -o $(BUILD)/mu_terrain.o
	$(CXX) $(BUILD)/mu_terrain.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

# Headless frame-loop skeleton (NATIVE-FRAME-001).
$(BUILD)/mu-frame: tools/mu_frame.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_frame.c -o $(BUILD)/mu_frame.o
	$(CXX) $(BUILD)/mu_frame.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

# Effect system driver (NATIVE-FX-001).
$(BUILD)/mu-effect: tools/mu_effect_tool.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_effect_tool.c -o $(BUILD)/mu_effect_tool.o
	$(CXX) $(BUILD)/mu_effect_tool.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

# The mesh-draw module alone, for the Python equivalence tests (ctypes).
$(BUILD)/libmumeshdraw.dylib $(BUILD)/libmumeshdraw.so: core/mu_meshdraw.c core/mu_meshdraw.h core/mu_meshdraw_case.c core/mu_meshdraw_case.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared core/mu_meshdraw.c core/mu_meshdraw_case.c -lm -o $@

# ---- network protocol module (NATIVE-NET-001) ----
# Self-contained: framing + send obfuscation only, no Crypto++ or client bytes.
$(BUILD)/mu-proto: tools/mu_proto.c core/mu_protocol.c core/mu_protocol.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) tools/mu_proto.c core/mu_protocol.c -o $@

$(BUILD)/libmuprotocol.dylib $(BUILD)/libmuprotocol.so: core/mu_protocol.c core/mu_protocol.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared core/mu_protocol.c -o $@

# Data tables (NATIVE-DATA-001): no Crypto++ or image dependencies.
DATA_SRC := core/mu_data.c $(RECON)/data/data_codec.c $(RECON)/data/data_tables.c
DATA_HDR := core/mu_data.h $(RECON)/data/data_codec.h $(RECON)/data/data_tables.h

$(BUILD)/mu-data: tools/mu_data.c $(DATA_SRC) $(DATA_HDR)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) tools/mu_data.c $(DATA_SRC) -o $@

# ---- windowed viewer ----
SDL_CONFIG ?= sdl2-config
ifeq ($(UNAME),Darwin)
GL_LIBS := -framework OpenGL
GLU_LIBS :=
GL_CFLAGS := -DGL_SILENCE_DEPRECATION
else
GL_LIBS := -lGL
GLU_LIBS := -lGLU
GL_CFLAGS :=
endif
VIEWER_SRC := viewer/main.c viewer/gl_backend.c viewer/gl_headless.c viewer/terrain_view.c

viewer: $(BUILD)/mu-viewer $(BUILD)/mu-frame-window
frame-window: $(BUILD)/mu-frame-window

$(BUILD)/mu-viewer: $(VIEWER_SRC) viewer/gl_backend.h $(LIB)
	@mkdir -p $(BUILD)/viewer
	for f in $(VIEWER_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/viewer/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/viewer/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) $(GL_LIBS) -lm -o $@

# Frame-loop skeleton window (SDL2 + OpenGL 2.1), NATIVE-FRAME-001.
FRAME_WINDOW_SRC := frame/main.c viewer/gl_backend.c viewer/gl_headless.c

$(BUILD)/mu-frame-window: $(FRAME_WINDOW_SRC) viewer/gl_backend.h viewer/gl_headless.h $(LIB)
	@mkdir -p $(BUILD)/frame-window
	for f in $(FRAME_WINDOW_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/frame-window/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/frame-window/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) $(GL_LIBS) $(GLU_LIBS) -lm -o $@

# ---- audio (NATIVE-AUDIO-001) ----
# Engine, WAV decoder, script host and the reconstructed client audio logic.
# No Crypto++ or SDL2: the offline tool builds everywhere; MP3/OGG decoding
# uses AudioToolbox on macOS and reports the codec as unavailable elsewhere.
AUDIO_SRC := core/mu_wav.c core/mu_audio.c core/mu_audio_decode.c core/mu_audio_host.c core/mu_png.c
AUDIO_RECON := $(RECON)/audio/audio_system.c $(RECON)/audio/audio_world.c $(RECON)/audio/audio_options.c
AUDIO_HEADERS := core/mu_wav.h core/mu_audio.h core/mu_audio_host.h core/mu_png.h $(RECON)/audio/client_audio.h
AUDIO_OBJ := $(patsubst core/%.c,$(BUILD)/audio/%.o,$(AUDIO_SRC)) $(patsubst $(RECON)/audio/%.c,$(BUILD)/audio/recon_%.o,$(AUDIO_RECON))
ifeq ($(UNAME),Darwin)
AUDIO_LIBS := -framework AudioToolbox -framework CoreFoundation
else
AUDIO_LIBS :=
endif
AUDIO_SO := $(BUILD)/libmuaudio.$(if $(filter Darwin,$(UNAME)),dylib,so)

audio: $(BUILD)/mu-audio $(AUDIO_SO)

$(BUILD)/audio/%.o: core/%.c $(AUDIO_HEADERS)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -fPIC -c $< -o $@

$(BUILD)/audio/recon_%.o: $(RECON)/audio/%.c $(AUDIO_HEADERS)
	@mkdir -p $(dir $@)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -ffp-contract=off -fPIC -c $< -o $@

$(BUILD)/libmuaudio.a: $(AUDIO_OBJ)
	rm -f $@
	ar rcs $@ $^

$(AUDIO_SO): $(AUDIO_OBJ)
	$(CC) -shared $^ $(AUDIO_LIBS) -lm -o $@

$(BUILD)/mu-audio: tools/mu_audio.c $(BUILD)/libmuaudio.a
	$(CC) $(CFLAGS) tools/mu_audio.c $(BUILD)/libmuaudio.a $(AUDIO_LIBS) -lm -o $@

# Live playback through SDL2 audio (optional, like the viewer).
audio-live: $(BUILD)/mu-audio-live

$(BUILD)/mu-audio-live: tools/mu_audio_live.c $(BUILD)/libmuaudio.a
	$(CC) $(CFLAGS) $$($(SDL_CONFIG) --cflags) tools/mu_audio_live.c $(BUILD)/libmuaudio.a \
	  $$($(SDL_CONFIG) --libs) $(AUDIO_LIBS) -lm -o $@

clean:
	rm -rf $(BUILD)

.PHONY: all viewer frame-window audio audio-live clean
