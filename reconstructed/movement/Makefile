CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = client_movement.c ../record-math/record_math.c
HDR = client_movement.h ../record-math/record_math.h

all: libclient_movement.$(SUFFIX)

libclient_movement.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

.PHONY: all
