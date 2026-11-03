/* RENDER-EFFECTS-009: the client's named-bone service and owner bone getter, on bone-name arrays.
 *
 * - 0x012bd35a(name, fallback), a model method: the index of the first bone record (0x8c bytes at +0x2c, count
 *   int16 +0x22) whose name equals the std::string, else `fallback` (also when the model has no records).
 * - 0x0129f18a(name, own), an object method: the same search on the object's model; NULL without a model, records
 *   or match; else BoneTransform 0x06fce398 + 0x30 * i, or with `own` the object's bone buffer +0x318 + 0x30 * i
 *   when that is set.
 * - 0x0129f12c(bone), an object method: the object's bone buffer +0x318 + 0x30 * bone when the model exists,
 *   +0x318 is set and 0 <= bone < the model's bone count, else NULL.
 * Verified against the instructions by scripts/validate_render_effects9.py (family named_bones). */
#ifndef MU_NAMED_BONES_H
#define MU_NAMED_BONES_H

#include <stdint.h>

int32_t mu_named_bone_index(const char *const *names, int32_t count, int has_records, const char *name,
                            int32_t fallback);
/* 0 = NULL, 1 = BoneTransform + 0x30 * *index, 2 = the object's own buffer + 0x30 * *index */
int mu_named_bone_matrix(const char *const *names, int32_t count, int has_records, int has_model, int own,
                         const char *name, int own_bones, int32_t *index);
int mu_owner_bone_valid(int has_model, int own_bones, int32_t count, int32_t bone);

#endif
