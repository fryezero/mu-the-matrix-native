/* Actual GFx item/FBO consumer on authored models. No movie/runtime/session. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../world/world_gfx_game.h"
#include "../viewer/gl_headless.h"
#include "../core/mu_png.h"

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    char error[256];
    if (mu_gl_headless_begin(256, 256, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 3;
    }
    wg_items *w = wg_items_open(argv[1]);
    if (!w) return 4;
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
        if (wg_items_icons(w, &d, 1, rgba, 256, 256)) return 5;
        mu_sha256_hex(rgba, sizeof rgba, hashes[i]);
        char path[4096];
        snprintf(path, sizeof path, "%s/gfx-skin-%d.png", argv[1], i);
        if (mu_png_write(path, rgba, 256, 256)) return 6;
    }
    long drawn, missing, icons;
    wg_items_counts(w, &drawn, &missing, &icons);
    printf("{\"drawn\":%ld,\"missing\":%ld,\"icons\":%ld,\"hashes\":[\"%s\",\"%s\",\"%s\",\"%s\"]}\n",
           drawn, missing, icons, hashes[0], hashes[1], hashes[2], hashes[3]);
    wg_items_close(w);
    mu_gl_headless_end();
    return 0;
}
