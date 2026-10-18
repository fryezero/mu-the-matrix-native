/* lightread <pid> <out.bin>: read-only snapshot of the lighting inputs of main.exe's model draws (NATIVE-LIGHT-001,
   docs/research/client-model-light.md). macOS host tool: build with `make -C mac-play/diagnostics lightread`
   (ad-hoc signed with the debugger entitlement so task_for_pid works on a Wine process the user started). Point it
   at the main.exe process of a client you started yourself, under the game lock; the snapshot holds game memory and
   stays local. Reads plain game memory through mach_vm_read_overwrite; never writes, never suspends.

   Contents ("MULITLV1", then tagged sections: u32 tag, u32 byte count, bytes):
     'GLOB': (u32 address, u32 size, bytes) for the globals below;
     'MODL': the model container [0x01d1dbec] (getter 0x00966cc4): its std::map<int, BMD *> at +4 walked in order
             (node: left +0, parent +4, right +8, isnil byte +0xd, key +0x10, value +0x14), per model
             (i32 key, u32 address, 0xd0 bytes of the BMD object: +0x50 lighting, +0x54 body light, +0x74 scale,
             +0x84 angle, +0x94 StreamMesh byte, +0x98 shadow angle, +0xcb secondary light byte);
     'CHAR': the live entries of CharactersClient ([[0x01d1dbbc] + 8] + i * 0x3670, 400 entries, OBJECT at +0x3254,
             live byte OBJECT +0), per entry (u32 index, 0x3670 bytes);
     'LITE': the primary and frame terrain light grids 0x0bab5430 / 0x0b9f5430 (256 * 256 * 3 binary32 each). */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static task_t t;
static int rd(uint32_t a, void *out, size_t n)
{
    mach_vm_size_t got = 0;
    return mach_vm_read_overwrite(t, a, n, (mach_vm_address_t)out, &got) == KERN_SUCCESS && got == n ? 0 : -1;
}
static uint32_t rd32(uint32_t a)
{
    uint32_t v = 0;
    return rd(a, &v, 4) ? 0 : v;
}
static void section(FILE *f, const char tag[4], const void *data, uint32_t size)
{
    fwrite(tag, 1, 4, f);
    fwrite(&size, 4, 1, f);
    fwrite(data, 1, size, f);
}

static const uint32_t globals[][2] = {
    {0x01cf15fc, 4}, {0x01cf1600, 4}, {0x01d1df70, 4}, {0x01cf1048, 4}, {0x01cf104c, 4}, {0x0b437bfc, 4},
    {0x06fce370, 4}, {0x0a39d754, 4}, {0x0bdc58f0, 12}, {0x0bdc5ab4, 12}, {0x01cf1634, 4}, {0x01cf1630, 4},
    {0x0bdc597c, 4}, {0x01d1dbec, 4}, {0x01d1dbbc, 4},
};

int main(int c, char **v)
{
    if (c < 3) {
        fprintf(stderr, "usage: lightread pid out.bin\n");
        return 2;
    }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &t)) {
        fprintf(stderr, "task_for_pid failed\n");
        return 1;
    }
    FILE *f = fopen(v[2], "wb");
    if (!f)
        return 1;
    fwrite("MULITLV1", 1, 8, f);

    static uint8_t buffer[1 << 20];
    uint32_t used = 0;
    for (size_t i = 0; i < sizeof globals / sizeof globals[0]; ++i) {
        memcpy(buffer + used, globals[i], 8);
        if (rd(globals[i][0], buffer + used + 8, globals[i][1]))
            memset(buffer + used + 8, 0xee, globals[i][1]);
        used += 8 + globals[i][1];
    }
    section(f, "GLOB", buffer, used);

    /* models: in-order walk of the container's map */
    uint32_t models = 0;
    used = 0;
    const uint32_t container = rd32(0x01d1dbec);
    const uint32_t head = container ? rd32(container + 4) : 0;
    if (head) {
        uint32_t node = rd32(head);   /* leftmost */
        for (int guard = 0; node && node != head && guard < 100000 && used + 8 + 0xd0 <= sizeof buffer; ++guard) {
            uint8_t isnil = 1;
            if (rd(node + 0xd, &isnil, 1) || isnil)
                break;
            const uint32_t key = rd32(node + 0x10), bmd = rd32(node + 0x14);
            memcpy(buffer + used, &key, 4);
            memcpy(buffer + used + 4, &bmd, 4);
            if (!bmd || rd(bmd, buffer + used + 8, 0xd0))
                memset(buffer + used + 8, 0xee, 0xd0);
            used += 8 + 0xd0;
            ++models;
            /* successor */
            uint32_t right = rd32(node + 8);
            uint8_t rnil = 1;
            if (right && !rd(right + 0xd, &rnil, 1) && !rnil) {
                node = right;
                for (int g = 0; g < 64; ++g) {
                    uint32_t left = rd32(node);
                    uint8_t lnil = 1;
                    if (!left || rd(left + 0xd, &lnil, 1) || lnil)
                        break;
                    node = left;
                }
            } else {
                uint32_t parent = rd32(node + 4);
                for (int g = 0; g < 64; ++g) {
                    uint8_t pnil = 1;
                    if (!parent || rd(parent + 0xd, &pnil, 1) || pnil || node != rd32(parent + 8))
                        break;
                    node = parent;
                    parent = rd32(node + 4);
                }
                node = parent;
            }
        }
    }
    section(f, "MODL", buffer, used);

    /* live characters */
    uint32_t characters = 0;
    const uint32_t manager = rd32(0x01d1dbbc);
    const uint32_t table = manager ? rd32(manager + 8) : 0;
    static uint8_t record[0x3670];
    long start = ftell(f);
    uint32_t size = 0;
    fwrite("CHAR", 1, 4, f);
    fwrite(&size, 4, 1, f);
    for (uint32_t i = 0; table && i < 400; ++i) {
        if (rd(table + i * 0x3670u, record, sizeof record) || !record[0x3254])
            continue;
        fwrite(&i, 4, 1, f);
        fwrite(record, 1, sizeof record, f);
        size += 4 + (uint32_t)sizeof record;
        ++characters;
    }
    long end = ftell(f);
    fseek(f, start + 4, SEEK_SET);
    fwrite(&size, 4, 1, f);
    fseek(f, end, SEEK_SET);

    static float grid[256 * 256 * 3];
    const uint32_t grids[2] = {0x0bab5430, 0x0b9f5430};
    for (int g = 0; g < 2; ++g) {
        if (rd(grids[g], grid, sizeof grid))
            memset(grid, 0xee, sizeof grid);
        section(f, "LITE", grid, (uint32_t)sizeof grid);
    }
    fclose(f);
    printf("container %08x models %u characters %u -> %s\n", container, models, characters, v[2]);
    return 0;
}
