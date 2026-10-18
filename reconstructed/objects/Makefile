CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libobjects.$(SUFFIX)

all: $(LIB)

# The model-codec v12 decoder is linked in so the validator and tests decode
# through the same authored routine the native module uses.
$(LIB): objects.c objects.h ../model-codec/model_codec.c ../model-codec/model_codec.h
	$(CC) $(CFLAGS) -shared objects.c ../model-codec/model_codec.c -o $@

clean:
	rm -f $(LIB)

.PHONY: all clean
