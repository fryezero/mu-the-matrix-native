/* parts/progress.c (WORLD-RT-001): experience, levels and stat points (NATIVE-PROGRESS-001, core/mu_progress with
 * the demo server): the demo server's answers through the client's handlers (reconstructed/progress), their
 * lines turned into the level-up's joints and ground effect at the hero, its sound and the chat lines. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_lang.h"
#ifndef MU_WORLD_NO_GL
#include "../../gfx/mu_gfx_layer.h"
#endif
#include "../world_rt_internal.h"

/* NATIVE-PROGRESS-001: GlobalText from the client's tables (MU_LANG_DIR), NULL for the stand-ins */
static const char *progress_text(void *context, int32_t index)
{
    (void)context;
    return mu_lang_text(mu_lang_shared(), index);
}

/* NATIVE-PROGRESS-001: the lines of the reconstructed progression handlers (reconstructed/progress): the
 * level-up's joints and ground effect at the hero, its sound, the chat lines. */
static void progress_line(void *context, const char *line)
{
    mu_world_rt *a = context;
    unsigned type = 0, sub = 0, scale_bits = 0, sound = 0;
    if (sscanf(line, "call 0153b02c %x o+158 o+158 o+164 %x o %x", &type, &sub, &scale_bits) == 3) {
        float scale;
        memcpy(&scale, &scale_bits, sizeof scale);
        if (a->combat)
            mu_combat_hero_joint(a->combat, (int32_t)type, (int32_t)sub, scale, 2);
    } else if (sscanf(line, "call 013c0eaa %x o+158 o+164 o+ec %x", &type, &sub) == 2) {
        if (a->combat)
            mu_combat_hero_effect(a->combat, (int32_t)type, (int32_t)sub);
    } else if (sscanf(line, "call 00a6ac96 %x", &sound) == 1) {
        if (a->has_sound)
            mu_audio_host_play(a->sound.host, (int32_t)sound, 0);   /* PlayBuffer(SOUND, 0, 0) */
    }
#ifndef MU_WORLD_NO_GL
    else if (!strncmp(line, "call 01219a39 \"", 15) || !strncmp(line, "call 0095f547 \"", 15)) {
        char text[256];
        size_t n = 0;
        for (const char *p = line + 15; *p && *p != '"' && n + 1 < sizeof text; p++)
            text[n++] = *p == '\\' && p[1] ? *++p : *p;
        text[n] = 0;
        if (a->gfx)
            mu_gfx_layer_chat(world_gfx_layer(a->gfx), 3, "", text);
    }
#endif
    if (!a->quiet && strncmp(line, "call 0153b02c", 13)) {
        char esc[600];
        size_t n = 0;
        for (const char *p = line; *p && n + 3 < sizeof esc; p++) {
            if (*p == '"' || *p == '\\')
                esc[n++] = '\\';
            esc[n++] = *p;
        }
        esc[n] = 0;
        printf("{\"progress_line\": \"%s\"}\n", esc);
    }
}

static int progress_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->progress_on && !a->progress) {   /* NATIVE-PROGRESS-001 */
        if (a->progress_config.class_byte == 0xff)
            a->progress_config.class_byte = a->class_byte;
        a->progress = calloc(1, sizeof *a->progress);
        if (a->progress) {
            a->progress->line = progress_line;
            a->progress->context = a;
            a->progress->global_text = progress_text;
            mu_progress_init(a->progress, &a->progress_config);
        }
    }
    return 0;
}

static void progress_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    free(a->progress);   /* NATIVE-PROGRESS-001 */
    a->progress = NULL;
}

/* The demo server's answers through the client's handlers. */
static void progress_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->progress)
        mu_progress_step(a->progress);
}

static void progress_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->progress) {   /* NATIVE-PROGRESS-001 */
        mu_progress_view v;
        mu_progress_get_view(a->progress, &v);
        printf("{\"progress\": {\"class\": %d, \"level\": %d, \"master_level\": %d, \"points\": %d, \"exp\": %lld, "
               "\"next_exp\": %lld, \"stats\": [%d, %d, %d, %d, %d], \"life_max\": %d, \"mana_max\": %d, "
               "\"damage\": [%d, %d], \"attack_rate\": %d, \"defense\": %d, \"defense_rate\": %d, \"kills\": %d, "
               "\"level_ups\": %d, \"requests\": %d, \"accepted\": %d, \"speed\": \"%s\", \"exp_bar\": %s}}\n",
               v.class_index, v.level, v.master_level, v.points, (long long)v.exp, (long long)v.next_exp,
               v.stats[0], v.stats[1], v.stats[2], v.stats[3], v.stats[4], v.life_max, v.mana_max, v.dmg_min,
               v.dmg_max, v.atk_rate, v.defense, v.def_rate, a->progress->kills, a->progress->level_ups,
               a->progress->requests, a->progress->accepted, v.speed_text,
               a->progress->exp_json[0] ? a->progress->exp_json : "null");
    }
}

const mu_world_part_ops mu_part_progress = {
    .name = "progress",
    .open = progress_open,
    .close = progress_close,
    .tick = progress_tick,
    .report_summary = progress_report_summary,
};
