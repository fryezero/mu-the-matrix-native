#include "help.h"
#include "../data/data_tables.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

mu_help_status mu_help_decode(mu_help_table *out, const uint8_t *file, size_t size)
{
    if (!out) return MU_HELP_BAD_ARGUMENT;
    memset(out, 0, sizeof *out);
    if (!file) return MU_HELP_BAD_ARGUMENT;
    if (size < MU_HELP_FILE_SIZE) return MU_HELP_TRUNCATED;
    uint8_t *image = malloc(MU_HELP_FILE_SIZE);
    if (!image) return MU_HELP_NO_MEMORY;
    memcpy(image, file, MU_HELP_FILE_SIZE);
    mu_data_result result;
    mu_data_status status = mu_data_decode(mu_data_find("helpdata.bmd"), image,
                                          MU_HELP_FILE_SIZE, NULL, NULL, &result);
    if (status == MU_DATA_OK) memcpy(out->rows, image, MU_HELP_PAYLOAD_SIZE);
    free(image);
    return status == MU_DATA_OK ? MU_HELP_OK : MU_HELP_CORRUPTED;
}

mu_help_status mu_help_read(mu_help_table *out, const char *path)
{
    if (!out) return MU_HELP_BAD_ARGUMENT;
    memset(out, 0, sizeof *out);
    if (!path) return MU_HELP_BAD_ARGUMENT;
    FILE *f = fopen(path, "rb");
    if (!f) return errno == ENOENT ? MU_HELP_MISSING : MU_HELP_IO_ERROR;
    uint8_t *image = malloc(MU_HELP_FILE_SIZE);
    if (!image) { fclose(f); return MU_HELP_NO_MEMORY; }
    size_t n = fread(image, 1, MU_HELP_FILE_SIZE, f);
    int failed = ferror(f);
    if (fclose(f)) failed = 1;
    mu_help_status status = failed ? MU_HELP_IO_ERROR : mu_help_decode(out, image, n);
    free(image);
    return status;
}

const char *mu_help_status_name(mu_help_status status)
{
    static const char *const names[] = {
        "ok", "missing", "truncated", "corrupted", "io-error", "no-memory", "bad-argument"
    };
    return (unsigned)status < sizeof names / sizeof names[0] ? names[status] : "unknown";
}
