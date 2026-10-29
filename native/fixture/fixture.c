/* FIXTURE-001: the fixture server core - scenario, server-side connections, the loopback transport,
 * the TCP listener and the behaviour services. See mu_fixture.h. */
#define _DARWIN_C_SOURCE 1
#define _DEFAULT_SOURCE 1
#include "mu_fixture.h"
#include "behavior.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

/* the generated behaviour list */
#define MU_FX_BEHAVIOR(sym) extern const mu_fixture_behavior mu_fx_##sym;
#include "fixture_behaviors.def"
#undef MU_FX_BEHAVIOR
static const mu_fixture_behavior *const BEHAVIORS[] = {
#define MU_FX_BEHAVIOR(sym) &mu_fx_##sym,
#include "fixture_behaviors.def"
#undef MU_FX_BEHAVIOR
    NULL};
static const char *const BEHAVIOR_NAMES[] = {
#define MU_FX_BEHAVIOR(sym) #sym,
#include "fixture_behaviors.def"
#undef MU_FX_BEHAVIOR
    NULL};

#define MAX_USES 8
#define MAX_LINES 512
#define TO_CLIENT_CAP (256u * 1024u)

typedef struct fx_link {
    int used;
    mu_conn_kind role;
    mu_link_state state;
    int server_closed;
    uint8_t *to_client;              /* answers the client has not read yet */
    size_t to_client_len;
    uint8_t *pending;                /* client writes not flushed yet */
    size_t pending_len, pending_cap;
    mu_recv from_client;             /* the server side's dechunker */
    int tcp_fd;                      /* mu_fixture_serve: the accepted socket, else -1 */
} fx_link;

typedef struct fx_command {
    uint32_t tick;
    int number;
    char text[240];
} fx_command;

struct mu_fixture_ctx {
    int has_endpoint[MU_CONN_KINDS];
    mu_endpoint endpoint[MU_CONN_KINDS];
    struct {
        const mu_fixture_behavior *b;
        void *self;
    } use[MAX_USES];
    int nuse;
    fx_command commands[MAX_LINES];
    size_t ncommands;
    mu_scenario_line client[MAX_LINES], expect[MAX_LINES], join;
    size_t nclient, nexpect;
    int has_join;
    fx_link links[MU_LINKS];
    uint32_t now, step, rng;
    mu_fixture_report report;
    mu_transport *transport;
    int transport_alive;
    mu_transport_counters tc;        /* the loopback transport's counters (as the sockets transport keeps them) */
};

struct mu_fixture {
    mu_fixture_ctx ctx;
};

static const char *const ROLE_NAMES[MU_CONN_KINDS] = {"connect", "game", "chat"};

static int role_of(const char *name)
{
    for (int k = 0; k < MU_CONN_KINDS; ++k)
        if (!strcmp(name, ROLE_NAMES[k]))
            return k;
    return -1;
}

/* ---- behaviour services ------------------------------------------------------------------- */

uint32_t mu_fixture_rand(mu_fixture_ctx *ctx)
{
    uint32_t x = ctx->rng ? ctx->rng : 0x9e3779b9u;   /* xorshift32 */
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    ctx->rng = x;
    return x;
}

uint32_t mu_fx_now(const mu_fixture_ctx *ctx) { return ctx->now; }
uint32_t mu_fx_step(const mu_fixture_ctx *ctx) { return ctx->step; }

static fx_link *link_of_role(mu_fixture_ctx *ctx, mu_conn_kind role)
{
    for (int i = 0; i < MU_LINKS; ++i)
        if (ctx->links[i].used && ctx->links[i].role == role && ctx->links[i].state == MU_LINK_OPEN &&
            !ctx->links[i].server_closed)
            return &ctx->links[i];
    return NULL;
}

