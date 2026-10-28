/* Synthetic lifecycle check for the optional HelpWindow adapter. */
#include "../gfx/mu_gfx_layer.h"
#include "../world/world_gfx_help.h"
#include "../core/mu_lang.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

const char *mu_lang_text_or(const mu_lang *lang, int32_t id, const char *fallback)
{
    (void)lang; (void)id;
    return fallback;
}

int main(int argc, char **argv)
{
    assert(argc == 5);
    mu_gfx_layer_config cfg = {.movie_dir = argv[1], .lib_path = argv[2], .width = 1024, .height = 768,
                               .standalone = 1};
    char error[512];
    mu_gfx_layer *layer = mu_gfx_layer_open(&cfg, error, sizeof error);
    if (!layer) { fprintf(stderr, "%s\n", error); return 1; }
    assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
    assert(!mu_gfx_layer_key(layer, 1, 'H', 0, 2));
    int ready = world_gfx_help_load(layer, argv[3], NULL);
    assert(ready == atoi(argv[4]));
    assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
    if (ready) {
        assert(mu_gfx_layer_key(layer, 1, 'H', 0, 2));
        assert(mu_gfx_layer_is_open(layer, MU_GFX_HELP));
        mu_gfx_layer_key(layer, 0, 'H', 0, 2);
        assert(mu_gfx_layer_is_open(layer, MU_GFX_HELP));
        assert(mu_gfx_layer_key(layer, 1, 27, 0, 0));
        assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
        assert(mu_gfx_layer_key(layer, 1, 'H', 0, 2));
        assert(mu_gfx_layer_key(layer, 1, 'H', 0, 2));
        assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
        mu_gfx_layer_key(layer, 1, 13, 0, 0);
        mu_gfx_layer_key(layer, 1, 'H', 0, 2);
        assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
        mu_gfx_layer_key(layer, 1, 27, 0, 0);
        assert(mu_gfx_layer_key(layer, 1, 'H', 0, 2));
        assert(mu_gfx_layer_is_open(layer, MU_GFX_HELP));
        mu_gfx_layer_help_ready(layer, 0);
        assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
    } else {
        assert(!mu_gfx_layer_key(layer, 1, 'H', 0, 2));
        assert(!mu_gfx_layer_is_open(layer, MU_GFX_HELP));
    }
    mu_gfx_layer_close(layer);
    printf("help lifecycle ready=%d ok\n", ready);
    return 0;
}
