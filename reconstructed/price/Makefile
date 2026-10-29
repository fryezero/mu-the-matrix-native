CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = item_price.c
HDR = item_price.h

all: libitemprice.$(SUFFIX)

libitemprice.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

# Negative controls for scripts/validate_item_price.py --mutations (not built by default).
mutant%.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -DMU_PRICE_MUTATION=$* -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libitemprice.$(SUFFIX) mutant*.$(SUFFIX)

.PHONY: all clean

include ../deps.mk
