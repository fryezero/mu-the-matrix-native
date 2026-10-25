/* native/tools/mu_session.c: the session's CLI, for validators, tests and humans (SESSION-CORE-001,
 * FIXTURE-001).
 *
 *   mu-session routes                          the dispatcher rows and intent routes (JSON lines)
 *   mu-session behaviors                       the fixture behaviours compiled in
 *   mu-session fixture SCENARIO [options]      a headless seeded session against the in-process fixture:
 *                                              JSON rows for every journal record, the hero, the cues, the
 *                                              journal summary and the scenario's expectations
 *       --seed N        the fixture's rng seed (default 1)
 *       --ticks N       steps to run (default: 20 past the scenario's last tick)
 *       --journal FILE  keep the journal there (default: a temporary file, removed afterwards)
 *       --quiet         no per-record rows
 *   mu-session connect SCENARIO --to HOST:PORT [options]
 *                                              the same over the product sockets transport (client lock
 *                                              included) to `mu-session serve` in another process;
 *                                              HOST must be a loopback address
 *   mu-session serve SCENARIO --port N [--seconds S] [--seed N] [--step-ms MS]
 *                                              the fixture on 127.0.0.1:N for one client
 *   mu-session journal FILE                    a journal's records as JSON lines
 *   mu-session replay JOURNAL                  the replay transport (not implemented yet: says so, exit 2)
 *
 * No subcommand connects to a non-loopback endpoint; live runs go through mu-client only.
 * Built with MU_SESSION_SEED (seeded sessions) and MU_SESSION_AUDIT (the lease audit aborts).
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "../session/mu_session.h"
#include "../session/mu_session_seed.h"
#include "../session/mu_session_tools.h"
#include "../session/mu_journal.h"
#include "../fixture/mu_fixture.h"

#define BASE_MS 100000u   /* GetTickCount of a running session: the stat request throttle compares with 0 at first */
#define STEP_MS 40u

static int quiet;

/* ---- JSON helpers ----------------------------------------------------------------------------- */

static void json_str(FILE *o, const char *s)
{
    fputc('"', o);
    for (const unsigned char *p = (const unsigned char *)s; p && *p; ++p) {
        if (*p == '"' || *p == '\\')
            fprintf(o, "\\%c", *p);
        else if (*p < 0x20 || *p >= 0x7f)
            fprintf(o, "\\u%04x", *p);
        else
            fputc(*p, o);
    }
    fputc('"', o);
}

static void json_hex(FILE *o, const uint8_t *p, size_t n)
{
    fputc('"', o);
    for (size_t i = 0; i < n; ++i)
        fprintf(o, "%s%02x", i ? " " : "", p[i]);
    fputc('"', o);
}

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

/* ---- routes ------------------------------------------------------------------------------------- */

static int cmd_routes(void)
{
    const mu_dispatch_row *rows;
    size_t n = mu_session_dispatch_rows(&rows);
    for (size_t i = 0; i < n; ++i) {
        printf("{\"route\": {\"opcode\": %u, \"sub\": %s", (unsigned)rows[i].opcode,
               rows[i].sub == 0x100u ? "null" : "");
        if (rows[i].sub != 0x100u)
            printf("%u", (unsigned)rows[i].sub);
        printf(", \"client_handler\": %u, \"apply\": ", (unsigned)rows[i].client_handler);
        if (rows[i].apply)
            json_str(stdout, rows[i].apply);
        else
            printf("null");
        printf("}}\n");
    }
    const char *const *names;
    size_t kinds = mu_session_intent_routes(&names);
    for (size_t k = 1; k < kinds; ++k) {
        printf("{\"intent\": {\"kind\": %zu, \"name\": ", k);
        json_str(stdout, mu_intent_kind_name((mu_intent_kind)k));
        printf(", \"submit\": ");
        if (names[k])
            json_str(stdout, names[k]);
        else
            printf("null");
        printf("}}\n");
    }
    return 0;
}

static int cmd_behaviors(void)
{
    const char *const *names;
    size_t n = mu_fixture_behavior_names(&names);
    for (size_t i = 0; i < n; ++i) {
        printf("{\"behavior\": ");
        json_str(stdout, names[i]);
        printf("}\n");
    }
    return 0;
}

/* ---- journal dump --------------------------------------------------------------------------------- */

