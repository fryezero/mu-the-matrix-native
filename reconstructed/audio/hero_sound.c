/* The hero's footstep sound and HeroTile. See hero_sound.h. */
#include "hero_sound.h"

#include "client_audio.h"

/* cvttss2si: NaN and out-of-range values give 0x80000000. */
static int32_t truncate_float(float value)
{
    if (!(value >= -2147483648.0f && value < 2147483648.0f))
        return INT32_MIN;
    return (int32_t)value;
}

int32_t mu_hero_tile_index(float x, float y)
{
    /* 0x016ad7a5: cvttss2si, cdq, idiv 100 (truncating), shl 8, add */
    int32_t ty = truncate_float(y) / 100;
    int32_t tx = truncate_float(x) / 100;
    int32_t index = (int32_t)(((uint32_t)ty << 8) + (uint32_t)tx);
    if (index < 0)           /* jns on the add's sign flag */
        return 0;
    if (index > 0xffff)
        return 0xffff;
    return index;
}

int32_t mu_hero_tile(const uint8_t *layer1, float x, float y)
{
    return layer1[mu_hero_tile_index(x, y)];   /* movzx byte [index + 0x0b735420] */
}

int mu_world_is_water(int32_t world)
{
    return mu_world_is_atlans(world) || (world >= 0x18 && world <= 0x1d) || world == 0x24;
}

int32_t mu_walk_sound_id(const mu_walk_sound_state *s, const uint16_t *attributes)
{
    if (s->hero_action >= 0x59 && s->hero_action <= 0x5f)
        return -1;
    if (s->manager_state)
        return -1;
    const int32_t w = s->world;
    if (w == 2 && s->hero_tile != 3 && s->hero_tile < 10)
        return MU_SOUND_WALK_SNOW;
    if (w == 0 && s->hero_tile == 0)
        return MU_SOUND_WALK_GRASS;
    if (w == 3 && s->hero_tile == 0)
        return MU_SOUND_WALK_GRASS;
    if (mu_world_is_water(w) && !s->hero_safe_zone)
        return MU_SOUND_SWIM;
    if (w >= 0x39 && w <= 0x3a)      /* 0x00ea233c */
        return MU_SOUND_WALK_SNOW;
    if (w == 0x79)
        return MU_SOUND_WALK_SNOW;
    if (w == 0x3e)                   /* 0x00e42f6d */
        return MU_SOUND_WALK_SNOW;
    if (w == 0x7a) {
        /* 0x016d34db: ((y & 0xff) << 8) + (x & 0xff) */
        uint32_t index = (((uint32_t)s->hero_y & 0xffu) << 8) + ((uint32_t)s->hero_x & 0xffu);
        return (attributes[index] & 0x8000) ? MU_SOUND_WALK_BRIDGE : MU_SOUND_WALK_SOIL;
    }
    return MU_SOUND_WALK_SOIL;
}

int mu_footstep_trigger(int32_t object_type, int is_hero, uint16_t action, float frame, uint8_t foot[2])
{
    if (object_type != 0xa91 || !is_hero)
        return 0;
    int walking = (action >= 0x32 && action <= 0x3e) || (action >= 0x4f && action < 0x6f);
    if (!walking)
        return 0;
    int calls = 0;
    if (frame >= 1.5f && !foot[0]) {   /* comiss; jb: unordered skips */
        foot[0] = 1;
        ++calls;
    }
    if (frame >= 4.5f && !foot[1]) {
        foot[1] = 1;
        ++calls;
    }
    return calls;
}

int mu_footstep_reset(uint8_t step_result, uint8_t foot[2], int32_t *field_168)
{
    if (step_result)
        return 0;
    *field_168 = -1;
    foot[0] = 0;
    foot[1] = 0;
    return 1;
}
