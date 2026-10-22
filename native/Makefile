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
            core/mu_effect.c core/mu_effect_scene.c core/mu_edge.c core/mu_walk.c core/mu_renderchar.c core/mu_path.c \
            core/mu_world_actors.c core/mu_charsel.c core/mu_charsel_ui.c core/mu_login.c \
            core/mu_data.c core/mu_hud.c core/mu_hud_tip.c core/mu_objects.c core/mu_objects_runtime.c core/mu_combat.c core/mu_env.c \
            core/mu_particles.c core/mu_joints.c core/mu_lang.c core/mu_items.c \
            core/mu_label.c core/mu_names.c core/mu_world_names.c core/mu_npc.c core/mu_world_players.c core/mu_perf.c \
            core/mu_world_helpers.c core/mu_quest.c core/mu_skill.c core/mu_map.c
RECON_SRC := $(RECON)/model-codec/model_codec.c $(RECON)/model-codec/client_lea.c \
             $(RECON)/model-codec/bone_tracks.c $(RECON)/model-codec/pose_builder.c \
             $(RECON)/model-codec/skinning.c $(RECON)/model-codec/character.c $(RECON)/record-math/record_math.c \
             $(RECON)/terrain/terrain.c $(RECON)/objects/objects.c $(RECON)/objects/object_render.c $(RECON)/objects/login_world.c $(RECON)/objects/charsel_world.c \
             $(RECON)/camera/client_camera.c $(RECON)/camera/client_world_camera.c \
             $(RECON)/camera/client_input.c $(RECON)/camera/client_frame.c \
             $(RECON)/actors/actors.c $(RECON)/path/client_path.c \
             $(RECON)/ui/ui2d.c $(RECON)/ui/ui_text.c $(RECON)/ui/ui_texture.c $(RECON)/ui/ui_login.c \
             $(RECON)/ui/ui_widget.c $(RECON)/ui/ui_server.c $(RECON)/ui/ui_credit.c $(RECON)/ui/ui_charsel.c \
             $(RECON)/ui/ui_loading.c $(RECON)/scene/scene.c \
             $(RECON)/effects/effects.c $(RECON)/effects/effects_json.c $(RECON)/effects/effects_tree.c \
             $(RECON)/movement/client_movement.c \
             $(RECON)/renderchar/renderchar.c $(RECON)/charsel/charsel.c $(RECON)/charsel/charsel_gfx.c $(RECON)/charsel/charcreate.c \
             $(RECON)/data/data_codec.c $(RECON)/data/data_tables.c $(RECON)/data/item_attributes.c \
             $(RECON)/data/table_layouts.c \
             $(RECON)/hud/inv_grid.c $(RECON)/hud/item_slots.c $(RECON)/hud/item_pass.c \
             $(RECON)/hud/tooltip_html.c $(RECON)/hud/tooltip_format.c \
             $(RECON)/combat/combat.c $(RECON)/combat/skill_fx.c $(RECON)/joints/joints.c \
             $(RECON)/environment/env_core.c $(RECON)/environment/env_boids.c $(RECON)/environment/env_fish.c \
             $(RECON)/environment/env_leaves.c $(RECON)/environment/env_world.c \
             $(RECON)/particles/particles.c $(RECON)/particles/sprites.c $(RECON)/particles/shadow.c \
             $(RECON)/particles/visual.c $(RECON)/particles/layout.c \
             $(RECON)/items/ground_items.c $(RECON)/items/item_sets.c \
             $(RECON)/names/overhead_names.c $(RECON)/players/remote_players.c \
             $(RECON)/npc/npc_talk.c $(RECON)/npc/npc_pick.c $(RECON)/npc/npc_dialogue.c \
             $(RECON)/price/item_price.c $(RECON)/helpers/helpers.c \
             $(RECON)/quest/quest_data.c $(RECON)/quest/quest_system.c $(RECON)/quest/quest_text.c \
             $(RECON)/quest/quest_ui.c $(RECON)/quest/quest_packets.c $(RECON)/quest/quest_api.c \
             $(RECON)/skill/skill_table.c $(RECON)/skill/skill_use.c $(RECON)/skill/skill_tooltip.c \
             $(RECON)/map/map_hud.c $(RECON)/map/map_move.c $(RECON)/map/map_gate.c
