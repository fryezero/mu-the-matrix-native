CC := i686-w64-mingw32-gcc
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion
ROOT := ../..

all: lea-compare.exe

lea-compare.exe: compare.c call_checked.S $(ROOT)/reconstructed/model-codec/client_lea.c $(ROOT)/reconstructed/model-codec/client_lea.h
	$(CC) $(CFLAGS) -static -I$(ROOT)/reconstructed/model-codec compare.c call_checked.S $(ROOT)/reconstructed/model-codec/client_lea.c -o $@ -lbcrypt

.PHONY: all
