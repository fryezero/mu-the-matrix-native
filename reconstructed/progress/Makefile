CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = progress_calc.c progress_bar.c progress_recv.c progress_window.c progress_options.c
HDR = progress.h

all: libprogress.$(SUFFIX)

libprogress.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -o $@

.PHONY: all