static const char *apply_name(int r)
{
    return r == 0 ? "done" : r == 1 ? "ignored" : r == 2 ? "world_change" : "?";
}

static const char *decode_name(int d)
{
    static const char *const N[] = {"ok", "serial", "crypto", "bad", "overflow"};
    return d >= 0 && d < 5 ? N[d] : "?";
}

static const char *send_name(int s)
{
    return s == 0 ? "ok" : s == -1 ? "not_open" : s == -2 ? "needs_crypto" : s == -3 ? "overflow" : "?";
}

static void print_record(const mu_journal_record *r)
{
    const uint8_t *p = r->payload;
    static const char *const CONN[] = {"connect", "game", "chat"};
    const char *conn = r->conn < 3 ? CONN[r->conn] : "?";
    switch (r->type) {
    case MU_JNL_OPEN:
    case MU_JNL_EVENT:
        printf("{\"jnl\": \"%s\", \"tick\": %u, \"text\": ", r->type == MU_JNL_OPEN ? "open" : "event", (unsigned)r->tick);
        {
            char text[512];
            size_t n = r->length < sizeof text - 1 ? r->length : sizeof text - 1;
            memcpy(text, p, n);
            text[n] = 0;
            json_str(stdout, text);
        }
        printf("}\n");
        break;
    case MU_JNL_FRAME:
        if (r->direction == MU_JNL_IN && r->length >= 48) {
            uint16_t sub = (uint16_t)(p[2] | p[3] << 8);
            char apply[33];
            memcpy(apply, p + 12, 32);
            apply[32] = 0;
            printf("{\"jnl\": \"frame_in\", \"tick\": %u, \"conn\": \"%s\", \"head\": %u, \"opcode\": %u, \"sub\": ",
                   (unsigned)r->tick, conn, p[0], p[1]);
            if (sub == 0x100u)
                printf("null");
            else
                printf("%u", sub);
            printf(", \"encrypted\": %u, \"decode\": \"%s\", \"result\": \"%s\", \"client_handler\": %u, \"apply\": ",
                   p[4], decode_name(p[5]), apply_name(p[6]), (unsigned)rd32(p + 8));
            if (apply[0])
                json_str(stdout, apply);
            else
                printf("null");
            printf(", \"cues\": %u, \"bytes\": ", (unsigned)rd32(p + 44));
            json_hex(stdout, p + 48, r->length - 48);
            printf("}\n");
        } else if (r->direction == MU_JNL_OUT && r->length >= 4) {
            printf("{\"jnl\": \"frame_out\", \"tick\": %u, \"conn\": \"%s\", \"send\": \"%s\", \"encrypted\": %u, "
                   "\"bytes\": ",
                   (unsigned)r->tick, conn, send_name((int8_t)p[0]), p[1]);
            json_hex(stdout, p + 4, r->length - 4);
            printf("}\n");
        }
        break;
    case MU_JNL_INTENT:
        if (r->length >= 12) {
            printf("{\"jnl\": \"intent\", \"tick\": %u, \"kind\": ", (unsigned)r->tick);
            json_str(stdout, mu_intent_kind_name((mu_intent_kind)rd32(p)));
            printf(", \"status\": \"%s\"}\n", mu_submit_status_name((mu_submit_status)rd32(p + 4)));
        }
        break;
    case MU_JNL_SNAPSHOT: {
        printf("{\"jnl\": \"snapshot\", \"tick\": %u, \"zones\": [", (unsigned)r->tick);
        size_t at = 0;
        int first = 1;
        while (at + 40 <= r->length) {
            char name[33];
            memcpy(name, p + at, 32);
            name[32] = 0;
            uint32_t off = rd32(p + at + 32), size = rd32(p + at + 36);
            printf("%s{\"name\": ", first ? "" : ", ");
            json_str(stdout, name);
            printf(", \"offset\": %u, \"size\": %u}", (unsigned)off, (unsigned)size);
            first = 0;
            at += 40u + size;
        }
        printf("]}\n");
        break;
    }
    default:
        break;
    }
}

