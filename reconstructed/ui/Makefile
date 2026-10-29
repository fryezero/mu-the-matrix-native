CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SOURCES = ui2d.c ui_text.c ui_texture.c ui_login.c ui_widget.c ui_server.c ui_credit.c ui_charsel.c ui_loading.c ui_probe.c
HEADERS = ui2d.h ui_text.h ui_texture.h ui_login.h ui_widget.h ui_server.h ui_credit.h ui_charsel.h ui_loading.h

all: libmu_ui.$(SUFFIX)

libmu_ui.$(SUFFIX): $(SOURCES) $(HEADERS)
	$(CC) $(CFLAGS) -shared $(SOURCES) -o $@
	$(DEPS)

clean:
	rm -f libmu_ui.dylib libmu_ui.so

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
