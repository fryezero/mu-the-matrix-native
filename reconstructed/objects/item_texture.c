/* The item model loader's texture step 0x00cd558e. See item_texture.h. */
#include "item_texture.h"

#include "../model-codec/character.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

#define GL_NEAREST_ 0x2600u
#define GL_CLAMP_ 0x2900u

/* _strnicmp 0x019965a3 (n = strlen(prefix)) in the C locale. */
static int prefix_nocase(const char *s, const char *prefix)
{
    for (size_t i = 0; prefix[i]; ++i)
        if (tolower((unsigned char)s[i]) != tolower((unsigned char)prefix[i]))
            return 0;
    return 1;
}

/* sprintf 0x009619dd(buffer, "%sTexture\%s", folder, name) into the 256-byte buffer [ebp-0x1e4]. */
static int texture_path(char out[256], const char *folder, const char *name)
{
    const int n = snprintf(out, 256, "%sTexture\\%s", folder, name);
    return n >= 0 && n < 256;
}

static int32_t special(const char *name)
{
    if (prefix_nocase(name, "skin_") || prefix_nocase(name, "level"))
        return MU_TL_SKIN;
    if (prefix_nocase(name, "hid"))
        return MU_TL_HIDE;
    if (prefix_nocase(name, "hair_"))
        return MU_TL_HAIR;
    return 0;
}

static int32_t special_hq(const char *name)
{
    if (prefix_nocase(name, "HQskin_"))
        return MU_TL_HQ_SKIN;
    if (prefix_nocase(name, "HQskin3"))
        return MU_TL_HQ_SKIN3;
    if (prefix_nocase(name, "HQskin2"))
        return MU_TL_HQ_SKIN2;
    if (prefix_nocase(name, "HQskin") || prefix_nocase(name, "HQlevel"))
        return MU_TL_HQ_SKIN;
    if (prefix_nocase(name, "HQhair_") || prefix_nocase(name, "HQhair"))
        return MU_TL_HQ_HAIR;
    return 0;
}

int32_t mu_it_open(const mu_tl_host *h, const char *folder, const char *name, int32_t *type, int *field, int *step)
{
    char path[256];
    int32_t index = MU_TL_DEFAULT;
    int found = MU_TL_DIRECT;
    *type = MU_IT_PLAIN;
    if (prefix_nocase(name, "nude_"))                /* 0x00cd57a4 */
        *type = MU_IT_NUDE;
    else if (prefix_nocase(name, "cotton2_"))
        *type = MU_IT_COTTON2;
    else if (prefix_nocase(name, "cotton_"))
        *type = MU_IT_COTTON;
    if (!texture_path(path, folder, name)) {
        if (step)
            *step = 0;
        return MU_TL_DEFAULT;
    }
    int32_t s = special(name);
    if (s) {
        index = s;
    } else if (strncmp(name, "field_", 6) == 0) {   /* 0x00cd58c6 */
        const size_t rest = strlen(name + 6);
        if (rest < 4) {
            if (step)
                *step = 0;
            return MU_TL_DEFAULT;
        }
        *field = 1;
        index = h->load(h->context, path, GL_NEAREST_, GL_CLAMP_);
        char tga[256];
        snprintf(tga, sizeof tga, "%.*s.tga", (int)(rest - 4), name + 6);
        if (!texture_path(path, folder, tga)) {
            if (step)
                *step = 0;
            return MU_TL_DEFAULT;
        }
        h->load(h->context, path, GL_NEAREST_, GL_CLAMP_);
    } else if ((s = special_hq(name)) != 0) {
        index = s;
    } else {
        index = h->load(h->context, path, GL_NEAREST_, GL_CLAMP_);   /* 0x00cd5b50 */
    }
    if (index == MU_TL_DEFAULT) {                    /* 0x00cd5b7a */
        const char *cached = NULL;
        const int32_t hit = h->find(h->context, name, &cached);
        if (hit >= 0) {
            h->reuse(h->context, hit, cached ? cached : "", GL_NEAREST_, GL_CLAMP_);
            index = hit;
            found = MU_TL_NAME_MAP;
        } else {
            found = MU_TL_MISSING;
            if (h->error)
                h->error(h->context, path);
        }
    }
    if (step)
        *step = found;
    return index;
}

int8_t mu_it_part_skin(uint8_t class_byte)
{
    return (int8_t)mu_character_skin_index(class_byte);   /* 0x0139d6a2, byte store at 0x0136a4bd */
}

int32_t mu_it_skin_bitmap(int32_t index_texture, int8_t skin)
{
    switch (index_texture) {
    case MU_TL_SKIN: case MU_TL_HAIR: case MU_TL_HQ_SKIN: case MU_TL_HQ_SKIN2: case MU_TL_HQ_SKIN3: case MU_TL_HQ_HAIR:
        return index_texture + skin;
    default:
        return index_texture;
    }
}

/* RENDER-ITEMS-TEX-003: 0x00c97730 for one LoadBitmap call. See item_texture.h. */

/* _stricmp 0x0198c794 in the C locale. */
static int same_nocase(const char *a, const char *b)
{
    for (;; ++a, ++b) {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b))
            return 0;
        if (!*a)
            return 1;
    }
}

/* 0x00c99025(path, out, 0): the _splitpath extension without its dot ("" when it is "" or "."). */
static const char *extension(const char *path)
{
    const char *base = path;
    for (const char *p = path; *p; ++p)
        if (*p == '\\' || *p == '/')
            base = p + 1;
    const char *dot = strrchr(base, '.');
    return dot && dot[1] ? dot + 1 : "";
}

int mu_it_register(mu_it_bitmap *slot, const char *path, uint32_t filter, uint32_t wrap)
{
    int what = 0;
    if (slot->path && slot->refs != 0) {             /* 0x00c977a1 */
        if (same_nocase(slot->path, path)) {         /* 0x00c977c3 */
            slot->refs = (uint8_t)(slot->refs + 1);
            return MU_IT_REG_REFERENCE;
        }
        what |= MU_IT_REG_UNLOAD;                    /* 0x00c9784d */
        slot->path = NULL;
        slot->refs = 0;
    }
    const char *ext = extension(path);
    if (same_nocase(ext, "jpg"))                     /* 0x00c97886 */
        what |= MU_IT_REG_JPG;
    else if (same_nocase(ext, "tga"))                /* 0x00c978c9 */
        what |= MU_IT_REG_TGA;
    else
        return what;
    slot->path = path;
    slot->filter = filter;
    slot->wrap = wrap;
    slot->refs = 1;
    return what;
}

int mu_it_registration(const mu_it_call *calls, size_t count, int32_t index, mu_it_bitmap *out)
{
    size_t lo = 0, hi = count;
    while (lo < hi) {                                /* the first call of the index */
        const size_t mid = lo + (hi - lo) / 2;
        if (calls[mid].index < index)
            lo = mid + 1;
        else
            hi = mid;
    }
    mu_it_bitmap slot = {NULL, 0, 0, 0};
    for (size_t i = lo; i < count && calls[i].index == index; ++i)
        mu_it_register(&slot, calls[i].path, calls[i].filter, calls[i].wrap);
    *out = slot;
    return slot.path != NULL;
}
