CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = npc_talk.c npc_pick.c npc_dialogue.c
HDR = npc_talk.h npc_pick.h npc_dialogue.h character_box_table.h

all: libnpc.$(SUFFIX)

libnpc.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

.PHONY: all

-include ../deps.mk   # optional: validators build copies of single directories
