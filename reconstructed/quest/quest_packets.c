/* The quest packets (receive dispatcher 0x01287ead, opcode 0xF6) and their state updates
 * (NATIVE-QUEST-001); see quest.h. */
#include "quest_internal.h"

#include <stdio.h>
#include <string.h>

static uint32_t u16(const uint8_t *p, size_t size, size_t at)
{
    return at + 2 <= size ? (uint32_t)p[at] | (uint32_t)p[at + 1] << 8 : 0;
}

static uint32_t u8(const uint8_t *p, size_t size, size_t at)
{
    return at < size ? p[at] : 0;
}

static uint32_t u32(const uint8_t *p, size_t size, size_t at)
{
    return at + 4 <= size ? (uint32_t)p[at] | (uint32_t)p[at + 1] << 8 | (uint32_t)p[at + 2] << 16 |
                                (uint32_t)p[at + 3] << 24
                          : 0;
}

static void notice(mu_quest_client *c, const char *text)
{
    char q[4096];
    mu_quest_json(q, sizeof q, text);
    mu_quest_logf(&c->log, "notice %s", q);
}

/* The message box 0x00b3967c(owner NpcQuestProgress, 0, text, title "Quest" GlobalText 0x474, 0, 0, 0). */
static void msgbox(mu_quest_client *c, const char *text)
{
    char q[4096], t[1024];
    mu_quest_json(q, sizeof q, text);
    mu_quest_json(t, sizeof t, mu_quest_text(c, 0x474));
    mu_quest_logf(&c->log, "msgbox NpcQuestProgress 0 %s %s 0 0 0", q, t);
}

/* MyQuestInfo's refresh when the quest's category is the open tab (handlers 0x6f, 0x72, 0x73, 0x74). */
static void info_refresh_tab(mu_quest_client *c, int32_t quest)
{
    if (c->info.visible && c->info.tab == mu_quest_category(quest)) {
        mu_quest_tab *t = mu_quest_info_tab(c, c->info.tab);
        if (t)
            mu_quest_tab_init(c, t);
        else
            mu_quest_tab_other(c, c->info.tab, 1);
    }
}

/* 0x012510fe (0x6f): a quest starts (a server-started quest: the state goes to 1). */
static void on_start(mu_quest_client *c, const uint8_t *p, size_t n)
{
    int32_t index = (int32_t)u16(p, n, 6);
    mu_quest *q = mu_quest_get(&c->qs, index);
    if (!q)
        return;
    q->state = 0;
    q->count = 0;
    q->seen = 0;
    q->state = 1;
    mu_quest_activate(c, index);
    info_refresh_tab(c, index);
    mu_quest_info_checked(c);
}

/* 0x0125313f (0x70, decoded): the character's quest list: every active set is cleared, then each entry
 * (10 bytes from offset 6: +2 quest, +6 count, +8 state, +9 seen) sets its quest and activates it. */
static void on_list(mu_quest_client *c, const uint8_t *p, size_t n)
{
    mu_quest_reset_active(c);
    int touched = 0;
    int32_t count = (int32_t)u16(p, n, 4);
    for (int32_t i = 0; i < count; i++) {
        size_t e = 6 + 10 * (size_t)i;
        int32_t index = (int32_t)u16(p, n, e + 2);
        mu_quest *q = mu_quest_get(&c->qs, index);
        if (!q)
            continue;
        q->state = (int32_t)u8(p, n, e + 8);
        q->count = (int32_t)u16(p, n, e + 6);
        q->seen = u8(p, n, e + 9) != 0;
        mu_quest_activate(c, index);
        if (mu_quest_category(index) == c->info.tab)
            touched = 1;
    }
    if (touched && c->info.visible) {
        mu_quest_tab *t = mu_quest_info_tab(c, c->info.tab);
        if (t)
            mu_quest_tab_init(c, t);
        else
            mu_quest_tab_other(c, c->info.tab, 1);
        mu_quest_info_checked(c);
    }
}

/* 0x0126d65c (0x71, decoded): an NPC's quests (6-byte entries from offset 6: +2 quest, +4 state) for
 * npcdialogue's quest list. */
static void on_npc_list(mu_quest_client *c, const uint8_t *p, size_t n)
{
    int32_t list[64];
    int32_t m = 0;
    int32_t count = (int32_t)u16(p, n, 4);
    for (int32_t i = 0; i < count; i++) {
        size_t e = 6 + 6 * (size_t)i;
        int32_t index = (int32_t)u16(p, n, e + 2);
        mu_quest *q = mu_quest_get(&c->qs, index);
        if (!q)
            continue;
        q->state = (int32_t)u8(p, n, e + 4);
        if (m < 64)
            list[m++] = index;
    }
    mu_quest_dialog_quests(c, list, m);
}

