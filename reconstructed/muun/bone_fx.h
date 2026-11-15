#ifndef MU_MUUN_BONE_FX_H
#define MU_MUUN_BONE_FX_H
#include "passes.h"
enum { MU_MV_BONE_OPS = 8 };
/* Points in order: 11,18,12,13,22,23,52. Every required point must be a posed own bone.
 * Random fractions and integer draws are supplied explicitly by the offline fixture. */
typedef struct mu_mv_bone_op {
    int32_t particle, type, subtype;
    float position[3], light[3], scale, rotation;
} mu_mv_bone_op;
int mu_mv_bone_row(int32_t model, int32_t mesh);
int mu_mv_bone_mesh(int32_t model, int32_t mesh, float time, float alpha, float light,
                    mu_mv_pass *pass, float uv[2]);
int mu_mv_bone_effects(int32_t model, int32_t mesh, float time, float scale,
                      const float points[7][3], const float fractions[12], int32_t random0,
                      int32_t random1, mu_mv_bone_op out[MU_MV_BONE_OPS]);
/* Raw authored inputs of 0x017f746f. No class/team meaning or authoritative lookup is inferred. */
int mu_mv_remote_buff_visible(int remote_found, uint8_t predicate, uint8_t buff18,
                              uint8_t local_byte16, uint8_t remote_byte16);
#endif
