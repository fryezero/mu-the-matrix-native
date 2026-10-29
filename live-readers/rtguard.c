/* rtguard <pid> <out.log> [--ms N] [--seconds S]: RENDER-TIME-003 read-only poller of the wheel-zoom guards.
   Read-only (mach_vm_read_overwrite): it never writes, suspends or injects. Every N ms (default 10) it reads the
   values below and prints a line whenever one changes, so a physical wheel event (sent separately) shows which
   guard state the client held when it refused or applied the zoom. Numbers only; no record bytes.

   Window procedure WM_MOUSEWHEEL (0x01210700..0x01210797, docs/research/client-render-time.md "RENDER-TIME-003"):
     g1 GFx mouse dispatch 0x00ac9800 consumed the event (not memory: observed through the hovered movie
        [[0x01d22c0c]+0x2e4] and the zoom result)
     g2 chat window [0x01d22c6c] +0x68 (InMouseViewBox, set by the movie callback at 0x00c5fbee)
     g3 GFx input object [[0x01d22c0c]+0x70] +0xc (set at 0x00ac0406 when the hit window's type is 6)
   Wheel handler 0x018588d9: NewUI window 0x3e open (map [0x01ec95a8]+0xc), world 0x8b (0x00da9d49), the
   world-FOV scenes (0x01851a7f: scene 0x01d1df70 != 6, worlds 6, 0x45..0x4a) and zoom settled 0x0bdc5ed8.
   Also: MouseWheel 0x0bdc59a4, zoom index 0x0bdc5914, FOV 0x01cf1634, MouseX/Y 0x0bdc5ad8/c (640x480 units).
   At start it lists the window map's ids (MSVC std::map node: key +0x10, window +0x14) with the address of
   window 0x3e's IsVisible (vtable +0x18), so its field can be identified statically. */
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/mach_vm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static task_t t;
static int rd(uint32_t a, void *out, size_t n)
{
    mach_vm_size_t got = 0;
    return mach_vm_read_overwrite(t, a, n, (mach_vm_address_t)out, &got) == KERN_SUCCESS && got == n ? 0 : -1;
}
static uint32_t rd32(uint32_t a) { uint32_t v = 0; return a && !rd(a, &v, 4) ? v : 0; }
static uint8_t rd8(uint32_t a) { uint8_t v = 0; return a && !rd(a, &v, 1) ? v : 0; }
static double now_ms(void)
{
    static mach_timebase_info_data_t tb;
    if (!tb.denom) mach_timebase_info(&tb);
    return (double)mach_absolute_time() * tb.numer / tb.denom / 1e6;
}

enum { GFX = 0x01d22c0c, CHAT = 0x01d22c6c, UI = 0x01ec95a8, WORLD = 0x01cf15fc, SCENE = 0x01d1df70,
       SETTLED = 0x0bdc5ed8, WHEEL = 0x0bdc59a4, ZOOM = 0x0bdc5914, FOV = 0x01cf1634, MX = 0x0bdc5ad8, MY = 0x0bdc5adc };

static int nodes;
static uint32_t window3e;   /* NewUI window 0x3e; its IsVisible 0x00eb5aba returns byte +8 */
static void walk(FILE *f, uint32_t node, uint32_t head, int depth)
{
    if (!node || node == head || depth > 64 || ++nodes > 4096 || rd8(node + 0xd)) return;
    walk(f, rd32(node), head, depth + 1);
    int32_t id = (int32_t)rd32(node + 0x10);
    uint32_t w = rd32(node + 0x14);
    if (id == 0x3e) window3e = w;
    if (id == 0x3e) fprintf(f, "window 0x3e present, IsVisible 0x%08x\n", rd32(rd32(w) + 0x18));
    fprintf(f, "id 0x%x\n", id);
    walk(f, rd32(node + 8), head, depth + 1);
}

int main(int c, char **v)
{
    if (c < 3) { fprintf(stderr, "usage: rtguard pid out.log [--ms N] [--seconds S]\n"); return 2; }
    int ms = 10; double seconds = 60;
    for (int i = 3; i + 1 < c; i += 2) {
        if (!strcmp(v[i], "--ms")) ms = atoi(v[i + 1]);
        else if (!strcmp(v[i], "--seconds")) seconds = atof(v[i + 1]);
    }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &t)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    FILE *f = fopen(v[2], "w");
    if (!f) return 1;
    uint32_t manager = rd32(UI), head = manager ? rd32(manager + 0xc) : 0;
    fprintf(f, "window map size %u\n", manager ? rd32(manager + 0x10) : 0);
    if (head) walk(f, rd32(head + 4), head, 0);
    char last[512] = "";
    double start = now_ms();
    while (now_ms() - start < seconds * 1000.0) {
        uint32_t gfx = rd32(GFX), input = rd32(gfx + 0x70), chat = rd32(CHAT);
        float fov = 0; rd(FOV, &fov, 4);
        char line[512];
        snprintf(line, sizeof line, "world %d scene %d settled %u wheel %d zoom %d fov %.3f mouse %d,%d "
                 "chat_in_view %u gfx_flag %u gfx_normal_path %u gfx_hit %s window3e_open %u",
                 (int32_t)rd32(WORLD), (int32_t)rd32(SCENE), rd8(SETTLED), (int32_t)rd32(WHEEL), (int32_t)rd32(ZOOM),
                 (double)fov, (int32_t)rd32(MX), (int32_t)rd32(MY), rd8(chat + 0x68), rd8(input + 0xc), rd8(input + 0x20),
                 rd32(gfx + 0x2e4) ? "yes" : "no", rd8(window3e + 8));
        if (strcmp(line, last)) {
            fprintf(f, "%.1f %s\n", now_ms() - start, line);
            fflush(f);
            strcpy(last, line);
        }
        usleep((useconds_t)ms * 1000);
    }
    fclose(f);
    return 0;
}
