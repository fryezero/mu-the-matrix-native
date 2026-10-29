CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libmodelcodec.$(SUFFIX)
BONES := libbonetracks.$(SUFFIX)
POSE := libposebuilder.$(SUFFIX)
SKIN := libskinning.$(SUFFIX)
CHAR := libcharacter.$(SUFFIX)
READER := libmodelreader.$(SUFFIX)

all: $(LIB) $(BONES) $(POSE) $(SKIN) $(CHAR) $(READER)

$(LIB): model_codec.c model_codec.h client_lea.c client_lea.h
	$(CC) $(CFLAGS) -shared model_codec.c client_lea.c -o $@
	$(DEPS)

# The bone-track loop calls the record-math rotation conversion; that source
# requires contraction to stay disabled.
$(BONES): bone_tracks.c bone_tracks.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -ffp-contract=off -shared bone_tracks.c ../record-math/record_math.c -lm -o $@
	$(DEPS)

# The pose builder seeds from the bone-track loop and calls record-math helpers.
$(POSE): pose_builder.c pose_builder.h bone_tracks.c bone_tracks.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -ffp-contract=off -shared pose_builder.c bone_tracks.c ../record-math/record_math.c -lm -o $@
	$(DEPS)

# The transform and tick are compared after the actual bone-track loop and
# pose builder, so one library carries all four authored stages.
$(SKIN): skinning.c skinning.h pose_builder.c pose_builder.h bone_tracks.c bone_tracks.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -ffp-contract=off -shared skinning.c pose_builder.c bone_tracks.c ../record-math/record_math.c -lm -o $@
	$(DEPS)

# Character assembly helpers (rotation/transform position, class skin index)
# run in chains with the skinning stack, so the library carries all stages.
$(CHAR): character.c character.h skinning.c skinning.h pose_builder.c pose_builder.h bone_tracks.c bone_tracks.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -ffp-contract=off -shared character.c skinning.c pose_builder.c bone_tracks.c ../record-math/record_math.c -lm -o $@
	$(DEPS)

# The plaintext reader section runs before the pose builder and the transform in
# the MODEL-EDGE chains, so one library carries the reader and those stages.
$(READER): model_reader.c model_reader.h skinning.c skinning.h pose_builder.c pose_builder.h bone_tracks.c bone_tracks.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -ffp-contract=off -shared model_reader.c skinning.c pose_builder.c bone_tracks.c ../record-math/record_math.c -lm -o $@
	$(DEPS)

.PHONY: all

-include ../deps.mk   # optional: validators build copies of single directories
