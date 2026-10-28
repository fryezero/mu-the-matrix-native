/* Per-world environment table and asset names (NATIVE-ENV-001). The table
 * restates the branches of the routines (static readings); the routines
 * themselves are what runs. */
#include <stdio.h>
#include <string.h>

#include "env.h"
#include "env_internal.h"

/* glClearColor of the render scene 0x0185916b (0x01859419..0x0185967b). */
static void clear_color(int32_t w, float rgb[3])
{
    rgb[0] = rgb[1] = rgb[2] = 0.0f;
    if (w == 0) {
        rgb[0] = 0.0390625f;    /* 10/256 */
        rgb[1] = 0.078125f;     /* 20/256 */
        rgb[2] = 0.0546875f;    /* 14/256 */
    } else if (w == 2) {
        rgb[2] = 0.0390625f;
    } else if (w == 0xa) {
        rgb[0] = 0.01171875f;
        rgb[1] = 0.09765625f;
        rgb[2] = 0.171875f;
    } else if (env_chaos_castle(w)) {
    } else if (w >= 0x2d && w <= 0x32) {
        rgb[0] = 0.03515625f;
        rgb[1] = 0.03125f;
        rgb[2] = 0.12890625f;
    } else if (env_kalima(w)) {
    } else if (w == 0x84) {
        rgb[0] = 0.149019614f;  /* 0x3e189899 */
    }
}

void mu_env_world_info_get(int32_t w, mu_env_world_info *info)
{
    memset(info, 0, sizeof *info);
    info->world = w;
    clear_color(w, info->clear);
    info->fog = w == 0x1e;
    /* MoveBoids: walk limit and the model of the spawn branch */
    if (w == 7 || env_abyss(w))
        info->boid_limit = 40;
    else if (w == 0xa || w == 0x84)
        info->boid_limit = 13;
    else if (w == 0x33)
        info->boid_limit = 2;
    else
        info->boid_limit = env_kalima(w) ? 2 : 5;
    info->boid_model = -1;
    if (w == 0)
        info->boid_model = MU_ENV_MODEL_BIRD;
    else if (w == 1 || w == 4 || env_deep_dungeon(w))
        info->boid_model = MU_ENV_MODEL_BAT;
    else if (w == 3)
        info->boid_model = MU_ENV_MODEL_BUTTERFLY;
    else if (env_blood_castle(w))
        info->boid_model = MU_ENV_MODEL_CROW;
    else if (w == 0x33)
        info->boid_model = MU_ENV_MODEL_ELBELAND;
    else if (env_atlans(w))
        info->boid_model = MU_ENV_MODEL_ATLANS_FISH;   /* 0x199 or 0x19a */
    else if (w == 0xa || w == 0x84)
        info->boid_model = 0x7c4;
    /* MoveFishs */
    info->fish_limit = (env_water_world(w) || w == 8 || w == 0x22 || w == 0x85) ? 10 : 3;
    info->fish_model = -1;
    if (w == 0 || w == 8 || w == 0x21 || w == 0x86)
        info->fish_model = MU_ENV_MODEL_FISH;
    else if (w == 1 || env_deep_dungeon(w))
        info->fish_model = MU_ENV_MODEL_RAT;
    else if (w == 6)
        info->fish_model = MU_ENV_MODEL_BUG;
    else if (w == 7 || env_abyss(w) || w == 0x85)
        info->fish_model = -2;   /* 0x199..0x1a0 */
    else if (w == 0x22)
        info->fish_model = 0x1b3;
    /* MoveLeaves */
    int32_t count = env_devil_square(w) ? 200 : 80;
    if (env_chaos_castle(w) || w == 0x37 || w == 0x83 || w == 0x85 || w == 0x88 || w == 0x8d || w == 0x8e)
        count = 80;
    else if (w == 0x1e)
        count = 40;
    else if (w == 0x71)
        count = 200;
    info->leaf_count = mu_env_leaves_active(w, 0, env_tormenta(w)) ? count : 0;
    info->leaf_bitmap = -1;
    if (w == 0 || w == 3 || env_atlans(w) || w == 2)
        info->leaf_bitmap = MU_ENV_BITMAP_LEAF1;
    else if (w == 0xa || w == 0x84 || env_tormenta(w) || env_devil_square(w) || env_chaos_castle(w))
        info->leaf_bitmap = MU_ENV_BITMAP_RAIN;
    if (w == 0x8f)
        info->leaf_blend = -1;
    else if (w == 2 || w == 7 || w == 0xa || env_abyss(w) || w == 0x84 || w == 0x85 || env_tormenta(w) ||
             w == 0x1e || w == 0x37 || w == 0x2a || env_event_leaf_world(w))
        info->leaf_blend = 1;
    info->leaf_billboard = w == 2 || (w >= 0x39 && w <= 0x3a) || w == 0x3e || w == 0x79;
}

