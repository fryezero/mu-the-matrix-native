CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = cloth.c ../record-math/record_math.c
HDR = cloth.h ../record-math/record_math.h

all: libcloth.$(SUFFIX)

libcloth.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libcloth.$(SUFFIX) libcloth.$(SUFFIX).d

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