static int to_client(mu_fixture_ctx *ctx, fx_link *l, const uint8_t *p, size_t n)
{
    if (l->to_client_len + n > TO_CLIENT_CAP) {
        snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "to-client buffer full");
        return -1;
    }
    memcpy(l->to_client + l->to_client_len, p, n);
    l->to_client_len += n;
    return 0;
}

int mu_fx_send(mu_fixture_ctx *ctx, mu_conn_kind conn, mu_packet *p, int encrypted)
{
    if (encrypted)
        return -2;   /* the mirror CryptoModule arrives with NET-CRYPTO-001 / NET-DECODE-001 */
    fx_link *l = link_of_role(ctx, conn);
    if (!l || p->overflow)
        return -1;
    uint32_t size = mu_packet_finish(p);
    if (to_client(ctx, l, &p->obj[2], size) != 0)
        return -1;
    ctx->report.answers++;
    return 0;
}

static const char *arg_find(const char *args, const char *key)
{
    size_t klen = strlen(key);
    for (const char *p = args; p && *p;) {
        while (*p == ' ' || *p == '\t')
            ++p;
        if (!strncmp(p, key, klen) && p[klen] == '=')
            return p + klen + 1;
        while (*p && *p != ' ' && *p != '\t')
            ++p;
    }
    return NULL;
}

int32_t mu_fx_arg_int(const char *args, const char *key, int32_t fallback)
{
    const char *v = arg_find(args, key);
    if (!v)
        return fallback;
    char *end;
    long n = strtol(v, &end, 0);
    return end == v ? fallback : (int32_t)n;
}

int mu_fx_arg_str(const char *args, const char *key, char *out, size_t cap)
{
    const char *v = arg_find(args, key);
    if (!v || !cap)
        return -1;
    size_t n = 0;
    while (v[n] && v[n] != ' ' && v[n] != '\t' && n + 1 < cap) {
        out[n] = v[n];
        ++n;
    }
    out[n] = 0;
    return 0;
}

/* ---- scenario ------------------------------------------------------------------------------ */

static const mu_fixture_behavior *behavior_named(const char *name)
{
    for (size_t i = 0; BEHAVIORS[i]; ++i)
        if (!strcmp(BEHAVIORS[i]->name, name))
            return BEHAVIORS[i];
    return NULL;
}

static void trim(char *s)
{
    char *h = strchr(s, '#');
    if (h)
        *h = 0;
    size_t n = strlen(s);
    while (n && isspace((unsigned char)s[n - 1]))
        s[--n] = 0;
}