int mu_env_model_file(int32_t world, int32_t model, char *out, size_t out_size)
{
    if (world == 10 && model == 0x7c4) {
        int n = snprintf(out,out_size,"Data/Monster/Monster32.bmd");
        return n>0 && (size_t)n<out_size;
    }
    if (world == 51 && (model == 0x1a3 || model == 0x1a4)) {
        int n = snprintf(out, out_size, "Data/Object52/%s.bmd", model == 0x1a3 ? "sos3bi01" : "typhoonall");
        return n > 0 && (size_t)n < out_size;
    }
    const char *name = NULL;
    int32_t folder = 0, number = 1;
    if (world == 8 && model == 0x198) {   /* Tarkan: AccessModel(0x198, Data\Object9\, Bug, 2) */
        name = "Bug";
        folder = 9;
        number = 2;
        model = -1;
    }
    switch (model) {
    case MU_ENV_MODEL_BIRD: name = "Bird"; folder = 1; break;
    case MU_ENV_MODEL_BUTTERFLY: name = "Butterfly"; folder = 1; break;
    case MU_ENV_MODEL_FISH: name = "Fish"; folder = 1; break;
    case MU_ENV_MODEL_BAT: name = "Bat"; folder = 2; break;
    case MU_ENV_MODEL_RAT: name = "Rat"; folder = 2; break;
    case MU_ENV_MODEL_BUG: name = "Bug"; folder = 7; break;
    case MU_ENV_MODEL_CROW: name = "Crow"; folder = 12; break;
    case -1:
        break;
    default:
        if (model >= 0x199 && model <= 0x1a0) {   /* 0x018392db, world 7: AccessModel(0x198 + k, Fish, k + 1) */
            name = "Fish";
            folder = 8;
            number = model - 0x198 + 1;
        }
        break;
    }
    if (!name)
        return 0;
    int n = snprintf(out, out_size, "Data/Object%d/%s%02d.bmd", folder, name, number);
    return n > 0 && (size_t)n < out_size;
}

int mu_env_bitmap_file(int32_t world, int32_t bitmap, char *out, size_t out_size)
{
    const char *name = NULL;
    /* 0x01829e21: "%s\\leaf01.jpg" (and leaf02.jpg) replace the .tga load in
     * every world but 0x5b/0x5c; CGlobalBitmap::LoadImage 0x00c97730 unloads
     * the .tga first, so a world without leaf01.OZJ ends with no bitmap. */
    int tga = world == 0x5b || world == 0x5c;
    switch (bitmap) {
    case MU_ENV_BITMAP_LEAF1: name = tga ? "leaf01.OZT" : "leaf01.OZJ"; break;
    case MU_ENV_BITMAP_LEAF2: if (tga) return 0; name = "leaf02.OZJ"; break;
    case MU_ENV_BITMAP_RAIN: name = world == 0x22 ? "rain011.OZT" : "rain01.OZT"; break;
    case MU_ENV_BITMAP_RAIN_SPLASH: name = "rain02.OZT"; break;
    case MU_ENV_BITMAP_RAIN_RING: name = "rain03.OZT"; break;
    default: return 0;
    }
    int32_t folder = world + 1;
    /* rain textures of the worlds outside the 0x5f..0x90 rain list come from World1/World10 */
    int rain_list = world == 0x5f || world == 0x60 || world == 0x6e || world == 0x6f || world == 0x90;
    if (bitmap == MU_ENV_BITMAP_RAIN && !rain_list)
        folder = 1;
    if (bitmap == MU_ENV_BITMAP_RAIN_SPLASH && !(rain_list || world == 0x8f))
        folder = 1;
    if (bitmap == MU_ENV_BITMAP_RAIN_RING && !(rain_list || world == 0x8f))
        folder = 10;
    int n = snprintf(out, out_size, "Data/World%d/%s", folder, name);
    return n > 0 && (size_t)n < out_size;
}
