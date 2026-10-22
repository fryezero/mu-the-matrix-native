/* NATIVE-SKILL-002. The client's tree routines, native GFx boundary and an explicit offline demo server. */
#include "world_gfx_tree.h"
#include "world_gfx_skill.h"
#include "../core/mu_skill.h"
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
    return t;
}

void wg_tree_close(wg_tree *t) { free(t); }

void wg_tree_call(wg_tree *t, int movie, const char *name, const char *args)
{
    if (!t)
        return;
    if (!strcmp(name, "CloseWindow")) {
        mu_gfx_layer_show(t->layer, movie, 0);
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
    else
        return 0;
    return 1;
}
