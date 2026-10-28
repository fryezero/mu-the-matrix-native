CC := clang
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC
SUFFIX := $(if $(filter Darwin,$(shell uname -s)),dylib,so)
LIB := librenderchar.$(SUFFIX)

all: $(LIB)

$(LIB): renderchar.c renderchar.h special_types.h item_glow.h skin_glow.h item_bodies.h skin_bodies.h item_links.h item_pulse_links.h back_matrices.h ../record-math/record_math.c
	$(CC) $(CFLAGS) -ffp-contract=off -shared renderchar.c ../record-math/record_math.c -lm -o $@

.PHONY: all
