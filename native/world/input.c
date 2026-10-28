/* INPUT-001: the world input router. See docs/research/client-input.md. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include "input_keys.h"

#ifndef MU_WORLD_NO_GL
#include "../core/mu_skill.h"
#include "../gfx/mu_gfx_layer.h"
#endif
#include "world_rt_internal.h"

/* A key press (not a repeat), after the key state and its window message. */
static int gameplay_key(mu_world_rt *a, int vk)
{
    int used = 0;
    if (a->ground && vk == 0x12) {   /* Alt: setItemView(!view) (0x00efc7d3) */
        mu_world_items_alt(a->ground);
        used = 1;
    }
    if (a->ground && vk == 0x20) {   /* space: the nearest item (0x00efd9ab) */
        mu_world_items_space(a->ground);
        used = 1;
    }
    if (a->combat && vk >= 0x30 && vk <= 0x39) {
        /* 1..6 (NATIVE-COMBAT-001), 7 Evil Spirit, 8 Hellfire, 9 Inferno, 0 Cyclone */
        static const int32_t keys[10] = {22, 4, 17, 22, 41, 24, 26, 9, 10, 14};
        mu_combat_cast(a->combat, keys[vk - 0x30], -1);
        used = 1;
    }
    return used;
}

#ifndef MU_WORLD_NO_GL
/* NATIVE-SKILL-001: the selected skill's cast at a monster through the client's checks (core/mu_skill: stats,
 * the class special cases, IsSkillReady, the mana/AG check, StartSkillDelay -> onUseSkillDelay), then the combat
 * path draws it (mu_combat_cast, NATIVE-COMBAT-001/002).  Returns MU_SKILL_CAST_*. */
int world_rt_skill_cast_at(mu_world_rt *a, int32_t actor, int32_t *skill)
{
    *skill = 0;
    if (!a->gfx)
        return MU_SKILL_CAST_NONE;
    int r = world_gfx_skill_cast(a->gfx, skill);
    if (r == MU_SKILL_CAST_OK) {
        a->skill_casts++;
        if (a->combat && actor >= 0)
            mu_combat_cast(a->combat, *skill, actor);
    } else {
        a->skill_refused++;
    }
    return r;
}
#endif

/* NATIVE-SKILL-001: the right button casts the bar's selected skill at the monster under the mouse (the classic
 * binding; the use controller 0x0107e99a runs the checks). */
static int right_button(mu_world_rt *a)
{
#ifndef MU_WORLD_NO_GL
    if (a->gfx && a->combat && mu_combat_pick(a->combat) >= 0) {
        int32_t actor = mu_combat_pick(a->combat), skill = 0;
        int r = world_rt_skill_cast_at(a, actor, &skill);
        if (!a->quiet)
            fprintf(stderr, "skill %d at actor %d: %s\n", (int)skill, (int)actor, mu_skill_cast_name(r));
        return 1;
    }
#else
    (void)a;
#endif
    return 0;
}

/* Existing view adapters submit their domain intents where migrated. Other gameplay
 * actions use the native demo adapters until their domains publish typed intents.
 * Unsupported windows are explicit refusals, never fabricated session requests. */
static const char *const menu_names[] = {
    "IngameShop", "CharacterInfoFrame", "MyQuestInfo", "CommandWindow", "MoveCommand",
    "winOption", "menu 6 (no-op)", "PersonalShop", "SystemMenu", "FriendMenu", "Guildmatching_2024",
    "GensRanking", "MatchingSelect", "PetInventoryFrame", "InventoryFrame", "GremoryCase",
    "ItemHotKey0", "ItemHotKey1", "ItemHotKey2", "ItemHotKey3", "mcRide mount toggle", "mcGiantRide mount toggle"
};

