#ifndef MU_WORLD_EMBED_H
#define MU_WORLD_EMBED_H

/* mu-world's walk-around session as a module for other front ends
 * (NATIVE-SHELL-001: mu-client's scene 6). world_embed.c compiles
 * world/main.c unchanged into its own translation unit and exposes its
 * load, frame and draw routines, so mu-client shows exactly what mu-world
 * shows (terrain, hero, actors, objects, sound) and follows mu-world's
 * changes without copies. Built with MU_WORLD_NO_GL for the software-only
 * tools (no draw_gl / gl_setup then). */

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_character.h"
#include "../core/mu_raster.h"
#include "../core/mu_walk.h"

typedef struct mu_world_embed mu_world_embed;

typedef struct mu_world_embed_config {
    const char *root;
    int32_t world;                 /* client world index (0 Lorencia) */
    uint8_t class_byte;
    int32_t tile[2];
    float angle;
    int32_t width, height;         /* drawable pixels */
    float near_plane;              /* 0: the client's 20 */
    const char *sound_table;       /* NULL: silent */
    int audio;                     /* open the sound session (needs sound_table to resolve) */
    int32_t audio_rate;
    const char *placement;         /* demo actor placement, may be NULL */
    const char *objects_dir;       /* local decoded objects, may be NULL */
    /* equipment: item files for MU_CHARACTER_ITEMS slots (index 1..5 body parts
     * replacing the class parts, 6/7 weapons, 8 wing); empty strings skipped */
    const char *items[MU_CHARACTER_ITEMS];
    int quiet;
} mu_world_embed_config;

mu_world_embed *mu_world_embed_open(const mu_world_embed_config *config, char *error, size_t error_size);
void mu_world_embed_close(mu_world_embed *e);

/* Window messages / keys in Win32 form. */
void mu_world_embed_message(mu_world_embed *e, uint32_t message, uint32_t wparam, uint32_t lparam);
void mu_world_embed_key(mu_world_embed *e, int vk, int down);
/* Sets the drawable size and mouse scale (window front ends after creating the context). */
void mu_world_embed_resize(mu_world_embed *e, int32_t width, int32_t height);
void mu_world_embed_set_clock(mu_world_embed *e, uint32_t now);

/* mu-world's per-frame logic: due logic steps, character placement, the
 * render-pass camera, the terrain frame and the effect update. */
int32_t mu_world_embed_advance(mu_world_embed *e, uint32_t now);
/* After the frame: the client cap (milliseconds to sleep) and the per-frame sound block. */
int32_t mu_world_embed_end_frame(mu_world_embed *e);
long mu_world_embed_draw_soft(mu_world_embed *e, mu_raster *raster);
#ifndef MU_WORLD_NO_GL
int mu_world_embed_gl_setup(mu_world_embed *e);
void mu_world_embed_gl_teardown(mu_world_embed *e);
long mu_world_embed_draw_gl(mu_world_embed *e, int32_t width, int32_t height);
#endif

/* Sound: stereo float frames due now (0 without sound), mixing them. */
int mu_world_embed_has_sound(const mu_world_embed *e);
uint32_t mu_world_embed_sound_rate(const mu_world_embed *e);
void mu_world_embed_mix(mu_world_embed *e, float *out, uint32_t frames);

/* State for reports. */
const mu_walk *mu_world_embed_walk(const mu_world_embed *e);
int32_t mu_world_embed_folder(const mu_world_embed *e);

#endif
