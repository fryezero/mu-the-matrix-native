CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = combat.c skill_fx.c ../joints/joints.c ../record-math/record_math.c ../movement/client_movement.c
HDR = combat.h attack_speed_table.h skill_fx.h ../joints/joints.h ../record-math/record_math.h ../movement/client_movement.h

all: libcombat.$(SUFFIX)

libcombat.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

.PHONY: all
