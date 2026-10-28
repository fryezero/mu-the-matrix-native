/* The skill host of the GFx layer (NATIVE-SKILL-001); see world_gfx_skill.h. */
#define _POSIX_C_SOURCE 200809L
#include "world_gfx_skill.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION 1
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "../core/mu_image.h"
#include "../core/mu_lang.h"
#include "../core/mu_skill.h"
#include "../session/mu_session.h"
#include "../gfx/mu_gfx_layer.h"

#define SHEETS 12

struct wg_skill {
    mu_skill_book *book;
    mu_session *session;
    mu_cue_cursor cursor;
    mu_gfx_layer *layer;
    mu_skill_stamp stamp;
    char root[4096];
    struct { int32_t bitmap; GLuint tex; int tried, ok; } sheets[SHEETS];
    long casts, refused, icons_drawn, tooltips;
    int32_t world;
    int32_t buffs[64];
    int nbuffs;
};

/* OFFLINE DEMO equipment: a right-hand sword (kind 1). No native equipment packet feed exists yet. */
static int demo_item_kind(void *user, int slot, int kind)
{
    (void)user;
    return slot == 0 && kind == 1;
}

static int demo_buff(void *user, int list, int32_t id)
{
    const wg_skill *s = user;
    (void)list;                    /* DEMO: the displayed buffs apply to the hero in each predicate */
    for (int i = 0; i < s->nbuffs; i++)
        if (s->buffs[i] == id)
            return 1;
    return 0;
}
static int skill_requirement(void *user, int32_t base, int32_t *skill, int32_t *master, int32_t *level)
{
    wg_skill *s = user;
    return mu_skill_book_requirement(s->book, base, skill, master, level);
}
static int skill_master_level(void *user, int32_t skill)
{
    wg_skill *s = user;
    return mu_master_level(mu_skill_book_master(s->book), skill);
}

void wg_skill_set_world(wg_skill *s, int32_t world)
{
    if (!s)
        return;
    s->world = world;
    mu_skill_use_env state = {.user = s, .world = world, .transform = 0xffff, .item_kind = demo_item_kind,
                              .skill_require = skill_requirement, .master_level = skill_master_level};
    for (int i = 0; i < 15; i++)
        state.items[i].code = -1;
    state.items[0].code = 0;       /* demo sword group 0/index 0 */
    mu_skill_env skills = {.user = s, .buff = demo_buff};
    state.skills = &skills;
    mu_skill_book_set_use_state(s->book, &state);
}

void wg_skill_set_buffs(wg_skill *s, const int32_t *ids, int count)
{
    if (!s)
        return;
    s->nbuffs = count < 0 ? 0 : count > 64 ? 64 : count;
    if (s->nbuffs && ids)
        memcpy(s->buffs, ids, (size_t)s->nbuffs * sizeof *ids);
    wg_skill_set_world(s, s->world);
}

wg_skill *wg_skill_open(const char *game_root, const mu_lang *lang, const char *lang_dir, int32_t class_byte, mu_session *session)
{
    wg_skill *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    (void)lang; (void)lang_dir; (void)class_byte;
    s->session = session;
    s->book = mu_session_skills(session);
    if (!s->book) {
        free(s);
        return NULL;
    }
    snprintf(s->root, sizeof s->root, "%s", game_root ? game_root : "");
    wg_skill_set_world(s, 0);
    mu_skill_book_stamp_open(s->book, &s->stamp);
    return s;
}

void wg_skill_close(wg_skill *s)
{
    if (!s)
        return;
    mu_skill_book_set_use_state(s->book,NULL);
    for (int i = 0; i < SHEETS; i++)
        if (s->sheets[i].ok)
            glDeleteTextures(1, &s->sheets[i].tex);

    free(s);
}

mu_session *wg_skill_session(wg_skill *s) { return s ? s->session : NULL; }

mu_skill_book *wg_skill_book(wg_skill *s) { return s ? s->book : NULL; }

