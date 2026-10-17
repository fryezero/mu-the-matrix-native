/* Per-frame ambient loops and music selection: client block
 * 0x0185280c..0x01854498 inside the frame routine 0x01851d39, plus the
 * OpenWorld music-group volume rule 0x018290be..0x018293a6.
 *
 * The block is a switch on the world that starts ambient loops (SND_Play with
 * loop 1) and per-world music, followed by unconditional "stop everything
 * that does not belong to this world" passes. Event worlds delegate to their
 * own managers, which are reported as MU_WORLD_DELEGATE events and not
 * reconstructed here. Calls appear in exactly the client order.
 */
#include "client_audio.h"

int mu_world_is_devil_square(int32_t world) { return world == 9 || world == 0x66; } /* 0x009dad09 */
int mu_world_is_dungeon(int32_t world) { return world >= 0x74 && world <= 0x78; }  /* 0x016a887a */
int mu_world_is_atlans(int32_t world) { return world == 7 || (world >= 0x80 && world <= 0x82); } /* 0x016a88ae */
int mu_world_is_karutan(int32_t world) { return world == 0x50 || world == 0x51; } /* 0x00e18ae9 */
int mu_world_is_kubera(int32_t world) { return world >= 0x7b && world <= 0x7f; }  /* 0x00e1e4b6 */
int mu_world_is_scorched(int32_t world) { return world == 0x83; }                  /* 0x00e45d40 */

typedef struct emitter {
    const mu_world_audio_hooks *hooks;
} emitter;

static void ev(const emitter *e, int kind, int32_t a, int32_t b)
{
    if (e->hooks->event) e->hooks->event(e->hooks->ctx, kind, a, b);
}
static void play(const emitter *e, int32_t id, int32_t loop) { ev(e, MU_WORLD_SND_PLAY, id, loop); }
static void stop(const emitter *e, int32_t id) { ev(e, MU_WORLD_SND_STOP, id, 0); }
static void mp3(const emitter *e, int32_t index) { ev(e, MU_WORLD_MP3_PLAY, index, 0); }
static void mp3stop(const emitter *e, int32_t index) { ev(e, MU_WORLD_MP3_STOP, index, 0); }
static void delegate(const emitter *e, int32_t address, int32_t argument)
{
    ev(e, MU_WORLD_DELEGATE, address, argument);
}

/* Switch at 0x01852824 (compare tree plus jump table 0x018544bd for 0x77..0x91). */
static void ambient_switch(const emitter *e, const mu_world_audio_state *s)
{
    const int32_t w = s->world;
    switch (w) {
    case 0x00:
        if (s->hero_tile == 4) {
            stop(e, 0);
            stop(e, 1);
        } else {
            play(e, 0, 1);
            if (s->rain > 0) play(e, 1, 1);
        }
        break;
    case 0x01: case 0x74: case 0x75: case 0x76: case 0x77: case 0x78:
        play(e, 3, 1);
        break;
    case 0x02:
        if (s->hero_tile == 3 || s->hero_tile >= 10) stop(e, 0);
        else play(e, 0, 1);
        break;
    case 0x03: {
        play(e, 0, 1);
        int32_t r = e->hooks->rand ? e->hooks->rand(e->hooks->ctx) : 0;
        if (r % 512 == 0) play(e, 2, 0);  /* signed remainder, as compiled */
        break;
    }
    case 0x04: play(e, 5, 1); break;
    case 0x07: case 0x80: case 0x81: case 0x82: play(e, 6, 1); break;
    case 0x08: play(e, 7, 1); break;
    case 0x0a: case 0x84: play(e, 0x14, 1); break;
    case 0x3a: play(e, 0, 1); break;
    case 0x4f: case 0x72: play(e, 0, 1); play(e, 1, 1); break;
    case 0x50: play(e, 0x3da, 1); break;
    case 0x51:
        if (s->hero_tile == 0x0c) {
            stop(e, 0x3da);
            play(e, 0x3dc, 1);
        } else {
            stop(e, 0x3dc);
            play(e, 0x3da, 1);
        }
        break;
    case 0x5b: case 0x5c: case 0x5f: case 0x60: play(e, 0x3e0, 1); break;
    case 0x64: case 0x65:
        if (s->hero_attribute & 0x800) {
            stop(e, 0x443);
            play(e, 0x444, 1);
            mp3(e, 48);
            mp3stop(e, 49);
        } else if (s->hero_attribute & 0x1000) {
            stop(e, 0x444);
            play(e, 0x443, 1);
            mp3(e, 49);
            mp3stop(e, 48);
        }
        break;
    case 0x6e: case 0x6f: play(e, 0x46e, 1); mp3(e, 53); break;
    case 0x71: play(e, 0x495, 1); mp3(e, 54); break;
    case 0x73: play(e, 0x4b0, 1); mp3(e, 55); break;
    case 0x79: play(e, 0x4b1, 1); mp3(e, 56); break;
    case 0x7a:
        /* 0x00fdc490(0x7a) casts the world object, 0x00e5ea60(x, y) tests it. */
        if (e->hooks->in_boss_zone && e->hooks->in_boss_zone(e->hooks->ctx, 0x7a, s->hero_x, s->hero_y)) {
            mp3(e, 58);
        } else {
            play(e, 0x4d6, 0);
            mp3(e, 57);
        }
        break;
    case 0x7b: case 0x7c: case 0x7d: case 0x7e: case 0x7f: mp3(e, 59); break;
    case 0x83: mp3(e, 60); break;
    case 0x85: mp3(e, 61); play(e, 0x52f, 1); break;
    case 0x86: mp3(e, 62); play(e, 0x530, 1); break;
    case 0x87: mp3(e, 63); break;
    case 0x88: mp3(e, 64); break;
    case 0x8a: mp3(e, 65); play(e, 0x566, 1); break;
    case 0x8c: mp3(e, 72); play(e, 0x575, 1); break;
    case 0x8d:
        if (s->hero_safe_zone == 1) play(e, 0x580, 1);
        else stop(e, 0x580);
        play(e, 0x57f, 1);
        break;
    case 0x8e: mp3(e, 73); play(e, 0x593, 1); break;
    case 0x8f: mp3(e, 74); break;
    case 0x91: mp3(e, 75); play(e, 0x5b2, 1); break;
    default: break;
    }
}

