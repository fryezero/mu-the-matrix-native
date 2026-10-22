/* NATIVE-SKILL-002. The client's tree routines, native GFx boundary and an explicit offline demo server.
 * NATIVE-SKILL-003: the SkillTree4th window over reconstructed/skill/tree4.c (core/mu_skill_tree4). */
#include "world_gfx_tree.h"
#include "world_gfx_skill.h"
#include "../core/mu_skill.h"
#include "../core/mu_skill_tree4.h"
#include "../core/mu_lang.h"
#include "../gfx/mu_gfx_layer.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GL_SILENCE_DEPRECATION 1
#include <OpenGL/gl.h>

struct wg_tree {
    wg_skill *skill;
    mu_skill_book *book;
    mu_gfx_layer *layer;
    const mu_lang *lang;
    int pending_slot, hover_slot;
    mu_skill_tree4 *t4;                 /* NATIVE-SKILL-003 */
    int t4_pending, t4_ready;           /* the click awaiting its second click (index + 1), the demo login sent */
    int t4_resend;                      /* resend the page at the next draw (layer choice: the movie's slot clips
                                           exist one frame after GenerateSkillTree) */
};

static void quote(char *dst, size_t cap, const char *src)
{
    size_t at = 0;
    if (cap < 3)
        return;
    dst[at++] = '"';
    for (; *src && at + 7 < cap; src++) {
        unsigned char c = (unsigned char)*src;
        if (c == '"' || c == '\\')
            dst[at++] = '\\', dst[at++] = (char)c;
        else if (c < 32)
            at += (size_t)snprintf(dst + at, cap - at, "\\u%04x", c);
        else
            dst[at++] = (char)c;
    }
    dst[at++] = '"';
    dst[at] = 0;
}

static const char *text(void *user, int32_t id)
{
    wg_tree *t = user;
    const char *s = mu_lang_text(t->lang, id);
    return s ? s : "";
}

static void invoke(void *user, const char *name, const char *args)
{
    wg_tree *t = user;
    char json[9000], utf8[4096], q[8192];
    if (!strcmp(name, "SetText")) {
        char *end;
        long type = strtol(args, &end, 10);
        while (*end == ' ')
            end++;
        mu_latin1_to_utf8(utf8, sizeof utf8, end);
        quote(q, sizeof q, utf8);
        snprintf(json, sizeof json, "[%ld,%s]", type, q);
    } else if (!strcmp(name, "SetSkillSlot")) {
        quote(q, sizeof q, args);
        snprintf(json, sizeof json, "[%s]", q);
    } else {
        int a = 0, b = 0;
        if (sscanf(args, "%d %d", &a, &b) != 2)
            return;
        snprintf(json, sizeof json, "[%d,%d]", a, b);
    }
    mu_gfx_layer_invoke(t->layer, MU_GFX_MASTER_TREE, NULL, name, json);
}

static void sync_hero(wg_tree *t)
{
    const mu_gfx_hero *hero = mu_gfx_layer_hero(t->layer);
    mu_master_env *env = mu_skill_book_master_env(t->book);
    if (hero) {
        env->level_sum = hero->level + hero->master_level;
        env->exp = (uint64_t)hero->exp;
        env->next_exp = (uint64_t)hero->exp_max;
    }
}

static void message(void *user, int owner, const char *s)
{
    (void)owner;
    wg_tree *t = user;
    char utf8[2048];
    mu_latin1_to_utf8(utf8, sizeof utf8, s);
    mu_gfx_layer_chat(t->layer, 3, "", utf8);
}

static void confirm(void *user, int id, const char *s)
{
    wg_tree *t = user;
    message(user, id, s);
    mu_gfx_layer_chat(t->layer, 3, "", "OFFLINE DEMO: click the same skill again to confirm. Esc or close cancels.");
}

static void tooltip(wg_tree *t, int slot)
{
    mu_master_tree *tree = mu_skill_book_master(t->book);
    char title[4096], body[32768];
    if (slot < 1 || slot > 108 || !tree->pos[slot].has ||
        !mu_skill_book_master_tooltip(t->book, slot, title, sizeof title, body, sizeof body)) {
        mu_gfx_layer_skill_popup(t->layer, 0, 0, NULL, NULL);
        return;
    }
    float x, y, sc = mu_gfx_layer_window_scale(t->layer, MU_GFX_MASTER_TREE);
    mu_gfx_layer_window_position(t->layer, MU_GFX_MASTER_TREE, &x, &y);
    mu_gfx_layer_skill_popup(t->layer, (int)(x + sc * (tree->pos[slot].x + 13)),
                             (int)(y + sc * tree->pos[slot].y), title, body);
    t->hover_slot = slot;
}

