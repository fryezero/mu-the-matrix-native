/* SESSION-CORE-001: the journal writer and reader (format in mu_journal.h). */
#include "session_internal.h"
#include "layout_all.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define HEADER_SIZE 80u
static const uint8_t MAGIC[8] = {'M', 'U', 'J', 'N', 'L', 0, 1, 0};

struct mu_journal {
    FILE *f;
    int started;
    int live;
    int holding;                 /* records made while a frame applies wait until its FRAME record is written */
    uint8_t *held;
    size_t held_len, held_cap;
    uint32_t *snapshots;
    size_t nsnapshots;
    mu_journal_summary sum;
};

struct mu_journal_reader {
    FILE *f;
    uint8_t build[32];
    uint8_t *buf;
    size_t cap;
};

static void put32(uint8_t *p, uint32_t v)
{
    for (int i = 0; i < 4; ++i)
        p[i] = (uint8_t)(v >> (8 * i));
}

static uint32_t get32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    if (c >= 'A' && c <= 'F')
        return c - 'A' + 10;
    return -1;
}

static void digest(const char *hex, uint8_t out[32])
{
    memset(out, 0, 32);
    for (int i = 0; hex && i < 32 && hex[2 * i] && hex[2 * i + 1]; ++i) {
        int hi = hexval(hex[2 * i]), lo = hexval(hex[2 * i + 1]);
        if (hi < 0 || lo < 0)
            break;
        out[i] = (uint8_t)(hi << 4 | lo);
    }
}

mu_journal *mu_journal_create(const mu_journal_options *o, char *error, size_t error_size)
{
    mu_journal *j = calloc(1, sizeof *j);
    if (!j) {
        snprintf(error, error_size, "journal: out of memory");
        return NULL;
    }
    if (o && o->path) {
        j->f = fopen(o->path, "wb");
        if (!j->f) {
            snprintf(error, error_size, "journal: cannot create %s", o->path);
            free(j);
            return NULL;
        }
    }
    if (o && o->snapshot_count) {
        j->snapshots = malloc(o->snapshot_count * sizeof *j->snapshots);
        if (j->snapshots) {
            memcpy(j->snapshots, o->snapshot_ticks, o->snapshot_count * sizeof *j->snapshots);
            j->nsnapshots = o->snapshot_count;
        }
    }
    j->live = o ? o->live : 0;
    return j;
}

void mu_journal_close(mu_journal *j)
{
    if (!j)
        return;
    mu_journal_end_frame(j);
    if (j->f)
        fclose(j->f);
    free(j->snapshots);
    free(j->held);
    free(j);
}

void mu_journal_summary_get(const mu_journal *j, mu_journal_summary *out)
{
    if (j)
        *out = j->sum;
    else
        memset(out, 0, sizeof *out);
}

void mu_journal_start(mu_journal *j, const char *build_sha256_hex)
{
    if (!j || j->started)
        return;
    j->started = 1;
    if (!j->f)
        return;
    uint8_t h[HEADER_SIZE];
    memset(h, 0, sizeof h);
    memcpy(h, MAGIC, sizeof MAGIC);
    digest(build_sha256_hex, h + 8);
    digest(MU_LAYOUT_SHA256, h + 40);
    put32(h + 72, j->live ? 1u : 0u);
    fwrite(h, 1, sizeof h, j->f);
}

static void out(mu_journal *j, const uint8_t *p, size_t n, int direct)
{
    if (!n)
        return;
    if (j->holding && !direct) {
        if (j->held_len + n > j->held_cap) {
            size_t cap = j->held_cap ? j->held_cap : 1024;
            while (cap < j->held_len + n)
                cap *= 2;
            uint8_t *q = realloc(j->held, cap);
            if (!q)
                return;
            j->held = q;
            j->held_cap = cap;
        }
        memcpy(j->held + j->held_len, p, n);
        j->held_len += n;
        return;
    }
    fwrite(p, 1, n, j->f);
}