CORE_OBJ := $(patsubst core/%.c,$(BUILD)/core/%.o,$(CORE_SRC))
RECON_OBJ := $(patsubst $(RECON)/%.c,$(BUILD)/recon/%.o,$(RECON_SRC))
MODULUS_OBJ := $(BUILD)/modulus.o
LIB := $(BUILD)/libmunative.a
HEADERS := $(wildcard core/*.h) $(wildcard $(RECON)/model-codec/*.h) $(RECON)/record-math/record_math.h \
           $(RECON)/terrain/terrain.h $(RECON)/objects/objects.h $(RECON)/objects/object_render.h $(RECON)/objects/login_world.h $(RECON)/objects/charsel_world.h $(wildcard $(RECON)/camera/*.h) $(wildcard $(RECON)/actors/*.h) \
           $(wildcard $(RECON)/ui/*.h) $(RECON)/effects/effects.h $(RECON)/effects/effects_internal.h \
           $(RECON)/movement/client_movement.h $(RECON)/path/client_path.h \
           $(wildcard $(RECON)/renderchar/*.h) $(RECON)/charsel/charsel.h $(RECON)/charsel/charsel_gfx.h $(RECON)/charsel/charcreate.h \
           $(wildcard $(RECON)/data/*.h) $(wildcard $(RECON)/hud/*.h) $(RECON)/scene/scene.h \
           $(wildcard $(RECON)/combat/*.h) $(RECON)/joints/joints.h \
           $(RECON)/environment/env.h $(RECON)/environment/env_internal.h \
           $(RECON)/particles/particles.h $(RECON)/particles/particles_internal.h \
           $(wildcard $(RECON)/items/*.h) \
           $(RECON)/names/overhead_names.h $(RECON)/players/remote_players.h \
           $(wildcard $(RECON)/npc/*.h) $(RECON)/price/item_price.h \
           $(RECON)/helpers/helpers.h $(RECON)/helpers/mount_classes.h $(wildcard $(RECON)/quest/*.h) \
           $(wildcard $(RECON)/skill/*.h) $(RECON)/map/map.h

SHLIB_EXT := $(if $(filter Darwin,$(UNAME)),dylib,so)

# The GDI text boundary uses CoreText on macOS (placeholder font elsewhere).
ifeq ($(UNAME),Darwin)
UI_LIBS := -framework CoreText -framework CoreGraphics -framework CoreFoundation
else
UI_LIBS :=
endif

all: $(BUILD)/mu-render $(BUILD)/mu-terrain $(BUILD)/mu-frame $(BUILD)/mu-effect $(BUILD)/libmumeshdraw.$(SHLIB_EXT) \
     $(BUILD)/mu-proto $(BUILD)/libmuprotocol.$(SHLIB_EXT) $(BUILD)/libmuui.$(SHLIB_EXT) $(BUILD)/libmuquest.$(SHLIB_EXT) \
     $(BUILD)/mu-data $(BUILD)/mu-walk $(BUILD)/mu-path $(BUILD)/mu-charsel $(BUILD)/mu-shell $(BUILD)/mu-lang audio \
     $(BUILD)/skill-book-host

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

$(BUILD)/mu-render: tools/mu_render.c tools/mu_render_ui.c tools/mu_render_world.c tools/mu_render_world.h charsel/main.c tools/mu_render_hud.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render.c -o $(BUILD)/mu_render.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_ui.c -o $(BUILD)/mu_render_ui.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_world.c -o $(BUILD)/mu_render_world.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_hud.c -o $(BUILD)/mu_render_hud.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CHARSEL_NO_GL -DMU_CHARSEL_TOOL_ONLY -c charsel/main.c -o $(BUILD)/mu_render_charsel.o
	$(CXX) $(BUILD)/mu_render.o $(BUILD)/mu_render_ui.o $(BUILD)/mu_render_world.o $(BUILD)/mu_render_charsel.o $(BUILD)/mu_render_hud.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# The 2D layer alone (reconstruction + software GL + assets), for the Python
# validator and tests (ctypes).
UI_LIB_SRC := core/mu_ui_raster.c core/mu_ui_assets.c core/mu_ui_font.c $(RECON)/ui/ui2d.c \
              $(RECON)/ui/ui_text.c $(RECON)/ui/ui_texture.c $(RECON)/ui/ui_login.c core/mu_png.c \
              $(RECON)/ui/ui_widget.c $(RECON)/ui/ui_server.c $(RECON)/ui/ui_credit.c $(RECON)/ui/ui_charsel.c \
              $(RECON)/ui/ui_loading.c
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

# Walk-around session, headless software build (NATIVE-WORLD-001).
# NATIVE-WORLD-002 links the audio library (in-world sound, WAV output).
$(BUILD)/mu-walk: world/main.c $(LIB) $(BUILD)/libmuaudio.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_WORLD_NO_GL -c world/main.c -o $(BUILD)/mu_walk.o
	$(CXX) $(BUILD)/mu_walk.o $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) -lm -o $@
	$(CXX) $(BUILD)/mu_walk.o $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(AUDIO_LIBS) $(UI_LIBS) -lm -o $@

# Click-to-move demonstrator (NATIVE-PATH-001).
$(BUILD)/mu-path: tools/mu_path.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_path.c -o $(BUILD)/mu_path.o
	$(CXX) $(BUILD)/mu_path.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

# Character-select scene, headless software build (NATIVE-CHARSEL-001).
$(BUILD)/mu-charsel: charsel/main.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CHARSEL_NO_GL -c charsel/main.c -o $(BUILD)/mu_charsel.o
	$(CXX) $(BUILD)/mu_charsel.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# NATIVE-SKILL-001: the skill book (core/mu_skill) test host.
$(BUILD)/skill-book-host: tests/skill_book_host.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tests/skill_book_host.c -o $(BUILD)/skill_book_host.o
	$(CXX) $(BUILD)/skill_book_host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# The mesh-draw module alone, for the Python equivalence tests (ctypes).
$(BUILD)/libmumeshdraw.dylib $(BUILD)/libmumeshdraw.so: core/mu_meshdraw.c core/mu_meshdraw.h core/mu_meshdraw_case.c core/mu_meshdraw_case.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared core/mu_meshdraw.c core/mu_meshdraw_case.c -lm -o $@

# ---- network protocol module (NATIVE-NET-001) ----
# Self-contained: framing + send obfuscation only, no Crypto++ or client bytes.
$(BUILD)/mu-proto: tools/mu_proto.c core/mu_protocol.c core/mu_protocol.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) tools/mu_proto.c core/mu_protocol.c -o $@

# NATIVE-QUEST-001: the quest session (core/mu_quest over reconstructed/quest) for the tests (ctypes).
QUEST_LIB_SRC := core/mu_quest.c $(wildcard $(RECON)/quest/quest_*.c)
$(BUILD)/libmuquest.dylib $(BUILD)/libmuquest.so: $(QUEST_LIB_SRC) core/mu_quest.h $(wildcard $(RECON)/quest/*.h)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared $(QUEST_LIB_SRC) -o $@

$(BUILD)/libmuprotocol.dylib $(BUILD)/libmuprotocol.so: core/mu_protocol.c core/mu_protocol.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared core/mu_protocol.c -o $@

# Data tables (NATIVE-DATA-001): no Crypto++ or image dependencies.
DATA_SRC := core/mu_data.c $(RECON)/data/data_codec.c $(RECON)/data/data_tables.c $(RECON)/data/item_attributes.c \
	$(RECON)/data/table_layouts.c
DATA_HDR := core/mu_data.h $(RECON)/data/data_codec.h $(RECON)/data/data_tables.h $(RECON)/data/item_attributes.h \
	$(RECON)/data/table_layouts.h

$(BUILD)/mu-data: tools/mu_data.c $(DATA_SRC) $(DATA_HDR)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) tools/mu_data.c $(DATA_SRC) -o $@

# Lang.mpr tables read from the client (NATIVE-LANG-001): no other dependency.
$(BUILD)/mu-lang: tools/mu_lang_tool.c core/mu_lang.c core/mu_lang.h core/mu_lang_maps.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) tools/mu_lang_tool.c core/mu_lang.c -o $@

# ---- windowed viewer ----
SDL_CONFIG ?= sdl2-config
ifeq ($(UNAME),Darwin)
GL_LIBS := -framework OpenGL
GLU_LIBS :=
GL_CFLAGS := -DGL_SILENCE_DEPRECATION
DL_LIBS :=
else
GL_LIBS := -lGL
GLU_LIBS := -lGLU
GL_CFLAGS :=
DL_LIBS := -ldl
endif
# NATIVE-GFX-002: the GFx layer (loads libmugfx at run time) for mu-world/mu-client.
GFX_SRC := world/world_gfx.c world/world_gfx_game.c gfx/mu_gfx_layer.c world/world_names_gfx.c world/world_gfx_skill.c \
           world/world_gfx_map.c
GFX_CFLAGS := -I gfx -I $(RECON)/hud
VIEWER_SRC := viewer/main.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c viewer/terrain_view.c

viewer: $(BUILD)/mu-viewer $(BUILD)/mu-frame-window $(BUILD)/mu-world $(BUILD)/mu-charsel-window $(BUILD)/mu-client
frame-window: $(BUILD)/mu-frame-window
world: $(BUILD)/mu-world
charsel: $(BUILD)/mu-charsel-window
client: $(BUILD)/mu-client

$(BUILD)/mu-viewer: $(VIEWER_SRC) viewer/gl_backend.h $(LIB)
	@mkdir -p $(BUILD)/viewer
	for f in $(VIEWER_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/viewer/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/viewer/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) $(GL_LIBS) -lm -o $@

# Frame-loop skeleton window (SDL2 + OpenGL 2.1), NATIVE-FRAME-001.
FRAME_WINDOW_SRC := frame/main.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c

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
AUDIO_SRC := core/mu_wav.c core/mu_audio.c core/mu_audio_decode.c core/mu_audio_host.c core/mu_png.c \
             core/mu_world_audio.c
AUDIO_RECON := $(RECON)/audio/audio_system.c $(RECON)/audio/audio_world.c $(RECON)/audio/audio_options.c \
               $(RECON)/audio/hero_sound.c
AUDIO_HEADERS := core/mu_wav.h core/mu_audio.h core/mu_audio_host.h core/mu_png.h $(RECON)/audio/client_audio.h \
                 core/mu_world_audio.h $(RECON)/audio/hero_sound.h
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

# Walk-around window (SDL2 + OpenGL 2.1), NATIVE-WORLD-001.
WORLD_SRC := world/main.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c $(GFX_SRC)

$(BUILD)/mu-world: $(WORLD_SRC) viewer/gl_backend.h viewer/gl_batch.h viewer/gl_headless.h world/world_gfx.h gfx/mu_gfx_layer.h gfx/mu_gfx_sdl.h $(LIB) $(BUILD)/libmuaudio.a
	@mkdir -p $(BUILD)/world
	for f in $(WORLD_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $(GFX_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/world/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/world/*.o $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) \
	  $(GL_LIBS) $(UI_LIBS) $(AUDIO_LIBS) $(DL_LIBS) -lm -o $@

# Character-select window (SDL2 + OpenGL 2.1), NATIVE-CHARSEL-001.
CHARSEL_SRC := charsel/main.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c

$(BUILD)/mu-charsel-window: $(CHARSEL_SRC) viewer/gl_backend.h viewer/gl_headless.h $(LIB)
	@mkdir -p $(BUILD)/charsel
	for f in $(CHARSEL_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/charsel/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/charsel/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) $(GL_LIBS) $(UI_LIBS) -lm -o $@

# ---- mu-client: the client's scene flow, offline (NATIVE-SHELL-001) ----
# client/shell.c runs reconstructed/scene over the character-select and world
# sessions, which world/world_embed.c and charsel/charsel_embed.c compile from
# world/main.c and charsel/main.c unchanged. build/mu-shell is the headless
# software build (portable tests), build/mu-client the SDL2 + OpenGL window.
CLIENT_SRC := client/main.c client/shell.c client/offline-session.c world/world_embed.c charsel/charsel_embed.c \
              charsel/charsel_list_gfx.c charsel/charsel_mugfx.c charsel/charsel_create_gfx.c
CLIENT_HDR := client/shell.h client/offline-session.h world/world_embed.h charsel/charsel_embed.h world/main.c charsel/main.c \
              charsel/charsel_list_gfx.h charsel/charsel_mugfx.h charsel/charsel_create_gfx.h

$(BUILD)/mu-shell: $(CLIENT_SRC) $(CLIENT_HDR) $(LIB) $(BUILD)/libmuaudio.a
	@mkdir -p $(BUILD)/shell
	for f in $(CLIENT_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CLIENT_NO_GL -DMU_WORLD_NO_GL -DMU_CHARSEL_NO_GL -c $$f \
	    -o $(BUILD)/shell/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/shell/*.o $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) $(DL_LIBS) -lm -o $@

CLIENT_GL_SRC := $(CLIENT_SRC) login/login_gl.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c viewer/ui_gl.c $(GFX_SRC)

$(BUILD)/mu-client: $(CLIENT_GL_SRC) $(CLIENT_HDR) login/login_gl.h viewer/gl_backend.h viewer/gl_batch.h viewer/gl_headless.h viewer/ui_gl.h $(LIB) $(BUILD)/libmuaudio.a
	@mkdir -p $(BUILD)/client
	for f in $(CLIENT_GL_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $(GFX_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f \
	    -o $(BUILD)/client/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/client/*.o $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) \
	  $(GL_LIBS) $(GLU_LIBS) $(UI_LIBS) $(AUDIO_LIBS) $(DL_LIBS) -lm -o $@

# ---- Mu The Matrix Native Preview.app (NATIVE-APP-001): mu-client as an ad-hoc signed macOS app ----
# app/Makefile: launcher, network guard, bundled dylibs, optional libmugfx (MUGFX_LIB=...).
preview-app: $(BUILD)/mu-client
	$(MAKE) -C app

clean:
	rm -rf $(BUILD)

.PHONY: all viewer frame-window world charsel client audio audio-live clean preview-app
