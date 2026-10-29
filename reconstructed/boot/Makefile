CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion

all: recover-block

recover-block: decoder.c decoder.h main.c
	$(CC) $(CFLAGS) decoder.c main.c -o $@
	$(DEPS)

clean:
	rm -f recover-block

.PHONY: all clean

include ../deps.mk