/* The hero values the checks read, from the layer's hero (DEMO values until a server feeds them). */
static void sync_stats(wg_skill *s)
{
    const mu_gfx_hero *h = s->layer ? mu_gfx_layer_hero(s->layer) : NULL;
    if (!h)
        return;
    const mu_skill_hero *hero = mu_skill_book_hero(s->book);
    mu_skill_stats st = {.class_byte = hero->class_index, .strength = (uint16_t)h->strength,
                         .agility = (uint16_t)h->agility, .vitality = (uint16_t)h->vitality,
                         .energy = (uint16_t)h->energy, .command = (uint16_t)h->command, .mana = h->mp, .ag = h->ag};
    mu_session_skills_context(s->session, &st);
}

/* ---- host callbacks ---------------------------------------------------------------------------------- */

static int host_feed(void *user, char *json, size_t cap)
{
    wg_skill *s = user;
    sync_stats(s);
    return mu_skill_book_feed(s->book, json, cap);
}

static void host_select(void *user, int slot, int skill)
{
    wg_skill *s = user;
    (void)skill;
    mu_intent in = {.kind=MU_INTENT_SKILL_SELECT}; in.u.skill_select.slot=slot;
    mu_session_submit(s->session,&in);
}

static int host_tooltip(void *user, int32_t skill, char *title, size_t title_cap, char *body, size_t body_cap)
{
    wg_skill *s = user;
    sync_stats(s);
    int ok = mu_skill_book_tooltip(s->book, skill, title, title_cap, body, body_cap);
    s->tooltips += ok;
    return ok;
}

static void host_stamp_open(void *user, int open)
{
    wg_skill *s = user;
    if (open)
        mu_skill_book_stamp_open(s->book, &s->stamp);
    else
        mu_skill_book_stamp_cancel(s->book, &s->stamp);      /* closed without Save */
}

static int32_t host_stamp_skill(void *user, int slot)
{
    wg_skill *s = user;
    if (slot >= 100)                                        /* scripted "tip": bar slot slot - 100 */
        return slot - 100 < MU_SKILL_SLOTS ? mu_skill_book_hotkeys(s->book)->slots[slot - 100] : 0;
    return mu_skill_book_stamp_skill(s->book, &s->stamp, slot);
}

static int host_stamp_page(void *user, int which, int delta)
{
    wg_skill *s = user;
    if (which == 0) {                                       /* 0x00c21aa2: only pages 1..count */
        int page = s->stamp.page + delta;
        if (page >= 1 && page <= s->stamp.pages)
            s->stamp.page = page;
        return s->stamp.page;
    }
    int sel = s->stamp.select_page + delta;                 /* 0x010976db: the two select pages */
    if (sel >= 0 && sel <= 1)
        s->stamp.select_page = sel;
    return s->stamp.select_page;
}

static int host_stamp_drop(void *user, int from, int to)
{
    wg_skill *s = user;
    return mu_skill_book_stamp_drop(s->book, &s->stamp, from, to);
}

static void host_stamp_save(void *user)
{
    wg_skill *s = user;
    /* 0x00c20db4: the stamp manager's Save, the CurrentSkill rule, the bar (the client also sends the slots to the
     * server; the demo keeps them) */
    mu_intent in = {.kind=MU_INTENT_SKILL_SAVE_KEYS};
    mu_session_submit(s->session,&in);
}

static int host_stamp_tab(void *user, int tab)
{
    wg_skill *s = user;
    return mu_skill_book_stamp_tab(s->book, &s->stamp, tab);
}

static float host_delay_left(void *user, int32_t skill)
{
    wg_skill *s = user;
    return mu_skill_book_delay_left(s->book, skill);
}