static int panel(mu_world_rt *a, int vk, int mods)
{
    int id = mu_input_menu(vk, mods);
#ifndef MU_WORLD_NO_GL
    mu_gfx_layer *l = a->gfx ? world_gfx_layer(a->gfx) : NULL;
    if (l && !mods && id >= 16 && id <= 19) {
        (void)mu_gfx_layer_use_item_hotkey(l, id - 16);
        return 1;
    }
    if (l && !mods && (vk == 'S' || vk == 'P') && mu_gfx_layer_is_open(l, MU_GFX_INVENTORY)) {
        if (mu_gfx_layer_is_open(l, MU_GFX_STORE_LIST)) mu_gfx_layer_show(l, MU_GFX_STORE_LIST, 0);
        else return mu_gfx_layer_service_action(l, "store", 0, 0) ? 1 : -1;
        return 1;
    }
    if (l && mods == 2 && (vk == 'A' || vk == 'J')) {
        int movie = vk == 'A' ? MU_GFX_TREE4 : MU_GFX_TREE5;
        if (*mu_gfx_layer_path(l, movie)) {
            mu_gfx_layer_toggle(l, movie);
            return 1;
        }
    }
    /* Existing adapters own toggle/close behavior and their context guards. */
    int native_key = vk == 'I' || vk == 'V' || vk == 'C' || vk == 'T' || vk == 'M' ||
                     vk == 'O' || vk == 'F' || vk == 'U' || vk == 'A' || vk == 27 || vk == 13 ||
                     vk == 9 || (vk >= '0' && vk <= '9') || vk == 'Q' || vk == 'R' || vk == 'W' || vk == 'E';
    if (l && native_key) {
        int used = mu_gfx_layer_key(l, 1, vk, (uint32_t)vk, mods);
        if (used) return 1;
    }
#endif
    if (mods == 2 && (vk == 'T' || vk == 'J' || vk == 'I' || vk == 'A' || vk == 'F' || vk == 'V')) {
        if (!a->quiet) fprintf(stderr, "input: Ctrl+%c unavailable (client modifier branch not migrated)\n", vk);
        return -1;
    }
    if (id == 6) {
        if (!a->quiet) fprintf(stderr, "input: menu 6 has an empty client handler (0x00c73690)\n");
        return 1;
    }
    if (id >= 0) {
        if (!a->quiet) fprintf(stderr, "input: %s unavailable (menu %d, domain/window not migrated)\n",
                               menu_names[id], id);
        return -1;
    }
    const char *missing = vk == 'Z' ? "MacroMain" : vk == 'H' ? "expanded StorageInven" :
                          vk == 'D' ? "CommandWindow" : vk == 'S' ? "PersonalShopProductList (requires inventory)" :
                          vk == 0x24 ? "MU Helper start/stop" : vk == 0x23 ? "HuntRecord" :
                          vk == 0x70 ? "legacy help (window 0x24/0x25)" : NULL;
    if (missing && !mods) {
        if (!a->quiet) fprintf(stderr, "input: %s unavailable (domain/window not migrated)\n", missing);
        return -1;
    }
    return 0;
}

