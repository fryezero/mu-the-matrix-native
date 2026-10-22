/* "Go Now" of MyQuestInfo's quest tabs: 0x00d4ffea and the move 0x00d5029b (NATIVE-QUEST-002); see quest.h.
 *
 * The target is the quest record's goal block (0x00d506a2: record + 0x9c): goal[1] the goal type, goal[8] the
 * world, goal[9] / goal[10] the tile.  On the hero's own map the client walks there with the hero's path
 * (0x0129c6be flag 2, mode 3, error check 1, then SendMove); standing on the tile, a talk goal (type 5) asks the
 * server with C1 F6 76; another map, or a tile the path finder cannot reach, arms the path (flag 1) and asks the
 * server to move the hero: C1 F6 7A (accept[1], quest) - the cross-map hook (NATIVE-MAP-001 owns the warp). */
#include "quest_internal.h"

#include <stdio.h>
#include <string.h>

void mu_quest_arrived_helper(mu_quest_client *c);   /* quest_guide.c */

/* 0x0128a52d and 0x012534ae. Neither answer reads a result or destination from the packet. */
void mu_quest_resume_path(mu_quest_resume_state *s, const mu_quest_resume_host *h, uint8_t subcode)
{
    if (s->flag != (MU_QUEST_MUTATION == 12 ? 2 : 1))
        return;
    s->flag = 0;
    if (!h || !h->find || !(h->find(h->user, s->x, s->y, s->target_x, s->target_y) & 0xff))
        return;
    if (!h->next || !(h->next(h->user) & 0xff))
        return;
    s->flag = MU_QUEST_MUTATION == 13 ? 1 : 2;
    if (h->send) {
        int moved = h->send(h->user) & 0xff;
        if (subcode == 0x56 ? moved == 1 : moved != 0)
            s->move_type = 0;
    }
}

void mu_quest_set_move_answer(mu_quest_client *c, void (*answer)(void *user, uint8_t subcode))
{
    c->move_answer = answer;
}

static void send_words(mu_quest_client *c, uint8_t sub, int32_t a, int32_t b)
{
    uint8_t body[6] = {0xf6, sub, (uint8_t)a, (uint8_t)(a >> 8), (uint8_t)b, (uint8_t)(b >> 8)};
    mu_quest_send(c, body, 6, 0, 0);
}

void mu_quest_move(mu_quest_client *c, int32_t quest)
{
    mu_quest *q = mu_quest_get(&c->qs, quest);
    if (!q || !q->record)
        return;
    const int32_t *g = q->record->goal;
    int32_t group = q->record->accept[1];
    if (c->host.helper_running && c->host.helper_running(c->host.user)) {
        uint8_t b[3] = {0xbf, 0x51, 1};
        mu_quest_send(c, b, 3, 0, 0);
    }
    if (c->info.visible)
        mu_quest_info_close(c);
    int32_t hx = c->hero_x, hy = c->hero_y, tx = g[MU_QUEST_MUTATION == 9 ? 8 : 9], ty = g[10];
    if (g[8] == c->world) {
        if (hx == tx && hy == ty) {
            if (c->host.path_reset)
                c->host.path_reset(c->host.user);
            mu_quest_logf(&c->log, "path reset");
            if (g[1] == 5)
                send_words(c, 0x76, group, q->index);
            mu_quest_arrived_helper(c);
            return;
        }
        int ok = c->host.path_start ? c->host.path_start(c->host.user, 2, hx, hy, tx, ty, 3, 1) : 0;
        mu_quest_logf(&c->log, "path start 2 %d %d %d %d 3 1 -> %d", hx, hy, tx, ty, ok);
        if (ok) {
            int moved = c->host.send_move ? c->host.send_move(c->host.user) : 0;
            mu_quest_logf(&c->log, "sendmove -> %d", moved);
            if (moved)
                c->hero_walk = 0;
            return;
        }
    }
    int ok = c->host.path_start ? c->host.path_start(c->host.user, 1, hx, hy, tx, ty, 3, 0) : 0;
    mu_quest_logf(&c->log, "path start 1 %d %d %d %d 3 0 -> %d", hx, hy, tx, ty, ok);
    send_words(c, 0x7a, group, q->index);
}

void mu_quest_tab_go(mu_quest_client *c, mu_quest_tab *t)
{
    if (!t)
        return;
    mu_quest_tab_action(c, t, t->selected);
}