/* 0x0185321d..0x01853a6e: stop what does not belong to the current world. */
static void stop_pass(const emitter *e, const mu_world_audio_state *s)
{
    const int32_t w = s->world;
    if (!(w == 0 || w == 2 || w == 3 || w == 0x3a || w == 0x4f || w == 0x79 || w == 0x72)) stop(e, 0);
    if (!(w == 0 || mu_world_is_devil_square(w) || w == 0x4f || w == 0x72)) stop(e, 1);
    if (!(w == 1 || mu_world_is_dungeon(w))) stop(e, 3);
    if (w != 3) stop(e, 2);
    if (w != 4) stop(e, 5);
    if (!mu_world_is_atlans(w)) stop(e, 6);
    if (w != 8) stop(e, 7);
    if (!(w == 0x0a || w == 0x84)) stop(e, 0x14);
    if (w != 0x33) {
        for (int32_t id = 0x313; id <= 0x319; id++) stop(e, id);
    }
    if (!mu_world_is_karutan(w)) stop(e, 0x3da);
    if (w != 0x50) stop(e, 0x3db);
    if (w != 0x51) stop(e, 0x3dc);
    if (!(w == 0x5b || w == 0x5c || w == 0x5f || w == 0x60)) stop(e, 0x3e0);
    if (!(w == 0x64 || w == 0x65)) {
        mp3stop(e, 49);
        mp3stop(e, 48);
        stop(e, 0x443);
        stop(e, 0x444);
        stop(e, 0x442);
    }
    if (!(w == 0x6e || w == 0x6f)) { mp3stop(e, 53); stop(e, 0x46e); }
    if (w != 0x71) { mp3stop(e, 54); stop(e, 0x495); }
    if (w != 0x73) { mp3stop(e, 55); stop(e, 0x4b0); }
    if (w != 0x79) { mp3stop(e, 56); stop(e, 0x4b1); }
    if (w != 0x7a) { mp3stop(e, 57); mp3stop(e, 58); stop(e, 0x4d6); }
    if (!mu_world_is_kubera(w)) { mp3stop(e, 59); stop(e, 0x4ee); stop(e, 0x4ef); }
    if (!mu_world_is_scorched(w)) mp3stop(e, 60);
    if (w != 0x85) { mp3stop(e, 61); stop(e, 0x52f); }
    if (w != 0x86) { mp3stop(e, 62); stop(e, 0x530); }
    if (w != 0x87) mp3stop(e, 63);
    if (w != 0x88) mp3stop(e, 64);
    if (w != 0x8a) { mp3stop(e, 65); stop(e, 0x566); }
    if (w != 0x8c) { mp3stop(e, 72); stop(e, 0x575); }
    if (w != 0x8d) { stop(e, 0x57f); stop(e, 0x580); }
    if (w != 0x8e) { mp3stop(e, 73); stop(e, 0x593); }
    if (w != 0x8f) mp3stop(e, 74);
    if (w != 0x91) { mp3stop(e, 75); stop(e, 0x5b2); }
}

