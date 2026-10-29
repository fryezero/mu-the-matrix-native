CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = client_camera.c client_world_camera.c client_input.c client_frame.c ../record-math/record_math.c
HDR = client_camera.h client_world_camera.h client_input.h client_frame.h ../record-math/record_math.h

all: libclient_camera.$(SUFFIX)

libclient_camera.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

.PHONY: all

include ../deps.mk