static void click(wg_tree *t, int slot)
{
    mu_master_tree *tree = mu_skill_book_master(t->book);
    mu_master_env *env = mu_skill_book_master_env(t->book);
    sync_hero(t);
    int confirming = t->pending_slot == slot && slot != 0;
    t->pending_slot = 0;
    /* Re-run the actual checks even on confirmation: the local server cannot spend stale points. */
    mu_master_env check = *env;
    if (confirming)
        check.confirm = NULL;
    if (!mu_master_click(tree, &check, mu_skill_book_hero(t->book), slot))
        return;
    if (!confirming) {
        t->pending_slot = slot;
        return;
    }
    int32_t skill;
    uint8_t request[8];
    if (mu_master_confirm(tree, 0x47, 0, &skill)) {
        size_t size = mu_master_request(request, sizeof request, skill);
        if (mu_skill_book_demo_master_request(t->book, request, size)) {
            mu_gfx_layer_chat(t->layer, 3, "", "OFFLINE DEMO: Master skill answer received.");
            tooltip(t, slot);
        }
    }
}

/* ---- SkillTree4th (NATIVE-SKILL-003) ---------------------------------------------------------------------- */

/* tree4.c hands JSON arguments; strings are client (Latin-1) bytes as \u00xx escapes, which the JSON reader
 * of the movie layer turns into the right code points. */
static void t4_invoke(void *user, const char *name, const char *json)
{
    wg_tree *t = user;
    mu_gfx_layer_invoke(t->layer, MU_GFX_TREE4, NULL, name, json && *json ? json : "[]");
}

static void t4_confirm(void *user, int id, const char *s)
{
    (void)id;
    message(user, 0, s);
    mu_gfx_layer_chat(((wg_tree *)user)->layer, 3, "", "OFFLINE DEMO: click the same skill again to confirm.");
}

static void t4_message(void *user, const char *s) { message(user, 0, s); }

static void t4_login(wg_tree *t)
{
    if (!t->t4 || t->t4_ready)
        return;
    const mu_skill_hero *hero = mu_skill_book_hero(t->book);
    mu_skill_tree4_enter(t->t4, hero ? hero->class_index : 0);
    const mu_gfx_hero *gh = mu_gfx_layer_hero(t->layer);
    /* OFFLINE DEMO points (the server's); the live hero showed "Skill Point: 0" */
    mu_skill_tree4_demo_login(t->t4, gh && gh->level >= 400 ? 30 : 10);
    mu_skill_tree4_demo_side(t->t4);
    t->t4_ready = 1;
}

static void t4_click(wg_tree *t, int index)
{
    mu_t4_window *w = mu_skill_tree4_window(t->t4);
    mu_t4_env env = *mu_skill_tree4_env(t->t4);
    int confirming = t->t4_pending == index + 1;
    t->t4_pending = 0;
    if (confirming)
        env.confirm = NULL;
    if (!mu_t4_click(w, &env, index))
        return;
    if (!confirming) {
        t->t4_pending = index + 1;
        return;
    }
    uint8_t group, req[16];
    uint16_t skill, idx;
    if (mu_t4_confirm(w, 0, &group, &skill, &idx)) {
        size_t n = mu_t4_request(req, sizeof req, group, skill, idx);
        if (mu_skill_tree4_demo_request(t->t4, req, n))
            mu_gfx_layer_chat(t->layer, 3, "", "OFFLINE DEMO: fourth tree answer received.");
    }
}

static void draw(void *user, int32_t bitmap, float x, float y, float w, float h, float u, float v, float uw,
                 float vh, uint32_t color);

