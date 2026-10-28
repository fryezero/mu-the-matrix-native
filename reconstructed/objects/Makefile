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
SOURCES := objects.c object_render.c devias.c tarkan.c elbeland.c raklion.c world_warp.c icarus.c noria.c ../movement/client_movement.c login_world.c charsel_world.c ../model-codec/model_codec.c ../terrain/terrain.c ../record-math/record_math.c

$(LIB): $(SOURCES) objects.h object_render.h worlds_b.h world_warp.h icarus.h ../combat/skill_fx.h worlds_b_internal.h login_world.h charsel_world.h ../model-codec/model_codec.h ../terrain/terrain.h ../record-math/record_math.h
	$(CC) $(CFLAGS) -shared $(SOURCES) -lm -o $@

clean:
	rm -f $(LIB)

.PHONY: all clean
