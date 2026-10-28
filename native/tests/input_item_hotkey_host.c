/* Existing native item policy, with synthetic movies and the stub renderer. */
#include <assert.h>
#include <stdio.h>
#include "../gfx/mu_gfx_layer.h"
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    mu_gfx_layer_config cfg = {0};
    cfg.movie_dir = argv[1]; cfg.lib_path = argv[2]; cfg.width = 640; cfg.height = 480;
    char error[512];
    mu_gfx_layer *l = mu_gfx_layer_open(&cfg, error, sizeof error);
    if (!l) { fprintf(stderr, "%s\n", error); return 1; }
    int hp = mu_gfx_layer_hero(l)->hp;
    for (int slot = 1; slot < 4; ++slot) assert(!mu_gfx_layer_use_item_hotkey(l, slot));
    assert(mu_gfx_layer_hero(l)->hp == hp);
    assert(!mu_gfx_layer_use_item_hotkey(l, -1));
    assert(!mu_gfx_layer_use_item_hotkey(l, 4));
    assert(mu_gfx_layer_use_item_hotkey(l, 0));
    assert(mu_gfx_layer_hero(l)->hp > hp);
    assert(mu_gfx_layer_hero(l)->hp <= mu_gfx_layer_hero(l)->max_hp);
    for (int n = 1; n < 25; ++n) assert(mu_gfx_layer_use_item_hotkey(l, 0));
    assert(!mu_gfx_layer_use_item_hotkey(l, 0));
    mu_gfx_layer_close(l);
    puts("item hotkeys: 25 uses, three empty slots, invalid indices and exhaustion verified");
    return 0;
}
