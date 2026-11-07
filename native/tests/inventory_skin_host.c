/* Actual GFx item/FBO consumer on authored models. No movie/runtime/session.
 * INVENTORY-FX: `world` as the second argument gives the icons a world particle pool (wg_items_set_world): the
 * client's icon effects join the world's sprite list and are never drawn over the icon. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../world/world_gfx_game.h"
#include "../viewer/gl_headless.h"
#include "../core/mu_particles.h"
#include "../core/mu_png.h"

static struct mu_world_particles *pool_of(void *user)
{
    return user;
}

int main(int argc, char **argv)
{
    if (argc != 2 && argc != 3) return 2;
    const int with_world = argc == 3 && !strcmp(argv[2], "world");
    char error[256];
    if (mu_gl_headless_begin(256, 256, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 3;
    }
    wg_items *w = wg_items_open(argv[1]);
    if (!w) return 4;
    mu_world_particles *pool = NULL;
    if (with_world) {
        pool = calloc(1, sizeof *pool);
        if (!pool || mu_world_particles_open(pool, argv[1], NULL, 0, 1, 0, error, sizeof error)) {
            fprintf(stderr, "%s\n", error);
            return 7;
        }
        const wg_items_world world = {pool, pool_of, NULL};
        wg_items_set_world(w, &world);
    }
    mu_gfx_item_draw d = {0};
    d.code = 0x1c17;
    d.level = 1;
    d.slot[0] = d.slot[1] = 220;
    d.slot[2] = d.slot[3] = 100;
    d.rect[0] = d.rect[1] = 80;
    d.rect[2] = d.rect[3] = 100;
    d.frame_scale = d.alpha = 1;
    uint8_t rgba[256*256*4];
    char hashes[4][65];
    const double clocks[4] = {0, 0, 500, 0};
    for (int i = 0; i < 4; ++i) {
        wg_items_set_time(w, clocks[i]);
        if (pool)
            pool->world_time = (float)clocks[i];
        if (wg_items_icons(w, &d, 1, rgba, 256, 256)) return 5;
        mu_sha256_hex(rgba, sizeof rgba, hashes[i]);
        char path[4096];
        snprintf(path, sizeof path, "%s/gfx-skin-%d.png", argv[1], i);
        if (mu_png_write(path, rgba, 256, 256)) return 6;
    }
    long drawn, missing, icons;
    wg_items_counts(w, &drawn, &missing, &icons);
    printf("{\"drawn\":%ld,\"missing\":%ld,\"icons\":%ld,\"world_sprites\":%llu,"
           "\"hashes\":[\"%s\",\"%s\",\"%s\",\"%s\"]}\n",
           drawn, missing, icons, pool ? (unsigned long long)pool->stats.sprites_created : 0ULL, hashes[0],
           hashes[1], hashes[2], hashes[3]);
    wg_items_close(w);
    if (pool) {
        mu_world_particles_close(pool);
        free(pool);
    }
    mu_gl_headless_end();
    return 0;
}
