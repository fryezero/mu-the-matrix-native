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
 * NUL-terminated key at 6, text at 0x46. The last two bytes are not read by
 * the reconstructed controller. See client-help-window.md for bounds. */
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

#endif
