#include "world_order.h"
#include <stddef.h>

static uint32_t call(const mu_scenemgr_host *h, uint32_t address)
{
    mu_scenemgr_call c = {0};
    c.routine = address;
    return h->call(h->user, &c);
}
static uint32_t virtual_call(const mu_scenemgr_host *h, uint32_t slot)
{
    mu_scenemgr_call c = {0};
    c.routine = MU_SC_VCALL;
    c.count = 1;
    c.args[0] = slot;
    return h->call(h->user, &c);
}
static uint32_t read_at(const mu_scenemgr_host *h, uint32_t a, int size)
{
    return h->peek(h->user, a, size);
}
static int32_t word(const mu_scenemgr_host *h, uint32_t a) { return (int32_t)read_at(h, a, 4); }
static uint32_t byte(const mu_scenemgr_host *h, uint32_t a) { return read_at(h, a, 1); }
static void write_at(const mu_scenemgr_host *h, uint32_t a, uint32_t v, int size)
{
    h->poke(h->user, a, v, size);
}
static uint32_t low_call(const mu_scenemgr_host *h, uint32_t a) { return call(h, a) & 255u; }
static void sequence(const mu_scenemgr_host *h, const uint32_t *a, size_t n)
{
    for (size_t i = 0; i < n; ++i) call(h, a[i]);
}
#define SEQ(...) do { const uint32_t a[] = {__VA_ARGS__}; sequence(h, a, sizeof a / sizeof *a); } while (0)

/* MoveLeaves gate, 0x01856a5c..0x01856ceb. Predicate calls short circuit. */
static int move_leaves(const mu_scenemgr_host *h, int32_t w, int32_t tile)
{
    if (w == 0 && tile != 4) return 1;
    if (w == 2 && tile != 3 && tile < 10) return 1;
    if (w == 3 || w == 7) return 1;
    if (low_call(h, 0x009dad09) == 1) return 1;
    call(h, 0x00c7dfcc);
    if (low_call(h, 0x009d3e63) == 1 || w == 10) return 1;
    if (low_call(h, 0x009dacb8) == 1 || w == 30) return 1;
    if (low_call(h, 0x00dfbbbb) == 1 || low_call(h, 0x00d61f81) == 1 || low_call(h, 0x00dabe97) == 1 || w == 42)
        return 1;
    if (low_call(h, 0x00ea233c) || low_call(h, 0x00e42f6d) || low_call(h, 0x00e94004) ||
        low_call(h, 0x00e3068f) || low_call(h, 0x00dd38c5) || low_call(h, 0x00dd897d) ||
        low_call(h, 0x00dde62f) || low_call(h, 0x00de5519) || low_call(h, 0x00e6eccc)) return 1;
    if (w == 95 || w == 96 || w == 100 || w == 101 || w == 110 || w == 111 || w == 113 ||
        w == 114 || w == 121 || w == 122) return 1;
    if (low_call(h, 0x00e1e4b6) || low_call(h, 0x016a8325) || low_call(h, 0x00e45d40) ||
        low_call(h, 0x00e0558b) || w == 133) return 1;
    call(h, 0x00ea594b);
    return low_call(h, 0x00ea2761) != 0;
}
static int draw_leaves(const mu_scenemgr_host *h, int32_t w, int32_t tile)
{
    if (w == 2 && tile != 3 && tile < 10) return 1;
    if (low_call(h, 0x00ea233c) || low_call(h, 0x00e42f6d) || low_call(h, 0x00e94004) ||
        low_call(h, 0x00e3068f) || low_call(h, 0x00dd38c5) || low_call(h, 0x00dd897d) ||
        low_call(h, 0x00dde62f) || low_call(h, 0x00de5519) || low_call(h, 0x00e6eccc)) return 1;
    if (w == 113 || w == 121 || w == 122) return 1;
    if (low_call(h, 0x00e1e4b6) || low_call(h, 0x00e45d40) || low_call(h, 0x00e0558b) || w == 133) return 1;
    call(h, 0x00ea594b);
    return low_call(h, 0x00ea2761) != 0;
}

