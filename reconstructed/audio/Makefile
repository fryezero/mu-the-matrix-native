CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = audio_system.c audio_world.c audio_options.c

all: libclient_audio.$(SUFFIX)

libclient_audio.$(SUFFIX): $(SRC) client_audio.h
	$(CC) $(CFLAGS) -shared $(SRC) -o $@

clean:
	rm -f libclient_audio.dylib libclient_audio.so

.PHONY: all clean