int mu_world_rt_input(mu_world_rt *a, const mu_input_msg *m)
{
    if (!a || !m) return 0;
#ifndef MU_WORLD_NO_GL
    mu_gfx_layer *l = a->gfx ? world_gfx_layer(a->gfx) : NULL;
#endif
    if (m->kind == MU_INPUT_FOCUS) {
        a->input_suspended = !m->down;
        if (!m->down) {
            for (int k = 0; k < 256; ++k) {
                a->input_state[k] = a->input_down[k] = 0;
                mu_walk_key(&a->walk, k, 0);
            }
            mu_walk_message(&a->walk, 0x202u, 0, 0);
            mu_walk_message(&a->walk, 0x205u, 0, 0);
            mu_walk_message(&a->walk, 0x208u, 0, 0);
            mu_walk_message(&a->walk, 0x101u, 0, 0);
            a->input_composing = 0;
#ifndef MU_WORLD_NO_GL
            if (l) mu_gfx_layer_compose(l, "", -1);
#endif
        }
        return 1;
    }
    if (a->input_suspended) return 1;
    if (m->kind == MU_INPUT_TEXT || m->kind == MU_INPUT_COMPOSE) {
        a->input_composing = m->kind == MU_INPUT_COMPOSE && m->text && *m->text;
#ifndef MU_WORLD_NO_GL
        return l ? (m->kind == MU_INPUT_TEXT ? mu_gfx_layer_text(l, m->text ? m->text : "") :
                    mu_gfx_layer_compose(l, m->text ? m->text : "", m->cursor)) : 0;
#else
        return 0;
#endif
    }
    if (m->kind == MU_INPUT_KEY) {
        if (m->vk <= 0 || m->vk >= 256) return 0;
        int was_down = a->input_down[m->vk];
        int mods = m->mods | (a->input_down[0x10] ? 1 : 0) | (a->input_down[0x11] ? 2 : 0) |
                   (a->input_down[0x12] ? 4 : 0);
        a->input_down[m->vk] = (uint8_t)(m->down != 0);
        mu_input_scan(a->input_state, a->input_down, 1, 1, 1, 0);
#ifndef MU_WORLD_NO_GL
        /* Text and IME candidates have first refusal, including repeated keys.
         * Never let a digit in preedit fall through to the combat hotkeys. */
        if (l && (mu_gfx_layer_text_active(l) || a->input_composing)) {
            mu_gfx_layer_key(l, m->down, m->vk, (uint32_t)m->vk, mods);
            mu_walk_key(&a->walk, m->vk, 0);
            return 1;
        }
#endif
        if (!m->down) {
            mu_walk_key(&a->walk, m->vk, 0);
            mu_walk_message(&a->walk, 0x101u, (uint32_t)m->vk, 0);
#ifndef MU_WORLD_NO_GL
            if (l && m->vk != 'Q' && m->vk != 'W' && m->vk != 'E' && m->vk != 'R')
                mu_gfx_layer_key(l, 0, m->vk, (uint32_t)m->vk, mods);
#endif
            return 1;
        }
        if (a->input_composing || was_down || m->repeat || a->input_state[m->vk] != 2) return 1;
        int used = panel(a, m->vk, mods);
        if (used) return used;
        if ((!mods || m->vk == 0x12) && gameplay_key(a, m->vk)) {
            if (m->vk == 0x12) {   /* SelectObjects also reads the held Alt state. */
                mu_walk_key(&a->walk, m->vk, 1);
                mu_walk_message(&a->walk, 0x100u, (uint32_t)m->vk, 0);
            }
            return 1;
        }
        mu_walk_key(&a->walk, m->vk, 1);
        mu_walk_message(&a->walk, 0x100u, (uint32_t)m->vk, 0);
        return 0;
    }
    if (m->kind == MU_INPUT_MESSAGE) {
        if (m->message == 0x100u || m->message == 0x101u) {
            mu_input_msg key = {.kind = MU_INPUT_KEY, .vk = (int)m->wparam, .down = m->message == 0x100u};
            return mu_world_rt_input(a, &key);
        }
        int x = (int16_t)(m->lparam & 0xffffu), y = (int16_t)(m->lparam >> 16);
        if (m->message >= 0x200u && m->message <= 0x208u) {
            a->input_x = x; a->input_y = y;
#ifndef MU_WORLD_NO_GL
            if (l) {
                int button = m->message >= 0x207u ? 2 : m->message >= 0x204u ? 1 : 0;
                int kind = m->message == 0x200u ? 0 :
                           (m->message == 0x202u || m->message == 0x205u || m->message == 0x208u) ? 2 : 1;
                if (mu_gfx_layer_mouse(l, kind, button, x, y)) return 1;
            }
#endif
            /* Update selection coordinates even for a press without prior motion. */
            mu_walk_message(&a->walk, MU_WM_MOUSEMOVE, 0, m->lparam);
            if (m->message == 0x204u && right_button(a)) return 1;
        }
#ifndef MU_WORLD_NO_GL
        if (l && m->message == MU_WM_MOUSEWHEEL &&
            mu_gfx_layer_mouse(l, 3, (int16_t)(m->wparam >> 16) / 120, a->input_x, a->input_y)) return 1;
#endif
        mu_walk_message(&a->walk, m->message, m->wparam, m->lparam);
        return 0;
    }
    return 0;
}

