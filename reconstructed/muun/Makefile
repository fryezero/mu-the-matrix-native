CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = visual.c passes.c ../movement/client_movement.c ../record-math/record_math.c
HDR = visual.h passes.h ../movement/client_movement.h ../record-math/record_math.h
all: libmuun_visual.$(SUFFIX)
libmuun_visual.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)
.PHONY: all
-include ../deps.mk
