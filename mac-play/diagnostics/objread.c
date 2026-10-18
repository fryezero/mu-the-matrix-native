/* objread <pid> <out.bin>: read-only snapshot of main.exe's static-object list (NATIVE-OBJECTS-001 live read,
   docs/research/client-objects.md section 6). macOS host tool: build with `make -C mac-play/diagnostics objread`
   (ad-hoc signed with the debugger entitlement so task_for_pid works on a Wine process the user started).
   Point it at the main.exe process of a client you started yourself, under the game lock; the snapshot holds
   decoded game data and stays local (scripts/live_objects_to_plain.py turns it into an EncTerrain plaintext).
   Reads plain game memory through mach_vm_read_overwrite: the world index [0x01cf15fc], the .obj count global
   [0x0bdb5888] and the 256 sector lists at 0x0bdb61f0 (head +4, tail +8; objects linked through +0x354), each
   object's 0x3d8 bytes. Never writes, never suspends. */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static task_t t;
static int rd(uint32_t a, void *out, size_t n) {
    mach_vm_size_t got = 0;
    return mach_vm_read_overwrite(t, a, n, (mach_vm_address_t)out, &got) == KERN_SUCCESS && got == n ? 0 : -1;
}
int main(int c, char **v) {
    if (c < 3) { fprintf(stderr, "usage: objread pid out.bin\n"); return 2; }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &t)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    int32_t world = -1, world2 = -1, count = 0;
    if (rd(0x01cf15fc, &world, 4) || rd(0x01cf1600, &world2, 4) || rd(0x0bdb5888, &count, 4)) {
        fprintf(stderr, "globals unreadable\n"); return 1;
    }
    uint8_t sectors[256 * 16];
    if (rd(0x0bdb61f0, sectors, sizeof sectors)) { fprintf(stderr, "sector table unreadable\n"); return 1; }
    FILE *f = fopen(v[2], "wb");
    if (!f) return 1;
    uint32_t total = 0;
    fwrite("MUOBJLV1", 1, 8, f);
    fwrite(&world, 4, 1, f); fwrite(&world2, 4, 1, f); fwrite(&count, 4, 1, f);
    long count_pos = ftell(f); fwrite(&total, 4, 1, f);
    static uint8_t obj[0x3d8];
    for (uint32_t s = 0; s < 256; ++s) {
        uint32_t p; memcpy(&p, sectors + 16 * s + 4, 4);
        for (int guard = 0; p && guard < 100000; ++guard) {
            if (rd(p, obj, sizeof obj)) { fprintf(stderr, "object %08x unreadable\n", p); break; }
            fwrite(&p, 4, 1, f); fwrite(&s, 4, 1, f); fwrite(obj, 1, sizeof obj, f);
            ++total;
            memcpy(&p, obj + 0x354, 4);
        }
    }
    fseek(f, count_pos, SEEK_SET); fwrite(&total, 4, 1, f); fclose(f);
    printf("world %d (%d) obj-count %d objects-in-sectors %u -> %s\n", world, world2, count, total, v[2]);
    return 0;
}
