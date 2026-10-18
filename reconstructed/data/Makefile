CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := libdatatables.$(SUFFIX)

all: $(LIB)

$(LIB): data_codec.c data_codec.h data_tables.c data_tables.h item_attributes.c item_attributes.h table_layouts.c table_layouts.h
	$(CC) $(CFLAGS) -shared data_codec.c data_tables.c item_attributes.c table_layouts.c -o $@

clean:
	rm -f $(LIB)

.PHONY: all clean
