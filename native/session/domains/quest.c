/* Verified reconstructed/quest runs here only. No fixture or demo policy in this domain. */
#include "../session_internal.h"
#ifdef MU_SESSION_SEED
#include "../mu_session_seed.h"
#endif
#include <stdio.h>
#include <math.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>

static void sink(void *user, const char *line)
{
    mu_session *s = user;
    if (!strncmp(line, "send ", 5))
    {
        uint8_t bytes[256];
        size_t n = 0;
        for (const char *p = line + 5; *p && *p != '|' && n < sizeof bytes;)
        {
            char *end;
            unsigned long v = strtoul(p, &end, 16);
            if (p == end)
                break;
            bytes[n++] = (uint8_t)v;
            p = end;
            while (*p == ' ')
                ++p;
        }
        if (n >= 3)
        {
            mu_packet packet;
            mu_packet_begin(&packet, bytes[0], bytes[2]);
            mu_packet_add(&packet, bytes + 3, n - 3, 1);
            const char *flags = strchr(line, '|');
            int encrypted = flags ? (int)strtol(flags + 1, NULL, 10) : 0;
            int rc = mu_session_send(s, &packet, encrypted);
            s->quest.sent++;
            s->quest.send_failed |= rc != MU_SEND_OK;
        }
        return;
    }
    /* A lossless, chunked window cue preserves the existing log grammar, including long JSON.
     * json is one fragment; args[0] says more follows. Views concatenate before replaying it. */
    size_t n = strlen(line), at = 0;
    do
    {
        mu_cue c = {0};
        c.kind = MU_CUE_WINDOW;
        c.handler = s->route.client_handler;
        c.u.window.verb = MU_WINDOW_INVOKE;
        snprintf(c.u.window.movie, sizeof c.u.window.movie, "quest");
        snprintf(c.u.window.method, sizeof c.u.window.method, "log");
        size_t take = n - at;
        if (take >= sizeof c.u.window.json)
            take = sizeof c.u.window.json - 1;
        c.u.window.args[1] = at == 0;
        memcpy(c.u.window.json, line + at, take);
        at += take;
        c.u.window.args[0] = at < n;
        mu_session_cue(s, &c);
    } while (at < n);
}
const mu_quest_client *mu_session_quest(const mu_session *s)
{
    return s && s->quest.ready ? &s->quest.client : NULL;
}
int mu_session_quest_bind(mu_session *s, const char *dir, const mu_quest_host *host)
{
    if (!s)
        return -1;
    if (!s->quest.ready)
    {
        if (!dir)
            dir = getenv("MU_LANG_DIR");
        if (!dir || mu_quest_load_dir(&s->quest.data, dir) <= 0)
        {
            mu_quest_data_free(&s->quest.data);
            return -1;
        }
        if (mu_quest_client_init(&s->quest.client, &s->quest.data, host))
            return -1;
        s->quest.ready = 1;
        s->quest.client.font = s->quest.client.font_default = 1;
        s->quest.client.play_tabs = s->quest.client.play_move = 1;
        mu_quest_enable_hud(&s->quest.client);
    }
    else if (host)
        s->quest.client.host = *host;
    mu_quest_set_sink(&s->quest.client, sink, s);
    return 0;
}
long mu_session_quest_classic(mu_session *s, const char *root)
{
    if (!s || !s->quest.ready)
        return -1;
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/quest.bmd", root ? root : ".");
    FILE *f = fopen(path, "rb");
    if (!f)
    {
        snprintf(path, sizeof path, "%s/Data/Local/Quest.bmd", root ? root : ".");
        f = fopen(path, "rb");
    }
    if (!f)
        return -1;
    uint8_t *buf = malloc(200000);
    size_t n = buf ? fread(buf, 1, 200000, f) : 0;
    fclose(f);
    long count = buf ? mu_classic_load(&s->quest.data, buf, n) : -1;
    free(buf);
    return count;
}
void mu_dom_quest_init(mu_session *s)
{
    (void)mu_session_quest_bind(s, NULL, NULL);
}
void mu_dom_quest_free(mu_session *s)
{
    if (s->quest.ready)
        mu_quest_client_free(&s->quest.client);
    mu_quest_data_free(&s->quest.data);
}
void mu_dom_quest_zones(const mu_session *s, mu_audit_zones *z)
{
    if (!s->quest.ready)
        return;
    const mu_quest_system *q = &s->quest.client.qs;
    mu_audit_add(z, "quest.records", (const uint8_t *)q->quests, 0, (uint32_t)(q->nquests * sizeof *q->quests),
                 MU_ZONE_REPLICATED, "quest records");
    mu_audit_add(z, "quest.system", (const uint8_t *)q, 0, sizeof *q, MU_ZONE_REPLICATED, "active sets and maps");
    for (int i = 0; i < 3; i++)
        mu_audit_add(z, "quest.active", (const uint8_t *)q->active[i], 0,
                     (uint32_t)(q->nactive[i] * sizeof *q->active[i]), MU_ZONE_REPLICATED, "active quest indices");
    mu_audit_add(z, "quest.items", (const uint8_t *)q->items, 0, (uint32_t)(q->nitems * sizeof *q->items),
                 MU_ZONE_REPLICATED, "item map");
    mu_audit_add(z, "quest.values", (const uint8_t *)q->values, 0, (uint32_t)(q->nvalues * sizeof *q->values),
                 MU_ZONE_REPLICATED, "value map");
}
#ifdef MU_SESSION_SEED
void mu_dom_quest_seed(mu_session *s, const struct mu_session_seed *seed)
{
    if (!s->quest.ready)
        return;
    s->quest.client.hero_class = seed->class_byte;
    s->quest.client.hero_level = s->quest.client.hero_level_total = seed->level;
    s->quest.client.world = seed->place.world;
    s->quest.client.hero_x = seed->place.tile[0];
    s->quest.client.hero_y = seed->place.tile[1];
    mu_quest_set_hero(&s->quest.client, seed->name);
}
#endif
void mu_dom_quest_step(mu_session *s, const mu_sim *sim)
{
    (void)sim;
    if (s->quest.ready)
        s->quest.client.time = (float)s->now;
}
mu_apply mu_quest_apply(mu_session *s, const mu_frame *f)
{
    if (f->opcode == 0xf6 && (f->bytes[3] == 0x70 || f->bytes[3] == 0x71))
    {
        ++s->undecodable;
        mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now,
                        "quest body undecoded: F6 70/71 requires 3 bytes at 0x06fca280");
        return MU_APPLY_UNDECODED;
    }
    if (f->head != MU_HEAD_C1 || !s->quest.ready)
    {
        ++s->undecodable;
        mu_journal_text(s->cfg.journal, MU_JNL_EVENT, s->tick, s->now,
                        "quest body not applied: missing static quest tables or unsupported head");
        return MU_APPLY_UNDECODED;
    }
    mu_quest_receive(&s->quest.client, f->bytes, f->length);
    if (f->opcode == 0xa4)
    {
        if (mu_classic_visible(&s->quest.client))
            mu_classic_window_state(&s->quest.client);
        if (s->quest.client.info.visible && s->quest.client.info.tab == 1)
            mu_classic_tab_refresh(&s->quest.client);
    }
    mu_session_touch(s, MU_DOMAIN_QUEST);
    return MU_APPLY_DONE;
}
mu_submit mu_quest_submit(mu_session *s, const mu_intent *in)
{
    mu_submit r = {MU_SUBMIT_SENT, -1};
    if (!s->quest.ready)
    {
        r.status = MU_SUBMIT_NOT_NOW;
        return r;
    }
    mu_quest_client *c = &s->quest.client;
    const char *name = in->u.quest_window.event, *text = in->u.quest_window.text;
    double v[2] = {in->u.quest_window.a, in->u.quest_window.b};
    if (!isfinite(v[0]) || !isfinite(v[1]) || v[0] < INT32_MIN || v[0] > INT32_MAX || v[1] < INT32_MIN ||
        v[1] > INT32_MAX)
    {
        r.status = MU_SUBMIT_REFUSED;
        return r;
    }
    s->quest.sent = s->quest.send_failed = 0;
    switch (in->u.quest_window.action)
    {
    case MU_Q_TOGGLE:
        if (c->info.visible)
            mu_quest_info_close(c);
        else
            mu_quest_info_open(c);
        break;
    case MU_Q_PROGRESS_LOAD:
        mu_quest_progress_onload(c);
        break;
    case MU_Q_INFO_LOAD:
        mu_quest_info_onload(c);
        break;
    case MU_Q_CLASSIC_REFRESH:
        mu_classic_tab_refresh(c);
        break;
    case MU_Q_SUMMARY_LOAD:
        mu_summary_onload(c);
        break;
    case MU_Q_SUMMARY:
        mu_summary_callback(c, name, (int32_t)v[0], (int32_t)v[1]);
        break;
    case MU_Q_NOTICE_LOAD:
        mu_quest_progress_info_onload(c);
        break;
    case MU_Q_CLASSIC_LOAD:
        mu_classic_onload(c);
        break;
    case MU_Q_PROGRESS_CLOSE:
        mu_quest_progress_close(c);
        break;
    case MU_Q_PROGRESS_CALLBACK:
        mu_quest_progress_callback(c, name, v[0], text);
        break;
    case MU_Q_INFO_CALLBACK:
        mu_quest_info_callback(c, name, v, 2, text);
        break;
    case MU_Q_GIVEUP:
        mu_quest_info_giveup_ok(c);
        break;
    case MU_Q_DIALOG_TEXT:
        mu_quest_dialog_set_text(c, text, 0);
        break;
    case MU_Q_PROGRESS_SELECT:
        mu_quest_progress_select(c, (int32_t)v[0]);
        break;
    case MU_Q_INFO_CLOSE:
        mu_quest_info_close(c);
        break;
    case MU_Q_CONFIRM:
        mu_quest_progress_confirm(c);
        break;
    case MU_Q_GUIDE_GO:
        mu_guide_go(c);
        break;
    case MU_Q_MOVE:
        mu_quest_move(c, (int32_t)v[0]);
        break;
    case MU_Q_CLASSIC_CALLBACK:
        mu_classic_callback(c, name, (int32_t)v[0]);
        break;
    case MU_Q_CLASSIC_COMPLETE:
        mu_classic_complete(c);
        break;
    case MU_Q_GUIDE_BOX:
        mu_guide_box(c, (int32_t)v[0], (int32_t)v[1]);
        break;
    case MU_Q_DIALOG_CHOICE:
        mu_quest_dialog_choice(c, (int32_t)v[0], NULL);
        break;
    case MU_Q_SUMMARY_REFRESH:
        mu_summary_guide_refresh(c);
        break;
    case MU_Q_DIALOG_VISIBLE:
        c->dialog.visible = (int32_t)v[0];
        break;
    case MU_Q_CLASSIC_KEY:
        mu_classic_key(c, (int32_t)v[0]);
        break;
    case MU_Q_TARGET:
        c->target_class = (int32_t)v[0];
        break;
    case MU_Q_DIALOG_RESET:
        c->dialog.list_mode = 0;
        break;
    case MU_Q_HERO_NAME:
        mu_quest_set_hero(c, text);
        break;
    case MU_Q_NPC_LIST:
    {
        uint8_t bytes[3] = {0x71, (uint8_t)(int32_t)v[0], (uint8_t)((int32_t)v[0] >> 8)};
        mu_packet p;
        mu_packet_begin(&p, MU_HEAD_C1, 0xf6);
        mu_packet_add(&p, bytes, sizeof bytes, 1);
        s->quest.send_failed = mu_session_send(s, &p, 0) != MU_SEND_OK;
        break;
    }
    default:
        r.status = MU_SUBMIT_REFUSED;
        return r;
    }
    if (s->quest.send_failed)
        r.status = MU_SUBMIT_NOT_NOW;
    mu_session_touch(s, MU_DOMAIN_QUEST);
    return r;
}
int mu_session_quest_window(mu_session *s, mu_quest_action action, const char *event, const char *text, double a,
                            double b)
{
    mu_intent in = {.kind = MU_INTENT_QUEST_WINDOW};
    in.u.quest_window.action = (int32_t)action;
    in.u.quest_window.a = a;
    in.u.quest_window.b = b;
    snprintf(in.u.quest_window.event, sizeof in.u.quest_window.event, "%s", event ? event : "");
    snprintf(in.u.quest_window.text, sizeof in.u.quest_window.text, "%s", text ? text : "");
    return mu_session_submit(s, &in).status == MU_SUBMIT_SENT;
}

mu_submit mu_quest_context_submit(mu_session *s, const mu_intent *in)
{
    mu_submit r = {MU_SUBMIT_NOT_NOW, -1};
    if (!s->quest.ready)
        return r;
    mu_quest_client *c = &s->quest.client;
    c->world = in->u.quest_context.world;
    c->hero_x = in->u.quest_context.x;
    c->hero_y = in->u.quest_context.y;
    c->hero_level = in->u.quest_context.level;
    c->hero_level_total = in->u.quest_context.total;
    c->money = in->u.quest_context.money;
    c->hero_class = in->u.quest_context.class_byte;
    c->hero_safe = in->u.quest_context.safe;
    c->holding_item = in->u.quest_context.holding;
    r.status = MU_SUBMIT_SENT;
    return r;
}

void mu_session_quest_services(mu_session *s, void (*move)(void *, uint8_t), const char *(*word)(void *, int32_t))
{
    if (!s || !s->quest.ready)
        return;
    mu_quest_set_move_answer(&s->quest.client, move);
    mu_quest_set_dialogue_words(&s->quest.client, word);
}
