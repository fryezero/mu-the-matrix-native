/* SESSION-CORE-001: the session journal - THE recording format. One format for fixture runs, live
 * runs (owner's account), recordings of the owner's original client (CAPTURE-KIT-001) and replay.
 *
 * File layout (little-endian):
 *   header  80 bytes: "MUJNL\0\1\0", the client build digest (main.exe SHA-256, 32 bytes), the
 *           layout manifest digest (32 bytes; generated layout.json SHA-256), flags (u32: bit 0 live),
 *           reserved (u32)
 *   record  16-byte head {u8 type, u8 direction, u8 conn, u8 flags, u32 tick, u32 ms, u32 length}
 *           then `length` payload bytes:
 *     OPEN      text: endpoint, build digest (never credentials)
 *     FRAME in  {u8 head, u8 opcode, u16 sub, u8 encrypted, u8 decode status, u8 apply result,
 *                u8 held, u32 client handler, char apply[32], u32 cues} + the frame bytes as the
 *                dechunker cut them (pre-decrypt)
 *     FRAME out {i8 send status, u8 Send's first argument (1: the C3/C4 wrap), u16 reserved} + the
 *                built frame (after XorData, before the wrap)
 *     INTENT    {u32 kind, i32 status, i32 notice} - never an intent payload
 *     EVENT     text: phase, barrier, close reason, lease audit
 *     SNAPSHOT  per domain zone {char name[32], u32 offset, u32 size} + bytes (client layout)
 * The type values are MU_JNL_* below. A reader refuses a journal whose build digest differs from
 * the running client's: a version-drifted recording fails to open instead of mis-decoding.
 *
 * Redaction is structural: mu_secret has no accessor and INTENT records carry no payload.
 * Journals of live sessions and recordings are local evidence (ignored directories), never
 * committed or uploaded.
 */
#ifndef MU_JOURNAL_H
#define MU_JOURNAL_H
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_journal mu_journal;

typedef struct mu_journal_options {
    const char *path;                 /* e.g. verify-runs/<run>/session.mujnl (ignored directory); NULL: counters only */
    const uint32_t *snapshot_ticks;   /* ticks at which every domain is dumped in client layout, may be NULL */
    size_t snapshot_count;
    int live;                         /* 1: the run talked to the live service (header flag) */
} mu_journal_options;

mu_journal *mu_journal_create(const mu_journal_options *o, char *error, size_t error_size);
void mu_journal_close(mu_journal *j);

enum {
    MU_JNL_OPEN = 1, MU_JNL_FRAME = 2, MU_JNL_INTENT = 3, MU_JNL_EVENT = 4, MU_JNL_SNAPSHOT = 5
};
enum { MU_JNL_IN = 0, MU_JNL_OUT = 1 };

/* Reading, for `mu-session journal` and later replay. build_sha256 NULL: accept any build. */
typedef struct mu_journal_reader mu_journal_reader;
typedef struct mu_journal_record {
    uint8_t type, direction, conn, flags;
    uint32_t tick, ms, length;
    const uint8_t *payload;           /* valid until the next read */
} mu_journal_record;
mu_journal_reader *mu_journal_open(const char *path, const uint8_t build_sha256[32], char *error, size_t error_size);
/* 1: a record; 0: end; -1: truncated or malformed */
int mu_journal_read(mu_journal_reader *r, mu_journal_record *out);
void mu_journal_reader_build(const mu_journal_reader *r, uint8_t out[32]);
void mu_journal_reader_close(mu_journal_reader *r);

/* Summary for reports and tests (verify-mu-native JSON rows). unbound_frames counts frames that hit a
 * route with no MU_OP (the coverage report lists them by client address); undecodable_frames the
 * frames the decode stage refused (C3/C4 before NET-DECODE-001, short frames); unsent_frames the
 * requests built but not sent (an encrypted Send before NET-DECODE-001). */
typedef struct mu_journal_summary {
    uint64_t frames_in, frames_out, intents, unrecovered_intents, unbound_frames, cues, inputs;
    uint64_t undecodable_frames, unsent_frames, snapshots;
    uint32_t ticks;
} mu_journal_summary;
void mu_journal_summary_get(const mu_journal *j, mu_journal_summary *out);

#ifdef __cplusplus
}
#endif

#endif
