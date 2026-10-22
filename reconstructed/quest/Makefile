CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = quest_data.c quest_system.c quest_text.c quest_ui.c quest_packets.c quest_api.c quest_guide.c quest_summary.c quest_move.c quest_wrap.c quest_classic.c
HDR = quest.h quest_internal.h

all: libquest.$(SUFFIX)

libquest.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -o $@

.PHONY: all
