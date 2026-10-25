/* parts/combat.c (WORLD-RT-001): combat (NATIVE-COMBAT-001/002, core/mu_combat): a click on a monster attacks it
 * with the client's attack rules (range, facing, SetPlayerAttack action, SetAttackSpeed PlaySpeed, AttackTime and
 * the end-of-attack effects); damage text, hit reactions, death, fade and removal run the client routines.  The
 * server side (damage, death, respawn, counter-attacks) is a labelled DEMO inside core/mu_combat until
 * SESSION-COMBAT-001 moves it to the fixture. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_scene.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

/* NATIVE-COMBAT-002: swings, skills, the hero's voice through SND_Play. */
static void combat_sound(void *context, int32_t id)
{
    mu_world_rt *a = context;
    mu_audio_host_play(a->sound.host, id, 0);   /* SND_Play(id, object, 0) */
}

/* NATIVE-QUEST-001: a monster died: the quest demo server counts it (core/mu_quest).  NATIVE-PROGRESS-001:
 * the progression demo server gives its experience. */
static void combat_kill(void *context, int32_t actor, int32_t server_class)
{
    mu_world_rt *a = context;
    if (a->progress)
        mu_progress_kill(a->progress, server_class, actor);
#ifndef MU_WORLD_NO_GL
    if (a->gfx)
        world_gfx_quest_kill(a->gfx, server_class);
#else
    (void)server_class;
#endif
}

/* NATIVE-PROGRESS-001: the hero's respawn (the server's 0xA0 sub 0x30 answer when the demo delay ends):
 * the DEMO town (mu_map_respawn: the teleport the host takes next step changes the world when needed)
 * and the client's handler over the progress session. */
int world_rt_combat_respawned(void *context)
{
    mu_world_rt *a = context;
    int32_t world = a->world, x = a->walk.hero.tile[0], y = a->walk.hero.tile[1];
    int placed = a->mapsess && mu_map_respawn(a->mapsess, a->world, &world, &x, &y);
    if (a->progress)
        mu_progress_respawn(a->progress, world, x, y, 1, a->mapsess ? (uint32_t)a->mapsess->zen : 0u);
    if (!a->quiet)
        printf("{\"respawn\": {\"world\": %d, \"tile\": [%d, %d], \"town\": %d}}\n", (int)world, (int)x, (int)y,
               placed);
    return placed;
}

static int combat_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (a->combat_on) {
        const char *file = mu_combat_weapon_file(a->combat_config.weapon);
        char path[4096];
        if (file) {
            snprintf(path, sizeof path, "%s/%s", a->root, file);
            FILE *f = fopen(path, "rb");
            if (f) {
                fclose(f);
                if (mu_character_set_item(&a->ch, MU_CHARACTER_WEAPON_ITEM(0), path, 0, error, sizeof error))
                    fprintf(stderr, "combat weapon: %s (continuing without it)\n", error);
            }
        }
        a->combat = calloc(1, sizeof *a->combat);
        if (!a->combat || mu_combat_init(a->combat, a->root, &a->walk, &a->ch, a->has_actors ? &a->actors : NULL,
                                         &a->combat_config, error, sizeof error)) {
            fprintf(stderr, "combat: %s\n", a->combat ? error : "out of memory");
            return 1;
        }
        if (a->has_particles)   /* NATIVE-PARTICLE-001: the skills' sprites and their legacy particle kinds */
            a->combat->legacy_particles = &a->particles;
        if (a->has_sound) {   /* NATIVE-COMBAT-002: swings, skills, the hero's voice through SND_Play */
            a->combat->play_sound = combat_sound;
            a->combat->sound_context = a;
        }
        a->combat->kill = combat_kill;   /* NATIVE-QUEST-001: the quest demo's kill progress */
        a->combat->kill_context = a;
        a->combat->hero_respawned = world_rt_combat_respawned;   /* NATIVE-PROGRESS-001 */
    }
    return 0;
}

static void combat_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->combat) {
        mu_combat_free(a->combat);
        free(a->combat);
        a->combat = NULL;
    }
}

/* MoveHero's attack case runs before its walk and click code. */
static void combat_pre_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->combat)
        mu_combat_pre_step(a->combat);
}

static void combat_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->combat)
        mu_combat_step(a->combat);
}

/* The effect lights after the frame's light copy. */
static void combat_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
    if (a->combat)
        mu_combat_terrain_lights(a->combat, a->map);
}

