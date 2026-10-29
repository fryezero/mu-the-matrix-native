/* langread <pid> <out.bin>: read-only snapshot of the tables main.exe builds from Data\Lang.mpr (NATIVE-LANG-001,
   docs/research/client-lang-tables.md). macOS host tool: build with `make -C live-readers langread`
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
   Output: "MULANGV1", u32 block count, then blocks of (u32 address, u32 size, bytes).

   Options after the output path (NATIVE-QUEST-001):
   - node:OFF=BYTES   copy BYTES per node for the table at manager offset OFF instead of the table span + 0x14
                      (MUQuest's 0x104-byte records: node:0x137c=0x118);
   - map:PTR+OFF=BYTES[,obj=N]   walk the std::map whose container is at [PTR] + OFF (PTR: a pointer variable of
                      the image, e.g. the quest system singleton 0x01ec2e60), BYTES per node; with obj=N the node
                      value at +0x14 is a pointer to an N-byte object, which is copied, chased for strings and
                      vectors, and scanned for std::map containers that are walked too (0x50 bytes per node);
   - nested:OFF       the table at manager offset OFF has std::map containers inside its records (Skill(Kor)'s
                      +0x64 ranks and +0x6c class map, NATIVE-SKILL-002: nested:0x6d8): every copied node value is
                      scanned for them and they are walked (0x18 bytes per node: std::map<int, int>).

   Options (NATIVE-QUEST-002):
   - deep:ADDR=BYTES,DEPTH   copy [ADDR, ADDR+BYTES) again and follow its strings and vectors DEPTH levels deep,
                      re-reading buffers an earlier pass copied without following them (GuideQuest's chapters ->
                      steps -> the steps' strings and vectors: deep:0x06fbb3d0=0x44,3);
   - ptr:PTR+OFF=BYTES   copy BYTES at [PTR] + OFF (an object behind a pointer variable, e.g. the classic quest
                      manager [0x01d1e71c]: ptr:0x01d1e71c+0=0x30dd0).

   Option (NATIVE-SKILL-003):
   - graph:ADDR=BYTES,DEPTH[,OBJ]   (ADDR may be a pointer path P0/P1/..: [[P0]+P1].., e.g. the SkillTree4th
                      handler [[0x01d22c0c]+0x1f8] is 0x01d22c0c/0x1f8/0) copy [ADDR, ADDR+BYTES) and follow, breadth first and DEPTH levels deep, what
                      it points to: std::map containers (every node, 0x100 bytes each, then the node's value), vectors
                      (the whole buffer), strings, and any other pointer (OBJ bytes there, default 0x200; OBJ 0 follows only maps, vectors and strings). Used for
                      the nested maps of 4ThTreeData (graph:0x06fbb8ec=0x44,8) and the lazily built fifth-tree
                      manager behind the static pointer 0x01d22c04. A pointer is only followed into heap memory
                      (currently read+write; module images are mapped read+execute under this Wine) or into main.exe's
                      uninitialised data 0x01ced000..0x0c000000; each root has a 96 MiB budget. */
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

/* Like chase, but every buffer is read for the recursion even when an earlier pass copied it. */
static void chase_deep(const uint8_t *b, uint32_t n, int depth)
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
            free(copy_block(p, &len, 0));
            if (depth > 0) {
                uint8_t *v = malloc(len);
                if (v && !rd(p, v, len))
                    chase_deep(v, len, depth - 1);
                free(v);
            }
        }
    }
}

static uint32_t walk(uint32_t head, uint32_t count, uint32_t node_bytes, uint32_t obj_bytes);

/* std::map containers (head pointer, size; the head's _Isnil byte set) inside a copied object: walked. */
static void scan_maps_n(const uint8_t *b, uint32_t n, uint32_t node_bytes)
{
    for (uint32_t o = 0; o + 8 <= n; o += 4) {
        uint32_t head = u32(b, o), count = u32(b, o + 4);
        uint8_t hn[0x10];
        if (head < 0x10000 || count > 100000 || rd(head, hn, sizeof hn) || hn[0xd] != 1)
            continue;
        if (u32(hn, 0) == 0 || u32(hn, 4) == 0 || u32(hn, 8) == 0)
            continue;
        uint32_t len = 0x10;
        free(copy_block(head, &len, 1));
        walk(head, count, node_bytes, 0);
    }
}

static void scan_maps(const uint8_t *b, uint32_t n) { scan_maps_n(b, n, 0x50); }

static int nested_walk;   /* the table being walked has maps in its records (nested:OFF) */

