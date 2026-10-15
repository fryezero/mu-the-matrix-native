CC = x86_64-w64-mingw32-gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -D__USE_MINGW_ANSI_STDIO=1

all: capture-client.exe

capture-client.exe: capture-client.c
	$(CC) $(CFLAGS) -municode -static $< -o $@ -lbcrypt

.PHONY: all
