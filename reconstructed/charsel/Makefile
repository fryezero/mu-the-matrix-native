CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libcharsel.$(SUFFIX)

all: $(LIB)

$(LIB): charsel.c charsel.h charsel_gfx.c charsel_gfx.h
	$(CC) $(CFLAGS) -shared charsel.c charsel_gfx.c -lm -o $@

clean:
	rm -f libcharsel.dylib libcharsel.so

.PHONY: all clean
