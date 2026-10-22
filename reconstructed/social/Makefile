CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -ffp-contract=off -fno-fast-math
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
all: libsocial.$(SUFFIX)
libsocial.$(SUFFIX): social.c social.h
	$(CC) $(CFLAGS) -shared -fPIC social.c -o $@
.PHONY: all
