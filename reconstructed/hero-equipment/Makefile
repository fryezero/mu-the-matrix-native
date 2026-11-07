CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = hero_equipment.c ../players/remote_players.c
HDR = hero_equipment.h ../players/remote_players.h

all: libheroequipment.$(SUFFIX)

libheroequipment.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libheroequipment.$(SUFFIX)

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