void mu_world_rt_message(mu_world_rt *a, uint32_t msg, uint32_t wp, uint32_t lp)
{
    mu_input_msg m = {.kind = MU_INPUT_MESSAGE, .message = msg, .wparam = wp, .lparam = lp};
    (void)mu_world_rt_input(a, &m);
}
void mu_world_rt_key(mu_world_rt *a, int vk, int down)
{
    mu_input_msg m = {.kind = MU_INPUT_KEY, .vk = vk, .down = down};
    (void)mu_world_rt_input(a, &m);
}

/* Percent encoding keeps the single-token script grammar independent of shell,
 * whitespace, locale and UTF-8 byte length. No decoded client data in scripts. */
static int unquote(char *out, size_t cap, const char *s)
{
    size_t n = 0;
    while (*s) {
        unsigned char v = (unsigned char)*s++;
        if (v == '%') {
            if (!isxdigit((unsigned char)s[0]) || !s[1] || !isxdigit((unsigned char)s[1])) return 0;
            char h[3] = {s[0], s[1], 0}; v = (unsigned char)strtoul(h, NULL, 16); s += 2;
            if (!v) return 0;
        }
        if (n + 1 >= cap) return 0;
        out[n++] = (char)v;
    }
    out[n] = 0; return 1;
}
int mu_world_rt_action(mu_world_rt *a, const char *action)
{
    mu_input_msg m = {0};
    char verb[24], arg[1024], decoded[1024];
    int n = 0;
    if (sscanf(action, "%23[^:]:%1023s%n", verb, arg, &n) != 2 || action[n]) return -2;
    if (!strcmp(verb, "key") || !strcmp(verb, "down") || !strcmp(verb, "up")) {
        char *end; long vk;
        if (arg[0] && !arg[1] && isalpha((unsigned char)arg[0])) vk = toupper((unsigned char)arg[0]);
        else { vk = strtol(arg, &end, 0); if (!arg[0] || *end) return -2; }
        if (vk <= 0 || vk > 255) return -2;
        m.kind = MU_INPUT_KEY; m.vk = (int)vk; m.down = strcmp(verb, "up") != 0;
        int r = mu_world_rt_input(a, &m);
        if (!strcmp(verb, "key")) { m.down = 0; (void)mu_world_rt_input(a, &m); }
        return r;
    }
    if (!strcmp(verb, "text") || !strcmp(verb, "compose")) {
        const char *text = arg;
        m.kind = MU_INPUT_TEXT;
        if (!strcmp(verb, "compose")) {
            char *end; long cursor = strtol(arg, &end, 10);
            if (end == arg || *end != ':' || cursor < -1 || cursor > 1023) return -2;
            m.kind = MU_INPUT_COMPOSE; m.cursor = (int)cursor; text = end + 1;
        }
        if (!unquote(decoded, sizeof decoded, text)) return -2;
        m.text = decoded; return mu_world_rt_input(a, &m);
    }
    if (!strcmp(verb, "wheel") || !strcmp(verb, "focus")) {
        char *end; long value = strtol(arg, &end, 10);
        if (end == arg || *end || value < -100 || value > 100) return -2;
        if (!strcmp(verb, "focus")) {
            if (value != 0 && value != 1) return -2;
            m.kind = MU_INPUT_FOCUS; m.down = (int)value;
        } else {
            m.kind = MU_INPUT_MESSAGE; m.message = MU_WM_MOUSEWHEEL;
            m.wparam = (uint32_t)(uint16_t)(value * 120) << 16;
        }
        return mu_world_rt_input(a, &m);
    }
    int x, y, used = 0;
    if (!strcmp(verb, "move") || !strcmp(verb, "ldown") || !strcmp(verb, "lup") ||
        !strcmp(verb, "rdown") || !strcmp(verb, "rup")) {
        if (sscanf(arg, "%d,%d%n", &x, &y, &used) != 2 || arg[used] ||
            x < -32768 || x > 32767 || y < -32768 || y > 32767) return -2;
        m.kind = MU_INPUT_MESSAGE;
        m.message = !strcmp(verb, "move") ? 0x200u : !strcmp(verb, "ldown") ? 0x201u :
                    !strcmp(verb, "lup") ? 0x202u : !strcmp(verb, "rdown") ? 0x204u : 0x205u;
        m.wparam = m.message == 0x201u ? 1u : 0u;
        m.lparam = ((uint32_t)(uint16_t)y << 16) | (uint16_t)x;
        return mu_world_rt_input(a, &m);
    }
    return -2;
}

