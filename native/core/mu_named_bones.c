/* RENDER-EFFECTS-009: the named-bone service (see mu_named_bones.h). */
#include "mu_named_bones.h"

#include <string.h>

/* 0x0096c6da: the std::string equals the record's name */
static int same_name(const char *record, const char *name)
{
    return record && name && strcmp(record, name) == 0;
}

int32_t mu_named_bone_index(const char *const *names, int32_t count, int has_records, const char *name,
                            int32_t fallback)
{
    if (!has_records)
        return fallback;   /* 0x012bd36b: no records */
    for (int32_t i = 0; i < count; ++i)
        if (same_name(names[i], name))
            return i;   /* the first equal name */
    return fallback;   /* 0x012bd3b1 */
}

int mu_named_bone_matrix(const char *const *names, int32_t count, int has_records, int has_model, int own,
                         const char *name, int own_bones, int32_t *index)
{
    if (!has_model || !has_records)
        return 0;   /* 0x0129f1ae / 0x0129f1be */
    for (int32_t i = 0; i < count; ++i)
        if (same_name(names[i], name)) {
            *index = i;
            return own && own_bones ? 2 : 1;
        }
    return 0;   /* 0x0129f249 */
}

int mu_owner_bone_valid(int has_model, int own_bones, int32_t count, int32_t bone)
{
    if (!has_model || !own_bones)
        return 0;   /* 0x0129f15b */
    if (bone < 0 || bone >= count)
        return 0;   /* 0x0129f173 */
    return 1;
}