/* Walk one std::map: _Left +0, _Parent +4, _Right +8, _Isnil +0xd, value from +0x10. */
static uint32_t walk(uint32_t head, uint32_t count, uint32_t node_bytes, uint32_t obj_bytes)
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
            if (nested_walk && len > 0x14) {
                nested_walk = 0;                   /* one level: the inner maps' nodes are not scanned again */
                scan_maps_n(b + 0x14, len - 0x14, 0x18);
                nested_walk = 1;
            }
            if (obj_bytes && len >= 0x18) {
                uint32_t obj = u32(b, 0x14), olen = obj_bytes;
                uint8_t *ob = obj >= 0x10000 ? copy_block(obj, &olen, 1) : NULL;
                if (ob) {
                    chase(ob, olen, 1);
                    scan_maps(ob, olen);
                    free(ob);
                }
            }
            free(b);
        }
        if (right != head && sp < 4096) stack[sp++] = right;
        if (left != head && sp < 4096) stack[sp++] = left;
    }
    free(stack);
    return copied;
}

/* graph: (NATIVE-SKILL-003) breadth-first pointer closure from one root, bounded by depth and a byte budget. */
#define GRAPH_QUEUE (1u << 20)
#define GRAPH_BUDGET (96u << 20)
#define GRAPH_NODE 0x100u
static uint32_t gq_addr[GRAPH_QUEUE], gq_len[GRAPH_QUEUE];
static uint8_t gq_depth[GRAPH_QUEUE], gq_kind[GRAPH_QUEUE];   /* kind 0 object, 1 map node (value from +0x10) */
static uint32_t gq_head, gq_tail, graph_bytes;
static uint32_t *gseen;

static int gmark(uint32_t a)
{
    uint32_t mask = (1u << SEEN_BITS) - 1, h = (a * 2654435761u) & mask;
    while (gseen[h]) {
        if (gseen[h] == a)
            return 0;
        h = (h + 1) & mask;
    }
    gseen[h] = a;
    return 1;
}

/* One VM region: [lo, hi) and its current protection; 0 when nothing is mapped at or after a. */
static int region_at(uint32_t a, uint32_t *lo, uint32_t *hi, int *prot)
{
    mach_vm_address_t addr = a;
    mach_vm_size_t size = 0;
    vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64;
    mach_port_t object = MACH_PORT_NULL;
    if (mach_vm_region(task, &addr, &size, VM_REGION_BASIC_INFO_64, (vm_region_info_t)&info, &count, &object))
        return 0;
    *lo = (uint32_t)addr; *hi = (uint32_t)(addr + size); *prot = info.protection;
    return 1;
}

/* Follow only into heap memory: a region whose current protection is readable and writable, or main.exe's
   uninitialised data. Under Wine on this Mac every region of the 32-bit space is backed by the Wine reserve file,
   but loaded module images (code and data sections, IGC.dll and RGS.dll included) are mapped read+execute while
   heap allocations are read+write(+execute): no module image is followed. */
static int followable(uint32_t a)
{
    if (a < 0x10000 || (a & 3))
        return 0;
    if (a >= 0x01ced000u && a < 0x0c000000u)
        return 1;
    if (a >= 0x00400000u && a < 0x0c000000u)
        return 0;
    static uint32_t cache_lo, cache_hi;
    static int cache_ok;
    if (a >= cache_lo && a < cache_hi)
        return cache_ok;
    uint32_t lo, hi;
    int prot;
    if (!region_at(a, &lo, &hi, &prot) || lo > a)
        return 0;
    cache_lo = lo; cache_hi = hi;
    cache_ok = (prot & (VM_PROT_READ | VM_PROT_WRITE)) == (VM_PROT_READ | VM_PROT_WRITE);
    return cache_ok;
}

static void gpush(uint32_t a, uint32_t len, int depth, int kind)
{
    if (depth < 0 || gq_tail - gq_head >= GRAPH_QUEUE || !followable(a))
        return;
    if (!gmark(a))
        return;
    uint32_t i = gq_tail++ % GRAPH_QUEUE;
    gq_addr[i] = a; gq_len[i] = len; gq_depth[i] = (uint8_t)depth; gq_kind[i] = (uint8_t)kind;
}

