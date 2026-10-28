/* Synthetic party server. Plaintext answer feed, encrypted invites/answers are
 * explicit fixture commands, never a claim of a Send(1,0) round trip. */
#define _POSIX_C_SOURCE 200809L
#include "../../core/mu_social.h"
#include "../../core/mu_world_players.h"
#include "../../session/mu_session_seed.h"
#include "../behavior.h"
#include "../party_demo.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef struct party_fixture
{
    mu_party members;
    char hero[11], peers[8][11];
    int32_t x[9], y[9], world, hp[9], mp[9], peer_count, incoming;
    int dirty, clear, invite, result, update;
    uint8_t raw[3400];
    size_t raw_size;
} party_fixture;
static void text(char out[11], const char *s) { snprintf(out, 11, "%.10s", s); }
static void put32(uint8_t *p, int32_t v)
{
    for (int i = 0; i < 4; ++i)
        p[i] = (uint8_t)((uint32_t)v >> (8 * i));
}
static int peer(party_fixture *s, const char *name)
{
    for (int i = 0; i < s->peer_count; ++i)
        if (!strcmp(name, s->peers[i]))
            return i;
    return -1;
}
static void add(party_fixture *s, const char *name)
{
    if (s->members.count == 5)
        return;
    mu_party_member *m = &s->members.members[s->members.count++];
    memset(m, 0, sizeof *m);
    text(m->name, name);
    m->number = s->members.count - 1;
}
static int join(party_fixture *s, int k, int incoming)
{
    if (k < 0 || k >= s->peer_count || s->members.count >= 5)
        return 0;
    for (int i = 0; i < s->members.count; ++i)
        if (!strcmp(s->members.members[i].name, s->peers[k]))
            return 0;
    if (!s->members.count)
    {
        add(s, incoming ? s->peers[k] : s->hero);
        add(s, incoming ? s->hero : s->peers[k]);
    }
    else
        add(s, s->peers[k]);
    s->dirty = 1;
    return 1;
}
static void *open_party(mu_fixture_ctx *ctx, const char *args, char *error, size_t cap)
{
    (void)ctx;
    (void)error;
    (void)cap;
    party_fixture *s = calloc(1, sizeof *s);
    if (!s)
        return NULL;
    if (!mu_fx_arg_str(args, "hero", s->hero, sizeof s->hero))
        text(s->hero, "Hero");
    char names[160] = {0};
    mu_fx_arg_str(args, "peers", names, sizeof names);
    char *save = NULL;
    for (char *p = strtok_r(names, ",", &save); p && s->peer_count < 8; p = strtok_r(NULL, ",", &save))
        text(s->peers[s->peer_count++], p);
    for (int i = 0; i < 9; ++i)
    {
        s->hp[i] = s->mp[i] = 100;
        s->x[i] = s->y[i] = 120;
    }
    s->invite = s->result = -1;
    return s;
}
static int command(void *self, mu_fixture_ctx *ctx, const char *line, char *error, size_t cap)
{
    (void)ctx;
    party_fixture *s = self;
    int k, incoming = 0, hp, mp;
    char name[11];
    if (sscanf(line, "join %d %d", &k, &incoming) >= 1 && join(s, k, incoming))
        return 0;
    if (sscanf(line, "invite %d", &k) == 1 && k >= 0 && k < 65536)
    {
        s->invite = k;
        return 0;
    }
    if (sscanf(line, "result %d", &k) == 1 && k >= 0 && k < 256)
    {
        s->result = k;
        return 0;
    }
    if (sscanf(line, "bars %10[^,],%d,%d", name, &hp, &mp) == 3 && hp >= 0 && hp <= 100 && mp >= 0 &&
        mp <= 100)
    {
        k = !strcmp(name, s->hero) ? 0 : peer(s, name) + 1;
        if (!k && strcmp(name, s->hero))
            goto bad;
        s->hp[k] = hp;
        s->mp[k] = mp;
        s->update = 1;
        return 0;
    }
    if (!strcmp(line, "clear"))
    {
        s->members.count = 0;
        s->clear = 1;
        return 0;
    }
bad:
    snprintf(error, cap, "invalid party command");
    return -1;
}
static int request(void *self, mu_fixture_ctx *ctx, const mu_fixture_request *r)
{
    (void)ctx;
    party_fixture *s = self;
    if (r->head != 0xc1 || r->opcode != 0xc3 || r->length != 15)
        return 0;
    char name[11];
    memcpy(name, r->bytes + 4, 10);
    name[10] = 0;
    for (int i = 0; i < s->members.count; ++i)
    {
        mu_party_member *m = &s->members.members[i];
        if (m->number != r->bytes[3] || strcmp(name, m->name))
            continue;
        if (!strcmp(name, s->hero))
        {
            s->members.count = 0;
            s->clear = 1;
        }
        else if (!strcmp(s->members.members[0].name, s->hero))
        {
            --s->members.count;
            memmove(m, m + 1, (size_t)(s->members.count - i) * sizeof *m);
            s->dirty = 1;
        }
        return 1;
    }
    return 1;
}
static void send_packet(mu_fixture_ctx *ctx, int head, int opcode, const uint8_t *b, size_t n)
{
    mu_packet p;
    mu_packet_begin(&p, (uint8_t)head, (uint8_t)opcode);
    mu_packet_add(&p, b, n, 0);
    mu_fx_send(ctx, MU_CONN_GAME, &p, 0);
}
static void step(void *self, mu_fixture_ctx *ctx, uint32_t now)
{
    (void)now;
    party_fixture *s = self;
    if (s->raw_size)
    {
        size_t at = s->raw[0] == 0xc2 ? 4 : 3;
        send_packet(ctx, s->raw[0], s->raw[at - 1], s->raw + at, s->raw_size - at);
        s->raw_size = 0;
    }
    if (s->invite >= 0)
    {
        uint8_t b[2] = {(uint8_t)(s->invite >> 8), (uint8_t)s->invite};
        send_packet(ctx, 0xc1, 0x40, b, 2);
        s->invite = -1;
    }
    if (s->result >= 0)
    {
        uint8_t b = (uint8_t)s->result;
        send_packet(ctx, 0xc1, 0x41, &b, 1);
        s->result = -1;
    }
    if (s->clear)
    {
        uint8_t b[2] = {0, 1};
        send_packet(ctx, 0xc1, 0x43, b, 2);
        s->clear = 0;
    }
    if (s->dirty)
    {
        uint8_t b[1 + 5 * 44] = {0};
        b[0] = (uint8_t)s->members.count;
        for (int i = 0; i < s->members.count; ++i)
        {
            mu_party_member *m = &s->members.members[i];
            uint8_t *r = b + 1 + i * 44;
            int k = peer(s, m->name) + 1;
            memcpy(r, m->name, 10);
            r[10] = (uint8_t)m->number;
            r[14] = (uint8_t)s->world;
            r[15] = (uint8_t)(s->world >> 8);
            r[16] = (uint8_t)s->x[k];
            r[17] = (uint8_t)s->y[k];
            put32(r + 20, s->hp[k]);
            put32(r + 24, 100);
            put32(r + 28, 1);
            put32(r + 32, s->mp[k]);
            put32(r + 36, 100);
        }
        send_packet(ctx, 0xc2, 0x42, b, 1 + (size_t)s->members.count * 44);
        s->dirty = 0;
    }
    if (s->update)
    {
        uint8_t b[1 + 5 * 13] = {0};
        b[0] = (uint8_t)s->members.count;
        for (int i = 0; i < s->members.count; ++i)
        {
            mu_party_member *m = &s->members.members[i];
            uint8_t *r = b + 1 + i * 13;
            int k = peer(s, m->name) + 1;
            r[0] = (uint8_t)s->hp[k];
            r[1] = (uint8_t)s->mp[k];
            memcpy(r + 2, m->name, 10);
        }
        send_packet(ctx, 0xc1, 0x44, b, 1 + (size_t)s->members.count * 13);
        s->update = 0;
    }
}
const mu_fixture_behavior mu_fx_party = {.name = "party",
                                         .open = open_party,
                                         .on_command = command,
                                         .on_step = step,
                                         .close = free,
                                         .on_plain_request = request};
