CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
CODEC := ../model-codec
MATH := ../record-math
LIB := libactors.$(SUFFIX)

all: $(LIB)

# The character animation speed runs the reconstructed animation tick, so the
# library carries the skinning stack (same contraction rule as model-codec).
$(LIB): actors.c actors.h monster_open_table.h monster_class_table.h npc_table.h player_action_table.h $(CODEC)/skinning.c $(CODEC)/skinning.h $(CODEC)/pose_builder.c $(CODEC)/bone_tracks.c $(MATH)/record_math.c
	$(CC) $(CFLAGS) -ffp-contract=off -shared actors.c $(CODEC)/skinning.c $(CODEC)/pose_builder.c $(CODEC)/bone_tracks.c $(MATH)/record_math.c -lm -o $@

.PHONY: all