void mu_journal_begin_frame(mu_journal *j)
{
    if (j)
        j->holding = 1;
}

void mu_journal_end_frame(mu_journal *j)
{
    if (!j || !j->holding)
        return;
    j->holding = 0;
    if (j->f && j->held_len)
        fwrite(j->held, 1, j->held_len, j->f);
    j->held_len = 0;
}

static void record_x(mu_journal *j, int direct, uint8_t type, uint8_t dir, uint8_t conn, uint32_t tick, uint32_t ms,
                     const uint8_t *a, size_t na, const uint8_t *b, size_t nb)
{
    if (!j || !j->f)
        return;
    uint8_t h[16];
    h[0] = type;
    h[1] = dir;
    h[2] = conn;
    h[3] = 0;
    put32(h + 4, tick);
    put32(h + 8, ms);
    put32(h + 12, (uint32_t)(na + nb));
    out(j, h, sizeof h, direct);
    out(j, a, na, direct);
    out(j, b, nb, direct);
}

static void record(mu_journal *j, uint8_t type, uint8_t dir, uint8_t conn, uint32_t tick, uint32_t ms,
                   const uint8_t *a, size_t na, const uint8_t *b, size_t nb)
{
    record_x(j, 0, type, dir, conn, tick, ms, a, na, b, nb);
}

void mu_journal_text(mu_journal *j, uint8_t type, uint32_t tick, uint32_t ms, const char *text)
{
    record(j, type, 0, 0, tick, ms, (const uint8_t *)text, strlen(text), NULL, 0);
}

void mu_journal_frame_in(mu_journal *j, uint32_t tick, uint32_t ms, const mu_frame *f, mu_decode_status ds,
                         const mu_route_info *route, int apply_result, int held, uint32_t cues)
{
    if (!j)
        return;
    j->sum.frames_in++;
    if (ds != MU_DECODE_OK)
        j->sum.undecodable_frames++;
    else if (route && !route->apply && !held)
        j->sum.unbound_frames++;
    uint8_t p[48];
    memset(p, 0, sizeof p);
    p[0] = f->head;
    p[1] = f->opcode;
    uint16_t sub = route ? route->sub : 0x100u;
    p[2] = (uint8_t)sub;
    p[3] = (uint8_t)(sub >> 8);
    p[4] = (uint8_t)f->encrypted;
    p[5] = (uint8_t)ds;
    p[6] = (uint8_t)apply_result;
    p[7] = (uint8_t)held;
    put32(p + 8, route ? route->client_handler : 0);
    if (route && route->apply)
        snprintf((char *)p + 12, 32, "%s", route->apply);
    put32(p + 44, cues);
    /* direct: the inbound frame precedes what its apply journaled (held since mu_journal_begin_frame) */
    record_x(j, 1, MU_JNL_FRAME, MU_JNL_IN, (uint8_t)f->conn, tick, ms, p, sizeof p, f->bytes, f->length);
}

void mu_journal_frame_out(mu_journal *j, uint32_t tick, uint32_t ms, mu_conn_kind conn, const uint8_t *frame,
                          size_t size, int send_status, int encrypted)
{
    if (!j)
        return;
    if (send_status == MU_SEND_OK)
        j->sum.frames_out++;
    else
        j->sum.unsent_frames++;
    uint8_t p[4] = {(uint8_t)(int8_t)send_status, (uint8_t)encrypted, 0, 0};
    record(j, MU_JNL_FRAME, MU_JNL_OUT, (uint8_t)conn, tick, ms, p, sizeof p, frame, size);
}

void mu_journal_intent(mu_journal *j, uint32_t tick, uint32_t ms, uint32_t kind, int32_t status, int32_t notice)
{
    if (!j)
        return;
    j->sum.intents++;
    if (status == MU_SUBMIT_UNRECOVERED)
        j->sum.unrecovered_intents++;
    uint8_t p[12];
    put32(p, kind);
    put32(p + 4, (uint32_t)status);
    put32(p + 8, (uint32_t)notice);
    record(j, MU_JNL_INTENT, 0, 0, tick, ms, p, sizeof p, NULL, 0);
}

