CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = client_path.c ../record-math/record_math.c
HDR = client_path.h ../record-math/record_math.h

all: libclient_path.$(SUFFIX)

libclient_path.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

.PHONY: all

-include ../deps.mk   # optional: validators build copies of single directories
