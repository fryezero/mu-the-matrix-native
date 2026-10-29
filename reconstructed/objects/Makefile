CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libobjects.$(SUFFIX)

all: $(LIB)

# The model-codec v12 decoder is linked in so the validator and tests decode
# through the same authored routine the native module uses. The object
# render routines (object_render.c, NATIVE-OBJECTS-002) use the terrain's
# TestFrustrum2D and record-math's AngleMatrix/VectorRotate. charsel_world.c is the
# character-select scene's handler (NATIVE-CHARSEL-002).
SOURCES := texture_lookup.c kanturu_underground.c ignis_volcano.c old_kethotum.c burning_kethotum.c bloody_tarkan.c abyss_atlans.c nixies_lake.c deep_dungeon.c loren_market.c uruk.c duel_arena.c world82.c santa_village.c vulcanus.c $(wildcard world_*_visual.c) world_after.c objects.c object_render.c icarus.c noria.c devias.c tarkan.c elbeland.c raklion.c raklion_event.c ../movement/client_movement.c login_world.c charsel_world.c ../model-codec/model_codec.c ../terrain/terrain.c ../record-math/record_math.c

$(LIB): texture_lookup.h texture_preload.inc worlds_p2.h worlds_p.h worlds_p_internal.h worlds_o.h worlds_n.h worlds_i.h worlds_h.h worlds_g.h worlds_g_internal.h world_visual.h world_visual_internal.h $(SOURCES) objects.h object_render.h icarus.h noria.h raklion_event.h worlds_b.h worlds_b_internal.h login_world.h charsel_world.h ../model-codec/model_codec.h ../terrain/terrain.h ../record-math/record_math.h
	$(CC) $(CFLAGS) -shared $(SOURCES) -lm -o $@
	$(DEPS)

clean:
	rm -f $(LIB)

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
