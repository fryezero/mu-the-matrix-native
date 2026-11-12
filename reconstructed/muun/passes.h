#ifndef MU_MUUN_PASSES_H
#define MU_MUUN_PASSES_H
#include <stdint.h>
/* 0x017f76ec's ordinary MuunMeshInfo branch. Records remain decoded, private inputs.
 * The five special models 0x2b7a/b, 0x2b8d/e and 0x2b90 are outside this branch. */
typedef struct mu_mv_pass {
    int32_t mesh, flags, blend, texture;
    float alpha, light, color[3];
} mu_mv_pass;
void mu_mv_mesh_pass(const uint8_t record[300], const float color[3], float alpha, int32_t blend,
                     float light, int32_t texture, float time, mu_mv_pass *out);
/* 0x009c2539, same-owner command branch: categories 50/53 request action 3;
 * 51/52/54/55 action 4. Other auxiliary categories request no action. */
int32_t mu_mv_command_action(int32_t category);
/* 0x009aa54b: ordinary owner, option and world gates of the slot shadow. */
float mu_mv_shadow_alpha(int32_t world, int option, int owner_kind, float owner_alpha, float record_alpha);
#endif
