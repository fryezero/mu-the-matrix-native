CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = overhead_names.c
HDR = overhead_names.h

all: libnames.$(SUFFIX)

libnames.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

.PHONY: all

include ../deps.mk