static GLuint sheet_texture(wg_skill *s, int32_t bitmap)
{
    int free_slot = -1;
    for (int i = 0; i < SHEETS; i++) {
        if (s->sheets[i].tried && s->sheets[i].bitmap == bitmap)
            return s->sheets[i].ok ? s->sheets[i].tex : 0;
        if (!s->sheets[i].tried && free_slot < 0)
            free_slot = i;
    }
    if (free_slot < 0 || !s->root[0])
        return 0;
    s->sheets[free_slot].tried = 1;
    s->sheets[free_slot].bitmap = bitmap;
    const char *file = mu_skill_icon_file(bitmap);
    if (!file)
        return 0;
    char dir[4096], name[256], path[4096];
    const char *slash = strrchr(file, '/');
    snprintf(dir, sizeof dir, "%s/Data/%.*s", s->root, (int)(slash - file), file);
    snprintf(name, sizeof name, "%s", slash + 1);
    mu_image img;
    char error[256];
    if (!mu_image_resolve(dir, name, path, sizeof path) || mu_image_load_file(path, &img, error, sizeof error))
        return 0;
    GLuint tex = 0;
    glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_2D, tex);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img.rgba);
    mu_image_free(&img);
    s->sheets[free_slot].tex = tex;
    s->sheets[free_slot].ok = 1;
    return tex;
}

void wg_skill_draw(wg_skill *s, int32_t bitmap, float x, float y, float w, float h, float u, float v, float uw,
                    float vh, uint32_t color)
{
    GLuint tex = sheet_texture(s, bitmap);
    if (!tex)
        return;
    glEnable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, tex);
    glColor4ub((GLubyte)color, (GLubyte)(color >> 8), (GLubyte)(color >> 16), (GLubyte)(color >> 24));
    glBegin(GL_QUADS);
    glTexCoord2f(u, v); glVertex2f(x, y);
    glTexCoord2f(u + uw, v); glVertex2f(x + w, y);
    glTexCoord2f(u + uw, v + vh); glVertex2f(x + w, y + h);
    glTexCoord2f(u, v + vh); glVertex2f(x, y + h);
    glEnd();
    s->icons_drawn++;
}

static void draw_quad(wg_skill *s, const mu_skill_quad *q)
{
    wg_skill_draw(s, q->bitmap, q->x, q->y, q->w, q->h, q->u, q->v, q->uw, q->vh, 0xffffffff);
}

/* RenderBitmap of each window icon (0x01097130's bitmap and cell; the texture rectangle u, v, uw, vh of
 * the 512-texel sheet), then the delay overlay of 0x00f18574. */
