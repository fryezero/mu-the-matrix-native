CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = ground_items.c item_sets.c ../record-math/record_math.c
HDR = ground_items.h item_sets.h item_angle_table.h item_name_table.h special_models.h ../record-math/record_math.h

all: libclient_items.$(SUFFIX)

libclient_items.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libclient_items.dylib libclient_items.so

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
