CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libdatatables.$(SUFFIX)

all: $(LIB)

$(LIB): data_codec.c data_codec.h data_tables.c data_tables.h
	$(CC) $(CFLAGS) -shared data_codec.c data_tables.c -o $@

clean:
	rm -f $(LIB)

.PHONY: all clean