/* First-tick calls. Synthetic shared-pointer callees return a handle whose
 * +4 says whether the corresponding local destructor releases a reference. */
static void initialize(const mu_scenemgr_host *h)
{
    SEQ(0x01163cae, 0x0095f6db);
    uint32_t selected = call(h, 0x009a13f4);
    if (selected) SEQ(0x0129deaa, 0x008e7f90, 0x01206598);
    write_at(h, 0x0bdc5ca3, 1, 1);
    if (selected) {
        write_at(h, 0x06fca2c4, 0x3c, 4);
        call(h, MU_SCENE_NET_SEND); /* 0x0185627f..0x0185636c, opaque */
    }
    SEQ(0x011e228b, 0x011e3117, 0x016a5524, 0x00c60187, 0x00ac3bf7, 0x00baf183,
        0x00ac3bf7, 0x00b9f203, 0x00b990b0, 0x00eb0d30, 0x00cb02e9, 0x00fdc138,
        0x01534e75, 0x01a7c7d8, 0x01206598, 0x01206aac, 0x0098647b, 0x00cfc8f2);
    uint32_t p = call(h, 0x0095c5da);
    call(h, 0x00c69008);
    if (read_at(h, p + 4, 4)) call(h, 0x009617c6);
    SEQ(0x00c8eabb, 0x00c8ec58);
    uint32_t shared = call(h, 0x00acbb85);
    SEQ(0x00cd4ea8, 0x00cd5d29, 0x01983b90);
    p = call(h, 0x0095c5da);
    SEQ(0x0095f7df, 0x00c8dbdd);
    if (read_at(h, p + 4, 4)) call(h, 0x009617c6);
    SEQ(0x0121d447, 0x00983bba);
    /* acbb85's output local at -0xec has a +4 reference too. */
    if (read_at(h, shared + 4, 4)) call(h, 0x009617c6);
}

void mu_world_order_tick(const mu_scenemgr_host *h)
{
    if (!byte(h, 0x0bdc5ca3)) initialize(h);
    if (word(h, 0x06fca2c4) == 0x3d) write_at(h, 0x0bdc5eb8, 1, 1);
    if (!byte(h, 0x0bdc5eb8)) return;
    SEQ(0x016ca4fa, 0x016caadb, 0x00abec22, 0x00a96955, 0x0095f659, 0x00952e05);
    if (!byte(h, 0x0bdc58b7) && word(h, 0x0b437c14) < 30) {
        SEQ(0x009fe825, 0x009fe955, 0x00a00fdb, 0x00ac3bf7, 0x00ac9613,
            0x00be6fc4, 0x00fe10b1, 0x00ac3bf7, 0x00c427fa, 0x00ac3bf7);
        uint32_t first = low_call(h, 0x00aae6f9);
        int update = !first;
        if (first) { call(h, 0x00ac3bf7); update = low_call(h, 0x00aae6f9) != 0; }
        if (update) SEQ(0x00f2bb92, 0x00f2b64c);
        SEQ(0x0095f6db, 0x009a1618);
        if (!low_call(h, 0x00da9d49)) {
            uint32_t pick = call(h, 0x016b47bf);
            if (pick != 0xffffffffu) {
                call(h, 0x0095f6db);
                uint32_t c = call(h, 0x009a13f4);
                if (!byte(h, c + 0x12)) SEQ(0x00ac3bf7, 0x0095f6db, 0x009a13f4, 0x00c0bd87);
            } else SEQ(0x00ac3bf7, 0x00c0c0d7);
        }
        if (byte(h, 0x0bdc5981) == 1) {
            call(h, 0x00f2bb92);
            if (!low_call(h, 0x00f2b602) && word(h, 0x06fbcd8c) == 0 &&
                !byte(h, read_at(h, 0x01d22c6c, 4) + 0x66)) {
                SEQ(0x00f2bb92, 0x00f2bf8b, 0x00ef428e, 0x011f8020);
                uint32_t active = call(h, 0x01a7c840);
                /* GetActiveWindow result compared with the saved window. */
                if (active != read_at(h, 0x06fc9c94, 4)) call(h, 0x01a7c7d8);
            }
        }
        SEQ(0x016ad82c, 0x016adb55);
        if (word(h, 0x0bdc5eb4) != 110) call(h, 0x011e03c9);
        SEQ(0x00cd4ea8, 0x00cd5d29, 0x01983b90);
    }
    call(h, 0x016d82c7);
    if (!byte(h, 0x0bdc58b7)) call(h, 0x017ea1aa);
    if (move_leaves(h, word(h, 0x01cf15fc), word(h, 0x0b437c10))) call(h, 0x01537a43);
    SEQ(0x00d038db, 0x00d03ee9, 0x00d038db, 0x00d039f8, 0x0121d54b, 0x009826ce,
        0x00c9eb04, 0x00ca05b3, 0x00c9e24a, 0x016a8fd2, 0x00fcfca4, 0x00fcfb4f,
        0x016a9150, 0x0137a7ce, 0x009c104e, 0x0106bbb2, 0x0121d447, 0x00984885,
        0x00ac3bf7, 0x00b04f6c, 0x00b990b0, 0x00eb0d64, 0x009c2aea, 0x009b9913,
        0x016914a0, 0x0158fa0a, 0x009c104e, 0x0106bcc5, 0x0150ddb1, 0x01589b06,
        0x0159122d, 0x009c104e, 0x0106bcc5, 0x0169223c, 0x009a6ef3, 0x0099b3ed,
        0x00aac00c, 0x00aac43c, 0x0095f7df, 0x0107d0d7, 0x009a595b, 0x010af5de,
        0x00ac3bf7, 0x00c42caf, 0x009c104e, 0x0106be65);
}

