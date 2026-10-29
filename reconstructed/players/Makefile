CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = remote_players.c
HDR = remote_players.h

all: libremoteplayers.$(SUFFIX)

libremoteplayers.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libremoteplayers.$(SUFFIX)

.PHONY: all clean

include ../deps.mk
