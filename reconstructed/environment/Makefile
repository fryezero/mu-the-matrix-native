CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = env_core.c raklion_snow.c env_boids.c env_elbeland.c env_icarus.c env_fish.c env_leaves.c env_world.c env_test_host.c ../record-math/record_math.c
HDR = env.h env_internal.h env_test_host.h ../record-math/record_math.h

all: libclient_env.$(SUFFIX)

libclient_env.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

clean:
	rm -f libclient_env.dylib libclient_env.so

.PHONY: all clean
