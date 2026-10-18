# Reconstructed effect system (NATIVE-FX-001, NATIVE-FX-002).
CC ?= clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -ffp-contract=off -fno-fast-math
UNAME := $(shell uname -s)
LIB := libeffects.$(if $(filter Darwin,$(UNAME)),dylib,so)

all: $(LIB)

$(LIB): effects.c effects_json.c effects_tree.c effects_capi.c effects.h effects_internal.h
	$(CC) $(CFLAGS) -fPIC -shared effects.c effects_json.c effects_tree.c effects_capi.c -lm -o $@

clean:
	rm -f libeffects.dylib libeffects.so

.PHONY: all clean