static int parse_scenario(mu_fixture_ctx *ctx, const char *path, char *error, size_t error_size)
{
    FILE *fp = fopen(path, "r");
    if (!fp) {
        snprintf(error, error_size, "fixture: cannot open scenario %s", path);
        return -1;
    }
    char line[512];
    int number = 0, rc = 0;
    while (rc == 0 && fgets(line, sizeof line, fp)) {
        ++number;
        trim(line);
        char *p = line;
        while (isspace((unsigned char)*p))
            ++p;
        if (!*p)
            continue;
        char word[32] = {0};
        int used = 0;
        sscanf(p, "%31s%n", word, &used);
        char *rest = p + used;
        while (isspace((unsigned char)*rest))
            ++rest;
        if (!strcmp(word, "endpoint")) {
            char role[16], ep[300];
            if (sscanf(rest, "%15s %299s", role, ep) != 2 || role_of(role) < 0) {
                snprintf(error, error_size, "%s:%d: endpoint ROLE HOST:PORT", path, number);
                rc = -1;
                break;
            }
            int k = role_of(role);
            if (mu_endpoint_parse(&ctx->endpoint[k], ep) != 0) {
                snprintf(error, error_size, "%s:%d: bad endpoint %s", path, number, ep);
                rc = -1;
                break;
            }
            ctx->has_endpoint[k] = 1;
        } else if (!strcmp(word, "use")) {
            char name[32] = {0};
            int n2 = 0;
            sscanf(rest, "%31s%n", name, &n2);
            const mu_fixture_behavior *b = behavior_named(name);
            if (!b) {
                snprintf(error, error_size, "%s:%d: no behaviour named %s", path, number, name);
                rc = -1;
                break;
            }
            if (ctx->nuse >= MAX_USES) {
                snprintf(error, error_size, "%s:%d: too many behaviours", path, number);
                rc = -1;
                break;
            }
            for (int i = 0; i < ctx->nuse; ++i)
                if (ctx->use[i].b == b) {
                    snprintf(error, error_size, "%s:%d: behaviour %s used twice", path, number, name);
                    rc = -1;
                }
            if (rc)
                break;
            char err[200] = {0};
            void *self = b->open ? b->open(ctx, rest + n2, err, sizeof err) : NULL;
            if (b->open && !self) {
                snprintf(error, error_size, "%s:%d: %s: %s", path, number, name, err);
                rc = -1;
                break;
            }
            ctx->use[ctx->nuse].b = b;
            ctx->use[ctx->nuse].self = self;
            ctx->nuse++;
        } else if (!strcmp(word, "join")) {
            ctx->has_join = 1;
            ctx->join.number = number;
            snprintf(ctx->join.text, sizeof ctx->join.text, "%s", rest);
        } else if (!strcmp(word, "expect")) {
            if (ctx->nexpect < MAX_LINES) {
                mu_scenario_line *e = &ctx->expect[ctx->nexpect++];
                e->number = number;
                snprintf(e->text, sizeof e->text, "%s", rest);
            }
        } else if (!strcmp(word, "at")) {
            char *end;
            long tick = strtol(rest, &end, 10);
            if (end == rest || tick < 0) {
                snprintf(error, error_size, "%s:%d: at TICK ...", path, number);
                rc = -1;
                break;
            }
            while (isspace((unsigned char)*end))
                ++end;
            if (!strncmp(end, "client ", 7)) {
                if (ctx->nclient < MAX_LINES) {
                    mu_scenario_line *c = &ctx->client[ctx->nclient++];
                    c->tick = (uint32_t)tick;
                    c->number = number;
                    snprintf(c->text, sizeof c->text, "%s", end + 7);
                }
            } else if (ctx->ncommands < MAX_LINES) {
                fx_command *c = &ctx->commands[ctx->ncommands++];
                c->tick = (uint32_t)tick;
                c->number = number;
                snprintf(c->text, sizeof c->text, "%s", end);
            }
        } else {
            snprintf(error, error_size, "%s:%d: unknown line \"%s\"", path, number, word);
            rc = -1;
        }
    }
    fclose(fp);
    return rc;
}

/* ---- the server side of each link ---------------------------------------------------------- */

typedef struct drain_ctx {
    mu_fixture_ctx *ctx;
    fx_link *link;
} drain_ctx;

static void on_frame(const uint8_t *frame, size_t size, void *ud)
{
    drain_ctx *d = ud;
    mu_fixture_ctx *ctx = d->ctx;
    ctx->report.requests++;
    uint32_t hlen = mu_frame_header_len(frame[0]);
    if (frame[0] == MU_HEAD_C3 || frame[0] == MU_HEAD_C4 || !hlen || size < (size_t)hlen + 1u) {
        ctx->report.undecodable_requests++;
        return;
    }
    mu_fixture_request rq = {d->link->role, frame[0], frame[hlen],
        size > (size_t)hlen + 1u ? frame[hlen + 1] : 0x100u, 0, frame, size};
    for (int i = 0; i < ctx->nuse; ++i)
        if (ctx->use[i].b->on_plain_request && ctx->use[i].b->on_plain_request(ctx->use[i].self, ctx, &rq))
            return;
    /* undo the client's XorData: every byte after the opcode went through AddData(.., 1) in the
     * request builders reconstructed so far (0x0095c204, the stat request 0x00b48aca) */
    mu_packet obj;
    memset(&obj, 0, sizeof obj);
    if (size > MU_PACKET_CAP) {
        ctx->report.undecodable_requests++;
        return;
    }
    obj.obj[0] = (uint8_t)size;
    obj.obj[1] = (uint8_t)(size >> 8);
    memcpy(&obj.obj[2], frame, size);
    mu_send_xor_decode(obj.obj, hlen + 1u, size);
    rq.conn = d->link->role;
    rq.head = frame[0];
    rq.opcode = frame[hlen];
    rq.sub = size > (size_t)hlen + 1u ? obj.obj[2 + hlen + 1] : 0x100u;
    rq.encrypted = 0;
    rq.bytes = &obj.obj[2];
    rq.length = size;
    for (int i = 0; i < ctx->nuse; ++i)
        if (ctx->use[i].b->on_request && ctx->use[i].b->on_request(ctx->use[i].self, ctx, &rq))
            return;
}

