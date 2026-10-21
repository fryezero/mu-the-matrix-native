/* libmugfx loaded at run time for the character select's movies; see charsel_mugfx.h. */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include "charsel_mugfx.h"

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

/* ---- libmugfx ---- */

static int exe_dir(char *out, size_t cap)
{
    char path[4096];
#ifdef __APPLE__
    uint32_t size = sizeof path;
    if (_NSGetExecutablePath(path, &size) != 0)
        return 0;
#else
    ssize_t n = readlink("/proc/self/exe", path, sizeof path - 1);
    if (n <= 0)
        return 0;
    path[n] = 0;
#endif
    char *slash = strrchr(path, '/');
    if (!slash)
        return 0;
    *slash = 0;
    snprintf(out, cap, "%s", path);
    return 1;
}

int mu_charsel_mugfx_load(mu_charsel_mugfx *a, const char *explicit_path, char *error, size_t cap)
{
#ifdef __APPLE__
    const char *lib = "libmugfx.dylib";
#else
    const char *lib = "libmugfx.so";
#endif
    char candidates[4][4096], dir[4096];
    int n = 0;
    if (explicit_path)
        snprintf(candidates[n++], sizeof candidates[0], "%s", explicit_path);
    if (getenv("MU_GFX_LIB"))
        snprintf(candidates[n++], sizeof candidates[0], "%s", getenv("MU_GFX_LIB"));
    if (exe_dir(dir, sizeof dir))
        snprintf(candidates[n++], sizeof candidates[0], "%s/../gfx/mugfx/target/release/%s", dir, lib);
    snprintf(candidates[n++], sizeof candidates[0], "native/gfx/mugfx/target/release/%s", lib);
    for (int i = 0; i < n && !a->dl; i++)
        a->dl = dlopen(candidates[i], RTLD_NOW | RTLD_LOCAL);
    if (!a->dl) {
        snprintf(error, cap, "libmugfx not found (native/gfx/build-mugfx.sh or MU_GFX_LIB): %s", dlerror());
        return -1;
    }
#define SYM(field, name)                                                                                     \
    do {                                                                                                       \
        *(void **)&a->field = dlsym(a->dl, name);                                                              \
        if (!a->field) {                                                                                       \
            snprintf(error, cap, "libmugfx lacks %s", name);                                                   \
            return -1;                                                                                         \
        }                                                                                                      \
    } while (0)
    SYM(abi_version, "mugfx_abi_version");
    if (a->abi_version() != MUGFX_ABI_VERSION) {
        snprintf(error, cap, "libmugfx ABI %d, expected %d", a->abi_version(), MUGFX_ABI_VERSION);
        return -1;
    }
    SYM(open, "mugfx_open");
    SYM(close, "mugfx_close");
    SYM(set_callback, "mugfx_set_callback");
    SYM(start, "mugfx_start");
    SYM(advance, "mugfx_advance");
    SYM(needs_render, "mugfx_needs_render");
    SYM(render, "mugfx_render");
    SYM(invoke, "mugfx_invoke");
    SYM(get_variable, "mugfx_get_variable");
    SYM(set_variable, "mugfx_set_variable");
    SYM(mouse, "mugfx_mouse");
    SYM(hit_test, "mugfx_hit_test");
    SYM(set_view, "mugfx_set_view");
    SYM(key, "mugfx_key");
    SYM(text, "mugfx_text");
    SYM(text_focus, "mugfx_text_focus");
#undef SYM
    return 0;
}

void mu_charsel_mugfx_unload(mu_charsel_mugfx *a)
{
    if (a->dl)
        dlclose(a->dl);
    memset(a, 0, sizeof *a);
}
