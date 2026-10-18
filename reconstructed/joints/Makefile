CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = joints.c ../record-math/record_math.c ../movement/client_movement.c
HDR = joints.h ../record-math/record_math.h ../movement/client_movement.h

all: libclient_joints.$(SUFFIX)

libclient_joints.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

clean:
	rm -f libclient_joints.dylib libclient_joints.so

.PHONY: all clean
