/* Read-only local comparison tool. No process attachment or network activity.
 * Supply your own pinned text capture. No captured instructions are embedded.
 */
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "client_lea.h"

#define TEXT_BYTES 23572480u
#define TEXT_BASE 0x401000u
#define WINDOW_BASE 0x927000u
#define WINDOW_BYTES 0x16000u
#define ARENA_BYTES 8192u
#define TEXT_SHA "2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724"

typedef void (__cdecl *decoder_fn)(void *, const void *, uint32_t, const void *);
typedef struct {
    uint32_t ebx, esi, edi, ebp, flags, after_esp, before_esp, runner_frame;
} abi_result;
extern void mu_lea_call_checked(decoder_fn function, void *destination,
                                const void *source, uint32_t length,
                                const void *context, uint32_t direction,
                                abi_result *result);

extern void mu_lea_bad_callee(void *, const void *, uint32_t, const void *);

static int hash_hex(const void *bytes, ULONG count, char output[65]) {
    BCRYPT_ALG_HANDLE algorithm = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char digest[32];
    int ok = BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL, 0) == 0;
    if (ok) ok = BCryptCreateHash(algorithm, &hash, NULL, 0, NULL, 0, 0) == 0;
    if (ok) ok = BCryptHashData(hash, (PUCHAR)bytes, count, 0) == 0;
    if (ok) ok = BCryptFinishHash(hash, digest, 32, 0) == 0;
    if (hash != NULL) BCryptDestroyHash(hash);
    if (algorithm != NULL) BCryptCloseAlgorithmProvider(algorithm, 0);
    if (!ok) return 0;
    for (unsigned index = 0; index < 32; ++index)
        (void)sprintf(output+2u*index, "%02x", digest[index]);
    output[64] = 0;
    return 1;
}

static int protection(void *address, SIZE_T count, DWORD flags) {
    DWORD previous;
    return VirtualProtect(address, count, flags, &previous) != 0;
}

