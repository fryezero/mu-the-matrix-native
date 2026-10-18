/* In-world sound for the walk-around session. See mu_world_audio.h. */
#include "mu_world_audio.h"

#include <stdio.h>
#include <string.h>

static void log_line(mu_world_sound *s, const char *text)
{
    if (s->log_count < MU_WORLD_SOUND_LOG)
        snprintf(s->log[s->log_count++], sizeof s->log[0], "%s", text);
}

static void observe(void *ctx, int kind, int32_t a, int32_t b)
{
    mu_world_sound *s = ctx;
    (void)b;
    char text[96];
    switch (kind) {
    case MU_WORLD_SND_PLAY:
        ++s->ambient_plays;
        break;
    case MU_WORLD_SND_STOP:
        ++s->ambient_stops;
        break;
    case MU_WORLD_MP3_PLAY:
        ++s->music_plays;
        if (a != s->last_music) {
            const char *path = s->has_table ? mu_audio_table_music_path(&s->table, a) : NULL;
            snprintf(text, sizeof text, "frame %u: music %d %s", s->frames, a, path ? path : "(unresolved)");
            for (char *c = text; *c; ++c)   /* report-friendly separators */
                if (*c == '\\')
                    *c = '/';
            log_line(s, text);
            s->last_music = a;
        }
        break;
    case MU_WORLD_MP3_STOP:
        ++s->music_stops;
        break;
    default:
        ++s->delegates;
        break;
    }
}

int mu_world_sound_open(mu_world_sound *s, const char *game_root, const char *table_path, uint32_t rate,
                        int32_t world, char *error, size_t error_size)
{
    memset(s, 0, sizeof *s);
    s->world = world;
    s->last_music = -1;
    s->field_168 = 0;
    if (table_path) {
        if (mu_audio_table_load(table_path, &s->table, error, error_size))
            return 1;
        s->has_table = 1;
    }
    mu_audio_host_config config;
    memset(&config, 0, sizeof config);
    config.engine.rate = rate ? rate : 44100;
    config.engine.game_root = game_root;
    config.table = s->has_table ? &s->table : NULL;
    s->host = mu_audio_host_new(&config, error, error_size);
    if (!s->host) {
        if (s->has_table)
            mu_audio_table_free(&s->table);
        s->has_table = 0;
        return 1;
    }
    mu_audio_host_set_observer(s->host, observe, s);
    /* OpenWorld 0x018290be: Music group 1.0 for the listed worlds, else 0.4 */
    mu_audio_set_group_volume(mu_audio_host_client(s->host), MU_AUDIO_GROUP_MUSIC, mu_audio_world_music_volume(world));
    return 0;
}

void mu_world_sound_close(mu_world_sound *s)
{
    if (s->host)
        mu_audio_host_free(s->host);
    if (s->has_table)
        mu_audio_table_free(&s->table);
    memset(s, 0, sizeof *s);
}

int32_t mu_world_sound_hero_step(mu_world_sound *s, const mu_world_sound_hero *h, const uint8_t *layer1,
                                 const uint16_t *attributes)
{
    ++s->steps;
    /* MoveHero tail 0x016ad7a5: HeroTile */
    s->hero_tile = mu_hero_tile(layer1, h->position[0], h->position[1]);
    /* 0x013a763e after the animation step 0x013960d2 */
    if (mu_footstep_reset(h->step_result, s->foot, &s->field_168))
        ++s->resets;
    /* 0x013b23f8: footstep trigger, PlayWalkSound per call */
    int calls = mu_footstep_trigger(h->object_type, 1, h->action, h->frame, s->foot);
    int32_t played = -1;
    for (int i = 0; i < calls; ++i) {
        mu_walk_sound_state state = {s->world, s->hero_tile, h->action, h->safe_zone, h->tile[0], h->tile[1], 0};
        int32_t id = mu_walk_sound_id(&state, attributes);
        if (id < 0)
            continue;
        if (s->host)
            mu_audio_host_play(s->host, id, 0);   /* SND_Play(id, hero, 0) */
        ++s->footsteps;
        if (id >= MU_SOUND_WALK_SOIL && id <= MU_SOUND_SWIM)
            ++s->footstep_ids[id - MU_SOUND_WALK_SOIL];
        else if (id == MU_SOUND_WALK_BRIDGE)
            ++s->bridge_steps;
        played = id;
    }
    return played;
}

void mu_world_sound_frame(mu_world_sound *s, const mu_world_sound_hero *h, uint16_t attribute)
{
    ++s->frames;
    if (!s->host)
        return;
    mu_world_audio_state state;
    memset(&state, 0, sizeof state);
    state.scene = 6;
    state.world = s->world;
    state.hero_tile = s->hero_tile;
    state.rain = s->rain;
    state.hero_safe_zone = h->safe_zone;
    state.hero_x = h->tile[0];
    state.hero_y = h->tile[1];
    state.hero_attribute = attribute;
    mu_audio_host_set_world(s->host, &state, 0);
    mu_audio_host_tick(s->host);   /* the frame block, then System::update */
}

void mu_world_sound_mix(mu_world_sound *s, float *out, uint32_t frames)
{
    if (s->host) {
        mu_audio_engine_mix(mu_audio_host_engine(s->host), out, frames);
    } else {
        memset(out, 0, (size_t)frames * 2 * sizeof *out);
    }
}

uint32_t mu_world_sound_rate(const mu_world_sound *s)
{
    return s->host ? mu_audio_engine_rate(mu_audio_host_engine(s->host)) : 44100;
}

int mu_world_sound_voices(const mu_world_sound *s)
{
    return s->host ? mu_audio_engine_active_voices(mu_audio_host_engine(s->host)) : 0;
}