/* 0x01853a6e..0x01854279: field music. */
static void music_pass(const emitter *e, const mu_world_audio_state *s)
{
    const int32_t w = s->world;
    if (w == 0) {
        if (s->hero_safe_zone == 1) mp3(e, s->hero_tile == 4 ? 0 : 21);
    } else {
        mp3stop(e, 0);
        mp3stop(e, 21);
    }
    if (w == 2) {
        if (s->hero_safe_zone == 1) {
            int church = s->hero_x >= 0xcd && s->hero_x <= 0xd6 && s->hero_y >= 0x0d && s->hero_y <= 0x1f;
            mp3(e, church ? 2 : 3);
        }
    } else {
        mp3stop(e, 2);
        mp3stop(e, 3);
    }
    if (w == 3) {
        if (s->hero_safe_zone == 1) mp3(e, 4);
    } else {
        mp3stop(e, 4);
    }
    if (w == 1 || mu_world_is_dungeon(w)) mp3(e, 5); else mp3stop(e, 5);
    if (mu_world_is_atlans(w)) mp3(e, 6); else mp3stop(e, 6);
    if (w == 0x0a || w == 0x84) mp3(e, 7); else mp3stop(e, 7);
    if (w == 8) mp3(e, 8); else mp3stop(e, 8);
    if (w == 4) mp3(e, 9); else mp3stop(e, 9);
    if ((w >= 0x18 && w <= 0x1d) || w == 0x24) mp3(e, 11); else mp3stop(e, 11);
    if (w == 0x1f) mp3(e, 15); else mp3stop(e, 15);
    if (w == 0x21) mp3(e, 16); else mp3stop(e, 16);
    delegate(e, 0x00db3e26, w);  /* Crywolf music (indices 17..20) */
    delegate(e, 0x00e8e857, w);  /* Kanturu battle music (24..26) */
    if (w == 0x25) mp3(e, 22); else mp3stop(e, 22);
    delegate(e, 0x00e84474, -1); /* Kanturu 2nd (23) */
    delegate(e, 0x00d557af, -1); /* Balgas (27, 28), on the 0x00d53c8f object */
    delegate(e, 0x00db747f, -1); /* cursed temple object getter (29, 30 via 0x00db7501) */
}

/* 0x018542c2..0x01854498 (segment B). */
static void music_pass_b(const emitter *e, const mu_world_audio_state *s)
{
    const int32_t w = s->world;
    if (w == 0x33) mp3(e, 31); else mp3stop(e, 31);
    if (w == 0x38 || w == 0x90) mp3(e, 33); else mp3stop(e, 33);
    if (w != 0x70) {
        stop(e, 0x46f);
        stop(e, 0x470);
    }
    /* Event-world managers, each obtained from a world getter and called. */
    static const int32_t managers[][2] = {
        {0x39, 0x00e9e9c5}, {0x3e, 0x00e42ad0}, {0x3f, 0x00e92fc8}, {0x45, 0x00dd306c},
        {0x46, 0x00dd8891}, {0x47, 0x00dde543}, {0x48, 0x00de5467}, {0x4f, 0x00e6dd22},
        {0x50, 0x00e189e4}, {0x5b, 0x00d73c38},
    };
    for (size_t i = 0; i < sizeof managers/sizeof managers[0]; i++)
        delegate(e, managers[i][1], managers[i][0]);
}

void mu_world_audio_frame(const mu_world_audio_state *state, const mu_world_audio_hooks *hooks)
{
    emitter e = {hooks};
    if (state->scene != 6) return;
    ambient_switch(&e, state);
    stop_pass(&e, state);
    music_pass(&e, state);
    ev(&e, MU_WORLD_UNRECOVERED, 0x01854279, 0);
    music_pass_b(&e, state);
}

/* ---- OpenWorld music volume -------------------------------------------- */

static const int32_t full_volume_worlds[] = {
    0x06, 0x09, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
    0x20, 0x22, 0x23, 0x27, 0x28, 0x2a, 0x2d, 0x2e, 0x2f, 0x30, 0x31, 0x32, 0x35, 0x3a, 0x3e,
    0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x4f, 0x52, 0x53, 0x54, 0x55, 0x56,
    0x57, 0x58, 0x59, 0x5a, 0x5c, 0x60, 0x65, 0x6f, 0x72, 0x73, 0x79, 0x8b,
};

size_t mu_audio_full_volume_worlds(const int32_t **worlds)
{
    if (worlds) *worlds = full_volume_worlds;
    return sizeof full_volume_worlds/sizeof full_volume_worlds[0];
}

int mu_audio_world_full_music_volume(int32_t world)
{
    for (size_t i = 0; i < sizeof full_volume_worlds/sizeof full_volume_worlds[0]; i++)
        if (full_volume_worlds[i] == world) return 1;
    return 0;
}

float mu_audio_world_music_volume(int32_t world)
{
    return mu_audio_world_full_music_volume(world) ? 1.0f : 0.4f;
}
