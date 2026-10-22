/* The character window's "+" buttons and the stat request (NATIVE-PROGRESS-001).  See progress.h. */
#include <string.h>

#include "progress_internal.h"

int32_t mu_prg_stat_button(const uint8_t *a, double row)
{
    static const double ROWS[5] = {8.0, 13.0, 24.0, 29.0, 42.0};
    if (mu_prg_u16(a, MU_PRG_A_POINTS) == 0)
        return -1;
    for (int i = 0; i < 5; i++)
        if (row == ROWS[i])
            return MU_PROGRESS_MUTATION == 7 && i == 4 ? 3 : i;
    return -1;
}

int mu_prg_stat_request(const mu_prg_env *e, uint32_t *last, uint32_t now, int32_t stat, uint8_t packet[5])
{
    if (now - *last < 100u)
        return 0;
    *last = now;
    packet[0] = 0xc1;
    packet[1] = 5;
    packet[2] = 0x01;
    packet[3] = 0x00;
    packet[4] = (uint8_t)stat;
    mu_prg_emitf(e, "call 00d51d4f 0 0");
    mu_prg_emitf(e, "call 00a6ac96 19 0 0");
    return 5;
}

/* ---- the speed row (0x00b40380) and its packet (0x0122a13d) --------------------------------------- */

int32_t mu_prg_speed_max(int32_t cls)
{
    static const int16_t MAX[16] = {0x11c, 0x120, 0x113, 0x15f, 0x122, 0xbc, 0x1b9, 0x111,
                                    0x112, 0x180, 0x118, 0x130, 0x122, 0x15e, 0x149, 0x11d};
    return cls >= 0 && cls < 16 ? MAX[cls] : 0xc8;
}

int mu_prg_speed_row(const mu_prg_env *e, int32_t cls, uint16_t cache[2], int visible)
{
    const uint8_t *a = e->attr;
    if (!visible)
        return 0;
    uint16_t speed = (cls == 0 || cls == 5 || cls == 8) ? mu_prg_u16(a, MU_PRG_A_MAGIC_SPEED)
                                                       : mu_prg_u16(a, MU_PRG_A_ATK_SPEED);
    if (e->tree && e->tree(e->user)) {
        int32_t value = mu_prg_u16(a, 0x1e6 + 2 * (size_t)(e->hero ? e->hero[0x32] : 0));
        int32_t id = e->tree_map ? e->tree_map(e->user, e->hero ? e->hero[0x12] & 0xf : 0, value) : -1;
        int32_t bonus = 0;
        if (e->tree_node && e->tree_node(e->user, id != -1 ? id : value, 0x3f0, &bonus))
            speed = (uint16_t)(speed + bonus);
    }
    if (a[MU_PRG_A_FLAGS_1A6] & 1)
        speed = (uint16_t)(speed + 0x14);
    else if (a[MU_PRG_A_FLAGS_1A6] & 8)
        speed = (uint16_t)(speed + 0x14);
    if (e->has_effect && e->has_effect(e->user, 0xb0))
        speed = (uint16_t)(int32_t)((float)speed * (MU_PROGRESS_MUTATION == 8 ? 0.25f : 0.5f));
    int32_t max = mu_prg_speed_max(cls);
    if ((int32_t)speed > max)
        speed = (uint16_t)max;
    if (cache[0] == speed && (int32_t)cache[1] == max)
        return 0;
    cache[0] = speed;
    cache[1] = (uint16_t)max;
    const char *fmt = e->global_text ? e->global_text(e->user, 0x10be) : NULL;
    char text[256], q[600];
    /* the client's formatter 0x009619dd over GlobalText 0x10be ("%d / %d") with the two words */
    size_t n = 0;
    int k = 0;
    const int32_t args[2] = {speed, max};
    for (const char *s = fmt ? fmt : ""; *s && n + 12 < sizeof text; s++) {
        if (s[0] == '%' && s[1] == 'd' && k < 2) {
            n += (size_t)snprintf(text + n, sizeof text - n, "%d", args[k++]);
            s++;
        } else if (s[0] == '%' && s[1] == '%') {
            text[n++] = '%';
            s++;
        } else {
            text[n++] = *s;
        }
    }
    text[n] = 0;
    mu_prg_json(q, sizeof q, text);
    mu_prg_emitf(e, "call 00b3e33f 15 %s", q);
    mu_prg_emitf(e, "call 00b3e2a4 15");
    mu_prg_emitf(e, "invoke UpdateScorllList [2]");
    return 1;
}

void mu_prg_recv_speed(const mu_prg_env *e, const uint8_t *p)
{
    mu_prg_set16(e->attr, MU_PRG_A_ATK_SPEED, (uint32_t)(p[4] | p[5] << 8));
    mu_prg_set16(e->attr, MU_PRG_A_MAGIC_SPEED, (uint32_t)(p[8] | p[9] << 8));
    mu_prg_emitf(e, "call 00b40380");
}
