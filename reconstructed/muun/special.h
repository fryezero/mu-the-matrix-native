#ifndef MU_MUUN_SPECIAL_H
#define MU_MUUN_SPECIAL_H
#include "passes.h"
/* Ordinary rows on the five special models are admitted individually. Three bone-effect branches stay refused. */
int mu_mv_special_admit(int32_t model, int32_t mesh);
/* Overlay the verified special mesh arguments on the ordinary row. c8 is persistent OBJECT +0xc8.
 * The caller supplies finite binary32 clocks/delta; UVs begin at OBJECT +0xac/+0xb0. */
void mu_mv_special_pass(int32_t model, int32_t action, const uint8_t record[300], float delta, float time,
                         float alpha, float light, float *c8, mu_mv_pass *pass, float uv[2]);
#endif
