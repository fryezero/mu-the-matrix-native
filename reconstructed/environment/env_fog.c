/* The render scene's fog tests (RENDER-WORLDS-FOG). See env_fog.h. */
#include "env_fog.h"

#include <string.h>

/* The box both tests compare with comiss/jb: x >= 16100 (0x01af7098), 19000 (0x01aae3f0) >= x,
 * y >= 18900 (0x01af70a0), 21700 (0x01af70a4) >= y. An unordered compare sets CF, so NaN fails each. */
static int in_box(const float p[3])
{
    return p[0] >= 16100.0f && 19000.0f >= p[0] && p[1] >= 18900.0f && 21700.0f >= p[1];
}

int mu_env_scene_fog_begin(int32_t world, const float hero[3], mu_env_fog *fog)
{
    if (world != 0x1e)
        return MU_ENV_FOG_KEEP;
    if (!in_box(hero))
        return MU_ENV_FOG_OFF;
    memset(fog, 0, sizeof *fog);
    fog->mode = 9729.0f;
    fog->start = 2000.0f;
    fog->end = 2700.0f;
    return MU_ENV_FOG_ON;
}

int mu_env_scene_fog_end(int32_t world, const float hero[3])
{
    return world == 0x1e && in_box(hero);
}
