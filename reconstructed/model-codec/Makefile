CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
LIB := $(if $(filter Darwin,$(shell uname -s)),libmodelcodec.dylib,libmodelcodec.so)

all: $(LIB)

$(LIB): model_codec.c model_codec.h
	$(CC) $(CFLAGS) -shared model_codec.c -o $@

.PHONY: all
