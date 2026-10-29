/* RenderObject 0x016d4fe4 for the environment objects RenderBoids/RenderFishs draw (RENDER-WORLDS-G3): the
 * setup's alpha step and test (0x017ec896) and the draw's generic RenderBody (0x017edf43) for an object whose
 * type no custom render takes. The environment objects never write +0x03 (shadow), +0x80 (render mode) or
 * +0xac/+0xb0 (blend texture offsets), so those keep the zero of their start state. */
#include <string.h>

#include "env.h"
#include "env_internal.h"

static uint32_t f32_bits(float v)
{
    uint32_t u;
    memcpy(&u, &v, sizeof u);
    return u;
}

int mu_env_render_body(mu_env_object *o, int32_t world, int chaos_hero_flag, uint32_t args[8])
{
    /* setup: Chaos Castle (0x009dacb8) with the hero's flag 1 dims the object every call */
    if (env_chaos_castle(world) && chaos_hero_flag == 1)
        o->alpha = o->alpha - 0.15f;
    if (0.01f > o->alpha)
        return 0;
    /* draw, bounds mode 0: HiddenMesh -2 hides the whole object */
    if (o->field_68 == -2)
        return 0;
    args[0] = 2;                          /* +0x80 != 0x80 */
    args[1] = f32_bits(o->alpha);         /* +0xdc */
    args[2] = (uint32_t)o->field_74;      /* BlendMesh +0x74 */
    args[3] = f32_bits(o->field_a8);      /* BlendMeshLight +0xa8 */
    args[4] = 0;                          /* BlendMeshTexCoordU +0xac */
    args[5] = 0;                          /* BlendMeshTexCoordV +0xb0 */
    args[6] = (uint32_t)o->field_68;      /* HiddenMesh +0x68 */
    args[7] = 0xffffffffu;
    return 1;
}
