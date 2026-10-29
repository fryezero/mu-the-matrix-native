/* OpenTexture 0x0181fbe9 and the name resolver 0x0181fead. See texture_lookup.h. */
#include "texture_lookup.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

#define GL_NEAREST_ 0x2600u
#define GL_CLAMP_ 0x2900u

/* _strnicmp 0x019965a3 in the C locale. */
static int prefix_nocase(const char *s, const char *prefix)
{
    for (size_t i = 0; prefix[i]; ++i)
        if (tolower((unsigned char)s[i]) != tolower((unsigned char)prefix[i]))
            return 0;
    return 1;
}

/* _splitpath 0x0198b9e3's extension: from the last '.' after the last separator. */
static const char *extension(const char *name)
{
    const char *dot = NULL;
    for (const char *p = name; *p; ++p)
        if (*p == '.')
            dot = p;
        else if (*p == '\\' || *p == '/' || *p == ':')
            dot = NULL;
    return dot ? dot : "";
}

int32_t mu_tl_resolve(const mu_tl_host *h, const char *path, const char *name, uint32_t wrap, uint32_t filter)
{
    if (name[0] == 's' && name[1] == 'k' && name[2] == 'i')
        return MU_TL_SKIN;
    if (strncmp(name, "level_", 6) == 0)
        return MU_TL_SKIN;
    if (name[0] == 'h' && name[1] == 'i' && name[2] == 'd')
        return MU_TL_HIDE;
    if (name[0] == 'h' && name[1] == 'a' && name[2] == 'i' && name[3] == 'r')
        return MU_TL_HAIR;
    if (strncmp(name, "face_", 5) == 0)
        return MU_TL_FACE;
    if (prefix_nocase(name, "HQskin3"))
        return MU_TL_HQ_SKIN3;
    if (prefix_nocase(name, "HQskin2"))
        return MU_TL_HQ_SKIN2;
    if (prefix_nocase(name, "HQskin"))
        return MU_TL_HQ_SKIN;
    if (prefix_nocase(name, "HQlevel_"))
        return MU_TL_HQ_SKIN;
    if (prefix_nocase(name, "HQhair_"))
        return MU_TL_HQ_HAIR;
    const char *ext = extension(name);
    const int kind = ext[0] ? tolower((unsigned char)ext[1]) : 0;
    if (kind == 't')   /* TGA: always GL_NEAREST */
        return h->load(h->context, path, GL_NEAREST_, wrap);
    if (kind == 'j')
        return h->load(h->context, path, filter, wrap);
    return MU_TL_DEFAULT;
}

static int join(char *out, size_t size, const char *a, const char *b, const char *c)
{
    const int n = snprintf(out, size, "%s%s%s", a, b, c);
    return n >= 0 && (size_t)n < size;
}

int32_t mu_tl_open(const mu_tl_host *h, const char *subfolder, const char *name, uint32_t wrap, uint32_t filter,
                   int *step)
{
    char path[256];
    int found = MU_TL_MISSING;
    int32_t index = MU_TL_DEFAULT;
    if (join(path, sizeof path, "Data\\", subfolder, name)) {
        index = mu_tl_resolve(h, path, name, wrap, filter);
        found = MU_TL_DIRECT;
    }
    if (index == MU_TL_DEFAULT) {
        const char *cached = NULL;
        const int32_t hit = h->find(h->context, name, &cached);
        if (hit >= 0) {
            h->reuse(h->context, hit, cached ? cached : "", GL_NEAREST_, GL_CLAMP_);
            index = hit;
            found = MU_TL_NAME_MAP;
        } else {
            static const char *const retry[2] = {"Item\\", "Item\\Texture\\"};
            for (int k = 0; k < 2 && index == MU_TL_DEFAULT; ++k)
                if (join(path, sizeof path, "Data\\", retry[k], name)) {
                    index = mu_tl_resolve(h, path, name, wrap, filter);
                    found = k == 0 ? MU_TL_ITEM : MU_TL_ITEM_TEXTURE;
                }
            if (index == MU_TL_DEFAULT) {
                found = MU_TL_MISSING;
                if (h->error)
                    h->error(h->context, path);
            }
        }
    }
    if (step)
        *step = found;
    return index;
}

#include "texture_preload.inc"

int32_t mu_tl_startup_count(void)
{
    return (int32_t)(sizeof startup / sizeof startup[0]);
}

const mu_tl_preload *mu_tl_startup(int32_t index)
{
    return index >= 0 && index < mu_tl_startup_count() ? &startup[index] : NULL;
}

int32_t mu_tl_world_preloads(int32_t world, const mu_tl_preload **first)
{
    for (size_t i = 0; i < sizeof world_preloads / sizeof world_preloads[0]; ++i)
        if (world_preloads[i].world == world) {
            if (first)
                *first = &world_extra[world_preloads[i].first];
            return world_preloads[i].count;
        }
    if (first)
        *first = NULL;
    return 0;
}

int mu_tl_preload_file(const mu_tl_preload *p, char *out, int32_t size)
{
    char file[128];
    int n;
    if (p->number == -1)
        n = snprintf(file, sizeof file, "%s%s.bmd", p->folder, p->name);
    else if (p->number < 10)
        n = snprintf(file, sizeof file, "%s%s0%d.bmd", p->folder, p->name, p->number);
    else
        n = snprintf(file, sizeof file, "%s%s%d.bmd", p->folder, p->name, p->number);
    if (n < 0 || (size_t)n >= sizeof file || size <= n)
        return 0;
    for (int i = 0; i <= n; ++i)
        out[i] = file[i] == '\\' ? '/' : file[i];
    return 1;
}
