/* parts/sound.c (WORLD-RT-001): the world's sound (core/mu_world_audio, NATIVE-WORLD-002): every logic step
 * HeroTile, the foot-flag reset and the footstep trigger with PlayWalkSound; every rendered frame after the cap
 * the per-frame ambient/music block.  Output (SDL2 audio, the WAV file) is the front end's. */
#include <stdio.h>

#include "../world_rt_internal.h"

static int sound_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (a->audio) {
        if (mu_world_sound_open(&a->sound, a->root, a->sound_table, (uint32_t)a->audio_rate, a->world, error,
                                sizeof error)) {
            fprintf(stderr, "sound: %s\n", error);
            return 1;
        }
        a->has_sound = 1;
    }
    return 0;
}

static void sound_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->has_sound)
        mu_world_sound_close(&a->sound);
}

/* SND_Play of the ambient creatures (aBird1/aBird2/aBat/the rat) and the ground items. */
void world_rt_env_sound(void *context, int32_t id)
{
    mu_world_rt *a = context;
    if (a->has_sound)
        mu_audio_host_play(a->sound.host, id, 0);
}

/* End of every logic step: the client's MoveCharacters runs the hero's per-character routine (foot reset after
 * its animation step, footstep trigger in 0x013b23f8). HeroTile was set at the end of MoveHero, which
 * mu_world_sound_hero_step does first. */
static void sound_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    const mu_hero *h = &a->walk.hero;
    if (a->has_sound) {
        mu_world_sound_hero hero = {{h->position[0], h->position[1]}, {h->tile[0], h->tile[1]}, h->action,
                                    h->frame, h->step_result, h->safe_zone, 0xa91};
        int32_t id = mu_world_sound_hero_step(&a->sound, &hero, a->map->layer1, a->map->attributes);
        (void)id;
    }
}

/* Once per rendered frame after the frame cap: the per-frame audio block. */
void world_rt_sound_frame(mu_world_rt *a)
{
    if (!a->has_sound)
        return;
    const mu_hero *h = &a->walk.hero;
    mu_world_sound_hero hero = {{h->position[0], h->position[1]}, {h->tile[0], h->tile[1]}, h->action, h->frame,
                                h->step_result, h->safe_zone, 0xa91};
    uint16_t attribute = a->map->attributes[((h->tile[1] & 0xff) << 8) + (h->tile[0] & 0xff)];
    mu_world_sound_frame(&a->sound, &hero, attribute);
}

static void sound_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->has_sound) {
        const mu_world_sound *s = &a->sound;
        printf("{\"sound\": true, \"table\": %s, \"steps\": %u, \"frames\": %u, \"footsteps\": %u,"
               " \"soil\": %u, \"grass\": %u, \"snow\": %u, \"swim\": %u, \"bridge\": %u, \"foot_resets\": %u,"
               " \"ambient_plays\": %u, \"ambient_stops\": %u, \"music_plays\": %u, \"music_stops\": %u,"
               " \"delegates\": %u, \"last_music\": %d, \"wav_frames\": %zu, \"rate\": %u}\n",
               s->has_table ? "true" : "false", s->steps, s->frames, s->footsteps, s->footstep_ids[0],
               s->footstep_ids[1], s->footstep_ids[2], s->footstep_ids[3], s->bridge_steps, s->resets,
               s->ambient_plays, s->ambient_stops, s->music_plays, s->music_stops, s->delegates, s->last_music,
               a->wav_frames, mu_world_sound_rate(s));
        if (!a->quiet)
            for (int32_t i = 0; i < s->log_count; ++i)
                printf("{\"sound_log\": \"%s\"}\n", s->log[i]);
    }
}

const mu_world_part_ops mu_part_sound = {
    .name = "sound",
    .open = sound_open,
    .close = sound_close,
    .tick = sound_tick,
    .report_summary = sound_report_summary,
};