static int dump_journal(const char *path)
{
    char err[256];
    mu_journal_reader *r = mu_journal_open(path, NULL, err, sizeof err);
    if (!r) {
        fprintf(stderr, "mu-session: %s\n", err);
        return 1;
    }
    mu_journal_record rec;
    int rc;
    while ((rc = mu_journal_read(r, &rec)) == 1)
        print_record(&rec);
    mu_journal_reader_close(r);
    if (rc < 0) {
        fprintf(stderr, "mu-session: %s: truncated record\n", path);
        return 1;
    }
    return 0;
}

/* ---- the stub world (a world tool's port, without a world) ------------------------------------------ */

typedef struct stub_world {
    int32_t world;
    int32_t tile[2];
    uint32_t placements;
} stub_world;

static void stub_motion(void *context, int32_t tile[2], float position[3], float angle[3])
{
    stub_world *w = context;
    tile[0] = w->tile[0];
    tile[1] = w->tile[1];
    position[0] = (float)w->tile[0] * 100.0f + 50.0f;   /* the tile's centre (TERRAIN_SCALE 100) */
    position[1] = (float)w->tile[1] * 100.0f + 50.0f;
    position[2] = 0.0f;
    angle[0] = angle[1] = angle[2] = 0.0f;
}

static void stub_place(void *context, const mu_place *place)
{
    stub_world *w = context;
    w->tile[0] = place->tile[0];
    w->tile[1] = place->tile[1];
    w->placements++;
}

static mu_world_port stub_port(stub_world *w)
{
    mu_world_port p;
    memset(&p, 0, sizeof p);
    p.context = w;
    p.world = w->world;
    p.hero_motion = stub_motion;
    p.place_hero = stub_place;
    return p;
}

/* ---- a headless run ------------------------------------------------------------------------------- */

typedef struct run {
    mu_session *session;
    mu_transport *transport;
    mu_fixture *fixture;
    mu_journal *journal;
    stub_world world;
    mu_cue_cursor cursor, late;
    uint32_t cue_kinds[16];
    uint32_t lost, late_lost, late_read;
    int failed_actions;
} run;

static int seed_from_join(const char *text, mu_session_seed *seed)
{
    memset(seed, 0, sizeof *seed);
    seed->place.world = mu_fx_arg_int(text, "world", 0);
    char tile[32] = "0,0";
    mu_fx_arg_str(text, "tile", tile, sizeof tile);
    if (sscanf(tile, "%d,%d", &seed->place.tile[0], &seed->place.tile[1]) != 2)
        return -1;
    seed->place.angle = (float)mu_fx_arg_int(text, "angle", 0);
    seed->class_byte = (uint8_t)mu_fx_arg_int(text, "class", 0x01);
    seed->level = mu_fx_arg_int(text, "level", 1);
    seed->slot = mu_fx_arg_int(text, "slot", 0);
    mu_fx_arg_str(text, "name", seed->name, sizeof seed->name);
    return 0;
}

static void drain_cues(run *r)
{
    mu_cue cues[64];
    size_t n;
    uint32_t lost;
    while ((n = mu_session_cues(r->session, &r->cursor, cues, 64, &lost)) > 0 || lost) {
        r->lost += lost;
        for (size_t i = 0; i < n; ++i)
            if ((unsigned)cues[i].kind < 16)
                r->cue_kinds[cues[i].kind]++;
        if (!n)
            break;
    }
}

static void row_action(uint32_t tick, const char *what, const char *status)
{
    if (quiet)
        return;
    printf("{\"client\": ");
    json_str(stdout, what);
    printf(", \"tick\": %u, \"status\": ", (unsigned)tick);
    json_str(stdout, status);
    printf("}\n");
}

