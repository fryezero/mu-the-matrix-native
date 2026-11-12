#ifndef MU_AURA_FX_H
#define MU_AURA_FX_H
#include "../joints/joints.h"
/* Authored presence only. IDs are the original visual consumer's IDs. */
enum { MU_AURA_ATTACK=1, MU_AURA_DEFENSE=2, MU_AURA_COMBINED=4,
       MU_AURA_HIDDEN=8, MU_AURA_ATTACK_UP=16, MU_AURA_DEFENSE_UP=32 };
typedef struct mu_aura_input {
    uint32_t buffs;
    int32_t owner, key, link[2];
    uint8_t existing4, existing9;
    float position[3], angle[3];
} mu_aura_input;
typedef struct mu_aura_env {
    const mu_jt_env *joint;
    int (*bone)(void *context, int32_t bone, float position[3]);
} mu_aura_env;
/* RenderCharacter 0x01370ccc..0x01371132. Missing bone ends the sprite loop. */
void mu_aura_plan(const mu_aura_input *in, const mu_aura_env *env);
/* Original CreateJoint common part and subtype 4. Other subtypes refused. */
int mu_aura_create(mu_jt_joint *j, const mu_aura_input *in, const mu_jt_env *env);
/* MoveJoint subtype 4, ordinary context with no equipment-driven subtype-9 switch. */
int mu_aura_move(mu_jt_joint *j, uint32_t buffs, const mu_jt_env *env, int32_t index, float step);
int mu_aura_render(const mu_jt_joint *j, uint8_t mode, float clock, const mu_jt_env *env, const mu_jt_gl *gl);
#endif
