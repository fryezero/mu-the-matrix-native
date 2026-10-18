CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = ground_items.c ../record-math/record_math.c
HDR = ground_items.h item_angle_table.h item_name_table.h ../record-math/record_math.h

all: libclient_items.$(SUFFIX)

libclient_items.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@

clean:
	rm -f libclient_items.dylib libclient_items.so

.PHONY: all clean