/* Compatibility facade, kept beside fixture policy like the quest facade. */
static party_fixture *model(mu_social_session *s)
{
    return mu_fixture_behavior_state(s->party_fixture, "party");
}
static void sync_party(mu_social_session *s)
{
    mu_party prior = s->party;
    mu_party_view v = mu_session_party(s->session);
    s->party = *v.members;
    s->request_key = v.request_key;
    if (s->party_revision != mu_session_rev(s->session, MU_DOMAIN_PARTY))
    {
        s->party_revision = mu_session_rev(s->session, MU_DOMAIN_PARTY);
        ++s->revision;
    }
    for (int i = 0; i < s->party.count; ++i)
    {
        mu_party_member *m = &s->party.members[i];
        int k = -1;
        for (int j = 0; s->players && j < s->players->count; ++j)
            if (!strcmp(m->name, s->players->list[j].spec.name))
                k = j;
        m->in_view = (uint8_t)(!strcmp(m->name, s->hero) || (k >= 0 && s->players->list[k].in_view));
    }
    if (memcmp(&prior, &s->party, sizeof prior))
        ++s->revision;
    if (v.pending && !s->pending)
    {
        party_fixture *f = model(s);
        int k = v.request_key - 0x200;
        s->pending = 1;
        s->incoming = 1;
        if (k >= 0 && k < f->peer_count)
            text(s->pending_name, f->peers[k]);
        else
            snprintf(s->pending_name, sizeof s->pending_name, "#%04X", (unsigned)v.request_key);
    }
    mu_cue cues[16];
    uint32_t lost;
    size_t n;
    while ((n = mu_session_cues(s->session, &s->party_cursor, cues, 16, &lost)) > 0)
        for (size_t i = 0; i < n; ++i)
            if (cues[i].kind == MU_CUE_NOTICE)
                s->party_notice = cues[i].u.notice.global_text;
}
void mu_party_demo_step(mu_social_session *s)
{
    if (!s->session)
        return;
    party_fixture *f = model(s);
    int changed = f->world != s->world;
    f->world = s->world;
    for (int k = 0; k <= f->peer_count; ++k)
    {
        int x = s->x, y = s->y;
        if (k && s->players && k <= s->players->count)
        {
            x = s->players->list[k - 1].c.tile[0];
            y = s->players->list[k - 1].c.tile[1];
        }
        changed |= x != f->x[k] || y != f->y[k];
        f->x[k] = x;
        f->y[k] = y;
    }
    if (changed && f->members.count)
        f->dirty = 1;
    mu_transport_flush(s->party_transport);
    mu_transport_poll(s->party_transport, ++s->party_tick * 40u);
    mu_session_pump(s->session, s->party_tick * 40u);
    sync_party(s);
}
void mu_party_demo_close(mu_social_session *s)
{
    if (s->session)
        mu_session_close(s->session);
    if (s->party_transport)
        mu_transport_free(s->party_transport);
    if (s->party_fixture)
        mu_fixture_close(s->party_fixture);
    s->session = NULL;
    s->party_transport = NULL;
    s->party_fixture = NULL;
}
int mu_party_demo_open(mu_social_session *s)
{
    char path[] = "/tmp/mu-party-XXXXXX", error[256];
    int fd = mkstemp(path);
    if (fd < 0)
        return 0;
    FILE *out = fdopen(fd, "w");
    if (!out)
    {
        close(fd);
        unlink(path);
        return 0;
    }
    fprintf(out, "endpoint game 127.0.0.1:55907\nuse party hero=%s\n", s->hero);
    fclose(out);
    mu_fixture_options fo = {path, NULL, 1};
    s->party_fixture = mu_fixture_open(&fo, error, sizeof error);
    unlink(path);
    if (!s->party_fixture)
        return 0;
    party_fixture *f = model(s);
    f->peer_count = s->players ? s->players->count : 0;
    if (f->peer_count > 8)
        f->peer_count = 8;
    for (int i = 0; i < f->peer_count; ++i)
        text(f->peers[i], s->players->list[i].spec.name);
    s->party_transport = mu_fixture_transport(s->party_fixture);
    mu_session_config cfg = {.transport = s->party_transport};
    mu_fixture_endpoint(s->party_fixture, "game", &cfg.connect_server);
    mu_session_seed seed = {.level = 1};
    text(seed.name, s->hero);
    s->session = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
    if (!s->session)
    {
        mu_party_demo_close(s);
        return 0;
    }
    s->party_cursor = mu_session_cue_cursor(s->session);
    for (int i = 0; i < f->peer_count; ++i)
        if (s->players->list[i].spec.party)
            join(f, i, 0);
    mu_party_demo_step(s);
    return 1;
}
int mu_party_demo_receive(mu_social_session *s, const uint8_t *b, size_t n)
{
    if (!s->session || !b || n < 4 || n > sizeof model(s)->raw)
        return 0;
    if ((b[0] == 0xc1 && b[1] != n) || (b[0] == 0xc2 && (((size_t)b[1] << 8) | b[2]) != n))
        return 0;
    size_t need = 0;
    if (b[0] == 0xc2 && b[3] == 0x42 && n >= 5 && b[4] <= 5)
        need = 5 + (size_t)b[4] * 44;
    if (b[0] == 0xc1)
    {
        if (b[2] == 0x40)
            need = 5;
        else if (b[2] == 0x41)
            need = 4;
        else if (b[2] == 0x43)
            need = 5;
        else if (b[2] == 0x44)
            need = 4 + (size_t)b[3] * 13;
    }
    if (!need || n != need || (b[2] == 0x40 && mu_session_party(s->session).pending))
        return 0;
    if ((b[0] == 0xc2 && b[3] == 0x42) || (b[0] == 0xc1 && b[2] == 0x43))
        mu_social_party_receive(&model(s)->members, b, n);
    memcpy(model(s)->raw, b, n);
    model(s)->raw_size = n;
    mu_party_demo_step(s);
    return 1;
}
int mu_party_demo_action(mu_social_session *s, const char *verb, const char *arg)
{
    if (!s->session)
        return 0;
    party_fixture *f = model(s);
    s->party_notice = 0;
    const char *name = *arg ? arg : s->target;
    int k = peer(f, name), notice = 0;
    mu_intent in = {0};
    if (!strcmp(verb, "party") || !strcmp(verb, "incoming-party"))
    {
        if (s->pending || s->trade.open || k < 0)
            return 0;
        for (int i = 0; i < s->party.count; ++i)
            if (!strcmp(s->party.members[i].name, name))
                return 0;
        if (!strcmp(verb, "incoming-party"))
        {
            f->invite = 0x200 + k;
            mu_party_demo_step(s);
            int is_friend = 0;
            for (int i = 0; i < s->friends.count; ++i)
                is_friend |= !strcmp(name, s->friends.list[i].name);
            if (mu_social_party_autoaccept(s->auto_enabled, s->auto_friends, s->auto_guild, is_friend, 1,
                                           s->guild_id, -1))
                return mu_party_demo_action(s, "accept", "");
            return 1;
        }
        if (!mu_social_party_permission(
                1, (s->world >= 18 && s->world <= 23) || s->world == 53 || s->world == 97,
                s->world >= 103 && s->world <= 106, s->party.count != 0,
                !s->party.count || !strcmp(s->party.members[0].name, s->hero), 0, 0, &s->party_notice))
            return 0;
        in.kind = MU_INTENT_PARTY_INVITE;
        in.u.party_invite.key = 0x200 + k;
        mu_social_party_invite(&s->request, (uint16_t)(0x200 + k), 1, 1);
        s->pending = 1;
        s->incoming = 0;
        text(s->pending_name, name);
    }
    else if (!strcmp(verb, "accept") || !strcmp(verb, "decline"))
    {
        if (s->pending != 1 && s->pending != 3)
            return 0;
        int accept = !strcmp(verb, "accept");
        k = peer(f, s->pending_name);
        if (s->pending == 3)
        {
            char who[11];
            text(who, s->pending_name);
            s->pending = 0;
            return !accept || mu_party_demo_action(s, "kick", who);
        }
        if (s->incoming)
        {
            in.kind = MU_INTENT_PARTY_ANSWER;
            in.u.party_answer.accept = accept;
            mu_social_party_answer(&s->request, (uint16_t)mu_session_party(s->session).request_key,
                                   (uint8_t)accept);
        }
        if (accept)
            join(f, k, s->incoming);
        else
            ++s->declined;
        s->pending = 0;
    }
    else if (!strcmp(verb, "confirm-leave") || !strcmp(verb, "kick") || !strcmp(verb, "leave"))
    {
        if (!strcmp(verb, "leave"))
            name = s->hero;
        k = -1;
        for (int i = 0; i < s->party.count; ++i)
            if (!strcmp(name, s->party.members[i].name))
                k = i;
        if (mu_social_party_leave_prompt(s->world, k >= 0, !strcmp(name, s->hero), &notice) != 1)
            return 0;
        if (!strcmp(verb, "confirm-leave"))
        {
            if (s->pending)
                return 0;
            s->pending = 3;
            text(s->pending_name, name);
            return 1;
        }
        if (strcmp(name, s->hero) && strcmp(s->party.members[0].name, s->hero))
            return 0;
        in.kind = MU_INTENT_PARTY_LEAVE;
        in.u.party_leave.member = k;
        mu_social_party_remove(&s->request, (uint8_t)s->party.members[k].number, name, 1, 0);
    }
    else if (!strcmp(verb, "health") || !strcmp(verb, "party-result"))
    {
        char line[96], error[64];
        snprintf(line, sizeof line, "%s %s", !strcmp(verb, "health") ? "bars" : "result", arg);
        if (command(f, NULL, line, error, sizeof error))
            return 0;
    }
    else
        return 0;
    if (in.kind)
    {
        mu_submit r = mu_session_submit(s->session, &in);
        if (r.status == MU_SUBMIT_REFUSED)
            return 0;
        ++s->requests;
    }
    mu_party_demo_step(s);
    return 1;
}
