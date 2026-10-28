/* A test host for native/world/world_gfx_options.c (NATIVE-PROGRESS-001): the options window and the
 * system menu without a GFx library.  The layer, the audio module and the text table are stubs that print
 * what the host asks of them; the window's game side (reconstructed/progress) and the menu's
 * (reconstructed/charsel) are the real code.
 *
 *   options-host SETTINGS_DIR OP...
 *     audio            attach a stub audio module (group volumes start at 1.0)
 *     load             replay the movies' onLoad (world_gfx.c does after the layer opened)
 *     key M            the layer's key: M = 0 the options window (O), 1 the system menu (Esc)
 *     call M JSON      a movie callback (M as above), e.g. ["onChange",{...}]
 *     step MS          logic time
 *     print            the values, the request and the stub audio's groups as a JSON line */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../world/world_gfx_options.h"
#include "../gfx/mu_gfx_layer.h"
#include "../../reconstructed/audio/client_audio.h"
#include "../core/mu_lang.h"

/* ---- stubs ---- */
struct stub_audio {
    float volume[4];
    int mute[4];
};
static struct stub_audio g_audio = {{1.0f, 1.0f, 1.0f, 1.0f}, {0, 0, 0, 0}};

float mu_audio_get_group_volume(mu_audio_client *c, int group)
{
    (void)c;
    return g_audio.volume[group & 3];
}
int mu_audio_get_group_mute(mu_audio_client *c, int group)
{
    (void)c;
    return g_audio.mute[group & 3];
}
void mu_audio_set_group_volume(mu_audio_client *c, int group, float volume)
{
    (void)c;
    g_audio.volume[group & 3] = volume;
    printf("audio volume %d %.4f\n", group, volume);
}
void mu_audio_set_group_mute(mu_audio_client *c, int group, int mute)
{
    (void)c;
    g_audio.mute[group & 3] = mute;
    printf("audio mute %d %d\n", group, mute);
}

const char *mu_gfx_layer_invoke(mu_gfx_layer *layer, int movie, const char *path, const char *method,
                                const char *args)
{
    (void)layer;
    printf("invoke %d %s %s %s\n", movie, path, method, args);
    return NULL;
}
const char *mu_gfx_layer_path(const mu_gfx_layer *layer, int movie)
{
    (void)layer;
    return movie == MU_GFX_MAIN ? "_level0.main" : "_level0.instance1";
}
void mu_gfx_layer_show(mu_gfx_layer *layer, int movie, int visible)
{
    (void)layer;
    printf("show %d %d\n", movie, visible);
}

mu_lang *mu_lang_load_default(void)
{
    return NULL;
}
void mu_lang_free(mu_lang *lang) { (void)lang; }
const char *mu_lang_text(const mu_lang *lang, int32_t index)
{
    (void)lang;
    (void)index;
    return NULL;
}

/* ---- hooks ---- */
static int g_use_audio;
static mu_audio_client *hook_audio(void *user)
{
    (void)user;
    return g_use_audio ? (mu_audio_client *)&g_audio : NULL;
}
static void hook_monster(void *user, int view)
{
    (void)user;
    printf("monster_info %d\n", view);
}
static void hook_chat(void *user, const char *text)
{
    (void)user;
    printf("chat %s\n", text);
}

int main(int argc, char **argv)
{
    if (argc < 2)
        return 2;
    wg_options_hooks h = {NULL, hook_audio, hook_monster, hook_chat};
    wg_options *o = wg_options_open((mu_gfx_layer *)&g_audio, argv[1], &h);
    if (!o)
        return 1;
    int movies[2] = {MU_GFX_OPTION, MU_GFX_SYSTEM_MENU};
    for (int i = 2; i < argc; i++) {
        const char *op = argv[i];
        if (!strcmp(op, "audio")) {
            g_use_audio = 1;
        } else if (!strcmp(op, "load")) {
            wg_options_call(o, MU_GFX_OPTION, "channel", "[\"onLoad\",\"_level0.instance1\"]");
            wg_options_call(o, MU_GFX_SYSTEM_MENU, "channel", "[\"onLoad\",\"_level0.instance1\"]");
        } else if (!strcmp(op, "key") && i + 1 < argc) {
            wg_options_call(o, movies[atoi(argv[++i]) & 1], "key", "[]");
        } else if (!strcmp(op, "call") && i + 2 < argc) {
            int m = movies[atoi(argv[i + 1]) & 1];
            wg_options_call(o, m, "channel", argv[i + 2]);
            i += 2;
        } else if (!strcmp(op, "step") && i + 1 < argc) {
            wg_options_step(o, atof(argv[++i]));
        } else if (!strcmp(op, "print")) {
            const mu_prg_options *v = wg_options_values(o);
            printf("{\"volume\": %d, \"mute\": %d, \"music_play\": %d, \"monster_info\": %d, \"auto_attack\": %d, "
                   "\"effect\": %d, \"request\": %d, \"effect_group\": %.4f, \"music_muted\": %d, \"path\": \"%s\"}\n",
                   (int)v->volume, (int)v->mute, (int)v->music_play, (int)v->monster_info, (int)v->auto_attack,
                   (int)v->effect, wg_options_take_request(o), g_audio.volume[2], g_audio.mute[0],
                   wg_options_path(o));
        } else {
            fprintf(stderr, "unknown op %s\n", op);
            return 2;
        }
    }
    wg_options_close(o);
    return 0;
}
