/* langread <pid> <out.bin>: read-only snapshot of the tables main.exe builds from Data\Lang.mpr (NATIVE-LANG-001,
   docs/research/client-lang-tables.md). macOS host tool: build with `make -C mac-play/diagnostics langread`
   (ad-hoc signed with the debugger entitlement so task_for_pid works on a Wine process the user started). Point it
   at the main.exe process of a client you started yourself, under the game lock, once the client shows its server
   list (the tables are filled before it). The snapshot holds decoded game text and stays local
   (scripts/live_lang_to_plain.py turns it into plaintext tables).

   What it reads, all through mach_vm_read_overwrite (never writes, never suspends):
   - the script-table manager 0x06fbaa60..0x06fbcd80 in the image's uninitialised data. Its tables were located
     through main.exe's own consumers: GlobalText 0x0095f027 uses this+0xe8 (0x06fbab48), the skill lookup
     0x00961620 uses this+0x6d8 (0x06fbb138), the EnchantEffect lookups 0x010ffd25.. use this+0xcf4, and the
     startup routine 0x0115eceb passes each table and its script name to the table loader;
   - every MSVC std::map inside that range (head pointer, size; a head node whose _Isnil byte +0xd is 1): the
     tree is walked through _Left +0 / _Right +8 and each node's bytes are copied (header 0x10, then the value);
   - buffers the copied bytes point to, by shape: an MSVC std::string (pointer at +0, size +0x10, capacity +0x14,
     capacity >= 16) gives its characters; a std::vector (begin <= end <= capacity end) gives its elements, and
     element buffers are scanned the same way once more.
   Output: "MULANGV1", u32 block count, then blocks of (u32 address, u32 size, bytes). */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MANAGER 0x06fbaa60u
#define MANAGER_END 0x06fbcd80u
#define NODE_MAX 0x400u
#define TOTAL_MAX (256u << 20)
#define CHASE_MAX 0x10000u

/* Table objects inside the manager: the offsets the startup routine 0x0115eceb hands to the table loader with a
   script name (Text(kor) +0xe8, Skill(Kor) +0x6d8, Gate +0x14c, Npcname(kor) +0xc04, EnchantEffect +0xcf4,
   movereq(kor) +0xdec, ...). A table spans up to the next offset. */
static const uint32_t TABLES[] = {
    0x0, 0x60, 0xa0, 0xe8, 0x14c, 0x1c0, 0x228, 0x270, 0x2b8, 0x3a0, 0x3ec, 0x49c, 0x538, 0x5a0, 0x608, 0x668,
    0x6d8, 0x7e8, 0x844, 0x8d0, 0x970, 0x9b4, 0xa0c, 0xa4c, 0xb00, 0xb7c, 0xbc4, 0xc04, 0xc70, 0xcf4, 0xd9c,
    0xdec, 0xe8c, 0xed0, 0xf50, 0xfe4, 0x1044, 0x108c, 0x10d8, 0x1148, 0x11f0, 0x1260, 0x12b8, 0x133c, 0x137c,
    0x13bc, 0x1410, 0x1450, 0x14c4, 0x151c, 0x156c, 0x15ac, 0x163c, 0x169c, 0x1700, 0x17e0, 0x1968, 0x1a1c,
    0x1a64, 0x1ac4, 0x1ca4, 0x1d10, 0x1d50, 0x1d90, 0x1dd0, 0x1e10, 0x1e5c, 0x1f84, 0x1fc8, 0x2040, 0x20b0,
    0x2148, 0x21a8, 0x222c, MANAGER_END - MANAGER};

static task_t task;
static FILE *out;
static uint32_t blocks, total;

/* Start addresses already copied (open addressing). */
#define SEEN_BITS 22
static uint32_t *seen;

static int rd(uint32_t a, void *dst, uint32_t n)
{
    mach_vm_size_t got = 0;
    return mach_vm_read_overwrite(task, a, n, (mach_vm_address_t)dst, &got) == KERN_SUCCESS && got == n ? 0 : -1;
}

static int mark(uint32_t a)   /* 1 when a was new */
{
    uint32_t mask = (1u << SEEN_BITS) - 1, h = (a * 2654435761u) & mask;
    while (seen[h]) {
        if (seen[h] == a)
            return 0;
        h = (h + 1) & mask;
    }
    seen[h] = a;
    return 1;
}

/* Copy [a, a+n) into the snapshot (shortened to what is readable); returns the bytes or NULL. */
static uint8_t *copy_block(uint32_t a, uint32_t *n, int force)
{
    if (!*n || total + *n > TOTAL_MAX || (!mark(a) && !force))
        return NULL;
    uint8_t *b = malloc(*n);
    if (!b)
        return NULL;
    while (*n >= 4 && rd(a, b, *n))
        *n /= 2;
    if (*n < 4) { free(b); return NULL; }
    fwrite(&a, 4, 1, out); fwrite(n, 4, 1, out); fwrite(b, 1, *n, out);
    ++blocks; total += *n;
    return b;
}