static void t4_tooltip(wg_tree *t, int side, int index)
{
    char title[4096], body[32768];
    int32_t pos[2] = {0, 0};
    if (!mu_skill_tree4_tooltip(t->t4, side, index, title, sizeof title, body, sizeof body, pos)) {
        mu_gfx_layer_skill_popup(t->layer, 0, 0, NULL, NULL);
        return;
    }
    float x, y, sc = mu_gfx_layer_window_scale(t->layer, MU_GFX_TREE4);
    mu_gfx_layer_window_position(t->layer, MU_GFX_TREE4, &x, &y);
    /* 0x00b8c631(x, y, 0x1a, 0x25): the popup beside the 26 x 37 anchor */
    mu_gfx_layer_skill_popup(t->layer, (int)(x + sc * ((float)pos[0] + 13)), (int)(y + sc * (float)pos[1]), title, body);
}

static void t4_side_click(wg_tree *t, int index)
{
    mu_t4_window *w = mu_skill_tree4_window(t->t4);
    mu_t4_env env = *mu_skill_tree4_env(t->t4);
    int confirming = t->t4_pending == 1000 + index;
    t->t4_pending = 0;
    if (confirming)
        env.confirm = NULL;
    if (!mu_t4_side_click(w, &env, index))
        return;
    if (!confirming) {
        t->t4_pending = 1000 + index;
        return;
    }
    uint8_t a, b, c, req[16];
    if (mu_t4_side_confirm(w, 0, &a, &b, &c)) {
        size_t n = mu_t4_side_request(req, sizeof req, a, b, c);
        if (mu_skill_tree4_demo_side_request(t->t4, req, n))
            mu_gfx_layer_chat(t->layer, 3, "", "OFFLINE DEMO: fourth tree side option answer received.");
    }
}

static void t4_call(wg_tree *t, const char *name, const char *args)
{
    mu_t4_window *w = mu_skill_tree4_window(t->t4);
    const mu_t4_env *env = mu_skill_tree4_env(t->t4);
    double v[5] = {0};
    int n = sscanf(args ? args : "", " [ %lf , %lf , %lf , %lf , %lf", &v[0], &v[1], &v[2], &v[3], &v[4]);
    if (!strcmp(name, "UIInit")) {
        /* 0x00c2300c: SetText (0x00c23175), GenerateSkillTree {NumRows 10, NumLines 7} (doubles 0x01a7e460 /
           0x01a99f00), SetSideOptionIndex (0x00c2436e) */
        mu_t4_set_text(env);
        mu_gfx_layer_invoke(t->layer, MU_GFX_TREE4, NULL, "GenerateSkillTree", "[{\"NumRows\":10,\"NumLines\":7}]");
        mu_t4_side_index(w, env);
    } else if (!strcmp(name, "WindowShown")) {
        if (!mu_skill_tree4_records(t->t4)) {
            mu_gfx_layer_chat(t->layer, 3, "", "No 4ThTreeData: MU_LANG_DIR/tree4.tsv (live_lang_to_plain.py) is absent.");
            return;
        }
        if (!t->t4_ready)
            t4_login(t);
        const mu_gfx_hero *gh = mu_gfx_layer_hero(t->layer);
        mu_t4_show_level(env, gh ? gh->level + gh->master_level : 0);     /* 0x00c230be: SetLevel */
        t->t4_resend = 1;
    } else if (!strcmp(name, "WindowHidden")) {
        t->t4_pending = 0;
    } else if (!strcmp(name, "RequestSlotUIInfo") && n == 5) {
        mu_t4_slot_rect(w, (int32_t)v[0], (float)v[1], (float)v[2], (float)v[3], (float)v[4]);
    } else if (!strcmp(name, "OnChangeTab") && n >= 1) {
        mu_t4_change_tab(w, env, (int32_t)v[0]);
    } else if (!strcmp(name, "onClickprevBtn") || !strcmp(name, "onClicknextBtn")) {
        mu_t4_step_page(w, env, name[7] == 'p' ? -1 : 1);
    } else if (!strcmp(name, "OnMouseClickSlot") && n >= 2) {
        t4_click(t, (int)v[1]);
    } else if (!strcmp(name, "OnMouseOverSlot") && n >= 2) {
        t4_tooltip(t, 0, (int)v[1]);
    } else if (!strcmp(name, "RequestSideOptionUIPos") && n >= 3) {
        mu_t4_side_rect(w, (int32_t)v[0], (float)v[1], (float)v[2]);
    } else if (!strcmp(name, "RequestSideOptionUISize") && n >= 2) {
        mu_t4_side_size(w, (float)v[0], (float)v[1]);
    } else if (!strcmp(name, "RequestSelectBranchUIPos") && n >= 3) {
        mu_t4_branch_rect(w, (int32_t)v[0], (float)v[1], (float)v[2]);
    } else if (!strcmp(name, "OnBtnOverSideOption") && n >= 1) {
        t4_tooltip(t, 1, (int)v[0]);
    } else if (!strcmp(name, "OnBtnClickSideOption") && n >= 1) {
        t4_side_click(t, (int)v[0]);
    } else if (!strcmp(name, "SelectBranchSkill") && n >= 2) {
        /* the choice opens the confirm box; the demo answers the second click of the same node */
        mu_t4_env e2 = *env;
        e2.confirm = t4_confirm;
        if (mu_t4_select_branch(w, &e2, (int32_t)v[0], (int32_t)v[1]))
            t->t4_pending = (int)v[1] + 1;
    } else if (!strcmp(name, "VisibleBranchSkill") && n >= 1) {
        w->branch_visible = (uint8_t)(v[0] != 0);
    } else if (!strcmp(name, "RollOut") || !strcmp(name, "OnMouseOutSlot")) {
        mu_gfx_layer_skill_popup(t->layer, 0, 0, NULL, NULL);
    }
}

