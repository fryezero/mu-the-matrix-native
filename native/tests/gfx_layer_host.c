/* Test host for native/gfx/mu_gfx_layer.c (NATIVE-GFX-002).
 *
 *   gfx-layer-host MOVIE_DIR LIBMUGFX [OP ...]
 *
 * Opens the layer (no GL: compiled with -DMU_GFX_NO_GL, read-back path) on
 * the given library (the real libmugfx or tests/gfx_stub_mugfx.c), adds
 * three demo items and runs the ops in order:
 *   key VK | text STR | click CELL | rclick CELL | hover CELL | at X Y (click)
 *   | closebtn | advance MS | composite | open MOVIE | print
 * `print` writes one JSON line with the layer state; each input op prints
 * whether the interface took it. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gfx/mu_gfx_layer.h"

static void print_state(mu_gfx_layer *L)
{
    printf("{\"inventory_open\": %d, \"character_open\": %d, \"held\": %d, \"cells\": [",
           mu_gfx_layer_is_open(L, MU_GFX_INVENTORY), mu_gfx_layer_is_open(L, MU_GFX_CHARACTER), mu_gfx_layer_held(L));
    for (int i = 0; i < mu_gfx_layer_item_count(L); i++)
        printf("%s%d", i ? ", " : "", mu_gfx_layer_item_cell(L, i));
    int32_t v[4];
    mu_gfx_layer_view(L, MU_GFX_INVENTORY, v);
    printf("], \"text_active\": %d, \"chat_sent\": \"%s\", \"main_path\": \"%s\", \"inventory_path\": \"%s\", "
           "\"inventory_view\": [%d, %d, %d, %d], \"points\": %d}\n",
           mu_gfx_layer_text_active(L), mu_gfx_layer_last_sent(L), mu_gfx_layer_path(L, MU_GFX_MAIN),
           mu_gfx_layer_path(L, MU_GFX_INVENTORY), v[0], v[1], v[2], v[3], mu_gfx_layer_hero(L)->points);
    fflush(stdout);
}

static int click(mu_gfx_layer *L, double x, double y, int button)
{
    mu_gfx_layer_mouse(L, 0, 0, x, y);
    int took = mu_gfx_layer_mouse(L, 1, button, x, y);
    mu_gfx_layer_mouse(L, 2, button, x, y);
    return took;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s MOVIE_DIR LIBMUGFX [OP ...]\n", argv[0]);
        return 2;
    }
    char error[512];
    double scale = getenv("MU_GFX_SCALE") ? atof(getenv("MU_GFX_SCALE")) : 1.0;
    mu_gfx_layer_config cfg = {argv[1], argv[2], (int32_t)(1280 * scale), (int32_t)(800 * scale), 1, 0, 0, NULL, NULL,
                               getenv("MU_GFX_LOG") ? stderr : NULL, scale};
    mu_gfx_layer *L = mu_gfx_layer_open(&cfg, error, sizeof error);
    if (!L) {
        printf("{\"error\": \"%s\"}\n", error);
        return 1;
    }
    mu_gfx_layer_add_item(L, 0, 9, 1, 3, "Kris");
    mu_gfx_layer_add_item(L, 3584, 7, 2, 2, "Bronze Helm");
    mu_gfx_layer_add_item(L, 7171, 0, 1, 1, "Healing Potion");
    for (int i = 3; i < argc; i++) {
        const char *op = argv[i], *a = i + 1 < argc ? argv[i + 1] : "0";
        double x, y;
        if (!strcmp(op, "print")) {
            print_state(L);
        } else if (!strcmp(op, "key")) {
            int vk = atoi(a);
            int d = mu_gfx_layer_key(L, 1, vk, 0, 0), u = mu_gfx_layer_key(L, 0, vk, 0, 0);
            printf("key %d took %d %d\n", vk, d, u);
            i++;
        } else if (!strcmp(op, "text")) {
            printf("text took %d\n", mu_gfx_layer_text(L, a));
            i++;
        } else if (!strcmp(op, "click") || !strcmp(op, "rclick") || !strcmp(op, "hover")) {
            if (!mu_gfx_layer_cell_center(L, atoi(a), &x, &y)) {
                printf("%s %s: no geometry\n", op, a);
            } else if (!strcmp(op, "hover")) {
                printf("hover %s took %d\n", a, mu_gfx_layer_mouse(L, 0, 0, x, y));
            } else {
                printf("%s %s took %d\n", op, a, click(L, x, y, op[0] == 'r' ? 1 : 0));
            }
            i++;
        } else if (!strcmp(op, "at") && i + 2 < argc) {
            printf("at %s %s took %d\n", argv[i + 1], argv[i + 2],
                   click(L, atof(argv[i + 1]) * scale, atof(argv[i + 2]) * scale, 0));
            i += 2;
        } else if (!strcmp(op, "closebtn")) {
            int32_t v[4];
            mu_gfx_layer_view(L, MU_GFX_INVENTORY, v);
            printf("closebtn took %d\n", click(L, (1280 - 332 + 315) * scale, (20 + 10) * scale, 0));
        } else if (!strcmp(op, "advance")) {
            mu_gfx_layer_advance(L, atof(a));
            i++;
        } else if (!strcmp(op, "composite")) {
            int32_t W = (int32_t)(1280 * scale), H = (int32_t)(800 * scale);
            uint8_t *px = calloc((size_t)W * (size_t)H, 4);
            mu_gfx_layer_composite(L, px, W, H);
            long drawn = 0;
            for (size_t p = 0; p < (size_t)W * (size_t)H; p++)
                drawn += px[p * 4 + 3] != 0;
            printf("composite drawn %ld\n", drawn);
            free(px);
        } else if (!strcmp(op, "open")) {
            mu_gfx_layer_toggle(L, atoi(a));
            i++;
        } else {
            fprintf(stderr, "unknown op %s\n", op);
            return 2;
        }
    }
    mu_gfx_layer_close(L);
    return 0;
}
