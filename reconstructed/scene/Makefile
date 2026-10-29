CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libscene.$(SUFFIX)

all: $(LIB)

$(LIB): scene.c scene.h
	$(CC) $(CFLAGS) -shared scene.c -o $@
	$(DEPS)

clean:
	rm -f libscene.dylib libscene.so

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