static uint32_t u32(const uint8_t *b, uint32_t o) { uint32_t v; memcpy(&v, b + o, 4); return v; }

/* Follow std::string and std::vector shapes inside a copied buffer. */
static void chase(const uint8_t *b, uint32_t n, int depth)
{
    for (uint32_t o = 0; o + 12 <= n; o += 4) {
        uint32_t p = u32(b, o);
        if (p < 0x10000)
            continue;
        if (o + 0x18 <= n) {
            uint32_t size = u32(b, o + 0x10), cap = u32(b, o + 0x14);
            if (cap >= 0x10 && cap < CHASE_MAX && size <= cap) {
                uint32_t len = size + 1;
                free(copy_block(p, &len, 0));
                continue;
            }
        }
        uint32_t e = u32(b, o + 4), c = u32(b, o + 8);
        if ((p & 3) == 0 && p <= e && e <= c && c > p && c - p <= CHASE_MAX && ((e - p) & 3) == 0) {
            uint32_t len = c - p;
            uint8_t *v = copy_block(p, &len, 0);
            if (v && depth > 0)
                chase(v, len, depth - 1);
            free(v);
        }
    }
}

/* Walk one std::map: _Left +0, _Parent +4, _Right +8, _Isnil +0xd, value from +0x10. */
static uint32_t walk(uint32_t head, uint32_t count, uint32_t node_bytes)
{
    uint32_t root, copied = 0;
    if (rd(head + 4, &root, 4))
        return 0;
    uint32_t *stack = malloc(sizeof(uint32_t) * 4096);
    size_t sp = 0;
    if (root != head)
        stack[sp++] = root;
    for (uint32_t visits = 0; sp && visits <= count; ++visits) {
        uint32_t node = stack[--sp];
        uint8_t hdr[0x10];
        if (rd(node, hdr, sizeof hdr) || hdr[0xd])
            continue;
        uint32_t left = u32(hdr, 0), right = u32(hdr, 8), len = node_bytes;
        uint8_t *b = copy_block(node, &len, 1);   /* nodes always: a chase may have copied a shorter block here */
        if (b) {
            ++copied;
            if (len > 0x10)
                chase(b + 0x10, len - 0x10, 1);
            free(b);
        }
        if (right != head && sp < 4096) stack[sp++] = right;
        if (left != head && sp < 4096) stack[sp++] = left;
    }
    free(stack);
    return copied;
}

int main(int c, char **v)
{
    if (c < 3) { fprintf(stderr, "usage: langread pid out.bin\n"); return 2; }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &task)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    static uint8_t mgr[MANAGER_END - MANAGER];
    if (rd(MANAGER, mgr, sizeof mgr)) { fprintf(stderr, "manager unreadable\n"); return 1; }
    seen = calloc(1u << SEEN_BITS, sizeof *seen);
    out = fopen(v[2], "wb");
    if (!out || !seen) return 1;
    fwrite("MULANGV1", 1, 8, out);
    long count_pos = ftell(out);
    fwrite(&blocks, 4, 1, out);
    uint32_t n = sizeof mgr;
    free(copy_block(MANAGER, &n, 1));
    chase(mgr, sizeof mgr, 1);
    uint32_t maps = 0, nodes = 0;
    for (size_t t = 0; t + 1 < sizeof TABLES / sizeof TABLES[0]; ++t) {
        uint32_t span = TABLES[t + 1] - TABLES[t];
        uint32_t node_bytes = (0x14 + span + 3) & ~3u;
        if (node_bytes > NODE_MAX)
            node_bytes = NODE_MAX;
        for (uint32_t o = TABLES[t]; o + 8 <= TABLES[t + 1]; o += 4) {
            uint32_t head = u32(mgr, o), count = u32(mgr, o + 4);
            uint8_t hn[0x10];
            if (head < 0x10000 || count > 1000000 || rd(head, hn, sizeof hn) || hn[0xd] != 1)
                continue;
            if (u32(hn, 0) == 0 || u32(hn, 4) == 0 || u32(hn, 8) == 0)
                continue;
            uint32_t len = 0x10;
            free(copy_block(head, &len, 1));
            uint32_t got = walk(head, count, node_bytes);
            printf("map %08x (table +0x%x, +0x%x) count %u copied %u\n", MANAGER + o, TABLES[t], o - TABLES[t],
                   count, got);
            ++maps; nodes += got;
        }
    }
    fseek(out, count_pos, SEEK_SET);
    fwrite(&blocks, 4, 1, out);
    fclose(out);
    printf("maps %u nodes %u blocks %u bytes %u -> %s\n", maps, nodes, blocks, total, v[2]);
    return 0;
}