static void client_action(run *r, const mu_scenario_line *line)
{
    char verb[16] = {0};
    int used = 0;
    sscanf(line->text, "%15s%n", verb, &used);
    const char *rest = line->text + used;
    while (*rest == ' ')
        ++rest;
    if (!strcmp(verb, "submit")) {
        char kind[32] = {0};
        long a = 0;
        int n = sscanf(rest, "%31s %li", kind, &a);
        mu_intent in;
        memset(&in, 0, sizeof in);
        in.kind = mu_intent_kind_by_name(kind);
        if (n < 1 || in.kind == MU_INTENT_NONE) {
            row_action(line->tick, line->text, "unknown intent");
            r->failed_actions++;
            return;
        }
        /* every hero intent payload starts with one int32 */
        memcpy(&in.u, &(int32_t){(int32_t)a}, sizeof(int32_t));
        mu_submit s = mu_session_submit(r->session, &in);
        row_action(line->tick, line->text, mu_submit_status_name(s.status));
    } else if (!strcmp(verb, "attach")) {
        r->world.world = (int32_t)strtol(rest, NULL, 0);
        mu_place pl = mu_session_place(r->session);
        r->world.tile[0] = pl.tile[0];
        r->world.tile[1] = pl.tile[1];
        mu_world_port port = stub_port(&r->world);
        mu_session_attach_world(r->session, &port);
        row_action(line->tick, line->text, "attached");
    } else if (!strcmp(verb, "detach")) {
        mu_session_detach_world(r->session);
        row_action(line->tick, line->text, "detached");
    } else if (!strcmp(verb, "lease")) {
        /* lease [write OFFSET VALUE]: one logic step; a write outside the motion zone is the planted bug */
        mu_sim sim = mu_session_sim_begin(r->session);
        int off = 0, value = 0;
        if (sscanf(rest, "write %i %i", &off, &value) == 2 && sim.hero_record && off >= 0 && off < 0x400)
            sim.hero_record[off] = (uint8_t)value;
        for (int d = 0; d < MU_DOMAIN_COUNT; ++d)
            mu_session_step(r->session, (mu_domain)d, &sim);
        mu_session_sim_end(r->session, &sim);
        row_action(line->tick, line->text, "lease ended");
    } else if (!strcmp(verb, "cues")) {
        /* the late reader: a cursor opened at the start and read only here */
        mu_cue cues[64];
        uint32_t lost;
        size_t n, total = 0;
        while ((n = mu_session_cues(r->session, &r->late, cues, 64, &lost)) > 0 || lost) {
            r->late_lost += lost;
            total += n;
            if (!n)
                break;
        }
        r->late_read += (uint32_t)total;
        if (!quiet)
            printf("{\"client\": \"cues\", \"tick\": %u, \"read\": %zu, \"lost\": %u}\n", (unsigned)line->tick, total,
                   (unsigned)r->late_lost);
    } else {
        row_action(line->tick, line->text, "unknown client verb");
        r->failed_actions++;
    }
}

static int64_t value_of(run *r, const char *key, int *ok)
{
    mu_hero_stats h;
    mu_session_hero(r->session, &h);
    mu_session_status st;
    mu_session_status_get(r->session, &st);
    mu_journal_summary js;
    mu_journal_summary_get(r->journal, &js);
    mu_fixture_report fr;
    mu_fixture_report_get(r->fixture, &fr);
    mu_place pl = mu_session_place(r->session);
    *ok = 1;
    struct {
        const char *k;
        int64_t v;
    } T[] = {
        {"hero.level", h.level}, {"hero.points", h.points}, {"hero.exp", h.exp}, {"hero.next_exp", h.next_exp},
        {"hero.max_hp", h.max_hp}, {"hero.max_mp", h.max_mp}, {"hero.max_sd", h.max_sd}, {"hero.max_ag", h.max_ag},
        {"hero.hp", h.hp}, {"hero.mp", h.mp}, {"hero.master_level", h.master_level},
        {"hero.strength", h.stats[0]}, {"hero.agility", h.stats[1]}, {"hero.vitality", h.stats[2]},
        {"hero.energy", h.stats[3]}, {"hero.command", h.stats[4]}, {"hero.attack_speed", h.attack_speed},
        {"hero.magic_speed", h.magic_speed}, {"hero.class", h.class_byte}, {"hero.derived", h.has_derived},
        {"hero.rev", mu_session_rev(r->session, MU_DOMAIN_HERO)}, {"money", mu_session_money(r->session)},
        {"place.world", pl.world}, {"place.x", pl.tile[0]}, {"place.y", pl.tile[1]}, {"place.seq", pl.seq},
        {"waiting", st.waiting_for_world}, {"phase", st.phase}, {"reason", st.reason},
        {"frames_in", (int64_t)js.frames_in}, {"frames_out", (int64_t)js.frames_out},
        {"unbound", (int64_t)js.unbound_frames}, {"undecodable", (int64_t)js.undecodable_frames},
        {"unsent", (int64_t)js.unsent_frames}, {"intents", (int64_t)js.intents},
        {"unrecovered", (int64_t)js.unrecovered_intents}, {"cues", (int64_t)js.cues},
        {"cues.lost", r->late_lost}, {"cues.level_up", r->cue_kinds[MU_CUE_LEVEL_UP]},
        {"cues.effect", r->cue_kinds[MU_CUE_EFFECT]}, {"cues.sound", r->cue_kinds[MU_CUE_SOUND]},
        {"fixture.requests", (int64_t)fr.requests}, {"fixture.answers", (int64_t)fr.answers},
        {"fixture.undecodable", (int64_t)fr.undecodable_requests}, {"stub.placements", r->world.placements},
    };
    for (size_t i = 0; i < sizeof T / sizeof T[0]; ++i)
        if (!strcmp(T[i].k, key))
            return T[i].v;
    *ok = 0;
    return 0;
}