static void take_client_bytes(mu_fixture_ctx *ctx, fx_link *l, const uint8_t *p, size_t n)
{
    drain_ctx d = {ctx, l};
    while (n) {
        size_t room = MU_RECV_CAP - l->from_client.len;
        size_t take = n < room ? n : room;
        if (!take) {
            ctx->report.undecodable_requests++;
            mu_recv_init(&l->from_client);   /* an over-long request: the fixture drops what it holds */
            continue;
        }
        mu_recv_push(&l->from_client, p, take);
        p += take;
        n -= take;
        mu_recv_drain(&l->from_client, on_frame, &d);
    }
}

static int hexbytes(const char *text, uint8_t *out, size_t cap)
{
    size_t n = 0;
    const char *p = text;
    while (*p) {
        while (isspace((unsigned char)*p))
            ++p;
        if (!*p)
            break;
        char *end;
        unsigned long v = strtoul(p, &end, 16);
        if (end == p || v > 0xff || n >= cap)
            return -1;
        out[n++] = (uint8_t)v;
        p = end;
    }
    return (int)n;
}

static void run_command(mu_fixture_ctx *ctx, const fx_command *c)
{
    char word[32] = {0};
    int used = 0;
    sscanf(c->text, "%31s%n", word, &used);
    const char *rest = c->text + used;
    while (isspace((unsigned char)*rest))
        ++rest;
    if (!strcmp(word, "send") || !strcmp(word, "close")) {
        char role[16] = {0};
        int n2 = 0;
        sscanf(rest, "%15s%n", role, &n2);
        int k = role_of(role);
        fx_link *l = k >= 0 ? link_of_role(ctx, (mu_conn_kind)k) : NULL;
        if (!l) {
            snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "line %d: no open %s link", c->number,
                     role);
            return;
        }
        if (!strcmp(word, "close")) {
            l->server_closed = 1;
            return;
        }
        uint8_t bytes[MU_RECV_CAP];
        int n = hexbytes(rest + n2, bytes, sizeof bytes);
        if (n <= 0) {
            snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "line %d: bad hex", c->number);
            return;
        }
        to_client(ctx, l, bytes, (size_t)n);
        ctx->report.answers++;
        return;
    }
    for (int i = 0; i < ctx->nuse; ++i)
        if (!strcmp(ctx->use[i].b->name, word)) {
            char err[160] = {0};
            if (!ctx->use[i].b->on_command || ctx->use[i].b->on_command(ctx->use[i].self, ctx, rest, err, sizeof err))
                snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "line %d: %s", c->number,
                         err[0] ? err : "command refused");
            return;
        }
    snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "line %d: no behaviour %s in use", c->number, word);
}