static float real(const mu_scenemgr_host *h, uint32_t a)
{
    union { uint32_t u; float f; } v;
    v.u = read_at(h, a, 4);
    return v.f;
}
static int castle_rectangle(const mu_scenemgr_host *h, uint32_t p)
{
    /* comiss/jb rejects unordered values as well as below-bound values. */
    float x = real(h, p), y = real(h, p + 4);
    return x >= real(h, 0x01af7098) && real(h, 0x01aae3f0) >= x &&
        y >= real(h, 0x01af70a0) && y >= real(h, 0x01af70a4);
}
int mu_world_order_draw(const mu_scenemgr_host *h)
{
    if (!byte(h, 0x0bdc5eb8) || word(h, 0x0b437c14) > 30) return 0;
    int32_t w = word(h, 0x01cf15fc), tile = word(h, 0x0b437c10);
    if (low_call(h, 0x0185498e) == 1) {
        SEQ(0x00cfc922, 0x00cfc922, 0x00cfc922);
    } else {
        int special = 0;
        if (w == 6) {
            call(h, 0x0094997e);
            special = low_call(h, 0x0129debb) != 0;
            if (!special) { call(h, 0x0094997e); special = low_call(h, 0x0129debb) != 0;
                call(h, 0x0094f183); }
            call(h, 0x0094f183);
        }
        if (special) SEQ(0x0094997e, 0x0129debb, 0x0094f183, 0x00cfc922);
        else {
            SEQ(0x00f2bb92, 0x00f2c012, 0x00ec3394, 0x009a6ef3);
            if (low_call(h, 0x0099b3b1)) {
                uint32_t p = call(h, 0x009a6ef3);
                if (!byte(h, p + 0x71)) SEQ(0x009a6ef3, 0x0099b4c0);
            }
        }
    }
    call(h, 0x016bc355);
    if (w != 0 && w != 2 && w != 10 && low_call(h, 0x009dacb8) != 1 &&
        !(w >= 45 && w <= 50) && !((w >= 24 && w <= 29) || w == 36)) call(h, 0x00e0558b);
    SEQ(0x01a7c6cc, 0x0184adc7, 0x016cba24);
    if (w == 30) {
        uint32_t p = call(h, 0x00cfc94a);
        call(h, castle_rectangle(h, p) ? 0x00d8cca8 : 0x01a7c758);
    }
    call(h, 0x01849f08);
    if (!low_call(h, 0x00deeaff)) {
        if (w == 39) {
            call(h, 0x009a6ef3);
            if (!low_call(h, 0x009a645f)) call(h, 0x016cd468);
        } else if (w != 10 && w != 132 && w != -1) {
            int first = low_call(h, 0x00e94004) != 0;
            if (!first) first = low_call(h, 0x00e3068f) != 0;
            if (first) call(h, 0x016d5020);
            call(h, 0x016cd468);
        }
    }
    if (!low_call(h, 0x00e94004) && !low_call(h, 0x00e3068f)) call(h, 0x016d5020);
    SEQ(0x0150f00e, 0x00c9fd8d, 0x0137a3c2);
    if (word(h, 0x0b437bfc)) call(h, 0x016cd468);
    if (!byte(h, 0x0bdc58b7)) call(h, 0x017e9495);
    SEQ(0x00ca1cf7, 0x00c9e4e3, 0x009c104e, 0x0106bc2b, 0x01538145);
    if (!low_call(h, 0x009dacb8)) SEQ(0x009c2aea, 0x009b99fa, 0x00b990b0, 0x00eb0dee);
    SEQ(0x00c9fd8d, 0x016d6949, 0x009c104e, 0x0106bcc5, 0x01589b56, 0x015181fa,
        0x009c104e, 0x0106bcc5, 0x01534b4c, 0x009c2aea, 0x009ba5bd, 0x00aee554, 0x00a75708, 0x00aee554);
    virtual_call(h, 4);
    SEQ(0x01692887, 0x0184a699, 0x009c104e, 0x0106bcc5);
    if (draw_leaves(h, w, tile)) call(h, 0x01538145);
    SEQ(0x0169270e, 0x0159123f, 0x009c2aea, 0x009ba4f1);
    if (!low_call(h, 0x00deeaff)) call(h, 0x0169159e);
    SEQ(0x009c104e, 0x0106bcc5, 0x00d038db, 0x00d03aba, 0x0184a6ab, 0x0150e599);
    if (low_call(h, 0x00deeaff) == 1) {
        SEQ(0x0184b6dd, 0x0184adc7, 0x00deebbd, 0x009c104e, 0x0106bcc5,
            0x01589b56, 0x015181fa, 0x01534b4c, 0x01692887, 0x0184a699);
        if (w == 2 && tile != 3 && tile < 10) call(h, 0x01538145);
        SEQ(0x0169270e, 0x0159123f, 0x0169159e, 0x009c104e, 0x0106bcc5, 0x0184a6ab, 0x0184b6dd, 0x0184adc7);
    }
    if (w == 30) { uint32_t p = call(h, 0x00cfc94a); if (castle_rectangle(h, p)) call(h, 0x00d8cd12); }
    SEQ(0x016b5157, 0x0184f793, 0x00def268);
    if (!byte(h, 0x0bdc58b7)) call(h, 0x016b229b);
    SEQ(0x016b3944, 0x0184f8d7, 0x00f2bb92, 0x00f2b67f, 0x0184f793,
        0x10b3e920, 0x00f2bb92, 0x00f2c05d);
    if (virtual_call(h, 0x18) & 255u) { SEQ(0x00f2bb92, 0x00f2c05d); virtual_call(h, 0); }
    SEQ(0x00aac00c, 0x00aac477, 0x0184f8d7, 0x00ac3bf7);
    if (!low_call(h, 0x00aae6f9)) SEQ(0x0184f793, 0x016b0b74, 0x0184f8d7);
    call(h, 0x0184b6dd);
    return 1;
}
