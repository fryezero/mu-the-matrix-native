CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libmodelcodec.$(SUFFIX)
BONES := libbonetracks.$(SUFFIX)

all: $(LIB) $(BONES)

$(LIB): model_codec.c model_codec.h client_lea.c client_lea.h
	$(CC) $(CFLAGS) -shared model_codec.c client_lea.c -o $@

# The bone-track loop calls the record-math rotation conversion; that source
# requires contraction to stay disabled.
$(BONES): bone_tracks.c bone_tracks.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -ffp-contract=off -shared bone_tracks.c ../record-math/record_math.c -lm -o $@

.PHONY: all
