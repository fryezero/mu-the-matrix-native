/* OpenTexture 0x0181fbe9 and its name resolver 0x0181fead (RENDER-WORLDS-G2).
 *
 * For each mesh of a model the client builds "Data\" + subfolder + mesh name and asks the resolver. The resolver
 * answers the special names itself (skin, hide, hair, level_, face_, HQ...), loads 't' and 'j' names through
 * LoadImage and answers 0x7530 for anything else or a file that does not load. On 0x7530 OpenTexture asks the
 * bitmap-name map (0x00c97e0c on 0x0bdc5f00: lowercased file name -> the first bitmap loaded under that name)
 * and reuses that bitmap (0x00c97730, which only counts a reference when the bitmap is already loaded); otherwise
 * it retries "Data\Item\" + name, then "Data\Item\Texture\" + name, and finally shows text 0xeaa.
 *
 * The routines below run the same steps against a host, so the validator can compare every host request with
 * the original instructions and the native loader can answer them from the installed files. */
#ifndef MU_TEXTURE_LOOKUP_H
#define MU_TEXTURE_LOOKUP_H

#include <stdint.h>

#define MU_TL_DEFAULT 0x7530   /* the resolver's "nothing loaded" index */
#define MU_TL_SKIN 0x7725
#define MU_TL_HIDE 0x791a
#define MU_TL_HAIR 0x7776
#define MU_TL_FACE 0x791c
#define MU_TL_HQ_SKIN3 0x7869
#define MU_TL_HQ_SKIN2 0x7818
#define MU_TL_HQ_SKIN 0x77c7
#define MU_TL_HQ_HAIR 0x78ba

typedef struct mu_tl_host {
    void *context;
    /* LoadImage 0x00c97689(path, filter, wrap): the bitmap index, or MU_TL_DEFAULT when the file does not load.
     * path is the client's string ("Data\Object64\bons.jpg"). */
    int32_t (*load)(void *context, const char *path, uint32_t filter, uint32_t wrap);
    /* 0x00c97e0c(name): the index of the bitmap the name map holds for this mesh name, or -1. path receives that
     * bitmap's file name (+4) for the reuse call. */
    int32_t (*find)(void *context, const char *name, const char **path);
    /* 0x00c97730(index, path, GL_NEAREST, GL_CLAMP) on a name-map hit. */
    void (*reuse)(void *context, int32_t index, const char *path, uint32_t filter, uint32_t wrap);
    /* the 0xeaa message after the last retry; may be NULL */
    void (*error)(void *context, const char *path);
} mu_tl_host;

/* How mu_tl_open found the index. */
enum { MU_TL_DIRECT = 1, MU_TL_NAME_MAP, MU_TL_ITEM, MU_TL_ITEM_TEXTURE, MU_TL_MISSING };

/* 0x0181fead(path, name, wrap, filter). */
int32_t mu_tl_resolve(const mu_tl_host *h, const char *path, const char *name, uint32_t wrap, uint32_t filter);

/* One mesh of 0x0181fbe9(model, subfolder, wrap, filter): the value stored in IndexTexture; *step (optional) says
 * which request answered. Paths are limited to the client's 256-byte buffers. */
int32_t mu_tl_open(const mu_tl_host *h, const char *subfolder, const char *name, uint32_t wrap, uint32_t filter,
                   int *step);

/* Models whose textures are in the name map before a world's objects are opened (static readings of the client,
 * compared under Unicorn by scripts/validate_worlds_g2.py):
 *   - the startup opener 0x01832af3, in OpenTexture order, each (model folder, name, number, texture subfolder)
 *     once (AccessModel 0x018202b4's file name rule: "%s.bmd" for -1, "%s0%d.bmd" below 10, "%s%d.bmd");
 *   - the world pass 0x018392db's own models outside the 0..299 object range, which it opens before the objects. */
typedef struct mu_tl_preload {
    const char *folder;      /* "Data\Skill\" */
    const char *name;
    int32_t number;
    const char *subfolder;   /* OpenTexture's subfolder, verbatim ("Item\texture" has no trailing backslash) */
} mu_tl_preload;

int32_t mu_tl_startup_count(void);
const mu_tl_preload *mu_tl_startup(int32_t index);
/* The world pass's extra models for one world, in order; returns the count. */
int32_t mu_tl_world_preloads(int32_t world, const mu_tl_preload **first);
/* The model file of an entry with '/' separators ("Data/Skill/Skeleton01.bmd"); 0 when it does not fit. */
int mu_tl_preload_file(const mu_tl_preload *p, char *out, int32_t size);

#endif
