CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SOURCES = inv_grid.c item_slots.c item_pass.c tooltip_html.c tooltip_format.c ../ui/ui2d.c
HEADERS = inv_grid.h item_slots.h item_pass.h tooltip_html.h tooltip_format.h ../ui/ui2d.h

all: libmu_hud.$(SUFFIX)

libmu_hud.$(SUFFIX): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -shared $(SOURCES) -o $@

clean:
	rm -f libmu_hud.dylib libmu_hud.so

.PHONY: all clean
