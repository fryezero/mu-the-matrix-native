CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = world_flames.c particles.c sprites.c shadow.c visual.c layout.c ../record-math/record_math.c
HDR = world_flames.h particles.h particles_internal.h ../record-math/record_math.h

all: libclient_particles.$(SUFFIX)

libclient_particles.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

clean:
	rm -f libclient_particles.dylib libclient_particles.so

.PHONY: all clean
