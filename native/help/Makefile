CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror
BUILD ?= build
SDL_CFLAGS := $(shell pkg-config --cflags sdl2)
SDL_LIBS := $(shell pkg-config --libs sdl2)
SRC := help_view.c ../../reconstructed/help/help.c ../../reconstructed/help/help_controller.c \
       ../../reconstructed/data/data_tables.c ../../reconstructed/data/data_codec.c \
       ../../reconstructed/hud/tooltip_html.c ../core/mu_png.c

all: $(BUILD)/mu-help-view

$(BUILD)/mu-help-view: $(SRC) ../../reconstructed/help/help.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(SDL_CFLAGS) $(SRC) $(SDL_LIBS) -o $@
	$(CC) $(CFLAGS) $(SDL_CFLAGS) -MM -MP -MT $@ $(SRC) > $@.d

# BUILD-DEPS-001: the headers the sources read (one -MM pass, as the build is one call).
-include $(BUILD)/mu-help-view.d

.PHONY: all
