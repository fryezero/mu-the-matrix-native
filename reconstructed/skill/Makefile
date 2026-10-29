CC = clang
CFLAGS = -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -fPIC -ffp-contract=off -fno-fast-math
SUFFIX = $(if $(filter Darwin,$(shell uname -s)),dylib,so)
SRC = skill_table.c skill_use.c skill_tooltip.c skill_list.c master_tree.c skill_canuse.c tree4.c tree4_ui.c tree4_side.c ../hud/tooltip_html.c
HDR = skill_table.h skill_use.h skill_tooltip.h skill_list.h master_tree.h skill_canuse.h tree4.h ../hud/tooltip_html.h

all: libclientskill.$(SUFFIX)

libclientskill.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -shared $(SRC) -lm -o $@
	$(DEPS)

# Negative controls for scripts/validate_skill.py --mutations (not built by default).
mutant%.$(SUFFIX): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -DMU_SKILL_MUTATION=$* -shared $(SRC) -lm -o $@
	$(DEPS)

clean:
	rm -f libclientskill.$(SUFFIX) mutant*.$(SUFFIX)

.PHONY: all clean

-include ../deps.mk   # optional: validators build copies of single directories