/* One fixture step: connects complete, client bytes become requests, due commands run, behaviours step. */
static int fixture_step(mu_fixture_ctx *ctx, uint32_t now_ms)
{
    ctx->now = now_ms;
    ctx->step++;
    ctx->report.steps = ctx->step;
    int changed = 0;
    for (int i = 0; i < MU_LINKS; ++i) {
        fx_link *l = &ctx->links[i];
        if (!l->used)
            continue;
        if (l->state == MU_LINK_CONNECTING) {
            l->state = MU_LINK_OPEN;
            changed++;
        }
    }
    for (size_t i = 0; i < ctx->ncommands; ++i)
        if (ctx->commands[i].tick == ctx->step)
            run_command(ctx, &ctx->commands[i]);
    for (int i = 0; i < ctx->nuse; ++i)
        if (ctx->use[i].b->on_step)
            ctx->use[i].b->on_step(ctx->use[i].self, ctx, now_ms);
    for (int i = 0; i < MU_LINKS; ++i)
        if (ctx->links[i].used && ctx->links[i].to_client_len)
            changed++;
    return changed;
}

/* ---- the loopback transport (the client's side of the links) ------------------------------- */

static mu_link_id lo_open(void *self, const mu_endpoint *e)
{
    mu_fixture_ctx *ctx = self;
    int slot = -1;
    for (int i = 0; i < MU_LINKS; ++i)
        if (!ctx->links[i].used) {
            slot = i;
            break;
        }
    if (slot < 0)
        return -1;
    fx_link *l = &ctx->links[slot];
    memset(l, 0, sizeof *l);
    l->used = 1;
    l->tcp_fd = -1;
    int role = -1;
    for (int k = 0; k < MU_CONN_KINDS; ++k)
        if (ctx->has_endpoint[k] && mu_endpoint_equal(&ctx->endpoint[k], e))
            role = k;
    if (role < 0) {
        l->state = MU_LINK_REFUSED;   /* not an endpoint of this scenario */
        ctx->report.refused_connects++;
        ctx->tc.links_refused++;
        return slot;
    }
    ctx->tc.connects_attempted++;
    ctx->tc.links_opened++;
    l->role = (mu_conn_kind)role;
    l->to_client = malloc(TO_CLIENT_CAP);
    if (!l->to_client) {
        l->state = MU_LINK_CLOSED;
        return slot;
    }
    mu_recv_init(&l->from_client);
    l->state = MU_LINK_CONNECTING;   /* open at the next step, like a connect completing */
    return slot;
}

static int lo_allow(void *self, const mu_endpoint *e)
{
    (void)self;
    (void)e;
    return 0;   /* the scenario's endpoints are the fixture's allowlist (lo_open) */
}

static fx_link *lo_get(mu_fixture_ctx *ctx, mu_link_id id)
{
    return id >= 0 && id < MU_LINKS && ctx->links[id].used ? &ctx->links[id] : NULL;
}

static mu_link_state lo_state(void *self, mu_link_id id, int *error_code)
{
    fx_link *l = lo_get(self, id);
    if (error_code)
        *error_code = 0;
    if (!l)
        return MU_LINK_CLOSED;
    if (l->server_closed && !l->to_client_len)
        return MU_LINK_CLOSED;
    return l->state;
}

static size_t lo_read(void *self, mu_link_id id, uint8_t *out, size_t cap)
{
    fx_link *l = lo_get(self, id);
    if (!l || !l->to_client_len)
        return 0;
    size_t n = l->to_client_len < cap ? l->to_client_len : cap;
    memcpy(out, l->to_client, n);
    memmove(l->to_client, l->to_client + n, l->to_client_len - n);
    l->to_client_len -= n;
    ((mu_fixture_ctx *)self)->tc.bytes_in += n;
    return n;
}

static int lo_write(void *self, mu_link_id id, const uint8_t *p, size_t n)
{
    fx_link *l = lo_get(self, id);
    if (!l || (l->state != MU_LINK_OPEN && l->state != MU_LINK_CONNECTING) || l->server_closed)
        return -1;
    if (l->pending_len + n > l->pending_cap) {
        size_t cap = l->pending_cap ? l->pending_cap : 1024;
        while (cap < l->pending_len + n)
            cap *= 2;
        uint8_t *q = realloc(l->pending, cap);
        if (!q)
            return -1;
        l->pending = q;
        l->pending_cap = cap;
    }
    memcpy(l->pending + l->pending_len, p, n);
    l->pending_len += n;
    ((mu_fixture_ctx *)self)->tc.bytes_out += n;
    return 0;
}

