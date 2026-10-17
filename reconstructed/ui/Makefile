CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SOURCES = ui2d.c ui_text.c ui_texture.c ui_login.c
HEADERS = ui2d.h ui_text.h ui_texture.h ui_login.h

all: libmu_ui.$(SUFFIX)

libmu_ui.$(SUFFIX): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -shared $(SOURCES) -o $@

clean:
	rm -f libmu_ui.dylib libmu_ui.so

.PHONY: all clean
