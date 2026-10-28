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
# NATIVE-PERF-003: optimize the native host across translation units while
# retaining the reconstructed binary32 arithmetic contract. The portable
# build keeps its existing flags and does not require an LTO linker plugin.
ifeq ($(UNAME),Darwin)
NATIVE_PERF_LTO ?= 1
endif
ifeq ($(NATIVE_PERF_LTO),1)
NATIVE_OPT := -O3 -flto=thin
else
NATIVE_OPT := -O2
endif
CFLAGS := -std=c11 $(NATIVE_OPT) -ffp-contract=off -fno-fast-math $(WARN)
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
            core/mu_terrain.c core/mu_world_haze.c core/mu_frame.c core/mu_actor.c core/mu_gif.c \
            core/mu_ui_raster.c core/mu_ui_assets.c core/mu_ui_font.c \
            core/mu_effect.c core/mu_effect_scene.c core/mu_edge.c core/mu_walk.c core/mu_renderchar.c core/mu_path.c \
            core/mu_world_actors.c core/mu_charsel.c core/mu_charsel_ui.c core/mu_login.c \
            core/mu_data.c core/mu_hud.c core/mu_hud_tip.c core/mu_objects.c core/mu_objects_icarus.c core/mu_objects_raklion.c core/mu_objects_runtime.c core/mu_objects_runtime_worlds_b.c core/mu_combat.c core/mu_env.c \
            core/mu_particles.c core/mu_joints.c core/mu_lang.c core/mu_items.c \
            core/mu_label.c core/mu_names.c core/mu_world_names.c core/mu_npc.c core/mu_world_players.c fixture/characters_spec.c fixture/monsters_spec.c core/mu_perf.c \
            core/mu_world_helpers.c core/mu_world_pets.c core/mu_quest.c core/mu_skill.c core/mu_map.c core/mu_skill_demo.c core/mu_skill_tree4.c core/mu_world_raven.c core/mu_social.c core/mu_mix.c \
            core/mu_progress.c core/mu_protocol.c \
            core/mu_social_messages.c core/mu_social_item_tables.c core/mu_social_item_view.c
RECON_SRC := $(RECON)/model-codec/model_codec.c $(RECON)/model-codec/client_lea.c \
             $(RECON)/model-codec/bone_tracks.c $(RECON)/model-codec/pose_builder.c \
             $(RECON)/model-codec/skinning.c $(RECON)/model-codec/character.c $(RECON)/record-math/record_math.c \
             $(RECON)/terrain/terrain.c $(RECON)/terrain/world_haze.c $(RECON)/objects/objects.c $(RECON)/objects/icarus.c $(RECON)/objects/loren_market.c $(RECON)/objects/uruk.c $(RECON)/objects/duel_arena.c $(RECON)/objects/world82.c $(RECON)/objects/santa_village.c $(RECON)/objects/vulcanus.c $(RECON)/objects/object_render.c $(wildcard $(RECON)/objects/world_*_visual.c) $(RECON)/objects/world_after.c $(RECON)/objects/devias.c $(RECON)/objects/tarkan.c $(RECON)/objects/elbeland.c $(RECON)/objects/raklion.c $(RECON)/objects/raklion_event.c $(RECON)/objects/world_warp.c $(RECON)/objects/noria.c $(RECON)/objects/login_world.c $(RECON)/objects/charsel_world.c \
             $(RECON)/camera/client_camera.c $(RECON)/camera/client_world_camera.c \
             $(RECON)/camera/client_input.c $(RECON)/camera/client_frame.c \
             $(RECON)/actors/actors.c $(RECON)/actors/viewport_monsters.c $(RECON)/path/client_path.c \
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
             $(RECON)/environment/env_core.c $(RECON)/environment/env_boids.c $(RECON)/environment/env_elbeland.c $(RECON)/environment/env_icarus.c $(RECON)/environment/env_fish.c \
             $(RECON)/environment/env_leaves.c $(RECON)/environment/raklion_snow.c $(RECON)/environment/env_world.c \
             $(RECON)/particles/particles.c $(RECON)/particles/world_flames.c $(RECON)/particles/elbeland.c $(RECON)/particles/sprites.c $(RECON)/particles/shadow.c \
             $(RECON)/particles/visual.c $(RECON)/particles/layout.c \
             $(RECON)/items/ground_items.c $(RECON)/items/item_sets.c \
             $(RECON)/names/overhead_names.c $(RECON)/players/remote_players.c \
             $(RECON)/npc/npc_talk.c $(RECON)/npc/npc_pick.c $(RECON)/npc/npc_dialogue.c \
             $(RECON)/price/item_price.c $(RECON)/helpers/helpers.c $(RECON)/helpers/mount_render.c $(RECON)/helpers/mount_class.c $(RECON)/raven/raven.c $(RECON)/pets/pets.c \
             $(RECON)/quest/quest_data.c $(RECON)/quest/quest_system.c $(RECON)/quest/quest_text.c \
             $(RECON)/quest/quest_ui.c $(RECON)/quest/quest_packets.c $(RECON)/quest/quest_api.c \
             $(RECON)/quest/quest_guide.c $(RECON)/quest/quest_summary.c $(RECON)/quest/quest_move.c \
             $(RECON)/quest/quest_wrap.c $(RECON)/quest/quest_classic.c \
             $(RECON)/skill/skill_table.c $(RECON)/skill/skill_use.c $(RECON)/skill/skill_tooltip.c $(RECON)/skill/skill_list.c \
             $(RECON)/skill/master_tree.c $(RECON)/skill/skill_canuse.c $(RECON)/skill/tree4.c $(RECON)/skill/tree4_ui.c $(RECON)/skill/tree4_side.c \
             $(RECON)/map/map_hud.c $(RECON)/map/map_move.c $(RECON)/map/map_gate.c $(RECON)/social/social.c \
             $(RECON)/mix/mix_rules.c $(RECON)/mix/mix_source.c $(RECON)/mix/mix_manager.c $(RECON)/mix/item_actions.c $(RECON)/mix/item_services.c \
             $(RECON)/progress/progress_calc.c $(RECON)/progress/progress_bar.c $(RECON)/progress/progress_recv.c \
             $(RECON)/progress/progress_window.c $(RECON)/progress/progress_options.c \
             $(RECON)/social/item_options.c $(RECON)/social/item_formula.c $(RECON)/social/item_display.c $(RECON)/social/item_present.c $(RECON)/social/social_packets.c
