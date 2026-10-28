/* parts/names.c (WORLD-RT-001): hudPlayerName's game side (NATIVE-NAMES-001: names, HP bars, chat bubbles): the
 * join and viewport packets' addInfo, HP packets, SetPlayerDie's removeInfo and respawns each step, the handler's
 * update each frame, and the plates as the stand-in overlay when no GFx movie draws them. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../world_rt_internal.h"

static int names_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (!a->no_names) {   /* NATIVE-NAMES-001: the join and viewport packets' addInfo */
        a->names = calloc(1, sizeof *a->names);
        mu_world_names_config nc = {a->hero_name, 0, NULL, NULL, !a->no_monster_info};
        if (a->names)
            mu_world_names_init(a->names, &nc, &a->walk, a->has_actors ? &a->actors : NULL, a->combat);
    }
    return 0;
}

static void names_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->names) {
        mu_world_names_free(a->names);
        free(a->names);
        a->names = NULL;
    }
}

/* NATIVE-NAMES-001: HP packets, SetPlayerDie's removeInfo, respawns. */
static void names_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->names)
        mu_world_names_step(a->names);
}

/* NATIVE-NAMES-001: 0x009a1618 in the tick, the hudPlayerName handler's update. */
static void names_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    if (a->names) {
#ifndef MU_WORLD_NO_GL
        if (a->gfx)
            world_names_gfx_frame(&a->names_gfx);
#endif
        a->names->hero_wing = a->has_character && a->ch.items[MU_CHARACTER_WING_ITEM].loaded;
        mu_world_names_frame(a->names, now);
    }
}

/* NATIVE-NAMES-001: the stand-in for the movie's plates (core/mu_label). */
static void names_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    if (a->names)
        mu_world_names_draw(a->names, raster->color, raster->width, raster->height);
}

/* NATIVE-NAMES-001: what the movie shows (key, type, x, y, clip visible, info visible, hp, hp bar, bubble). */
static void names_report_frame(const struct mu_world_rt *a, const void *self, int32_t frame)
{
    (void)self;
    if (a->names) {
        printf("{\"names_frame\": %d, \"plates\": [", frame);
        for (int32_t i = 0; i < a->names->names.plate_count; ++i) {
            const mu_names_plate *p = &a->names->names.plates[i];
            printf("%s[%d, %d, %.2f, %.2f, %d, %d, %d, %d, \"%s\"]", i ? ", " : "", (int)p->key, (int)p->type,
                   (double)p->x, (double)p->y, p->mc_visible, p->info_visible, (int)p->hp, p->hp_show,
                   p->message[0] ? "msg" : "");
        }
        printf("], \"selected\": %d}\n", (int)a->names->names.window.selected);
    }
}

static void names_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->names) {   /* NATIVE-NAMES-001 */
        char line[512];
        mu_names_report(&a->names->names, line, sizeof line);
        printf("{%s}\n", line);
        if (!a->quiet)
            for (int32_t i = 0; i < a->names->names.plate_count; ++i) {
                const mu_names_plate *p = &a->names->names.plates[i];
                printf("{\"plate\": %d, \"type\": %d, \"x\": %.2f, \"y\": %.2f, \"visible\": %d, \"info\": %d,"
                       " \"hp\": %d, \"message\": %d}\n", (int)p->key, (int)p->type, (double)p->x, (double)p->y,
                       p->mc_visible, p->info_visible, (int)p->hp, p->message[0] != 0);
            }
    }
}

#ifndef MU_WORLD_NO_GL
typedef struct names_part {
    GLuint names_tex;
} names_part;

/* NATIVE-NAMES-001: the stand-in plates as one window-sized overlay texture (no movie running). */
static void names_gl(mu_world_rt *a, names_part *p, int32_t width, int32_t height)
{
    size_t bytes = (size_t)width * (size_t)height * 4;
    uint8_t *overlay = calloc(bytes, 1);
    if (!overlay)
        return;
    mu_world_names_draw(a->names, overlay, width, height);
    if (!p->names_tex)
        glGenTextures(1, &p->names_tex);
    glBindTexture(GL_TEXTURE_2D, p->names_tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, overlay);
    free(overlay);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0, width, height, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glViewport(0, 0, width, height);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_LIGHTING);
    glEnable(GL_TEXTURE_2D);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glColor4f(1, 1, 1, 1);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(0, 0);
    glTexCoord2f(1, 0); glVertex2f((float)width, 0);
    glTexCoord2f(1, 1); glVertex2f((float)width, (float)height);
    glTexCoord2f(0, 1); glVertex2f(0, (float)height);
    glEnd();
    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
}

/* The last of the labels' phase (opened by the item_labels part). */
static void names_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    if (a->names && !world_names_gfx_active(&a->names_gfx))
        names_gl(a, self, d->width, d->height);
    mu_perf_end(a->perf, MU_PERF_LABELS, d->perf);
}
#endif

const mu_world_part_ops mu_part_names = {
    .name = "names",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(names_part),
    .draw_gl = names_draw_gl,
#endif
    .open = names_open,
    .close = names_close,
    .tick = names_tick,
    .frame = names_frame,
    .draw_soft = names_draw_soft,
    .report_frame = names_report_frame,
    .report_summary = names_report_summary,
};