static decoder_fn load_decoder(const char *filename) {
    FILE *source = fopen(filename, "rb");
    if (source == NULL) return NULL;
    unsigned char *text = malloc(TEXT_BYTES);
    if (text == NULL) { fclose(source); return NULL; }
    const size_t count = fread(text, 1, TEXT_BYTES, source);
    const int extra = fgetc(source), read_error = ferror(source);
    fclose(source);
    char digest[65];
    if (count != TEXT_BYTES || extra != EOF || read_error ||
        !hash_hex(text, TEXT_BYTES, digest) || strcmp(digest, TEXT_SHA) != 0) {
        free(text);
        fprintf(stderr, "Input does not match pinned restored text.\n");
        return NULL;
    }
    /* Relative control flow relocates together. Static checks establish no
     * absolute memory operands and only selected internal CALL targets.
     * Only pages intersecting the four pinned bodies become executable.
     */
    unsigned char *window = VirtualAlloc(NULL, WINDOW_BYTES, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
    if (window == NULL) { free(text); return NULL; }
    static const uint32_t bodies[][2] = {
        {0x927060u, 4677u}, {0x929370u, 4288u},
        {0x92be30u, 198u}, {0x93bb20u, 1798u}
    };
    for (unsigned index = 0; index < 4; ++index)
        memcpy(window+bodies[index][0]-WINDOW_BASE,
               text+bodies[index][0]-TEXT_BASE, bodies[index][1]);
    free(text);
    if (!protection(window, WINDOW_BYTES, PAGE_NOACCESS)) return NULL;
    for (unsigned index = 0; index < 4; ++index) {
        const uint32_t start = (bodies[index][0]-WINDOW_BASE) & ~4095u;
        const uint32_t end = (bodies[index][0]-WINDOW_BASE+bodies[index][1]+4095u) & ~4095u;
        if (!protection(window+start, end-start, PAGE_EXECUTE_READ)) return NULL;
    }
    if (!FlushInstructionCache(GetCurrentProcess(), window, WINDOW_BYTES)) return NULL;
    return (decoder_fn)(window+0x92be30u-WINDOW_BASE);
}

static int abi_matches(const abi_result *result, uint32_t direction) {
    return result->ebx == 0x12345678u && result->esi == 0x23456789u &&
           result->edi == 0x3456789au && result->ebp == 0x456789abu &&
           result->before_esp == result->after_esp && ((result->flags >> 10) & 1u) == direction;
}

static int check_call(decoder_fn function, void *output, const void *input,
                      uint32_t length, const void *context, uint32_t direction) {
    abi_result result = {0};
    mu_lea_call_checked(function, output, input, length, context, direction, &result);
    return abi_matches(&result, direction);
}

int main(int argc, char **argv) {
    if (argc != 2 || sizeof(void *) != 4) {
        fprintf(stderr, "Usage: lea-compare.exe PINNED-RESTORED-TEXT\n");
        return 2;
    }
    if (check_call(mu_lea_bad_callee, NULL, NULL, 0, NULL, 0)) {
        fprintf(stderr, "ABI bridge failed its authored negative control.\n");
        return 2;
    }
    decoder_fn original = load_decoder(argv[1]);
    if (original == NULL) return 2;
    /* Arena guard pages catch accesses outside the complete comparison arena.
     * Full-byte comparison catches writes outside each selected output span.
     * This is not an instruction memory-read trace inside the accessible arena.
     */
    unsigned char *allocation = VirtualAlloc(NULL, ARENA_BYTES+8192u, MEM_COMMIT|MEM_RESERVE, PAGE_NOACCESS);
    unsigned char *context_page = VirtualAlloc(NULL, 4096, MEM_COMMIT|MEM_RESERVE, PAGE_READWRITE);
    if (allocation == NULL || context_page == NULL ||
        !protection(allocation+4096, ARENA_BYTES, PAGE_READWRITE)) return 2;
    unsigned char *actual = allocation+4096;
    unsigned char initial[ARENA_BYTES], expected[ARENA_BYTES], wrong[ARENA_BYTES];
    static const uint32_t lengths[] = {16,32,48,64,80,112,128,144,192,208,240,256,272,384,512};
    static const int displacements[] = {-257,-129,-65,-17,-1,0,1,15,16,63,127,2048};
    uint32_t cases = 0, mismatches = 0, abi_failures = 0, wrong_differences = 0, noop_cases = 0;
    unsigned char key[32];
    for (unsigned pattern = 0; pattern < 3; ++pattern) {
        for (unsigned index = 0; index < 32; ++index)
            key[index] = pattern == 0 ? 0 : pattern == 1 ? (uint8_t)index : (uint8_t)(index*73u+19u);
        for (int32_t key_size = 16; key_size <= 32; key_size += 8) {
            for (unsigned alignment = 0; alignment < 4; ++alignment) {
                if (!protection(context_page, 4096, PAGE_READWRITE)) return 2;
                memset(context_page, 0xa5, 4096);
                unsigned char *context = context_page+128+alignment;
                mu_client_lea_setup(context, key, key_size);
                if (!protection(context_page, 4096, PAGE_READONLY)) return 2;
                for (unsigned li = 0; li < sizeof(lengths)/sizeof(lengths[0]); ++li) {
                    const uint32_t length = lengths[li];
                    for (unsigned di = 0; di < sizeof(displacements)/sizeof(displacements[0]); ++di) {
                        const unsigned source = 2048u+alignment;
                        const unsigned target = (unsigned)((int)source+displacements[di]);
                        for (uint32_t direction = 0; direction < 2; ++direction) {
                            for (unsigned index = 0; index < ARENA_BYTES; ++index)
                                initial[index] = (uint8_t)((index*29u+(index >> 4)+pattern*61u) & 255u);
                            memcpy(actual, initial, ARENA_BYTES);
                            memcpy(expected, initial, ARENA_BYTES);
                            mu_client_lea_decode(expected+target, expected+source, length, context);
                            const int abi_ok = check_call(original, actual+target, actual+source, length, context, direction);
                            ++cases;
                            if (!abi_ok) ++abi_failures;
                            if (memcmp(actual, expected, ARENA_BYTES) != 0) ++mismatches;
                            memcpy(wrong, initial, ARENA_BYTES);
                            for (uint32_t offset = 0; offset < length; offset += 16)
                                mu_client_lea_decode(wrong+target+offset, wrong+source+offset, 16, context);
                            if (memcmp(actual, wrong, ARENA_BYTES) != 0) ++wrong_differences;
                        }
                    }
                }
            }
        }
    }
    /* Intentionally unmapped pointer 1 exposes premature reads at the gates. */
    static const uint32_t invalid_lengths[] = {0,1,15,16,17,0xffffffffu};
    for (unsigned index = 0; index < sizeof(invalid_lengths)/sizeof(invalid_lengths[0]); ++index) {
        const uint32_t length = invalid_lengths[index];
        for (uint32_t direction = 0; direction < 2; ++direction) {
            abi_failures += (uint32_t)!check_call(original, (void *)1, (void *)1, length, NULL, direction);
            abi_failures += (uint32_t)!check_call(original, NULL, (void *)1, length, (void *)1, direction);
            abi_failures += (uint32_t)!check_call(original, (void *)1, NULL, length, (void *)1, direction);
            noop_cases += 3;
            if (length == 0 || (length & 15u) != 0) {
                abi_failures += (uint32_t)!check_call(original, (void *)1, (void *)1, length, (void *)1, direction);
                ++noop_cases;
            }
        }
    }
    printf("{\"format\":\"mu-client-lea-guest-comparison-v1\",\"text_sha256\":\"%s\","
           "\"valid_cases\":%lu,\"noop_cases\":%lu,\"mismatches\":%lu,"
           "\"abi_failures\":%lu,\"wrong_scalar_batch_differences\":%lu,"
           "\"pointer_bits\":32,\"relocated_original_code\":true,"
           "\"memory_read_trace\":false,\"abi_negative_control_rejected\":true}\n", TEXT_SHA, (unsigned long)cases,
           (unsigned long)noop_cases, (unsigned long)mismatches, (unsigned long)abi_failures,
           (unsigned long)wrong_differences);
    return mismatches != 0 || abi_failures != 0 || wrong_differences == 0 ? 1 : 0;
}
