/* objread <pid> <out.bin>: read-only snapshot of main.exe's static-object list (NATIVE-OBJECTS-001 live read,
   docs/research/client-objects.md section 6). macOS host tool: build with `make -C live-readers objread`
   (ad-hoc signed with the debugger entitlement so task_for_pid works on a Wine process the user started).
   Point it at the main.exe process of a client you started yourself, under the game lock; the snapshot holds
   decoded game data and stays local (scripts/live_objects_to_plain.py turns it into an EncTerrain plaintext).
   Reads plain game memory through mach_vm_read_overwrite: the world index [0x01cf15fc], the .obj count global
   [0x0bdb5888] and the 256 sector lists at 0x0bdb61f0 (head +4, tail +8; objects linked through +0x354), each
   object's 0x3d8 bytes. Never writes, never suspends.
   objread <pid> <out.bin> <globals.bin> (NATIVE-LOGIN-001) also copies a fixed list of scene globals (camera
   angle 0x0bdc58f0, camera position 0x0bdc5ab4, CameraFOV 0x01cf1634, the far plane 0x01cf1630, SceneFlag
   0x01d1df70, WorldTime 0x06fce370, the login overlay fade 0x0bdc5b80) as "MUGLBLV1" + (address, size, bytes)
   entries. */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "build/layout_reader.h"
static task_t t;
static int rd(uint32_t a, void *out, size_t n) {
    mach_vm_size_t got = 0;
    return mach_vm_read_overwrite(t, a, n, (mach_vm_address_t)out, &got) == KERN_SUCCESS && got == n ? 0 : -1;
}
int main(int c, char **v) {
    if (c < 3) { fprintf(stderr, "usage: objread pid out.bin [globals.bin]\n"); return 2; }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &t)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    int32_t world = -1, world2 = -1, count = 0;
    if (rd(MU_READER_SceneWorld, &world, 4) || rd(MU_READER_SceneWorld2, &world2, 4) || rd(0x0bdb5888, &count, 4)) {
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
    static uint8_t obj[MU_READER_OBJECT_SIZE];
    for (uint32_t s = 0; s < 256; ++s) {
        uint32_t p; memcpy(&p, sectors + 16 * s + 4, 4);
        for (int guard = 0; p && guard < 100000; ++guard) {
            if (rd(p, obj, sizeof obj)) { fprintf(stderr, "object %08x unreadable\n", p); break; }
            fwrite(&p, 4, 1, f); fwrite(&s, 4, 1, f); fwrite(obj, 1, sizeof obj, f);
            ++total;
            memcpy(&p, obj + MU_READER_OBJECT_NEXT, 4);
        }
    }
    fseek(f, count_pos, SEEK_SET); fwrite(&total, 4, 1, f); fclose(f);
    if (c > 3) {
        FILE *g = fopen(v[3], "wb");
        if (!g) return 1;
        fwrite("MUGLBLV1", 1, 8, g);
        for (size_t i = 0; i < sizeof mu_reader_scene_globals / sizeof mu_reader_scene_globals[0]; ++i) {
            uint8_t bytes[16] = {0};
            if (rd(mu_reader_scene_globals[i][0], bytes, mu_reader_scene_globals[i][1])) { fprintf(stderr, "global %08x unreadable\n", mu_reader_scene_globals[i][0]); continue; }
            fwrite(mu_reader_scene_globals[i], 4, 2, g); fwrite(bytes, 1, mu_reader_scene_globals[i][1], g);
        }
        fclose(g);
    }
    printf("world %d (%d) obj-count %d objects-in-sectors %u -> %s\n", world, world2, count, total, v[2]);
    return 0;
}