static void link_free(fx_link *l)
{
    if (l->tcp_fd >= 0)
        close(l->tcp_fd);
    free(l->to_client);
    free(l->pending);
    memset(l, 0, sizeof *l);
    l->tcp_fd = -1;
}

static void lo_close(void *self, mu_link_id id)
{
    fx_link *l = lo_get(self, id);
    if (l)
        link_free(l);
}

static int lo_poll(void *self, uint32_t now_ms)
{
    return fixture_step(self, now_ms);
}

static size_t lo_flush(void *self)
{
    mu_fixture_ctx *ctx = self;
    for (int i = 0; i < MU_LINKS; ++i) {
        fx_link *l = &ctx->links[i];
        if (!l->used || !l->pending_len || l->state != MU_LINK_OPEN)
            continue;
        size_t n = l->pending_len;
        l->pending_len = 0;
        take_client_bytes(ctx, l, l->pending, n);
    }
    return 0;
}

static void lo_free(void *self)
{
    mu_fixture_ctx *ctx = self;
    ctx->transport_alive = 0;   /* the fixture owns the state; only the wrapper goes */
}

static void lo_counters(const void *self, mu_transport_counters *out)
{
    const mu_fixture_ctx *ctx = self;
    *out = ctx->tc;
}

static const mu_transport_ops LOOPBACK_OPS = {
    .open = lo_open,
    .allow = lo_allow,
    .state = lo_state,
    .read = lo_read,
    .write = lo_write,
    .close = lo_close,
    .poll = lo_poll,
    .flush = lo_flush,
    .free = lo_free,
    .counters = lo_counters,
};

/* ---- lifecycle ---------------------------------------------------------------------------- */

mu_fixture *mu_fixture_open(const mu_fixture_options *o, char *error, size_t error_size)
{
    if (!o || !o->scenario) {
        snprintf(error, error_size, "fixture: no scenario");
        return NULL;
    }
    mu_fixture *f = calloc(1, sizeof *f);
    if (!f) {
        snprintf(error, error_size, "fixture: out of memory");
        return NULL;
    }
    f->ctx.rng = o->seed ? o->seed : 1u;
    for (int i = 0; i < MU_LINKS; ++i)
        f->ctx.links[i].tcp_fd = -1;
    if (parse_scenario(&f->ctx, o->scenario, error, error_size) != 0) {
        mu_fixture_close(f);
        return NULL;
    }
    f->ctx.report.behaviors = (uint32_t)f->ctx.nuse;
    return f;
}

void mu_fixture_close(mu_fixture *f)
{
    if (!f)
        return;
    for (int i = 0; i < f->ctx.nuse; ++i)
        if (f->ctx.use[i].b->close)
            f->ctx.use[i].b->close(f->ctx.use[i].self);
    for (int i = 0; i < MU_LINKS; ++i)
        if (f->ctx.links[i].used)
            link_free(&f->ctx.links[i]);
    free(f);
}

mu_transport *mu_fixture_transport(mu_fixture *f)
{
    if (!f)
        return NULL;
    mu_transport *t = mu_transport_wrap(&LOOPBACK_OPS, &f->ctx);
    f->ctx.transport_alive = t != NULL;
    return t;
}

int mu_fixture_is_transport(const mu_transport *t)
{
    return mu_transport_impl(t, &LOOPBACK_OPS) != NULL;
}

void mu_fixture_report_get(const mu_fixture *f, mu_fixture_report *out)
{
    if (f)
        *out = f->ctx.report;
    else
        memset(out, 0, sizeof *out);
}