wg_tree *wg_tree_open(wg_skill *skill, mu_gfx_layer *layer, const mu_lang *lang)
{
    if (!skill || !layer)
        return NULL;
    wg_tree *t = calloc(1, sizeof *t);
    if (!t)
        return NULL;
    t->skill = skill;
    t->book = wg_skill_book(skill);
    t->layer = layer;
    t->lang = lang;
    mu_master_env *env = mu_skill_book_master_env(t->book);
    env->user = t;
    env->text = text;
    env->invoke = invoke;
    env->msgbox = message;
    env->confirm = confirm;
    t->t4 = mu_skill_tree4_open(getenv("MU_LANG_DIR"), t->book);
    mu_skill_tree4_host host = {t, text, t4_invoke, t4_message, t4_confirm};
    mu_skill_tree4_set_host(t->t4, &host);
    return t;
}

void wg_tree_close(wg_tree *t)
{
    if (t)
        mu_skill_tree4_close(t->t4);
    free(t);
}

void wg_tree_call(wg_tree *t, int movie, const char *name, const char *args)
{
    if (!t)
        return;
    if (!strcmp(name, "CloseWindow")) {
        mu_gfx_layer_show(t->layer, movie, 0);
        return;
    }
    if (movie == MU_GFX_TREE4 && t->t4) {
        t4_call(t, name, args);
        return;
    }
    if (movie != MU_GFX_MASTER_TREE) {
        if (!strcmp(name, "UIInit")) {
            /* Empty original windows only. Their live Lang records and server inventories are not decoded. */
            mu_gfx_layer_invoke(t->layer, movie, NULL,
                                movie == MU_GFX_TREE4 ? "GenerateSkillTree" : "GetSlotInfo",
                                movie == MU_GFX_TREE4 ? "[{\"NumRows\":10,\"NumLines\":7}]" : "[]");
        } else if (!strcmp(name, "WindowShown")) {
            mu_gfx_layer_chat(t->layer, 3, "", "This tree has no decoded local data yet. See client-skills.md.");
        }
        return;
    }
    mu_master_tree *tree = mu_skill_book_master(t->book);
    if (!strcmp(name, "UIInit")) {
        sync_hero(t);
        mu_gfx_layer_invoke(t->layer, movie, NULL, "Init", "[]");
        mu_skill_book_master_build(t->book);
    } else if (!strcmp(name, "WindowShown")) {
        sync_hero(t);
        mu_master_set_text(tree, mu_skill_book_master_env(t->book), 8);
    } else if (!strcmp(name, "WindowHidden")) {
        t->pending_slot = t->hover_slot = 0;
        mu_gfx_layer_skill_popup(t->layer, 0, 0, NULL, NULL);
    } else if (!strcmp(name, "RequestPositionInfo")) {
        double slot, x, y;
        if (sscanf(args, " [ %lf , %lf , %lf", &slot, &x, &y) == 3 && slot >= 1 && slot <= 108)
            mu_master_position(tree, (int)slot, (float)x, (float)y, mu_gfx_layer_window_scale(t->layer, movie), 1, 1);
    } else if (!strcmp(name, "OnClickBtnSkillSlot") || !strcmp(name, "OnBtnSkillSlotOver")) {
        int slot;
        if (sscanf(args, " [ %d", &slot) == 1) {
            if (!strcmp(name, "OnClickBtnSkillSlot"))
                click(t, slot);
            else
                tooltip(t, slot);
        }
    } else if (!strcmp(name, "RollOut")) {
        t->hover_slot = 0;
        mu_gfx_layer_skill_popup(t->layer, 0, 0, NULL, NULL);
    }
}

