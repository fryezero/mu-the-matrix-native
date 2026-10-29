CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = pets.c ../helpers/helpers.c ../movement/client_movement.c ../record-math/record_math.c
HDR = pets.h ../helpers/helpers.h ../helpers/mount_classes.h ../movement/client_movement.h ../record-math/record_math.h

all: libclient_pets.$(SUFFIX)

libclient_pets.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libclient_pets.dylib libclient_pets.so

.PHONY: all clean

include ../deps.mk