static void combat_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    if (a->combat)
        mu_combat_draw_raster(a->combat, d->raster);
}

static void combat_report_frame(const struct mu_world_rt *a, const void *self, int32_t frame)
{
    (void)self;
    if (a->combat)
        mu_combat_report_frame(a->combat, stdout, frame);
}

static void combat_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->combat)
        mu_combat_report_summary(a->combat, stdout, a->quiet);
}

#ifndef MU_WORLD_NO_GL
typedef struct combat_part {
    mu_gl_backend combat_gl[MU_COMBAT_MODELS];
    GLuint combat_tex[MU_COMBAT_BITMAPS];
} combat_part;

static void combat_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    combat_part *p = self;
    for (int i = 0; i < MU_COMBAT_MODELS; ++i)
        if (p->combat_gl[i].textures)
            mu_gl_release(&p->combat_gl[i]);
    for (int i = 0; i < MU_COMBAT_BITMAPS; ++i)
        if (p->combat_tex[i]) {
            glDeleteTextures(1, &p->combat_tex[i]);
            p->combat_tex[i] = 0;
        }
}

/* NATIVE-COMBAT-001: effect models through the scene draw, then the frame's quads (effect bitmaps, RenderPoints)
 * in immediate mode. */
static void combat_model_gl(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                            const mu_draw_options *draw_options)
{
    combat_part *p = context;
    mu_gl_backend *gl = &p->combat_gl[slot];
    if (!gl->textures)
        mu_gl_upload(gl, textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_draw_options options = *draw_options;   /* RenderObject's RenderBody arguments (mu_combat) */
    options.textures = textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, &options, &backend, &ds);
}

static void combat_draw(mu_world_rt *a, combat_part *p)
{
    mu_combat *c = a->combat;
    mu_combat_draw_models(c, combat_model_gl, p);
    static mu_combat_quad quads[1024];
    int32_t n = mu_combat_quads(c, quads, 1024);
    glDepthMask(GL_FALSE);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_CULL_FACE);
    glEnable(GL_BLEND);
    for (int32_t i = 0; i < n; ++i) {
        const mu_combat_quad *q = &quads[i];
        if (q->bitmap >= 0) {
            const mu_combat_bitmap *b = &c->bitmaps[q->bitmap];
            if (!p->combat_tex[q->bitmap]) {
                glGenTextures(1, &p->combat_tex[q->bitmap]);
                glBindTexture(GL_TEXTURE_2D, p->combat_tex[q->bitmap]);
                glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, b->image.width, b->image.height, 0, GL_RGBA,
                             GL_UNSIGNED_BYTE, b->image.rgba);
            }
            glEnable(GL_TEXTURE_2D);
            glBindTexture(GL_TEXTURE_2D, p->combat_tex[q->bitmap]);
            glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
        } else {
            glDisable(GL_TEXTURE_2D);
        }
        if (q->src || q->dst)
            glBlendFunc((GLenum)q->src, (GLenum)q->dst);   /* RenderJoints' render types (NATIVE-COMBAT-002) */
        else if (q->additive)
            glBlendFunc(GL_ONE, GL_ONE);
        else
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        if (q->depth_test)
            glEnable(GL_DEPTH_TEST);
        else
            glDisable(GL_DEPTH_TEST);
        if (q->eye_space) {   /* RenderSpriteUV draws eye-space corners with an identity modelview */
            glMatrixMode(GL_MODELVIEW);
            glPushMatrix();
            glLoadIdentity();
        }
        glBegin(GL_QUADS);
        for (int k = 0; k < 4; ++k) {
            glColor4fv(q->color[k]);
            glTexCoord2fv(q->texcoord[k]);
            glVertex3fv(q->position[k]);
        }
        glEnd();
        if (q->eye_space)
            glPopMatrix();
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);
}

/* The last of the effects' phase (opened by the actor_effects part). */
static void combat_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    if (a->combat)
        combat_draw(a, self);
    mu_perf_end(MU_PERF_EFFECTS, d->perf);
}
#endif

const mu_world_part_ops mu_part_combat = {
    .name = "combat",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(combat_part),
    .draw_gl = combat_draw_gl,
    .gl_teardown = combat_gl_teardown,
#endif
    .open = combat_open,
    .close = combat_close,
    .pre_tick = combat_pre_tick,
    .tick = combat_tick,
    .frame = combat_frame,
    .draw_soft = combat_draw_soft,
    .report_frame = combat_report_frame,
    .report_summary = combat_report_summary,
};