static void graph_scan(const uint8_t *b, uint32_t n, int depth, uint32_t obj_bytes)
{
    for (uint32_t o = 0; o + 4 <= n; o += 4) {
        uint32_t p = u32(b, o);
        if (p < 0x10000)
            continue;
        if (o + 8 <= n) {   /* std::map container: head (_Isnil 1), size */
            uint32_t count = u32(b, o + 4);
            uint8_t hn[0x10];
            if (count <= 100000 && !rd(p, hn, sizeof hn) && hn[0xd] == 1 && u32(hn, 0) && u32(hn, 4) && u32(hn, 8)) {
                uint32_t len = 0x10;
                if (gmark(p))
                    free(copy_block(p, &len, 1));
                /* every node of the tree, in order: walk from the head */
                uint32_t stack[512], sp = 0, root = u32(hn, 4), visits = 0;
                if (root != p)
                    stack[sp++] = root;
                while (sp && visits++ <= count) {
                    uint32_t node = stack[--sp];
                    uint8_t h2[0x10];
                    if (rd(node, h2, sizeof h2) || h2[0xd])
                        continue;
                    gpush(node, GRAPH_NODE, depth - 1, 1);
                    if (u32(h2, 8) != p && sp < 512) stack[sp++] = u32(h2, 8);
                    if (u32(h2, 0) != p && sp < 512) stack[sp++] = u32(h2, 0);
                }
                o += 4;
                continue;
            }
        }
        /* A vector's three words can be followed by bytes that also read as a string's size and capacity
           (RENDER-EFFECTS-008: a map-object effect type node, capacity word 0xbd): a candidate of both shapes is
           followed as both, so it is never copied short. */
        int vector = 0;
        if (o + 12 <= n) {   /* std::vector: begin <= end <= capacity end */
            uint32_t e = u32(b, o + 4), c = u32(b, o + 8);
            vector = (p & 3) == 0 && p <= e && e <= c && c > p && c - p <= CHASE_MAX && ((e - p) & 3) == 0;
            if (vector)
                gpush(p, c - p, depth - 1, 0);
        }
        if (o + 0x18 <= n) {   /* std::string with a heap buffer */
            uint32_t size = u32(b, o + 0x10), cap = u32(b, o + 0x14);
            if (cap >= 0x10 && cap < CHASE_MAX && size <= cap && followable(p)) {
                uint32_t len = size + 1;
                free(copy_block(p, &len, 1));
                o += vector ? 8 : 0x14;
                continue;
            }
        }
        if (vector) {
            o += 8;
            continue;
        }
        if (obj_bytes)
            gpush(p, obj_bytes, depth - 1, 0);
    }
}

static void graph(uint32_t root, uint32_t bytes, int depth, uint32_t obj_bytes)
{
    gq_head = gq_tail = graph_bytes = 0;
    uint8_t *b = malloc(bytes);
    if (!b || rd(root, b, bytes)) { free(b); return; }
    uint32_t len = bytes, objects = 0;
    free(copy_block(root, &len, 1));
    gmark(root);
    graph_scan(b, bytes, depth, obj_bytes);
    free(b);
    while (gq_head < gq_tail && graph_bytes < GRAPH_BUDGET) {
        uint32_t i = gq_head++ % GRAPH_QUEUE, a = gq_addr[i], n = gq_len[i];
        int d = gq_depth[i], kind = gq_kind[i];
        uint8_t *v = malloc(n);
        if (!v)
            break;
        while (n >= 4 && rd(a, v, n))
            n /= 2;
        if (n >= 4) {
            uint32_t got = n;
            free(copy_block(a, &got, 1));
            graph_bytes += n; ++objects;
            if (kind == 1) {   /* map node: links +0/+4/+8 are walked by the container; scan the value */
                if (n > 0x10)
                    graph_scan(v + 0x10, n - 0x10, d, obj_bytes);
            } else {
                graph_scan(v, n, d, obj_bytes);
            }
        }
        free(v);
    }
    printf("graph %08x+0x%x depth %d objects %u bytes %u queued-left %u\n", root, bytes, depth, objects, graph_bytes,
           gq_tail - gq_head);
}