static int check_expect(run *r, const mu_scenario_line *e)
{
    char key[64] = {0}, op[4] = {0}, val[64] = {0};
    if (sscanf(e->text, "%63[^ =!<>] %3[=!<>] %63s", key, op, val) != 3 &&
        sscanf(e->text, "%63[^ =!<>]%3[=!<>]%63s", key, op, val) != 3)
        return -1;
    int ok;
    int64_t have = value_of(r, key, &ok);
    if (!ok)
        return -1;
    int64_t want;
    if (!strcmp(key, "phase") && (val[0] < '0' || val[0] > '9')) {
        want = -1;
        for (int p = 0; p <= MU_PHASE_CLOSED; ++p)
            if (!strcmp(mu_phase_name((mu_phase)p), val))
                want = p;
    } else if (!strcmp(key, "reason") && (val[0] < '0' || val[0] > '9')) {
        want = -1;
        for (int p = 0; p <= MU_CLOSE_NEEDS_OPERATOR_CONTRACT; ++p)
            if (!strcmp(mu_close_reason_name((mu_close_reason)p), val))
                want = p;
    } else {
        want = strtoll(val, NULL, 0);
    }
    int pass = !strcmp(op, "=") ? have == want : !strcmp(op, "!=") ? have != want : !strcmp(op, "<") ? have < want
             : !strcmp(op, "<=") ? have <= want : !strcmp(op, ">") ? have > want : !strcmp(op, ">=") ? have >= want : -1;
    printf("{\"expect\": ");
    json_str(stdout, e->text);
    printf(", \"line\": %d, \"value\": %lld, \"pass\": %s}\n", e->number, (long long)have, pass == 1 ? "true" : "false");
    return pass == 1 ? 0 : 1;
}

static void print_hero(run *r)
{
    mu_hero_stats h;
    mu_session_hero(r->session, &h);
    printf("{\"hero\": {\"name\": ");
    json_str(stdout, h.name);
    printf(", \"class\": %u, \"level\": %d, \"points\": %d, \"exp\": %lld, \"next_exp\": %lld, \"master_level\": %d, "
           "\"hp\": [%d, %d], \"mp\": [%d, %d], \"sd\": [%d, %d], \"ag\": [%d, %d], "
           "\"stats\": [%d, %d, %d, %d, %d], \"speed\": [%d, %d], \"derived\": %d, \"damage\": [%d, %d], "
           "\"defense\": %d, \"money\": %lld, \"rev\": %u, \"exp_bar\": ",
           h.class_byte, h.level, h.points, (long long)h.exp, (long long)h.next_exp, h.master_level, h.hp, h.max_hp,
           h.mp, h.max_mp, h.sd, h.max_sd, h.ag, h.max_ag, h.stats[0], h.stats[1], h.stats[2], h.stats[3], h.stats[4],
           h.attack_speed, h.magic_speed, h.has_derived, h.dmg_min, h.dmg_max, h.defense,
           (long long)mu_session_money(r->session), (unsigned)mu_session_rev(r->session, MU_DOMAIN_HERO));
    json_str(stdout, mu_session_hero_exp_bar(r->session));
    printf(", \"speed_text\": ");
    json_str(stdout, mu_session_hero_speed_text(r->session));
    printf("}}\n");
}