int mu_fixture_endpoint(const mu_fixture *f, const char *role, mu_endpoint *out)
{
    int k = role ? role_of(role) : -1;
    if (!f || k < 0 || !f->ctx.has_endpoint[k])
        return -1;
    *out = f->ctx.endpoint[k];
    return 0;
}

void mu_fixture_script_get(const mu_fixture *f, mu_fixture_script *out)
{
    memset(out, 0, sizeof *out);
    if (!f)
        return;
    out->client = f->ctx.client;
    out->nclient = f->ctx.nclient;
    out->expect = f->ctx.expect;
    out->nexpect = f->ctx.nexpect;
    out->join = f->ctx.has_join ? &f->ctx.join : NULL;
}

size_t mu_fixture_behavior_names(const char *const **names)
{
    size_t n = sizeof BEHAVIOR_NAMES / sizeof BEHAVIOR_NAMES[0] - 1;
    *names = BEHAVIOR_NAMES;
    return n;
}

/* ---- TCP: one client over a loopback socket --------------------------------------------------- */

#ifndef MU_FIXTURE_NO_TCP
static uint32_t clock_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)((uint64_t)ts.tv_sec * 1000u + (uint64_t)ts.tv_nsec / 1000000u);
}

/* FIXTURE-PROBE-001: the listener is open to every local process, and some connect only to probe it (T3 Code
 * sends "GET / HTTP/1.1" to each new 127.0.0.1 listener, TEST-FLAKE-001). The MU server speaks first, so a
 * client may stay silent: a peer is served when its first byte is a C1-C4 frame head or when it stays silent
 * for screen_ms. A peer whose first byte is anything else, or that closes or fails first, is a stray: counted,
 * logged, closed, and the fixture keeps listening. Returns 1 to serve the peer, 0 for a stray. */
static int screen_peer(mu_fixture_ctx *ctx, int fd, uint32_t screen_ms)
{
    const char *reason = NULL;
    int first = -1;
    struct pollfd pp = {fd, POLLIN, 0};
    uint32_t begin = clock_ms();
    for (;;) {
        uint32_t spent = clock_ms() - begin;
        int r = poll(&pp, 1, spent < screen_ms ? (int)(screen_ms - spent) : 0);
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0)
            return 1;   /* silent: a client waiting for the server's first frame */
        uint8_t b;
        ssize_t n = recv(fd, &b, 1, MSG_PEEK);
        if (n < 0 && errno == EINTR)
            continue;
        if (n == 1 && b >= MU_HEAD_C1 && b <= MU_HEAD_C4)
            return 1;   /* a frame: left in the socket for the session */
        if (n == 1) {
            reason = "not a frame";
            first = b;
        } else {
            reason = n == 0 ? "closed" : "error";
        }
        break;
    }
    ctx->report.rejected_peers++;
    printf("{\"fixture_rejected\": {\"peer\": %llu, \"reason\": \"%s\", \"first_byte\": %d}}\n",
           (unsigned long long)ctx->report.rejected_peers, reason, first);
    fflush(stdout);
    return 0;
}

