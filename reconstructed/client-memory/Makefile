CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)

all: libclient_memory.$(SUFFIX)

libclient_memory.$(SUFFIX): copy64.c copy64.h clear64.c clear64.h
	$(CC) $(CFLAGS) -shared copy64.c clear64.c -o $@

.PHONY: all
