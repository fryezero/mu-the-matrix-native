CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = map_hud.c map_move.c map_gate.c
HDR = map.h

all: libmap.$(SUFFIX)

libmap.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -o $@
	$(DEPS)

.PHONY: all

include ../deps.mk
