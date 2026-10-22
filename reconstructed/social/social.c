#include "social.h"
#include <string.h>
#ifndef MU_SOCIAL_MUTATION
#define MU_SOCIAL_MUTATION 0
#endif
static uint16_t u16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }
static int32_t i32(const uint8_t *p)
{
    uint32_t u = (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
    int32_t v;
    memcpy(&v, &u, 4);
    return v;
}
static void name10(char out[11], const uint8_t *p)
{
    memcpy(out, p, 10);
    out[10] = 0;
}
static int32_t percent(int32_t n, int32_t d, int hp)
{
    if (hp ? d <= 0 : d == 0)
        return 0;
    float ratio = 100.0f / (float)d;
    float v = ratio * (float)n;
    if (v >= 2147483648.0f || v < -2147483648.0f)
        return INT32_MIN;
    return (int32_t)v;
}
int mu_social_party_state(int32_t server, int in_view)
{
    if (server == 0)
        return 2;
    return in_view == 1 ? 1 : (MU_SOCIAL_MUTATION == 1 ? 2 : 3);
}
int mu_social_party_request(const uint8_t *b, size_t n, int blocked, int32_t *key)
{
    if (!b || n < 5 || !key)
        return 0;
    *key = MU_SOCIAL_MUTATION == 10 ? u16(b + 3) : ((int32_t)b[3] << 8) | b[4];
    return !blocked;
}
void mu_social_party_member(const uint8_t r[44], int32_t slot, mu_party_member *m)
{
    memset(m, 0, sizeof *m);
    name10(m->name, r);
    m->slot = slot;
    m->number = r[10];
    m->server = i32(r + 28);
    m->world = u16(r + 14);
    m->x = r[16];
    m->y = r[17];
    m->hp = i32(r + 20);
    m->max_hp = i32(r + (MU_SOCIAL_MUTATION == 6 ? 20 : 24));
    m->mp = i32(r + 32);
    m->max_mp = i32(r + 36);
    m->hp_percent = percent(m->hp, m->max_hp, 1);
    m->mp_percent = percent(m->mp, m->max_mp, 0);
    m->control = r[40] == 1;
    m->special = r[41] != 0;
}
int mu_social_party_hp(const mu_party *p, const char *name, int32_t *hp)
{
    for (int i = 0; i < p->count; ++i)
        if (!strcmp(p->members[i].name, name)) {
            *hp = p->members[i].hp_percent;
            return 1;
        }
    return 0;
}
int mu_social_party_receive(mu_party *p, const uint8_t *b, size_t n)
{
    if (n < 4)
        return 0;
    if (b[0] == 0xc2 && b[3] == 0x42) {
        if (n < 5 || b[4] > MU_SOCIAL_PARTY || n < 5 + (size_t)b[4] * 44)
            return 0;
        mu_party next = {0};
        next.count = b[4];
        for (int i = 0; i < next.count; i++)
            mu_social_party_member(b + 5 + i * 44, i, &next.members[i]);
        *p = next;
        return 1;
    }
    if (b[2] == 0x43) {
        memset(p, 0, sizeof *p);
        return 1;
    }
    if (b[2] != 0x44 || n < 4 + (size_t)b[3] * 13)
        return 0;
    for (int i = 0; i < b[3]; i++) {
        const uint8_t *r = b + 4 + i * 13;
        char name[11];
        name10(name, r + 2);
        for (int j = 0; j < p->count; j++)
            if (!strcmp(name, p->members[j].name)) {
                int cap = MU_SOCIAL_MUTATION == 2 ? 99 : 100;
                p->members[j].hp_percent = r[0] > cap ? cap : r[0];
                p->members[j].mp_percent = r[1] > cap ? cap : r[1];
            }
    }
    return 1;
}
int mu_social_party_markers(const mu_party *p, const char *hero, int32_t server, int32_t world,
                            mu_party_marker out[5])
{
    int n = 0;
    for (int i = 0; i < p->count; i++) {
        const mu_party_member *m = &p->members[i];
        if (!strcmp(hero, m->name) || m->server != server || (MU_SOCIAL_MUTATION != 3 && m->world != world))
            continue;
        out[n].key = m->slot;
        out[n].x = (float)m->x * 2.0f;
        out[n].y = (256.0f - (float)m->y) * 2.0f;
        memcpy(out[n].name, m->name, 11);
        n++;
    }
    return n;
}
void mu_social_trade_lock(mu_trade *t, uint8_t state)
{
    if (state == 0 || state == 1)
        t->ok[1] = state;
    if (state == 2) {
        t->warned = 1;
        t->ok[0] = 0;
        t->ok[1] = 0;
        t->wait = MU_SOCIAL_MUTATION == 4 ? 24 : 25;
    }
}
void mu_social_trade_result(mu_trade *t, uint8_t result)
{
    static const int32_t notice[8] = {
        0x1ec, MU_SOCIAL_MUTATION == 8 ? 0x1ec : 0, 0x1ef, 0x1f0, 0x83c, 0x1f0, 0xe8f, 0xe90};
    t->result = result;
    t->notice = result < 8 ? notice[result] : 0;
    t->open = 0;
}
int mu_social_trade_receive(mu_trade *t, const uint8_t *b, size_t n)
{
    if (n < 4)
        return 0;
    switch (b[2]) {
    case 0x54:
        if (b[3] != 1) {
            t->notice = b[3] == 0 ? 0x1ec : b[3] == 2 ? 0x1ed : b[3] == 4 ? 0xfb2 : 0;
            return 1;
        }
        if (n < 20)
            return 0;
        memset(t, 0, sizeof *t);
        t->open = 1;
        t->result = -1;
        name10(t->name, b + 4);
        t->level = u16(b + 14);
        t->guild = i32(b + 16);
        return 1;
    case 0x38:
        if (b[3] < 32)
            memset(&t->items[1][b[3]], 0, sizeof t->items[1][0]);
        return 1;
    case 0x39:
        if (n < 4 + MU_SOCIAL_ITEM_BYTES || b[3] >= 32)
            return 0;
        t->items[1][b[3]].present = 1;
        memcpy(t->items[1][b[3]].bytes, b + 4, MU_SOCIAL_ITEM_BYTES);
        return 1;
    case 0x3b:
        if (n < 8)
            return 0;
        t->zen[1] = i32(b + (MU_SOCIAL_MUTATION == 7 ? 3 : 4));
        return 1;
    case 0x73:
        t->zen[0] = b[3] ? t->proposed_zen : 0;
        return 1;
    case 0x3e:
        mu_social_trade_lock(t, b[3]);
        return 1;
    case 0xbd:
        mu_social_trade_result(t, b[3]);
        return 1;
    default:
        return 0;
    }
}
int mu_social_friend_set(mu_social_friends *f, const char *name, int32_t server)
{
    for (int i = 0; i < f->count; i++)
        if (!strncmp(name, f->list[i].name, 10)) {
            f->list[i].server = server;
            return 1;
        }
    if (f->count >= MU_SOCIAL_FRIENDS)
        return 0;
    mu_social_friend *q = &f->list[f->count++];
    memset(q, 0, sizeof *q);
    size_t n = strlen(name);
    if (n > 10)
        n = 10;
    memcpy(q->name, name, n);
    q->server = server;
    return 1;
}
int mu_social_friend_remove(mu_social_friends *f, const char *name)
{
    for (int i = 0; i < f->count; i++)
        if (!strncmp(name, f->list[i].name, 10)) {
            memmove(f->list + i, f->list + i + 1, (size_t)(f->count - i - 1) * sizeof f->list[0]);
            f->count--;
            return 1;
        }
    return 0;
}
int mu_social_friends_receive(mu_social_friends *f, const uint8_t *b, size_t n)
{
    if (n < 7 || b[6] > MU_SOCIAL_FRIENDS || n < 7 + (size_t)b[6] * 11)
        return 0;
    mu_social_friends next = {0};
    next.count = b[6];
    for (int i = 0; i < next.count; i++) {
        const uint8_t *r = b + 7 + i * 11;
        name10(next.list[i].name, r);
        next.list[i].server = r[MU_SOCIAL_MUTATION == 9 ? 9 : 10];
    }
    *f = next;
    return 1;
}
int mu_social_whisper(const uint8_t *b, size_t n, int bypass, int blocked, char name[11], char text[61])
{
    if (n < 13 || (!bypass && blocked && MU_SOCIAL_MUTATION != 5))
        return 0;
    name10(name, b + 3);
    memset(text, 0, 61);
    size_t k = n - 13;
    if (k > 60)
        k = 60;
    memcpy(text, b + 13, k);
    return 1;
}
