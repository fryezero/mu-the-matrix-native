CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libterrain.$(SUFFIX)

all: $(LIB)

$(LIB): terrain.c terrain.h
	$(CC) $(CFLAGS) -shared terrain.c -lm -o $@

.PHONY: all