static void host_icons(void *user, const mu_gfx_skill_icon *icons, int n, int32_t stage_w, int32_t stage_h)
{
    wg_skill *s = user;
    sync_stats(s);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, stage_w, stage_h, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_LIGHTING);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    for (int i = 0; i < n; i++) {
        const float *r = icons[i].rect;
        mu_skill_icon ic;
        if (!mu_skill_book_icon(s->book, icons[i].skill, &ic))
            continue;
        GLuint tex = sheet_texture(s, ic.bitmap);
        if (tex) {
            glEnable(GL_TEXTURE_2D);
            glBindTexture(GL_TEXTURE_2D, tex);
            glColor4f(1, 1, 1, 1);
        } else {
            glDisable(GL_TEXTURE_2D);
            glColor4f(.35f, .55f, .9f, 1);
        }
        glBegin(GL_QUADS);
        glTexCoord2f(ic.u, ic.v);
        glVertex2f(r[0], r[1]);
        glTexCoord2f(ic.u + ic.uw, ic.v);
        glVertex2f(r[0] + r[2], r[1]);
        glTexCoord2f(ic.u + ic.uw, ic.v + ic.vh);
        glVertex2f(r[0] + r[2], r[1] + r[3]);
        glTexCoord2f(ic.u, ic.v + ic.vh);
        glVertex2f(r[0], r[1] + r[3]);
        glEnd();
        s->icons_drawn++;
        int32_t base = 0, learned = 0;
        int imprint = 0;
        if (mu_skill_book_stamp_entry(s->book, &s->stamp, icons[i].slot, &base, &learned, &imprint)) {
            float sc = icons[i].frame_scale;
            float ox = icons[i].stamp_offset[0], oy = icons[i].stamp_offset[1];
            mu_skill_stamp_entry entry = {base, learned, (uint8_t)imprint};
            mu_skill_quad q;
            if (mu_skill_stamp_marker(mu_skill_book_hero(s->book)->elemental, &entry, r[0] + ox * sc,
                                      r[1] + oy * sc, 17, 17, 17 * sc, 17 * sc, &q))
                draw_quad(s, &q);
            const mu_skill_record *rec = mu_skill_book_record(s->book, learned);
            if (rec && mu_skill_damage_type_icon(rec->damage_type, learned, r[0] + (10 - ox) * sc,
                                                 r[1] + (oy + 7) * sc, 21, 23, 17 * sc, 17 * sc, &q))
                draw_quad(s, &q);
        }
        if (icons[i].delay > 0.0f) {
            float h = r[3] * icons[i].delay;
            glDisable(GL_TEXTURE_2D);
            glColor4f(1.0f, 0.5f, 0.5f, 0.5f);
            glBegin(GL_QUADS);
            glVertex2f(r[0], r[1] + r[3] - h);
            glVertex2f(r[0] + r[2], r[1] + r[3] - h);
            glVertex2f(r[0] + r[2], r[1] + r[3]);
            glVertex2f(r[0], r[1] + r[3]);
            glEnd();
        }
    }
    glDisable(GL_TEXTURE_2D);
    glColor4f(1, 1, 1, 1);
}

void wg_skill_attach(wg_skill *s, mu_gfx_layer *layer)
{
    if (!s || !layer)
        return;
    s->layer = layer;
    sync_stats(s);
    mu_gfx_skill_host host = {.user = s, .feed = host_feed, .select = host_select, .tooltip = host_tooltip,
                              .stamp_open = host_stamp_open, .stamp_skill = host_stamp_skill,
                              .stamp_page = host_stamp_page, .stamp_drop = host_stamp_drop,
                              .stamp_save = host_stamp_save, .delay_left = host_delay_left, .icons = host_icons,
                              .stamp_tab = host_stamp_tab};
    mu_gfx_layer_set_skill_host(layer, &host);
}

int wg_skill_cast(wg_skill *s, int32_t *skill)
{
    if (skill)
        *skill = 0;
    if (!s)
        return MU_SKILL_CAST_NONE;
    sync_stats(s);
    int32_t k = mu_skill_book_selected(s->book);
    if (skill)
        *skill = k;
    int potion=0;
    int r=mu_skill_book_check_cast(s->book,k,&potion);
    if(r==MU_SKILL_CAST_OK)++s->casts;else ++s->refused;
    return r;
}

void wg_skill_set_screen(wg_skill *s, int32_t width)
{
    if (s)
        mu_skill_book_set_screen(s->book, width);
}

void wg_skill_tick(wg_skill *s, double dt_ms)
{
    (void)dt_ms;
    if (!s) return;
    mu_cue cues[32]; uint32_t lost; size_t n;
    do {
        n=mu_session_cues(s->session,&s->cursor,cues,32,&lost);
        for(size_t i=0;i<n;++i)
            if(cues[i].kind==MU_CUE_WINDOW && !strcmp(cues[i].u.window.movie,"skills") &&
               !strcmp(cues[i].u.window.method,"delay"))
                mu_gfx_layer_skill_delay(s->layer,cues[i].u.window.args[0],cues[i].u.window.args[1]);
    } while(n);
}

void wg_skill_counts(const wg_skill *s, long *casts, long *refused, long *icons_drawn, long *tooltips)
{
    *casts = s ? s->casts : 0;
    *refused = s ? s->refused : 0;
    *icons_drawn = s ? s->icons_drawn : 0;
    *tooltips = s ? s->tooltips : 0;
}