CORE_OBJ := $(patsubst %.c,$(BUILD)/%.o,$(CORE_SRC))
RECON_OBJ := $(patsubst $(RECON)/%.c,$(BUILD)/recon/%.o,$(RECON_SRC))
MODULUS_OBJ := $(BUILD)/modulus.o
LIB := $(BUILD)/libmunative.a
HEADERS := $(wildcard core/*.h) $(wildcard $(RECON)/model-codec/*.h) $(RECON)/record-math/record_math.h \
           $(RECON)/terrain/terrain.h $(RECON)/terrain/world_haze.h $(RECON)/objects/objects.h $(RECON)/objects/object_render.h $(RECON)/objects/worlds_g.h $(RECON)/objects/worlds_g_internal.h $(RECON)/objects/worlds_i.h $(RECON)/objects/icarus.h $(wildcard $(RECON)/objects/world_visual*.h) $(RECON)/objects/worlds_b.h $(RECON)/objects/world_warp.h $(RECON)/objects/noria.h $(RECON)/objects/worlds_b_internal.h $(RECON)/objects/login_world.h $(RECON)/objects/charsel_world.h $(wildcard $(RECON)/camera/*.h) $(wildcard $(RECON)/actors/*.h) \
           $(wildcard $(RECON)/ui/*.h) $(RECON)/effects/effects.h $(RECON)/effects/effects_internal.h \
           $(RECON)/movement/client_movement.h $(RECON)/path/client_path.h \
           $(wildcard $(RECON)/renderchar/*.h) $(RECON)/charsel/charsel.h $(RECON)/charsel/charsel_gfx.h $(RECON)/charsel/charcreate.h \
           $(wildcard $(RECON)/data/*.h) $(wildcard $(RECON)/hud/*.h) $(RECON)/scene/scene.h \
           $(wildcard $(RECON)/combat/*.h) $(RECON)/joints/joints.h $(RECON)/joints/icarus_joints.inc $(RECON)/particles/icarus_clouds.inc $(RECON)/particles/worlds_l.inc \
           $(RECON)/environment/env.h $(RECON)/environment/env_internal.h \
           $(RECON)/particles/particles.h $(RECON)/particles/world_flames.h $(RECON)/particles/particles_internal.h \
           $(wildcard $(RECON)/items/*.h) \
           $(RECON)/names/overhead_names.h $(RECON)/players/remote_players.h \
           $(wildcard $(RECON)/npc/*.h) $(RECON)/price/item_price.h \
           $(RECON)/helpers/helpers.h $(RECON)/helpers/mount_classes.h $(RECON)/helpers/mount_render.h $(RECON)/helpers/mount_class.h $(RECON)/raven/raven.h $(RECON)/pets/pets.h $(wildcard $(RECON)/quest/*.h) \
           $(wildcard $(RECON)/skill/*.h) $(RECON)/map/map.h $(wildcard $(RECON)/social/*.h) $(wildcard $(RECON)/mix/*.h) \
           $(wildcard $(RECON)/progress/*.h)

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

# Reconstructed sources stay unchanged. Keep their arithmetic flags while
# allowing the native-only ThinLTO build to inline the memory/vector helpers.
$(BUILD)/recon/%.o: $(RECON)/%.c $(HEADERS)
	@mkdir -p $(dir $@)
	$(CC) -std=c11 $(NATIVE_OPT) -Wall -Wextra -Werror -Wconversion -ffp-contract=off -fno-fast-math -c $< -o $@

$(MODULUS_OBJ): ../model-recovery/modulus.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CRYPTOPP_CFLAGS) -c $< -o $@

$(LIB): $(CORE_OBJ) $(RECON_OBJ) $(MODULUS_OBJ) $(BUILD)/data-manifest.o
	rm -f $@
	ar rcs $@ $^

# CHARSEL-RT-001: scene 5 is one module in every front end, with a separate CLI.
CHARSEL_RT_SRC := charsel/charsel_rt.c $(sort $(wildcard charsel/parts/*.c))
CHARSEL_RT_HDR := charsel/mu_charsel_rt.h charsel/charsel_rt_internal.h charsel/charsel_part.h charsel/parts.def
CHARSEL_RT_OBJ := $(patsubst %.c,$(BUILD)/charsel-rt/%.o,$(CHARSEL_RT_SRC))
$(BUILD)/charsel-rt/%.o: %.c $(CHARSEL_RT_HDR) $(HEADERS)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CHARSEL_NO_GL -c $< -o $@

$(BUILD)/mu-render: tools/mu_render.c tools/mu_render_ui.c tools/mu_render_world.c tools/mu_render_world.h charsel/charsel_tool.c $(CHARSEL_RT_OBJ) tools/mu_render_hud.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render.c -o $(BUILD)/mu_render.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_ui.c -o $(BUILD)/mu_render_ui.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_world.c -o $(BUILD)/mu_render_world.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_render_hud.c -o $(BUILD)/mu_render_hud.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CHARSEL_NO_GL -c charsel/charsel_tool.c -o $(BUILD)/mu_render_charsel.o
	$(CXX) $(BUILD)/mu_render.o $(BUILD)/mu_render_ui.o $(BUILD)/mu_render_world.o $(BUILD)/mu_render_charsel.o $(BUILD)/mu_render_hud.o $(CHARSEL_RT_OBJ) $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

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

# ---- WORLD-RT-001: the world runtime (world/mu_world_rt.h) and its command line (world/world_tool.c) ----
# world_rt.c, input.c and parts/*.c (one or two rows of world/parts.def each) are the one world runtime that
# mu-world, mu-walk, mu-client, mu-shell and the test hosts link, built twice: without GL into build/world-rt
# (mu-walk, mu-shell, hosts) and with GL and the GFx layer's headers into build/world-rt-gl (mu-world).
# mu-client and mu-shell compile the same sources through CLIENT_SRC.
WORLD_RT_SRC := world/world_rt.c world/input.c world/parts/terrain.c world/parts/hero.c world/parts/sound.c \
                world/parts/npc.c world/parts/actors.c world/parts/objects.c world/parts/env.c \
                world/parts/particles.c world/parts/combat.c world/parts/progress.c world/parts/items.c \
                world/parts/characters.c world/parts/names.c world/parts/players.c world/parts/social.c world/parts/helpers.c \
                world/parts/haze.c world/parts/map.c world/parts/gfx.c world/parts/skills.c world/parts/marker.c
WORLD_RT_HDR := world/mu_world_rt.h world/world_rt_internal.h world/world_part.h world/parts.def
WORLD_RT_SRC += world/input_keys.c
WORLD_RT_HDR += world/input_keys.h world/input_sdl.h world/time_series.h
WORLD_RT_HDR += fixture/skills_demo.h
WORLD_RT_OBJ := $(patsubst world/%.c,$(BUILD)/world-rt/%.o,$(WORLD_RT_SRC))
WORLD_RT_GL_OBJ := $(patsubst world/%.c,$(BUILD)/world-rt-gl/%.o,$(WORLD_RT_SRC))

$(BUILD)/world-rt/%.o: world/%.c $(WORLD_RT_HDR) $(HEADERS) $(GEN_STAMP) $(LAYOUT_STAMP)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED -DMU_WORLD_NO_GL -c $< -o $@

$(BUILD)/world-rt-gl/%.o: world/%.c $(WORLD_RT_HDR) $(HEADERS) $(GEN_STAMP) $(LAYOUT_STAMP) world/world_gfx.h gfx/mu_gfx_layer.h
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED $(GL_CFLAGS) $(GFX_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $< -o $@

# Walk-around session, headless software build (NATIVE-WORLD-001).
# NATIVE-WORLD-002 links the audio library (in-world sound, WAV output).
$(BUILD)/mu-walk: $(BUILD)/world-rt/world_tool.o $(WORLD_RT_OBJ) $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	$(CXX) $(BUILD)/world-rt/world_tool.o $(WORLD_RT_OBJ) $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) \
	  $(AUDIO_LIBS) $(UI_LIBS) -lm -o $@
# ---- end WORLD-RT-001 block ----

# Click-to-move demonstrator (NATIVE-PATH-001).
$(BUILD)/mu-path: tools/mu_path.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tools/mu_path.c -o $(BUILD)/mu_path.o
	$(CXX) $(BUILD)/mu_path.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@

# Character-select scene, headless software build (NATIVE-CHARSEL-001).
$(BUILD)/mu-charsel: charsel/main.c charsel/charsel_tool.c $(CHARSEL_RT_OBJ) $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CHARSEL_NO_GL -c charsel/main.c -o $(BUILD)/mu_charsel.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_CHARSEL_NO_GL -c charsel/charsel_tool.c -o $(BUILD)/mu_charsel_tool.o
	$(CXX) $(BUILD)/mu_charsel.o $(BUILD)/mu_charsel_tool.o $(CHARSEL_RT_OBJ) $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# RENDER-ITEMS-002b saved-pose and sprite-capacity regression.
$(BUILD)/item-render-host: tests/item_render_host.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $(BUILD)/item_render_host.o
	$(CXX) $(BUILD)/item_render_host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/inventory-skin-host: tests/inventory_skin_host.c world/world_gfx_game.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c core/mu_renderchar.h $(LIB)
	@mkdir -p $(BUILD)/inventory-skin
	for f in tests/inventory_skin_host.c world/world_gfx_game.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c; do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) -DGL_SILENCE_DEPRECATION -c $$f -o $(BUILD)/inventory-skin/$$(basename $$f .c).o || exit; \
	done
	$(CXX) $(BUILD)/inventory-skin/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(GL_LIBS) -lm -o $@

# Synthetic native helper/effect ownership regression host.
$(BUILD)/helper-fx-host: tests/helper_fx_host.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $(BUILD)/helper_fx_host.o
	$(CXX) $(BUILD)/helper_fx_host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/quest-travel-host: tests/quest_travel_host.c $(WORLD_RT_HDR) $(WORLD_RT_OBJ) $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED -DMU_WORLD_NO_GL -c $< -o $(BUILD)/quest_travel_host.o
	$(CXX) $(BUILD)/quest_travel_host.o $(WORLD_RT_OBJ) $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) -lm -o $@

# NATIVE-SKILL-001: the skill book (core/mu_skill) test host.
$(BUILD)/skill-book-host: tests/skill_book_host.c $(LIB) $(BUILD)/libmusession.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tests/skill_book_host.c -o $(BUILD)/skill_book_host.o
	$(CXX) $(BUILD)/skill_book_host.o $(BUILD)/libmusession.a $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

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

# ---- C3/C4 CryptoModule (NET-CRYPTO-001) ----
# native/net/crypto.cpp over Crypto++; a library of its own for the tests and
# scripts/validate_crypto.py (ctypes). Planted mistakes for the validator:
# build/crypto-mutants/libmucrypto_m<k> built with -DMU_CRYPTO_MUTATION=<k>.
CRYPTO_LIB := $(BUILD)/libmucrypto.$(SHLIB_EXT)
all: $(CRYPTO_LIB)
$(CRYPTO_LIB): net/crypto.cpp net/mu_crypto.h
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) $(CRYPTOPP_CFLAGS) -fPIC -shared net/crypto.cpp $(CRYPTOPP_LIBS) -o $@
$(BUILD)/crypto-mutants/libmucrypto_m%.$(SHLIB_EXT): net/crypto.cpp net/mu_crypto.h
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CRYPTOPP_CFLAGS) -DMU_CRYPTO_MUTATION=$* -fPIC -shared net/crypto.cpp $(CRYPTOPP_LIBS) -o $@

# Data tables (NATIVE-DATA-001): no Crypto++ or image dependencies.
DATA_SRC := core/mu_data.c $(RECON)/data/data_codec.c $(RECON)/data/data_tables.c $(RECON)/data/item_attributes.c \
	$(RECON)/data/table_layouts.c
DATA_HDR := core/mu_data.h $(RECON)/data/data_codec.h $(RECON)/data/data_tables.h $(RECON)/data/item_attributes.h \
	$(RECON)/data/table_layouts.h

$(BUILD)/mu-data: tools/mu_data.c $(DATA_SRC) $(DATA_HDR)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) tools/mu_data.c $(DATA_SRC) -o $@

# Lang.mpr tables read from the client; managed exports use the manifest guard.
$(BUILD)/mu-lang: tools/mu_lang_tool.c core/mu_lang.c core/mu_lang.h core/mu_lang_maps.h $(BUILD)/data-manifest.o
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c tools/mu_lang_tool.c -o $(BUILD)/mu_lang_tool.o
	$(CC) $(CFLAGS) -c core/mu_lang.c -o $(BUILD)/mu_lang.o
	$(CXX) $(BUILD)/mu_lang_tool.o $(BUILD)/mu_lang.o $(BUILD)/data-manifest.o $(CRYPTOPP_LIBS) -o $@

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
GFX_SRC := world/world_gfx.c world/world_gfx_game.c gfx/mu_gfx_layer.c world/world_names_gfx.c world/world_gfx_skill.c world/world_gfx_tree.c \
           world/world_gfx_map.c world/world_gfx_options.c world/world_gfx_social.c
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
                 core/mu_world_audio.h $(RECON)/audio/hero_sound.h $(RECON)/audio/audio_registration.inc session/mu_cue.h
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

$(BUILD)/mu-audio: tools/mu_audio.c $(BUILD)/libmuaudio.a $(BUILD)/data-manifest.o
	$(CC) $(CFLAGS) -c tools/mu_audio.c -o $(BUILD)/mu_audio_tool.o
	$(CXX) $(BUILD)/mu_audio_tool.o $(BUILD)/libmuaudio.a $(BUILD)/data-manifest.o $(CRYPTOPP_LIBS) $(AUDIO_LIBS) -lm -o $@

# Live playback through SDL2 audio (optional, like the viewer).
audio-live: $(BUILD)/mu-audio-live

$(BUILD)/mu-audio-live: tools/mu_audio_live.c $(BUILD)/libmuaudio.a $(BUILD)/data-manifest.o
	$(CC) $(CFLAGS) $$($(SDL_CONFIG) --cflags) -c tools/mu_audio_live.c -o $(BUILD)/mu_audio_live.o
	$(CXX) $(BUILD)/mu_audio_live.o $(BUILD)/libmuaudio.a $(BUILD)/data-manifest.o $(CRYPTOPP_LIBS) \
	  $$($(SDL_CONFIG) --libs) $(AUDIO_LIBS) -lm -o $@

# Walk-around window (SDL2 + OpenGL 2.1), NATIVE-WORLD-001.  WORLD-RT-001: the runtime and world_tool.c come
# from build/world-rt-gl; build/world/main.o of an earlier build (world/main.c) is removed first.
WORLD_SRC := viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c $(GFX_SRC)

$(BUILD)/mu-world: $(WORLD_SRC) $(BUILD)/world-rt-gl/world_tool.o $(WORLD_RT_GL_OBJ) viewer/gl_backend.h viewer/gl_batch.h viewer/gl_headless.h world/world_gfx.h gfx/mu_gfx_layer.h gfx/mu_gfx_services.inc gfx/mu_gfx_services_state.h gfx/mu_gfx_sdl.h $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	@mkdir -p $(BUILD)/world
	@rm -f $(BUILD)/world/main.o
	for f in $(WORLD_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED $(GL_CFLAGS) $(GFX_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/world/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/world/*.o $(BUILD)/world-rt-gl/world_tool.o $(WORLD_RT_GL_OBJ) $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) \
	  $(GL_LIBS) $(UI_LIBS) $(AUDIO_LIBS) $(DL_LIBS) -lm -o $@

# Character-select window (SDL2 + OpenGL 2.1), NATIVE-CHARSEL-001.
CHARSEL_SRC := charsel/main.c charsel/charsel_tool.c $(CHARSEL_RT_SRC) viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c

$(BUILD)/mu-charsel-window: $(CHARSEL_SRC) $(CHARSEL_RT_HDR) viewer/gl_backend.h viewer/gl_headless.h $(LIB)
	@mkdir -p $(BUILD)/charsel
	for f in $(CHARSEL_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) $(GL_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f -o $(BUILD)/charsel/$$(basename $$f .c).o || exit 1; \
	done
	$(CXX) $(BUILD)/charsel/*.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) $(GL_LIBS) $(UI_LIBS) -lm -o $@

# ---- mu-client: the client's scene flow, offline (NATIVE-SHELL-001) ----
# client/shell.c runs reconstructed/scene over the character-select and world
# sessions: the world runtime (WORLD-RT-001, world/mu_world_rt.h) and
# charsel/mu_charsel_rt.h. build/mu-shell is the headless
# software build (portable tests), build/mu-client the SDL2 + OpenGL window.
CLIENT_SRC := client/main.c client/shell.c client/offline-session.c $(WORLD_RT_SRC) $(CHARSEL_RT_SRC) \
              charsel/charsel_list_gfx.c charsel/charsel_mugfx.c charsel/charsel_create_gfx.c
CLIENT_HDR := gfx/mu_gfx_services.inc gfx/mu_gfx_services_state.h client/shell.h client/offline-session.h $(WORLD_RT_HDR) $(CHARSEL_RT_HDR) \
              charsel/charsel_list_gfx.h charsel/charsel_mugfx.h charsel/charsel_create_gfx.h

$(BUILD)/mu-shell: $(CLIENT_SRC) $(CLIENT_HDR) $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	@mkdir -p $(BUILD)/shell
	@rm -f $(BUILD)/shell/*.o # CHARSEL-RT-001: migrate the old basename objects
	for f in $(CLIENT_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED -DMU_CLIENT_NO_GL -DMU_WORLD_NO_GL -DMU_CHARSEL_NO_GL -c $$f \
	    -o $(BUILD)/shell/$$(echo "$${f%.c}" | tr / _).o || exit 1; \
	done
	$(CXX) $(BUILD)/shell/*.o $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) $(DL_LIBS) -lm -o $@

CLIENT_GL_SRC := $(CLIENT_SRC) login/login_gl.c viewer/gl_backend.c viewer/gl_batch.c viewer/gl_headless.c viewer/ui_gl.c $(GFX_SRC)

$(BUILD)/mu-client: $(CLIENT_GL_SRC) $(CLIENT_HDR) login/login_gl.h viewer/gl_backend.h viewer/gl_batch.h viewer/gl_headless.h viewer/ui_gl.h $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	@mkdir -p $(BUILD)/client
	@rm -f $(BUILD)/client/*.o # CHARSEL-RT-001: migrate the old basename objects
	for f in $(CLIENT_GL_SRC); do \
	  $(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED $(GL_CFLAGS) $(GFX_CFLAGS) $$($(SDL_CONFIG) --cflags) -c $$f \
	    -o $(BUILD)/client/$$(echo "$${f%.c}" | tr / _).o || exit 1; \
	done
	$(CXX) $(BUILD)/client/*.o $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $$($(SDL_CONFIG) --libs) \
	  $(GL_LIBS) $(GLU_LIBS) $(UI_LIBS) $(AUDIO_LIBS) $(DL_LIBS) -lm -o $@

# ---- Mu The Matrix Native Preview.app (NATIVE-APP-001): mu-client as an ad-hoc signed macOS app ----
# app/Makefile: launcher, network guard, bundled dylibs, optional libmugfx (MUGFX_LIB=...).
preview-app: $(BUILD)/mu-client
	$(MAKE) -C app

# ---- NET-LINK-001: the transport, links and connections (native/net) ----
# mu_protocol.c is in CORE_SRC since NET-LINK-001 (no code change; verify-protocol-cbmc reran).
# build/libmunet: the net layer alone, for native/tests/test_transport.py (ctypes).
NET_SRC := net/transport.c net/transport_lock.c net/transport_sockets.c net/transport_replay.c net/conn.c
NET_HDR := $(wildcard net/*.h) core/mu_protocol.h
NET_SO := $(BUILD)/libmunet.$(SHLIB_EXT)

all: $(NET_SO)

$(NET_SO): $(NET_SRC) core/mu_protocol.c $(NET_HDR)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -fPIC -shared $(NET_SRC) core/mu_protocol.c -o $@

# ---- SESSION-CORE-001: the session core and its domains (native/session) ----
# scripts/gen_domains.py generates the domain, route, intent and behaviour lists into build/gen and
# fails the build on a broken rule (a duplicate route binding, an unrouted intent kind, ...). Two
# variants of the objects: dev (MU_SESSION_SEED and MU_SESSION_AUDIT, fixture included) for
# mu-session and the tests, and product (neither, no fixture), whose library must carry no seed or
# fixture symbol (native/tests/test_session_core.py).
PYTHON ?= python3
# The generator needs only the standard library. A relative PYTHON (make test PYTHON=tools/python/bin/python
# from the repository root) is resolved as given or relative to the root; otherwise python3.
GEN_PYTHON := $(firstword $(wildcard $(PYTHON) ../$(PYTHON)) $(if $(findstring /,$(PYTHON)),python3,$(PYTHON)))
GEN := $(BUILD)/gen
GEN_STAMP := $(GEN)/.stamp
GEN_INPUTS := ../scripts/gen_domains.py $(wildcard session/domains/*) $(wildcard session/ops/*.ops) \
              $(wildcard net/dispatch.def net/dispatch.seed.def net/ignore.def) $(wildcard fixture/behaviors/*.c)
SESSION_SRC := session/session.c session/dispatch.c session/cues.c session/lease.c session/journal.c \
               $(wildcard session/domains/*.c)
FIXTURE_SRC := fixture/fixture.c fixture/skills_model.c $(wildcard fixture/behaviors/*.c)
SESSION_HDR := $(NET_HDR) $(wildcard session/*.h session/domains/*.h fixture/*.h) $(RECON)/progress/progress.h core/mu_world_players.h fixture/characters_demo.h
SESSION_CFLAGS := -I $(GEN) -I session -Werror=initializer-overrides
LAYOUT_STAMP := $(GEN)/.layout-stamp
LAYOUT_INPUTS := ../scripts/gen_layout.py $(wildcard session/layout/*.def)

$(LAYOUT_STAMP): $(LAYOUT_INPUTS)
	@mkdir -p $(GEN)
	$(GEN_PYTHON) ../scripts/gen_layout.py --out $(GEN)
	@touch $@

SESSION_DEV_OBJ := $(patsubst %.c,$(BUILD)/sdev/%.o,$(NET_SRC) $(SESSION_SRC) $(FIXTURE_SRC))
SESSION_PROD_OBJ := $(patsubst %.c,$(BUILD)/sprod/%.o,$(NET_SRC) $(SESSION_SRC))

all: $(BUILD)/libmusession.a $(BUILD)/libmusession_product.a

$(GEN_STAMP): $(GEN_INPUTS)
	@mkdir -p $(GEN)
	$(GEN_PYTHON) ../scripts/gen_domains.py --out $(GEN)
	@touch $@

$(BUILD)/sdev/%.o: %.c $(SESSION_HDR) $(GEN_STAMP) $(LAYOUT_STAMP)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(SESSION_CFLAGS) -DMU_SESSION_SEED -DMU_SESSION_AUDIT -c $< -o $@

$(BUILD)/sprod/%.o: %.c $(SESSION_HDR) $(GEN_STAMP) $(LAYOUT_STAMP)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(SESSION_CFLAGS) -c $< -o $@

$(BUILD)/libmusession.a: $(SESSION_DEV_OBJ)
	rm -f $@
	ar rcs $@ $^

$(BUILD)/libmusession_product.a: $(SESSION_PROD_OBJ)
	rm -f $@
	ar rcs $@ $^

# ---- FIXTURE-001: the fixture server (native/fixture) and the session CLI (native/tools/mu_session.c) ----
all: $(BUILD)/mu-session

$(BUILD)/mu-session: tools/mu_session.c $(BUILD)/libmusession.a $(LIB) $(SESSION_HDR) $(GEN_STAMP) $(LAYOUT_STAMP)
	$(CC) $(CFLAGS) $(SESSION_CFLAGS) -DMU_SESSION_SEED -c tools/mu_session.c -o $(BUILD)/mu_session.o
	$(CC) $(BUILD)/mu_session.o $(BUILD)/libmusession.a $(LIB) $(UI_LIBS) -lm -o $@

clean:
	rm -rf $(BUILD)

.PHONY: all viewer frame-window world charsel client audio audio-live clean preview-app

# SESSION-QUEST-001: offline tools now use the dev session/fixture library.
CFLAGS += -I build/gen -I session
$(BUILD)/mu-walk $(BUILD)/mu-world $(BUILD)/mu-shell $(BUILD)/mu-client $(BUILD)/quest-travel-host: $(BUILD)/libmusession_world.a
$(WORLD_RT_OBJ) $(WORLD_RT_GL_OBJ): $(GEN_STAMP)
QUEST_LIB_SRC := $(RECON)/items/ground_items.c $(RECON)/movement/client_movement.c fixture/monsters_spec.c $(RECON)/actors/viewport_monsters.c $(RECON)/actors/actors.c $(RECON)/model-codec/skinning.c $(RECON)/model-codec/pose_builder.c $(RECON)/model-codec/bone_tracks.c $(RECON)/record-math/record_math.c fixture/characters_spec.c $(RECON)/players/remote_players.c $(SESSION_SRC) $(NET_SRC) $(FIXTURE_SRC) $(wildcard $(RECON)/quest/quest_*.c) core/mu_protocol.c $(wildcard $(RECON)/progress/progress_*.c) core/mu_lang.c
$(BUILD)/libmuquest.dylib $(BUILD)/libmuquest.so: $(QUEST_LIB_SRC) $(LIB) $(GEN_STAMP) $(LAYOUT_STAMP)
	$(CC) $(CFLAGS) $(SESSION_CFLAGS) -DMU_SESSION_SEED -shared -fPIC $(QUEST_LIB_SRC) $(LIB) $(UI_LIBS) -lm -o $@

# Offline app keeps its no-network-import contract; TCP fixture serving stays in mu-session.
$(BUILD)/sdev/fixture/world_fixture.o: fixture/fixture.c $(SESSION_HDR) $(GEN_STAMP) $(LAYOUT_STAMP)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(SESSION_CFLAGS) -DMU_SESSION_SEED -DMU_SESSION_AUDIT -DMU_FIXTURE_NO_TCP -c $< -o $@
$(BUILD)/libmusession_world.a: $(filter-out $(BUILD)/sdev/fixture/fixture.o,$(SESSION_DEV_OBJ)) $(BUILD)/sdev/fixture/world_fixture.o
	rm -f $@
	ar rcs $@ $^

# DATA-ACQ-004: shared portable manifest validator and acquisition helper.
all: $(BUILD)/mu-native-data
$(BUILD)/data-manifest.o: data/manifest.cpp data/manifest.h
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) $(CRYPTOPP_CFLAGS) -c $< -o $@
$(BUILD)/mu-native-data: data/manifest.cpp data/manifest.h
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) $(CRYPTOPP_CFLAGS) -DMU_MANIFEST_TOOL $< $(CRYPTOPP_LIBS) -o $@

.PHONY: layout
layout: $(LAYOUT_STAMP)

$(BUILD)/core/mu_world_players.o: core/mu_world_players.c $(HEADERS) $(GEN_STAMP) $(LAYOUT_STAMP)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c core/mu_world_players.c -o $@

$(BUILD)/fixture/%.o: fixture/%.c $(HEADERS)
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $@

$(WORLD_RT_OBJ) $(WORLD_RT_GL_OBJ): $(GEN_STAMP) $(LAYOUT_STAMP) $(SESSION_HDR)

# Core facades consume session headers too, including generated intents and layouts.
$(CORE_OBJ): $(GEN_STAMP) $(LAYOUT_STAMP) $(SESSION_HDR)


$(BUILD)/icarus-host: tests/icarus_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/icarus-host.o
	$(CXX) $(BUILD)/icarus-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/worlds-e-host: tests/worlds_e_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/worlds-e-host.o
	$(CXX) $(BUILD)/worlds-e-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@


$(BUILD)/world-haze-host: tests/world_haze_host.c $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $(BUILD)/world-haze-host.o
	$(CXX) $(BUILD)/world-haze-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) -lm -o $@
# VIEWPORT-MONSTER-001: decoded-record -> model/effect cache lifecycle.
$(BUILD)/monsters-lifecycle-host: tests/monsters_lifecycle_host.c $(WORLD_RT_HDR) $(WORLD_RT_OBJ) $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $(BUILD)/monsters_lifecycle_host.o
	$(CXX) $(BUILD)/monsters_lifecycle_host.o $(WORLD_RT_OBJ) $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) -lm -o $@

$(BUILD)/worlds-g-host: tests/worlds_g_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/worlds-g-host.o
	$(CXX) $(BUILD)/worlds-g-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/worlds-h-host: tests/worlds_h_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/worlds-h-host.o
	$(CXX) $(BUILD)/worlds-h-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# Core consumers include the generated public domain and intent headers.
$(CORE_OBJ): $(GEN_STAMP) $(LAYOUT_STAMP)

$(BUILD)/worlds-i-host: tests/worlds_i_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/worlds-i-host.o
	$(CXX) $(BUILD)/worlds-i-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

# SESSION-GLOBALS-001: real session/world tool entries, twice without exec.
$(BUILD)/session-repeat-host: tests/session_repeat_host.c tools/mu_session.c $(BUILD)/libmusession.a $(LIB)
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED -Dmain=mu_session_tool_main -c tools/mu_session.c -o $(BUILD)/session_repeat_tool.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c tests/session_repeat_host.c -o $(BUILD)/session_repeat_host.o
	$(CXX) $(BUILD)/session_repeat_host.o $(BUILD)/session_repeat_tool.o $(BUILD)/libmusession.a $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/world-repeat-host: tests/session_repeat_host.c world/world_tool.c $(WORLD_RT_HDR) $(WORLD_RT_OBJ) $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED -DMU_WORLD_NO_GL -Dmain=mu_world_tool_main -c world/world_tool.c -o $(BUILD)/world_repeat_tool.o
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DREPEAT_WORLD -c tests/session_repeat_host.c -o $(BUILD)/world_repeat_host.o
	$(CXX) $(BUILD)/world_repeat_host.o $(BUILD)/world_repeat_tool.o $(WORLD_RT_OBJ) $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) -lm -o $@

$(BUILD)/globals-owner-host: tests/globals_owner_host.c $(WORLD_RT_HDR) $(WORLD_RT_OBJ) $(LIB) $(BUILD)/libmuaudio.a $(BUILD)/libmusession_world.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -DMU_SESSION_SEED -DMU_WORLD_NO_GL -c $< -o $(BUILD)/globals_owner_host.o
	$(CXX) $(BUILD)/globals_owner_host.o $(WORLD_RT_OBJ) $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) -lm -o $@

$(BUILD)/particle-consumers-host: tests/particle_consumers_host.c $(LIB) $(HEADERS) $(BUILD)/libmusession_world.a $(BUILD)/libmuaudio.a
	$(CC) $(CFLAGS) $(JPEG_CFLAGS) -c $< -o $(BUILD)/particle_consumers_host.o
	$(CXX) $(BUILD)/particle_consumers_host.o $(BUILD)/libmusession_world.a $(LIB) $(BUILD)/libmuaudio.a $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) $(AUDIO_LIBS) -lm -o $@

$(BUILD)/worlds-j-host: tests/worlds_j_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/worlds-j-host.o
	$(CXX) $(BUILD)/worlds-j-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@

$(BUILD)/worlds-l-host: tests/worlds_l_host.c $(LIB) $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $(BUILD)/worlds-l-host.o
	$(CXX) $(BUILD)/worlds-l-host.o $(LIB) $(CRYPTOPP_LIBS) $(JPEG_LIBS) $(UI_LIBS) -lm -o $@
