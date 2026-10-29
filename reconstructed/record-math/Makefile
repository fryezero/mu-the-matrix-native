CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)

all: librecord_math.$(SUFFIX)

librecord_math.$(SUFFIX): record_math.c record_math.h
	$(CC) $(CFLAGS) -shared record_math.c -lm -o $@
	$(DEPS)

.PHONY: all

-include ../deps.mk   # optional: validators build copies of single directories
