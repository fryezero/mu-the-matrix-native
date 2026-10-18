/* memread <pid> <out-prefix> <address:size>...: read-only copy of fixed ranges of main.exe's static data
   (NATIVE-PATH-002 live read, docs/research/client-path.md "Neighbour table"). macOS host tool: build with
   `make -C mac-play/diagnostics memread` (ad-hoc signed with the debugger entitlement so task_for_pid works on
   a Wine process the user started). Point it at the main.exe process of a client you started yourself, under
   the game lock. Each range goes to <out-prefix>-<address>.bin (hex address, 8 digits); the copies hold client
   bytes and stay local. Reads plain game memory through mach_vm_read_overwrite: never writes, never suspends,
   and only reads the ranges named on the command line. */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
int main(int c, char **v) {
    if (c < 4) { fprintf(stderr, "usage: memread pid out-prefix address:size...\n"); return 2; }
    task_t t;
    if (task_for_pid(mach_task_self(), atoi(v[1]), &t)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    int failures = 0;
    for (int i = 3; i < c; ++i) {
        char *colon = NULL;
        unsigned long address = strtoul(v[i], &colon, 0), size = colon && *colon == ':' ? strtoul(colon + 1, NULL, 0) : 0;
        if (!size || size > (64u << 20)) { fprintf(stderr, "bad range %s\n", v[i]); ++failures; continue; }
        uint8_t *bytes = malloc(size);
        mach_vm_size_t got = 0;
        if (!bytes || mach_vm_read_overwrite(t, address, size, (mach_vm_address_t)bytes, &got) != KERN_SUCCESS || got != size) {
            fprintf(stderr, "range %08lx+%lx unreadable\n", address, size);
            free(bytes); ++failures; continue;
        }
        char path[4096];
        snprintf(path, sizeof path, "%s-%08lx.bin", v[2], address);
        FILE *f = fopen(path, "wb");
        if (!f || fwrite(bytes, 1, size, f) != size) { fprintf(stderr, "%s: write failed\n", path); ++failures; }
        if (f) fclose(f);
        free(bytes);
        printf("%08lx %lu -> %s\n", address, size, path);
    }
    return failures ? 1 : 0;
}
