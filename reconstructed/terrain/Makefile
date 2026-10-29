CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libterrain.$(SUFFIX)

all: $(LIB)

$(LIB): terrain.c terrain.h world_haze.c world_haze.h ../record-math/record_math.c ../record-math/record_math.h
	$(CC) $(CFLAGS) -shared terrain.c world_haze.c ../record-math/record_math.c -lm -o $@
	$(DEPS)

.PHONY: all

include ../deps.mk
