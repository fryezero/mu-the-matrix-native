CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = raven.c ../movement/client_movement.c ../record-math/record_math.c
HDR = raven.h ../movement/client_movement.h ../record-math/record_math.h

all: libclient_raven.$(SUFFIX)

libclient_raven.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

clean:
	rm -f libclient_raven.dylib libclient_raven.so

.PHONY: all clean
