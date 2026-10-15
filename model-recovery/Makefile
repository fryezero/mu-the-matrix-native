CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion

UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
LIBRARY = liblea256.dylib
SHARED = -dynamiclib
else
LIBRARY = liblea256.so
SHARED = -shared -fPIC
endif

all: $(LIBRARY)

$(LIBRARY): lea256.c
	$(CC) $(CFLAGS) $(SHARED) $< -o $@

clean:
	rm -f liblea256.dylib liblea256.so

.PHONY: all clean