static int run_session(const char *scenario, const char *to, uint32_t seed, uint32_t ticks, const char *journal_path)
{
    run r;
    memset(&r, 0, sizeof r);
    char err[512];
    mu_fixture_options fo = {scenario, NULL, seed};
    r.fixture = mu_fixture_open(&fo, err, sizeof err);
    if (!r.fixture) {
        fprintf(stderr, "mu-session: %s\n", err);
        return 2;
    }
    mu_fixture_script script;
    mu_fixture_script_get(r.fixture, &script);
    if (!script.join) {
        fprintf(stderr, "mu-session: %s has no join line\n", scenario);
        mu_fixture_close(r.fixture);
        return 2;
    }
    mu_session_seed sd;
    if (seed_from_join(script.join->text, &sd) != 0) {
        fprintf(stderr, "mu-session: bad join line: %s\n", script.join->text);
        mu_fixture_close(r.fixture);
        return 2;
    }
    mu_endpoint game;
    if (to) {
        if (mu_endpoint_parse(&game, to) != 0 || !mu_endpoint_is_loopback(&game)) {
            fprintf(stderr, "mu-session: --to must be a loopback HOST:PORT\n");
            mu_fixture_close(r.fixture);
            return 2;
        }
        mu_transport_status ts;
        r.transport = mu_transport_sockets(&game, 1, &ts, err, sizeof err);
        if (!r.transport) {
            printf("{\"transport\": \"%s\", \"error\": ", ts == MU_TRANSPORT_LOCKED ? "locked" : "error");
            json_str(stdout, err);
            printf("}\n");
            mu_fixture_close(r.fixture);
            return ts == MU_TRANSPORT_LOCKED ? 3 : 2;
        }
    } else {
        if (mu_fixture_endpoint(r.fixture, "game", &game) != 0) {
            fprintf(stderr, "mu-session: %s declares no game endpoint\n", scenario);
            mu_fixture_close(r.fixture);
            return 2;
        }
        r.transport = mu_fixture_transport(r.fixture);
    }
    char tmp[512] = {0};
    if (!journal_path) {
        const char *dir = getenv("TMPDIR");
        snprintf(tmp, sizeof tmp, "%s/mu-session-XXXXXX", dir && *dir ? dir : "/tmp");
        int fd = mkstemp(tmp);
        if (fd < 0) {
            fprintf(stderr, "mu-session: mkstemp: %s\n", strerror(errno));
            return 2;
        }
        close(fd);
        journal_path = tmp;
    }
    uint32_t snaps[1] = {ticks};
    mu_journal_options jo = {journal_path, snaps, 1, 0};
    r.journal = mu_journal_create(&jo, err, sizeof err);
    if (!r.journal) {
        fprintf(stderr, "mu-session: %s\n", err);
        return 2;
    }
    mu_session_config cfg;
    memset(&cfg, 0, sizeof cfg);
    cfg.connect_server = game;
    cfg.transport = r.transport;
    cfg.build = &MU_PINNED_BUILD;
    cfg.proof = mu_proof_not_required();
    cfg.journal = r.journal;
    r.session = mu_session_open_seeded(&cfg, &sd, err, sizeof err);
    if (!r.session) {
        fprintf(stderr, "mu-session: %s\n", err);
        return 2;
    }
    r.cursor = mu_session_cue_cursor(r.session);
    r.late = r.cursor;
    r.world.world = sd.place.world;
    r.world.tile[0] = sd.place.tile[0];
    r.world.tile[1] = sd.place.tile[1];
    mu_world_port port = stub_port(&r.world);
    mu_session_attach_world(r.session, &port);   /* a world tool has its world loaded */

    for (uint32_t tick = 1; tick <= ticks; ++tick) {
        uint32_t now = BASE_MS + tick * STEP_MS;
        mu_transport_poll(r.transport, now);
        mu_session_pump(r.session, now);
        drain_cues(&r);
        for (size_t i = 0; i < script.nclient; ++i)
            if (script.client[i].tick == tick)
                client_action(&r, &script.client[i]);
        drain_cues(&r);
        mu_transport_flush(r.transport);
        if (to)
            usleep(STEP_MS * 1000u);   /* a TCP peer runs on its own clock */
    }

    mu_session_status st;
    mu_session_status_get(r.session, &st);
    mu_place pl = mu_session_place(r.session);
    print_hero(&r);
    printf("{\"status\": {\"phase\": \"%s\", \"reason\": \"%s\", \"code\": %d, \"protocol_state\": %d, "
           "\"waiting_for_world\": %d, \"frames_in\": %u, \"frames_out\": %u, \"unhandled\": %u, \"undecodable\": %u, "
           "\"unsent\": %u, \"place\": [%d, %d, %d, %u]}}\n",
           mu_phase_name(st.phase), mu_close_reason_name(st.reason), (int)st.code, (int)st.protocol_state,
           (int)st.waiting_for_world, (unsigned)st.frames_in, (unsigned)st.frames_out, (unsigned)st.unhandled,
           (unsigned)st.undecodable, (unsigned)st.unsent, (int)pl.world, (int)pl.tile[0], (int)pl.tile[1],
           (unsigned)pl.seq);
    printf("{\"cues\": {\"sound\": %u, \"effect\": %u, \"damage\": %u, \"chat\": %u, \"window\": %u, \"level_up\": %u, "
           "\"unhandled\": %u, \"call\": %u, \"lost_main\": %u, \"late_read\": %u, \"late_lost\": %u}}\n",
           r.cue_kinds[MU_CUE_SOUND], r.cue_kinds[MU_CUE_EFFECT], r.cue_kinds[MU_CUE_DAMAGE], r.cue_kinds[MU_CUE_CHAT],
           r.cue_kinds[MU_CUE_WINDOW], r.cue_kinds[MU_CUE_LEVEL_UP], r.cue_kinds[MU_CUE_UNHANDLED],
           r.cue_kinds[MU_CUE_CALL], r.lost, r.late_read, r.late_lost);
    mu_fixture_report fr;
    mu_fixture_report_get(r.fixture, &fr);
    printf("{\"fixture\": {\"requests\": %llu, \"answers\": %llu, \"undecodable_requests\": %llu, "
           "\"refused_connects\": %llu, \"behaviors\": %u, \"steps\": %u, \"last_error\": ",
           (unsigned long long)fr.requests, (unsigned long long)fr.answers,
           (unsigned long long)fr.undecodable_requests, (unsigned long long)fr.refused_connects, fr.behaviors,
           fr.steps);
    json_str(stdout, fr.last_error);
    printf("}}\n");
    mu_transport_counters tc;
    mu_transport_counters_get(r.transport, &tc);
    printf("{\"transport\": {\"kind\": \"%s\", \"bytes_in\": %llu, \"bytes_out\": %llu, \"links_opened\": %u, "
           "\"links_refused\": %u, \"connects_attempted\": %u}}\n",
           to ? "sockets" : "fixture", (unsigned long long)tc.bytes_in, (unsigned long long)tc.bytes_out,
           tc.links_opened, tc.links_refused, tc.connects_attempted);

    int failures = r.failed_actions;
    for (size_t i = 0; i < script.nexpect; ++i) {
        int rc = check_expect(&r, &script.expect[i]);
        if (rc < 0) {
            printf("{\"expect\": ");
            json_str(stdout, script.expect[i].text);
            printf(", \"line\": %d, \"error\": \"unknown key or malformed\"}\n", script.expect[i].number);
        }
        failures += rc != 0;
    }

    mu_session_close(r.session);
    mu_journal_summary js;
    mu_journal_summary_get(r.journal, &js);
    mu_journal_close(r.journal);
    mu_transport_free(r.transport);
    mu_fixture_close(r.fixture);
    if (!quiet)
        dump_journal(journal_path);
    printf("{\"summary\": {\"frames_in\": %llu, \"frames_out\": %llu, \"intents\": %llu, \"unrecovered_intents\": %llu, "
           "\"unbound_frames\": %llu, \"undecodable_frames\": %llu, \"unsent_frames\": %llu, \"cues\": %llu, "
           "\"inputs\": %llu, \"snapshots\": %llu, \"ticks\": %u}}\n",
           (unsigned long long)js.frames_in, (unsigned long long)js.frames_out, (unsigned long long)js.intents,
           (unsigned long long)js.unrecovered_intents, (unsigned long long)js.unbound_frames,
           (unsigned long long)js.undecodable_frames, (unsigned long long)js.unsent_frames, (unsigned long long)js.cues,
           (unsigned long long)js.inputs, (unsigned long long)js.snapshots, js.ticks);
    if (tmp[0])
        unlink(tmp);
    return failures ? 1 : 0;
}

