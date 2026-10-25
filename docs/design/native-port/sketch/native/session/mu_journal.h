/* SESSION-CORE-001 (sketch): the session journal - THE recording format. One format for fixture
 * runs, live runs (owner's account), recordings of the owner's original client (CAPTURE-KIT-001,
 * written by the Wine-track tap) and replay. A recording that cannot be replayed into a native
 * session is not a journal.
 *
 * Header: the client build digest (main.exe SHA-256, MU_PINNED_BUILD) and the layout manifest
 * digest (build/gen/layout.json). A reader refuses a journal whose build digest differs from the
 * running client's - a version-drifted recording never mis-decodes; it fails to open.
 *
 * Records, each stamped with the session tick, wall ms and - when the producer knows it - the
 * client WorldTime ([0x06fce370]), so native and original runs align on the client's own clock:
 *   FRAME   direction, connection kind, the link bytes as they crossed the wire (pre-decrypt), and
 *           for C3/C4 the decoded plaintext beside them (a ciphertext/plaintext pair is real-traffic
 *           evidence for NET-CRYPTO-001/NET-DECODE-001, not only known-answer tests); inbound frames
 *           also carry the decoded (head, opcode, sub, encrypted), the route's client address, the
 *           apply result and the cue count
 *   INPUT   one Win32-form input message (mu_input_msg), so one script drives both clients
 *   INTENT  kind and submit status (DONE / REFUSED / NOT_NOW / UNRECOVERED)
 *   SNAPSHOT every domain's records dumped in client layout (the layout manifest decides the bytes)
 *           at chosen ticks, for scripts/session_compare.py against live-readers/memread captures and
 *           for the replay oracle (VERIFY-REPLAY-001)
 *
 * Redaction is structural: mu_secret has no accessor, so LOGIN/DELETE payloads cannot reach the
 * journal; their frames are written with the body replaced by its length. Nothing the official
 * launcher or IGC.dll produces is ever recorded or replayed: such login fields are written as their
 * length and provenance tag only. Journals of live sessions and recordings are local evidence
 * (ignored directories), never committed or uploaded.
 */
#ifndef MU_JOURNAL_H
#define MU_JOURNAL_H
#include <stddef.h>
#include <stdint.h>

typedef struct mu_journal mu_journal;

typedef struct mu_journal_options {
    const char *path;                 /* e.g. verify-runs/<run>/session.mujnl (ignored directory) */
    const uint32_t *snapshot_ticks;   /* ticks at which every domain is dumped in client layout, may be NULL */
    size_t snapshot_count;
    int live;                         /* 1: the run talked to the live service (report header, stricter redaction) */
} mu_journal_options;

mu_journal *mu_journal_create(const mu_journal_options *o, char *error, size_t error_size);
void mu_journal_close(mu_journal *j);

/* Reading, for `mu-session replay` and the Python side (scripts/journal.py mirrors the format). */
typedef struct mu_journal_reader mu_journal_reader;
mu_journal_reader *mu_journal_open(const char *path, const uint8_t build_sha256[32], char *error, size_t error_size);
void mu_journal_reader_close(mu_journal_reader *r);

/* Summary for reports and tests (verify-mu-native JSON rows). unbound_frames counts frames that hit a
 * route with no MU_OP (the coverage report lists them by client address). */
typedef struct mu_journal_summary {
    uint64_t frames_in, frames_out, intents, unrecovered_intents, unbound_frames, cues, inputs;
    uint32_t ticks;
} mu_journal_summary;
void mu_journal_summary_get(const mu_journal *j, mu_journal_summary *out);

#endif