int mu_journal_wants_snapshot(const mu_journal *j, uint32_t tick)
{
    if (!j)
        return 0;
    for (size_t i = 0; i < j->nsnapshots; ++i)
        if (j->snapshots[i] == tick)
            return 1;
    return 0;
}

void mu_journal_snapshot(mu_journal *j, uint32_t tick, uint32_t ms, const mu_audit_zones *zones)
{
    if (!j)
        return;
    j->sum.snapshots++;
    if (!j->f)
        return;
    size_t total = 0;
    for (int i = 0; i < zones->count; ++i)
        total += 40u + zones->z[i].size;
    uint8_t *p = malloc(total ? total : 1);
    if (!p)
        return;
    size_t at = 0;
    for (int i = 0; i < zones->count; ++i) {
        const mu_audit_zone *z = &zones->z[i];
        memset(p + at, 0, 40);
        snprintf((char *)p + at, 32, "%s", z->name);
        put32(p + at + 32, z->offset);
        put32(p + at + 36, z->size);
        memcpy(p + at + 40, z->base + z->offset, z->size);
        at += 40u + z->size;
    }
    record(j, MU_JNL_SNAPSHOT, 0, 0, tick, ms, p, at, NULL, 0);
    free(p);
}

void mu_journal_count_cues(mu_journal *j, uint64_t cues)
{
    if (j)
        j->sum.cues += cues;
}

void mu_journal_set_ticks(mu_journal *j, uint32_t ticks)
{
    if (j)
        j->sum.ticks = ticks;
}

/* ---- reader ------------------------------------------------------------------------------ */

mu_journal_reader *mu_journal_open(const char *path, const uint8_t build_sha256[32], char *error, size_t error_size)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        snprintf(error, error_size, "journal: cannot open %s", path);
        return NULL;
    }
    uint8_t h[HEADER_SIZE];
    if (fread(h, 1, sizeof h, f) != sizeof h || memcmp(h, MAGIC, sizeof MAGIC) != 0) {
        snprintf(error, error_size, "journal: %s is not a session journal", path);
        fclose(f);
        return NULL;
    }
    if (build_sha256 && memcmp(h + 8, build_sha256, 32) != 0) {
        snprintf(error, error_size, "journal: %s was recorded for another client build", path);
        fclose(f);
        return NULL;
    }
    mu_journal_reader *r = calloc(1, sizeof *r);
    if (!r) {
        fclose(f);
        snprintf(error, error_size, "journal: out of memory");
        return NULL;
    }
    r->f = f;
    memcpy(r->build, h + 8, 32);
    return r;
}

int mu_journal_read(mu_journal_reader *r, mu_journal_record *out)
{
    uint8_t h[16];
    size_t n = fread(h, 1, sizeof h, r->f);
    if (n == 0)
        return 0;
    if (n != sizeof h)
        return -1;
    out->type = h[0];
    out->direction = h[1];
    out->conn = h[2];
    out->flags = h[3];
    out->tick = get32(h + 4);
    out->ms = get32(h + 8);
    out->length = get32(h + 12);
    if (out->length > (64u << 20))
        return -1;
    if (out->length > r->cap) {
        uint8_t *b = realloc(r->buf, out->length);
        if (!b)
            return -1;
        r->buf = b;
        r->cap = out->length;
    }
    if (out->length && fread(r->buf, 1, out->length, r->f) != out->length)
        return -1;
    out->payload = r->buf;
    return 1;
}

void mu_journal_reader_build(const mu_journal_reader *r, uint8_t out[32])
{
    memcpy(out, r->build, 32);
}

void mu_journal_reader_close(mu_journal_reader *r)
{
    if (!r)
        return;
    fclose(r->f);
    free(r->buf);
    free(r);
}