/* 0x01222933 (0x72): the answer to the accept request. */
static void on_accept(mu_quest_client *c, const uint8_t *p, size_t n)
{
    uint32_t result = u8(p, n, 8);
    if (result == 0) {
        int32_t index = (int32_t)u16(p, n, 6);
        mu_quest *q = mu_quest_get(&c->qs, index);
        if (!q)
            return;
        q->state = 1;
        q->count = 0;
        if (!c->progress.visible) {
            mu_quest_progress_set(c, index);
            mu_quest_progress_open(c);
        } else {
            mu_quest_progress_show_page(c);
            mu_quest_progress_refresh(c);
        }
        mu_quest_activate(c, index);
        info_refresh_tab(c, index);
        mu_quest_info_checked(c);
    } else if (result == 1) {
        notice(c, mu_quest_text(c, 0x118b));
    }
}

/* 0x0122287a (0x73): the answer to the give-up request. */
static void on_giveup(mu_quest_client *c, const uint8_t *p, size_t n)
{
    if (u8(p, n, 8) != 0)
        return;
    int32_t index = (int32_t)u16(p, n, 6);
    mu_quest_deactivate(c, index);
    info_refresh_tab(c, index);
}

/* 0x0122adf5 (0x74): the answer to the complete request. */
static void on_complete(mu_quest_client *c, const uint8_t *p, size_t n)
{
    uint32_t result = u8(p, n, 8);
    if (result == 0) {
        if (c->progress.visible)
            mu_quest_progress_close(c);
        int32_t index = (int32_t)u16(p, n, 6);
        mu_quest_deactivate(c, index);
        if (c->info.visible) {
            info_refresh_tab(c, index);
            mu_quest_info_checked(c);
        }
        return;
    }
    if (c->progress.visible)
        mu_quest_progress_button(c, 0);
    char text[1024];
    switch (result) {
    case 1:
        msgbox(c, mu_quest_text(c, 0xb00));
        break;
    case 2:
    case 3:
    case 4: {
        static const int32_t SECOND[5] = {0, 0, 0x177, 0x13d5, 0xb17};
        mu_qarg a[2] = {{1, 0, mu_quest_text(c, SECOND[result])}, {1, 0, mu_quest_text(c, 0x176)}};
        mu_quest_sprintf(text, sizeof text, "%s %s", a, 2);
        msgbox(c, text);
        break;
    }
    default:
        break;
    }
}

/* 0x01253577 (0x75): progress (+8 count, +10 state). */
static void on_progress(mu_quest_client *c, const uint8_t *p, size_t n)
{
    int32_t index = (int32_t)u16(p, n, 6);
    mu_quest *q = mu_quest_get(&c->qs, index);
    if (!q)
        return;
    q->state = (int32_t)u8(p, n, 10);
    q->count = (int32_t)u16(p, n, MU_QUEST_MUTATION == 4 ? 9 : 8);
    if (c->progress.visible) {
        mu_quest_progress_show_page(c);
        mu_quest_progress_refresh(c);
    }
    mu_quest_tab *t = mu_quest_info_tab(c, q->category);
    if (t && t->selected == q->index)
        mu_quest_tab_select(c, t, q->index);
    if (c->summary && c->hud)
        mu_summary_update(c);
    else if (c->summary)
        mu_quest_logf(&c->log, "summary update");
}

/* 0x012533c9 (0x81): "Cannot move to %s." (GlobalText 0x154a) with the map name of +4. */
static void on_move_refused(mu_quest_client *c, const uint8_t *p, size_t n)
{
    const char *map = c->host.map_name ? c->host.map_name(c->host.user, (int32_t)u16(p, n, 4)) : NULL;
    char text[1024];
    mu_qarg a = {1, 0, map ? map : ""};
    mu_quest_sprintf(text, sizeof text, mu_quest_text(c, 0x154a), &a, 1);
    notice(c, text);
}

int mu_quest_receive(mu_quest_client *c, const uint8_t *p, size_t n)
{
    if (!c || !p || n < 4)
        return 0;
    switch (p[2]) {
    case 0xc0: mu_classic_receive_states(c, p, n); return 1;
    case 0xa1: mu_classic_receive_state(c, p, n); return 1;
    case 0xa4: mu_classic_receive_kills(c, p, n); return 1;
    case 0x86: mu_classic_receive_result(c, p, n); return 1;
    case 0xf6: break;
    default: return 0;
    }
    switch (p[3]) {
    case 0x1c: mu_classic_receive_kill_list(c, p, n); return 1;
    case 0x50: mu_guide_receive_state(c, p, n); return 1;
    case 0x51: mu_guide_receive_result(c, p, n); return 1;
    case 0x6f: on_start(c, p, n); return 1;
    case 0x70: on_list(c, p, n); return 1;
    case 0x71: on_npc_list(c, p, n); return 1;
    case 0x72: on_accept(c, p, n); return 1;
    case 0x73: on_giveup(c, p, n); return 1;
    case 0x74: on_complete(c, p, n); return 1;
    case 0x75: on_progress(c, p, n); return 1;
    case 0x81: on_move_refused(c, p, n); return 1;
    case 0x82: mu_quest_value_set(&c->qs, (int32_t)u16(p, n, 6), (int32_t)u32(p, n, 8)); return 1;
    case 0x83: mu_quest_value_erase(&c->qs, (int32_t)u16(p, n, 6)); return 1;
    default: return 0;
    }
}