void mu_world_rt_input_report(const mu_world_rt *a, FILE *out)
{
    if (!a) return;
    fprintf(out, "{\"input_state\":true,\"casts\":%u,\"pickups\":%u,\"pickup_requests\":%u,"
                 "\"alt_toggles\":%u,\"skill_casts\":%u,\"skill_refused\":%u}",
            a->combat ? a->combat->stats.skills : 0u, a->ground ? a->ground->stats.picks_done : 0u,
            a->ground ? a->ground->stats.picks_requested : 0u, a->ground ? a->ground->stats.alt_toggles : 0u,
#ifndef MU_WORLD_NO_GL
            a->skill_casts, a->skill_refused
#else
            0u, 0u
#endif
            );
    fputc('\n', out);
    fprintf(out, "{\"input_items\":true,\"kills\":%u,\"drops\":%u,\"lands\":%u,\"space_picks\":%u}\n",
            a->combat ? a->combat->stats.kills : 0u, a->ground ? a->ground->stats.drops : 0u,
            a->ground ? a->ground->stats.lands : 0u, a->ground ? a->ground->stats.space_picks : 0u);
#ifndef MU_WORLD_NO_GL
    if (a->gfx) {
        char b[4096]; world_gfx_report(a->gfx, b, sizeof b); fprintf(out, "{%s}\n", b);
    }
#endif
}

char *mu_input_script_read(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    char *text = malloc(65538);
    if (!text) { fclose(f); return NULL; }
    size_t n = fread(text, 1, 65537, f);
    int bad = ferror(f) || n > 65536;
    fclose(f);
    if (bad) { free(text); return NULL; }
    text[n] = 0;
    int comment = 0;
    for (size_t i = 0; i < n; ++i) {
        if (!text[i]) { free(text); return NULL; }
        if (text[i] == '#') comment = 1;
        if (text[i] == '\n' || text[i] == '\r') comment = 0;
        if (comment || text[i] == '\n' || text[i] == '\r' || text[i] == '\t') text[i] = ' ';
    }
    return text;
}

int mu_input_script_parse(const char *text, mu_input_action out[MU_INPUT_SCRIPT_MAX])
{
    int count = 0;
    const char *p = text;
    while (*p) {
        while (isspace((unsigned char)*p) || *p == ';') ++p;
        if (!*p) break;
        if (count == MU_INPUT_SCRIPT_MAX) return -1;
        char *end;
        errno = 0;
        long frame = strtol(p, &end, 10);
        if (errno || end == p || *end != ':' || frame < 0 || frame > INT32_MAX) return -1;
        p = end + 1;
        size_t n = 0;
        while (p[n] && !isspace((unsigned char)p[n]) && p[n] != ';') ++n;
        if (!n || n >= sizeof out[count].what) return -1;
        out[count].frame = (int32_t)frame;
        memcpy(out[count].what, p, n); out[count].what[n] = 0;
        ++count; p += n;
    }
    return count;
}