static void draw(void *user, int32_t bitmap, float x, float y, float w, float h, float u, float v, float uw,
                  float vh, uint32_t color)
{
    wg_tree *t = user;
    wg_skill_draw(t->skill, bitmap, x, y, w, h, u, v, uw, vh, color);
}

void wg_tree_draw(wg_tree *t, int movie, int32_t w, int32_t h)
{
    if (t && movie == MU_GFX_TREE4 && t->t4 && t->t4_resend) {
        mu_t4_window *w4 = mu_skill_tree4_window(t->t4);
        const mu_t4_tab *tab = NULL;
        for (int i = 0; i < w4->ntabs; ++i)
            if (w4->tabs[i].key == w4->cur_tab)
                tab = &w4->tabs[i];
        mu_t4_show_page(w4, mu_skill_tree4_env(t->t4), tab ? tab->page : 0);
        /* layer choice: ask the slot rectangles again now that the clips exist */
        mu_gfx_layer_invoke(t->layer, MU_GFX_TREE4, NULL, "RequestSlotUIInfo", "[]");
        mu_t4_side_refresh(w4, mu_skill_tree4_env(t->t4));
        t->t4_resend = 0;
    }
    if (t && movie == MU_GFX_TREE4 && t->t4) {
        float x, y, sc = mu_gfx_layer_window_scale(t->layer, movie);
        mu_gfx_layer_window_position(t->layer, movie, &x, &y);
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(0, w, h, 0, -1, 1);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        glDisable(GL_DEPTH_TEST);
        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        mu_skill_tree4_icons(t->t4, x, y, sc, draw, t);
        glDisable(GL_TEXTURE_2D);
        glColor4f(1, 1, 1, 1);
        return;
    }
    if (!t || movie != MU_GFX_MASTER_TREE)
        return;
    mu_master_tree *tree = mu_skill_book_master(t->book);
    float x, y, sc = mu_gfx_layer_window_scale(t->layer, movie);
    mu_gfx_layer_window_position(t->layer, movie, &x, &y);
    tree->icon_w = sc * 26;
    tree->icon_h = sc * 37;
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(0, w, h, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glDisable(GL_DEPTH_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    mu_master_icons(tree, mu_skill_book_master_env(t->book), mu_skill_book_hero(t->book), x, y, sc, 1, 1, draw, t);
    glDisable(GL_TEXTURE_2D);
    glColor4f(1, 1, 1, 1);
}

int wg_tree_action(wg_tree *t, const char *verb, int slot)
{
    if (!t)
        return 0;
    int movie = !strcmp(verb, "tree") ? MU_GFX_MASTER_TREE : !strcmp(verb, "tree4") ? MU_GFX_TREE4 :
                !strcmp(verb, "tree5") ? MU_GFX_TREE5 : -1;
    if (movie >= 0)
        mu_gfx_layer_toggle(t->layer, movie);
    else if (!strcmp(verb, "treeover"))
        tooltip(t, slot);
    else if (!strcmp(verb, "treeclick"))
        click(t, slot);
    else if (!strcmp(verb, "tree4click") && t->t4)          /* NATIVE-SKILL-003: OnMouseClickSlot(group, index) */
        t4_click(t, slot);
    else if (!strcmp(verb, "tree4over") && t->t4)
        t4_tooltip(t, 0, slot);
    else if (!strcmp(verb, "t4sideover") && t->t4)
        t4_tooltip(t, 1, slot);
    else if (!strcmp(verb, "t4side") && t->t4)
        t4_side_click(t, slot);
    else if (!strcmp(verb, "tree4tab") && t->t4)
        mu_t4_change_tab(mu_skill_tree4_window(t->t4), mu_skill_tree4_env(t->t4), slot);
    else if (!strcmp(verb, "tree4page") && t->t4)
        mu_t4_step_page(mu_skill_tree4_window(t->t4), mu_skill_tree4_env(t->t4), slot ? 1 : -1);
    else
        return 0;
    return 1;
}
