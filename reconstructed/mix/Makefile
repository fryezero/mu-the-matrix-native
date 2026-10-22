CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = item_actions.c mix_rules.c mix_source.c mix_manager.c
all: libmix.$(SUFFIX)
libmix.$(SUFFIX): $(SRC) item_actions.h mix_rules.h
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
.PHONY: all