int mu_fixture_serve(mu_fixture *f, const char *host, uint16_t port, uint32_t seconds, uint32_t step_ms,
                     int screen_ms)
{
    mu_fixture_ctx *ctx = &f->ctx;
    mu_endpoint here;
    memset(&here, 0, sizeof here);
    snprintf(here.host, sizeof here.host, "%s", host);
    here.port = port;
    if (!mu_endpoint_is_loopback(&here)) {
        snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "serve: %s is not a loopback address", host);
        return -1;
    }
    int role = -1;
    for (int k = 0; k < MU_CONN_KINDS; ++k)
        if (ctx->has_endpoint[k] && ctx->endpoint[k].port == port)
            role = k;
    if (role < 0) {
        snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "serve: the scenario declares no port %u",
                 (unsigned)port);
        return -1;
    }
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE | AI_NUMERICHOST;
    char portstr[8];
    snprintf(portstr, sizeof portstr, "%u", (unsigned)port);
    if (getaddrinfo(strcmp(host, "localhost") ? host : "127.0.0.1", portstr, &hints, &res) != 0 || !res) {
        snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "serve: cannot resolve %s", host);
        return -1;
    }
    int ls = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    int one = 1;
    if (ls >= 0)
        setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (ls < 0 || bind(ls, res->ai_addr, res->ai_addrlen) != 0 || listen(ls, 8) != 0) {
        snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "serve: listen %s:%u: %s", host,
                 (unsigned)port, strerror(errno));
        if (ls >= 0)
            close(ls);
        freeaddrinfo(res);
        return -1;
    }
    freeaddrinfo(res);
    printf("{\"fixture_listening\": \"%s:%u\"}\n", host, (unsigned)port);
    fflush(stdout);
    uint32_t start = clock_ms(), limit = seconds * 1000u;
    struct pollfd pl = {ls, POLLIN, 0};
    int fd = -1;
    while (fd < 0 && clock_ms() - start < limit) {
        if (poll(&pl, 1, 100) > 0) {
            fd = accept(ls, NULL, NULL);
            if (fd >= 0 && screen_ms >= 0 && !screen_peer(ctx, fd, (uint32_t)screen_ms)) {
                close(fd);
                fd = -1;
            }
        }
    }
    close(ls);
    if (fd < 0) {
        snprintf(ctx->report.last_error, sizeof ctx->report.last_error, "serve: no client connected");
        return -1;
    }
    fx_link *l = &ctx->links[0];
    if (l->used)
        link_free(l);
    memset(l, 0, sizeof *l);
    l->used = 1;
    l->role = (mu_conn_kind)role;
    l->state = MU_LINK_OPEN;
    l->tcp_fd = fd;
    l->to_client = malloc(TO_CLIENT_CAP);
    mu_recv_init(&l->from_client);
    if (!l->to_client) {
        link_free(l);
        return -1;
    }
    int peer_closed = 0;
    uint32_t next = clock_ms();
    while (!peer_closed && clock_ms() - start < limit) {
        struct pollfd pc = {fd, POLLIN, 0};
        int wait = (int)(next > clock_ms() ? next - clock_ms() : 0);
        if (poll(&pc, 1, wait) > 0 && (pc.revents & (POLLIN | POLLHUP | POLLERR))) {
            uint8_t buf[4096];
            ssize_t n = recv(fd, buf, sizeof buf, 0);
            if (n > 0)
                take_client_bytes(ctx, l, buf, (size_t)n);
            else if (n == 0 || (errno != EAGAIN && errno != EINTR))
                peer_closed = 1;
        }
        if (clock_ms() >= next) {
            fixture_step(ctx, clock_ms() - start);
            next += step_ms ? step_ms : 40u;
        }
        size_t sent = 0;
        while (sent < l->to_client_len) {
            ssize_t n = send(fd, l->to_client + sent, l->to_client_len - sent, 0);
            if (n <= 0)
                break;
            sent += (size_t)n;
        }
        if (sent) {
            memmove(l->to_client, l->to_client + sent, l->to_client_len - sent);
            l->to_client_len -= sent;
        }
        if (l->server_closed && !l->to_client_len)
            break;
    }
    link_free(l);
    return 0;
}

#endif /* MU_FIXTURE_NO_TCP */

void *mu_fixture_behavior_state(mu_fixture *f, const char *name) {
    return mu_fx_behavior_state(f ? &f->ctx : NULL, name);
}

void *mu_fx_behavior_state(mu_fixture_ctx *ctx, const char *name) {
    for (int i=0; ctx && i<ctx->nuse; i++) if(!strcmp(ctx->use[i].b->name,name)) return ctx->use[i].self;
    return NULL;
}