int main(int c, char **v)
{
    if (c < 3) { fprintf(stderr, "usage: langread pid out.bin [node:OFF=BYTES] [map:PTR+OFF=BYTES[,obj=N]] [nested:OFF] "
                             "[deep:ADDR=BYTES,DEPTH] [ptr:PTR+OFF=BYTES] [graph:ADDR=BYTES,DEPTH[,OBJ]]\n"); return 2; }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &task)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    static uint8_t mgr[MANAGER_END - MANAGER];
    if (rd(MANAGER, mgr, sizeof mgr)) { fprintf(stderr, "manager unreadable\n"); return 1; }
    seen = calloc(1u << SEEN_BITS, sizeof *seen);
    gseen = calloc(1u << SEEN_BITS, sizeof *gseen);
    out = fopen(v[2], "wb");
    if (!out || !seen || !gseen) return 1;
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
        for (int a = 3; a < c; ++a) {
            unsigned off = 0, bytes = 0;
            if (sscanf(v[a], "node:%i=%i", &off, &bytes) == 2 && off == TABLES[t])
                node_bytes = (bytes + 3) & ~3u;
        }
        if (node_bytes > NODE_MAX)
            node_bytes = NODE_MAX;
        int nested = 0;
        for (int a = 3; a < c; ++a) {
            unsigned off = 0;
            if (sscanf(v[a], "nested:%i", &off) == 1 && off == TABLES[t])
                nested = 1;
        }
        for (uint32_t o = TABLES[t]; o + 8 <= TABLES[t + 1]; o += 4) {
            uint32_t head = u32(mgr, o), count = u32(mgr, o + 4);
            uint8_t hn[0x10];
            if (head < 0x10000 || count > 1000000 || rd(head, hn, sizeof hn) || hn[0xd] != 1)
                continue;
            if (u32(hn, 0) == 0 || u32(hn, 4) == 0 || u32(hn, 8) == 0)
                continue;
            uint32_t len = 0x10;
            free(copy_block(head, &len, 1));
            nested_walk = nested;
            uint32_t got = walk(head, count, node_bytes, 0);
            nested_walk = 0;
            printf("map %08x (table +0x%x, +0x%x) count %u copied %u\n", MANAGER + o, TABLES[t], o - TABLES[t],
                   count, got);
            ++maps; nodes += got;
        }
    }
    for (int a = 3; a < c; ++a) {
        unsigned ptr = 0, off = 0, bytes = 0, obj = 0;
        int k = sscanf(v[a], "map:%i+%i=%i,obj=%i", &ptr, &off, &bytes, &obj);
        if (k < 3)
            continue;
        uint32_t base = 0, len = 4;
        free(copy_block(ptr, &len, 1));
        if (rd(ptr, &base, 4) || base < 0x10000)
            continue;
        uint8_t cont[8], hn[0x10];
        if (rd(base + off, cont, 8))
            continue;
        uint32_t head = u32(cont, 0), count = u32(cont, 4);
        if (head < 0x10000 || count > 1000000 || rd(head, hn, sizeof hn) || hn[0xd] != 1)
            continue;
        len = off + 8;
        free(copy_block(base, &len, 1));
        len = 0x10;
        free(copy_block(head, &len, 1));
        if (bytes > NODE_MAX)
            bytes = NODE_MAX;
        uint32_t got = walk(head, count, (bytes + 3) & ~3u, k == 4 ? obj : 0);
        printf("map [%08x]+0x%x count %u copied %u\n", ptr, off, count, got);
        ++maps; nodes += got;
    }
    for (int a = 3; a < c; ++a) {
        unsigned addr = 0, bytes = 0, depth = 0, ptr = 0, off = 0;
        if (sscanf(v[a], "deep:%i=%i,%i", &addr, &bytes, &depth) == 3 && bytes && bytes <= CHASE_MAX) {
            uint8_t *b = malloc(bytes);
            if (b && !rd(addr, b, bytes)) {
                uint32_t len = bytes;
                free(copy_block(addr, &len, 1));
                chase_deep(b, bytes, (int)depth);
                printf("deep %08x+0x%x depth %u\n", addr, bytes, depth);
            }
            free(b);
        } else if (sscanf(v[a], "ptr:%i+%i=%i", &ptr, &off, &bytes) == 3 && bytes) {
            uint32_t base = 0, len = 4;
            free(copy_block(ptr, &len, 1));
            if (!rd(ptr, &base, 4) && base >= 0x10000) {
                len = bytes;
                free(copy_block(base + off, &len, 1));
                printf("ptr [%08x]+0x%x -> %08x, 0x%x bytes\n", ptr, off, base + off, len);
            }
        }
    }
    for (int a = 3; a < c; ++a) {
        unsigned addr = 0, bytes = 0, depth = 0, obj = 0x200;
        if (strncmp(v[a], "graph:", 6))
            continue;
        /* ADDR is P0[/P1/.../Pn]: a = P0, then a = [a] + Pi for each later Pi (a pointer path) */
        char *s = v[a] + 6, *e = NULL;
        addr = (unsigned)strtoul(s, &e, 0);
        int bad = 0;
        while (e && *e == '/') {
            uint32_t at = addr, next = 0;
            unsigned off = (unsigned)strtoul(e + 1, &e, 0);
            uint32_t len = 4;
            free(copy_block(at, &len, 1));
            if (rd(at, &next, 4) || next < 0x10000) { bad = 1; break; }
            addr = next + off;
        }
        if (bad || !e || *e != '=') { fprintf(stderr, "graph %s: unresolved\n", v[a]); continue; }
        if (sscanf(e, "=%i,%i,%i", &bytes, &depth, &obj) >= 2 && bytes && bytes <= CHASE_MAX &&
            depth < 64 && obj <= CHASE_MAX) {
            memset(gseen, 0, sizeof *gseen << SEEN_BITS);
            graph(addr, bytes, (int)depth, obj & ~3u);
        }
    }
    fseek(out, count_pos, SEEK_SET);
    fwrite(&blocks, 4, 1, out);
    fclose(out);
    printf("maps %u nodes %u blocks %u bytes %u -> %s\n", maps, nodes, blocks, total, v[2]);
    return 0;
}
