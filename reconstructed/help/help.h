#ifndef MU_HELP_H
#define MU_HELP_H

#include <stddef.h>
#include <stdint.h>

#define MU_HELP_ROWS 512
#define MU_HELP_ROW_SIZE 136
#define MU_HELP_PAYLOAD_SIZE (MU_HELP_ROWS * MU_HELP_ROW_SIZE)
#define MU_HELP_FILE_SIZE (MU_HELP_PAYLOAD_SIZE + 4)

/* Authored byte-oriented interface to HelpWindow's table at handler +0x78.
 * Original reader: 0x00b8968b. No decoded game data is included here.
 * Row: signed i32 id at 0; category byte at 4; auxiliary category byte at 5;
 * NUL-terminated key starts at 6, text at 0x46. Native string bounds are
 * 64 bytes before the text and 66 bytes remaining in the record. The
 * original declared text-array extent versus trailing padding is unknown;
 * its string constructors read to NUL. See client-help-window.md. */
typedef struct { uint8_t rows[MU_HELP_ROWS][MU_HELP_ROW_SIZE]; } mu_help_table;

typedef enum {
    MU_HELP_OK, MU_HELP_MISSING, MU_HELP_TRUNCATED, MU_HELP_CORRUPTED,
    MU_HELP_IO_ERROR, MU_HELP_NO_MEMORY, MU_HELP_BAD_ARGUMENT
} mu_help_status;

/* Replaces out atomically on success; clears it on any failure, including a
 * reload. Trailing bytes are ignored as in the client. The size and I/O
 * checks are native policy: the original ignores fread's return values. */
mu_help_status mu_help_decode(mu_help_table *out, const uint8_t *file, size_t size);
mu_help_status mu_help_read(mu_help_table *out, const char *path);
const char *mu_help_status_name(mu_help_status status);

/* Original vectors copy whole rows, including their strings. They are not
 * views into the reader's table. Capacity is a native bound; the original
 * STL storage can grow. A build that would exceed it refuses atomically. */
typedef struct {
    mu_help_table list[3];
    uint32_t count[3];
} mu_help_provider;

typedef void (*mu_help_invoke_fn)(void *user, const char *method, size_t argc,
                                 const char *const *args);

void mu_help_provider_init(mu_help_provider *provider);
/* 0x00b89866: clears lists 0/1 but appends to list 2. Stops at zero row ID. */
int mu_help_build(mu_help_provider *provider, const mu_help_table *table);
/* String arguments are encoded bytes. Native hosting must supply the same
 * ANSI-to-UTF-8 service as the other recovered windows. Synthetic comparison
 * uses ASCII; no code-page equivalence is implied by it. */
int mu_help_hotkeys(const mu_help_provider *, int alternate_mode, mu_help_invoke_fn, void *);
int mu_help_chatkeys(const mu_help_provider *, mu_help_invoke_fn, void *);
/* 0x00b89c17: ClearDataProvider then both row emitters. */
int mu_help_reload(const mu_help_provider *, int alternate_mode, mu_help_invoke_fn, void *);
/* 0x00b89977 after its file-read boundary. Labels are converted GlobalText
 * 0xd57..0xd5b. A false base_loaded emits nothing and changes no provider. */
int mu_help_load(mu_help_provider *, const mu_help_table *, int base_loaded,
                 int alternate_mode, const char *const labels[5], mu_help_invoke_fn, void *);

#endif
