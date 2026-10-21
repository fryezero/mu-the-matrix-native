#ifndef MU_CHARSEL_MUGFX_H
#define MU_CHARSEL_MUGFX_H

/* libmugfx loaded at run time for the character select's movies (NATIVE-CHARSEL-003, NATIVE-CHARCREATE-001):
 * CharacterSelect (the list and the create panel), Caution (the message boxes) and winSystemMenu (the menu).
 * The HUD layer native/gfx/mu_gfx_layer.c keeps its own loader. */

#include <stddef.h>
#include <stdint.h>

#include "../gfx/mugfx/include/mugfx.h"

typedef struct mu_charsel_mugfx {
    void *dl;
    int (*abi_version)(void);
    MuGfx *(*open)(const char *, int, int, char *, size_t);
    void (*close)(MuGfx *);
    void (*set_callback)(MuGfx *, mugfx_callback, void *);
    void (*start)(MuGfx *);
    void (*advance)(MuGfx *, double);
    int (*needs_render)(MuGfx *);
    int (*render)(MuGfx *, uint8_t *, size_t);
    const char *(*invoke)(MuGfx *, const char *, const char *, const char *);
    const char *(*get_variable)(MuGfx *, const char *);
    int (*set_variable)(MuGfx *, const char *, const char *);
    int (*mouse)(MuGfx *, int, int, double, double);
    int (*hit_test)(MuGfx *, double, double);
    int (*set_view)(MuGfx *, int, int, int, int, int, int, double);
    int (*key)(MuGfx *, int, int, uint32_t, int);
    int (*text)(MuGfx *, const char *);
    int (*text_focus)(MuGfx *);
    /* NATIVE-PERF-001: optional (shared rendering into an IOSurface), NULL when absent */
    MuGfx *(*open_shared)(const char *, int, int, char *, size_t);
    int (*render_shared)(MuGfx *, int);
    void *(*iosurface)(MuGfx *, int *, int *, uint32_t *);
} mu_charsel_mugfx;

/* explicit_path, then $MU_GFX_LIB, next to the executable, the repository build. Returns 0 or -1 with error. */
int mu_charsel_mugfx_load(mu_charsel_mugfx *a, const char *explicit_path, char *error, size_t cap);
void mu_charsel_mugfx_unload(mu_charsel_mugfx *a);

#endif