static uint32_t last_tick(const char *scenario, uint32_t seed)
{
    char err[256];
    mu_fixture_options fo = {scenario, NULL, seed};
    mu_fixture *f = mu_fixture_open(&fo, err, sizeof err);
    if (!f)
        return 0;
    mu_fixture_script s;
    mu_fixture_script_get(f, &s);
    uint32_t last = 0;
    for (size_t i = 0; i < s.nclient; ++i)
        if (s.client[i].tick > last)
            last = s.client[i].tick;
    mu_fixture_close(f);
    /* fixture-side lines are not exposed; scenarios end with a client line or use --ticks */
    return last;
}

static int usage(void)
{
    fprintf(stderr, "usage: mu-session routes | behaviors | journal FILE | replay JOURNAL\n"
                    "       mu-session fixture SCENARIO [--seed N] [--ticks N] [--journal FILE] [--quiet]\n"
                    "       mu-session connect SCENARIO --to HOST:PORT [--seed N] [--ticks N] [--journal FILE] [--quiet]\n"
                    "       mu-session serve SCENARIO --port N [--seconds S] [--seed N] [--step-ms MS]\n");
    return 2;
}

int main(int argc, char **argv)
{
    if (argc < 2)
        return usage();
    const char *cmd = argv[1];
    if (!strcmp(cmd, "routes"))
        return cmd_routes();
    if (!strcmp(cmd, "behaviors"))
        return cmd_behaviors();
    if (!strcmp(cmd, "journal"))
        return argc == 3 ? dump_journal(argv[2]) : usage();
    if (!strcmp(cmd, "replay")) {
        char err[256];
        mu_transport *t = mu_transport_replay(argc > 2 ? argv[2] : NULL, MU_REPLAY_STRICT, err, sizeof err);
        if (!t) {
            printf("{\"replay\": \"unavailable\", \"error\": ");
            json_str(stdout, err);
            printf("}\n");
            return 2;
        }
        mu_transport_free(t);
        return 0;
    }
    if (strcmp(cmd, "fixture") && strcmp(cmd, "connect") && strcmp(cmd, "serve"))
        return usage();
    if (argc < 3)
        return usage();
    const char *scenario = argv[2], *journal = NULL, *to = NULL;
    uint32_t seed = 1, ticks = 0, seconds = 30, step_ms = STEP_MS;
    long port = 0;
    for (int i = 3; i < argc; ++i) {
        if (!strcmp(argv[i], "--seed") && i + 1 < argc)
            seed = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--ticks") && i + 1 < argc)
            ticks = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--journal") && i + 1 < argc)
            journal = argv[++i];
        else if (!strcmp(argv[i], "--to") && i + 1 < argc)
            to = argv[++i];
        else if (!strcmp(argv[i], "--port") && i + 1 < argc)
            port = strtol(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--seconds") && i + 1 < argc)
            seconds = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--step-ms") && i + 1 < argc)
            step_ms = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--quiet"))
            quiet = 1;
        else
            return usage();
    }
    if (!strcmp(cmd, "serve")) {
        if (port <= 0 || port > 65535)
            return usage();
        char err[256];
        mu_fixture_options fo = {scenario, NULL, seed};
        mu_fixture *f = mu_fixture_open(&fo, err, sizeof err);
        if (!f) {
            fprintf(stderr, "mu-session: %s\n", err);
            return 2;
        }
        int rc = mu_fixture_serve(f, "127.0.0.1", (uint16_t)port, seconds, step_ms);
        mu_fixture_report fr;
        mu_fixture_report_get(f, &fr);
        printf("{\"fixture\": {\"requests\": %llu, \"answers\": %llu, \"undecodable_requests\": %llu, \"steps\": %u, "
               "\"last_error\": ",
               (unsigned long long)fr.requests, (unsigned long long)fr.answers,
               (unsigned long long)fr.undecodable_requests, fr.steps);
        json_str(stdout, fr.last_error);
        printf("}}\n");
        mu_fixture_close(f);
        return rc == 0 ? 0 : 1;
    }
    if (!ticks)
        ticks = last_tick(scenario, seed) + 20u;
    if (!strcmp(cmd, "connect") && !to)
        return usage();
    return run_session(scenario, !strcmp(cmd, "connect") ? to : NULL, seed, ticks, journal);
}
