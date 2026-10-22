CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = helpers.c mount_render.c ../movement/client_movement.c ../record-math/record_math.c
HDR = helpers.h mount_render.h mount_classes.h ../movement/client_movement.h ../record-math/record_math.h

all: libclient_helpers.$(SUFFIX)

libclient_helpers.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

clean:
	rm -f libclient_helpers.dylib libclient_helpers.so

.PHONY: all clean
