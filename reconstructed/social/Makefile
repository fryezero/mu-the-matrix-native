CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -ffp-contract=off -fno-fast-math
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
all: libsocial.$(SUFFIX)
libsocial.$(SUFFIX): social.c social.h item_options.c item_formula.c item_display.c item_present.c item_options.h item_formula.h item_display.h item_present.h social_packets.c social_packets.h
	$(CC) $(CFLAGS) -shared -fPIC social.c item_options.c item_formula.c item_display.c item_present.c social_packets.c -o $@
	$(DEPS)
.PHONY: all

-include ../deps.mk   # optional: validators build copies of single directories
