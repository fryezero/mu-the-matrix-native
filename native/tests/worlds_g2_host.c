/* RENDER-WORLDS-G2 production host: OpenTexture's name map and Item retries over a synthetic game root
 * (mu_texture_names), and the Vulcanus far plane through mu_walk_init / mu_walk_begin_render.
 *   worlds-g2-host ROOT   (ROOT prepared by test_native_worlds_g2.py) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/objects/texture_lookup.h"
#include "../core/mu_terrain.h"
#include "../core/mu_texture_names.h"
#include "../core/mu_walk.h"

static int failures;

static void expect(const char *root, int32_t world, const char *sub, const char *name, int want_found,
                   int want_step, const char *want_suffix)
{
    char path[2048] = "";
    int step = 0;
    const int found = mu_texture_names_find(root, world, sub, name, path, sizeof path, &step);
    const size_t n = strlen(path), m = want_suffix ? strlen(want_suffix) : 0;
    const int suffix_ok = !want_suffix || (n >= m && !strcmp(path + n - m, want_suffix));
    if (found != want_found || step != want_step || !suffix_ok) {
        fprintf(stderr, "world %d %s%s: found %d step %d path %s (want %d %d %s)\n", world, sub, name, found, step,
                path, want_found, want_step, want_suffix ? want_suffix : "-");
        ++failures;
    }
}

static float far_of(int32_t world)
{
    static mu_walk walk;
    mu_world *map = calloc(1, sizeof *map);
    if (!map)
        return -1.0f;
    map->world = world;
    const mu_camera_info info = {{0, 0, 0}, {0, 0, 0}, 0.179f, 9.1f, 39.0f, 0};
    mu_walk_init(&walk, map, &info, 640, 480, 128, 128, 0.0f, 0, 1, 20.0f);
    mu_walk_begin_render(&walk, 1000);
    const float far = walk.frame.view.view_far;
    mu_walk_free(&walk);
    free(map);
    return far;
}

int main(int argc, char **argv)
{
    if (argc != 2)
        return 2;
    const char *root = argv[1];
    /* Deep Dungeon 1 (116, folder 117): its pass preloads Data\Object2\DungeonStone01 before the objects. */
    expect(root, 116, "Object117\\", "direct.tga", 1, MU_TL_DIRECT, "Object117/direct.OZT");
    expect(root, 116, "Object117\\", "probe.tga", 1, MU_TL_NAME_MAP, "Skill/probe.OZT");
    expect(root, 116, "Object117\\", "PROBE.tga", 1, MU_TL_NAME_MAP, "Skill/probe.OZT");
    expect(root, 116, "Object117\\", "wallx.tga", 1, MU_TL_NAME_MAP, "Object2/wallx.OZT");
    expect(root, 116, "Object117\\", "itemonly.tga", 1, MU_TL_ITEM, "Item/itemonly.OZT");
    expect(root, 116, "Object117\\", "deep.tga", 1, MU_TL_ITEM_TEXTURE, "Texture/deep.OZT");
    expect(root, 116, "Object117\\", "skin_x.tga", 0, MU_TL_DIRECT, NULL);
    expect(root, 116, "Object117\\", "nowhere.tga", 0, MU_TL_MISSING, NULL);
    /* Vulcanus (63) preloads only Monster models: Object2's wall is not in its map; the startup skeleton is. */
    expect(root, 63, "Object64\\", "wallx.tga", 0, MU_TL_MISSING, NULL);
    expect(root, 63, "Object64\\", "probe.tga", 1, MU_TL_NAME_MAP, "Skill/probe.OZT");
    /* back to 116: the world extras are rebuilt */
    expect(root, 116, "Object117\\", "wallx.tga", 1, MU_TL_NAME_MAP, "Object2/wallx.OZT");
    mu_texture_names_stats stats;
    mu_texture_names_get_stats(&stats);
    if (stats.startup_models != 1 || stats.world_models != 1 || stats.world != 116) {
        fprintf(stderr, "stats: startup %d world %d (%d)\n", stats.startup_models, stats.world_models, stats.world);
        ++failures;
    }
    /* MoveMainCamera's event-world far plane: 3700 in Vulcanus and 0x52..0x5a, 2000 * 9.1 * 0.179 elsewhere */
    const int32_t worlds[] = {63, 0x52, 0x5a, 62, 64, 0x5b};
    const float want[] = {3700.0f, 3700.0f, 3700.0f, 2000.0f * 9.1f * 0.179f, 2000.0f * 9.1f * 0.179f,
                          2000.0f * 9.1f * 0.179f};
    for (int i = 0; i < 6; ++i) {
        const float far = far_of(worlds[i]);
        if (far < want[i] - 0.01f || far > want[i] + 0.01f) {
            fprintf(stderr, "world %d far %.3f want %.3f\n", worlds[i], (double)far, (double)want[i]);
            ++failures;
        }
    }
    if (failures)
        return 1;
    printf("worlds-g2 host: 11 lookups, 6 far planes ok\n");
    return 0;
}
