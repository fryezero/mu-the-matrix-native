#include "decoder.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "Usage: recover-block INPUT OFFSET NEW_OUTPUT\n");
        return 2;
    }
    char *end;
    errno = 0;
    unsigned long offset = strtoul(argv[2], &end, 0);
    if (errno || *end || end == argv[2]) return 2;
    FILE *input = fopen(argv[1], "rb");
    if (!input) { perror("input"); return 1; }
    if (fseek(input, 0, SEEK_END)) { fclose(input); return 1; }
    long length = ftell(input);
    if (length < 0 || length > 128 * 1024 * 1024 || offset >= (unsigned long)length) {
        fclose(input); return 1;
    }
    rewind(input);
    uint8_t *source = malloc((size_t)length);
    const size_t capacity = 0x280a000;
    uint8_t *output = malloc(capacity);
    if (!source || !output) { free(source); free(output); fclose(input); return 1; }
    size_t read = fread(source, 1, (size_t)length, input);
    int close_error = fclose(input);
    size_t consumed, written;
    if (read != (size_t)length || close_error ||
        mu_decode_block(source + offset, (size_t)length - offset, output, capacity,
                        &consumed, &written)) {
        fprintf(stderr, "Invalid or incomplete compressed block\n");
        free(source); free(output); return 1;
    }
    FILE *destination = fopen(argv[3], "wbx");
    if (!destination) { perror("new output"); free(source); free(output); return 1; }
    size_t saved = fwrite(output, 1, written, destination);
    close_error = fclose(destination);
    free(source); free(output);
    if (saved != written || close_error) return 1;
    printf("{\"compressed_bytes\":%zu,\"decoded_bytes\":%zu}\n", consumed, written);
    return 0;
}
