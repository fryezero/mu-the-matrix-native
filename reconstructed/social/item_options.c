#include "item_options.h"
#include <limits.h>
#include <math.h>
#include <string.h>
void mu_social_item_unpack(const uint8_t b[15], mu_social_item_wire *out) {
    memset(out, 0, sizeof *out);
    out->code = mu_social_item_code(b);
#ifdef MU_SOCIAL2_MUTATION_ITEM
    out->code ^= 0x100;
#endif
    out->level_word = b[1];
    out->durability = b[2];
    out->excellent = b[3] & 0x7f;
    out->ancient = b[4];
    out->flags = b[5] & 0x0f;
    out->harmony = b[6];
    memcpy(out->sockets, b + 7, 5);
    memcpy(out->extra, b + 12, 3);
}
void mu_social_item_pack(const mu_social_item_wire *it, uint8_t b[15]) {
    b[0] = (uint8_t)it->code;
    b[1] = it->level_word;
    b[2] = it->durability;
    b[3] = (uint8_t)((it->excellent & 0x7f) | ((it->code >> 1) & 0x80));
    b[4] = it->ancient;
    b[5] = (uint8_t)((it->flags & 0x0e) | ((it->code >> 5) & 0xf0) | ((it->code >> 13) & 1));
    b[6] = it->harmony;
    memcpy(b + 7, it->sockets, 5);
    memcpy(b + 12, it->extra, 3);
}

static int valid(const mu_social_item_wire *w) {
    return w->code >= 0 && w->code <= 0x2c00;
}
static int kind_a(const mu_social_item_wire *w, const mu_social_item_context *c, int a) {
    return valid(w) && c->kind_a == a;
}
static int kind_b(const mu_social_item_wire *w, const mu_social_item_context *c, int b) {
    return valid(w) && c->kind_b == b;
}
static int grade(const mu_social_item_wire *w, const mu_social_item_context *c, int g) {
    return valid(w) && c->grade == g;
}
static int ancient(const mu_social_item_wire *w, const mu_social_item_context *c) {
    return valid(w) && !kind_a(w, c, 0x19) && (w->ancient & 0x33) != 0;
}
static int ordinary_category(const mu_social_item_wire *w, const mu_social_item_context *c) {
    static const int values[] = {1, 3, 14, 15, 18, 27, 33, 55};
    for (unsigned i = 0; i < sizeof values / sizeof values[0]; i++)
        if (kind_a(w, c, values[i]))
            return 1;
    return 0;
}
static int category_extra(const mu_social_item_wire *w, const mu_social_item_context *c) {
    return valid(w) && ((c->kind_a >= 0x2d && c->kind_a <= 0x31) || c->kind_a == 0x38);
}
static int period(const mu_social_item_wire *w) {
    return !!(w->flags & 2) || (w->code == 0x21fe && (w->harmony & 0x10));
}
int mu_social_item_advanced_eligible(const mu_social_item_wire *w, const mu_social_item_context *c,
                                     int check_level) {
    if (!w || !c || (check_level && ((w->level_word >> 3) & 15) < 9))
        return 0;
    if ((c->normalized_slot < 15 && !grade(w, c, 4) && !c->slot_flags[0] && !c->slot_flags[1] &&
         !c->slot_flags[2] && !c->slot_flags[3]) ||
        period(w))
        return 0;
    if (!(valid(w) && c->excellent_resolved == 1) && !ancient(w, c) && !grade(w, c, 2) && !grade(w, c, 4) &&
        !grade(w, c, 6) && !grade(w, c, 8))
        return 0;
    return ordinary_category(w, c) || category_extra(w, c);
}
int mu_social_item_advanced_group(const mu_social_item_wire *w, const mu_social_item_context *c) {
    if (!mu_social_item_advanced_eligible(w, c, 0))
        return 0;
    if ((c->kind_b >= 1 && c->kind_b <= 9) || c->kind_b == 0x4b || c->kind_b == 0x51 || c->kind_b == 0x7b)
        return 1;
    switch (c->kind_b) {
    case 0x0c:
    case 0x0d:
    case 0x4e:
    case 0x54:
    case 0x59:
    case 0x5a:
    case 0x72:
    case 0x73:
        return 2;
    case 0x0f:
    case 0x10:
    case 0x11:
    case 0x12:
    case 0x13:
    case 0x14:
        return 3;
    case 0x0e:
        return 4;
    default:
        return 0;
    }
}
void mu_social_item_convert(const mu_social_item_wire *w, const mu_social_item_context *c,
                            mu_social_item_decoded *d) {
    memset(d, 0, sizeof *d);
    d->code = w->code;
    d->level_word = w->level_word;
    d->level = (w->level_word >> 3) & 15;
    d->skill_bit = !!(w->level_word & 0x80);
    d->luck_bit = !!(w->level_word & 4);
    d->add_rank = (w->level_word & 3) + ((w->excellent & 0x40) >> 4);
    if (d->skill_bit && c->skill)
        d->skill = c->skill;
    if (d->luck_bit) {
        int value = (ordinary_category(w, c) || kind_a(w, c, 6)) ? 25 : category_extra(w, c) ? 10 : 0;
        if (value) {
            d->prefix[0] = (mu_social_item_option){5, value};
            d->prefix_count = 1;
        }
    }
    d->durability = w->durability;
    d->excellent = w->excellent;
    d->ancient = kind_a(w, c, 0x19) ? 0 : w->ancient;
    d->period = !!(w->flags & 2);
    d->expired = !!(w->flags & 4);
    if (w->code == 0x21fe) {
        d->expired = !!(w->harmony & 0x10);
        if (d->expired)
            d->period = 1;
    }
    d->harmony_kind = w->harmony >> 4;
    d->harmony_level = w->harmony & 15;
    if (!grade(w, c, 2) && !ancient(w, c) && !kind_a(w, c, 8) && !kind_b(w, c, 0x4c) && !kind_b(w, c, 0x6a) &&
        !kind_a(w, c, 0x14) && !kind_a(w, c, 0x19) && !kind_a(w, c, 0x1a) && !kind_a(w, c, 0x1c) &&
        w->sockets[3] != 0xff) {
        d->harmony_kind = w->sockets[3];
        d->harmony_level = w->sockets[4];
    }
    for (int i = 0; i < 5; i++) {
        d->socket_raw[i] = w->sockets[i];
        d->seed_index[i] = 0xff;
        d->special_raw[i] = 0xff;
        d->extra_124[i] = 0xff;
    }
    d->socket_bonus = 0xff;
    d->element_aux = -1;
    d->advanced_slot = -1;
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            d->rank[i][j] = -1;
    for (int i = 0; i < 3; i++)
        d->extra_excellent[i] = 0xff;
    if (grade(w, c, 3))
        d->flag_72 = !!(w->flags & 8);
    else if (grade(w, c, 2)) {
        d->excellent = w->excellent & 0x40;
        d->ancient = 0;
        d->socket_subtype = w->excellent & 0x3f;
        for (int i = 0; i < 5; i++) {
            int mask = i < 4 ? (w->ancient << (2 * i)) & 0xc0 : (w->excellent << 2) & 0xc0;
#ifdef MU_SOCIAL2_MUTATION_SOCKET_MASK
            mask >>= 6;
#endif
            int s = w->sockets[i];
            if (s == 0xff && !mask)
                break;
            if (s != 0xfe || mask) {
                int t = mask ? s + 4 * mask - 2 : s;
                d->seed_index[i] = (uint8_t)(t % 50);
                d->seed_level[i] = (uint8_t)(t / 50 + 1);
            }
            d->socket_count++;
        }
        d->socket_bonus = w->harmony;
        d->harmony_kind = d->harmony_level = 0;
    } else if (kind_a(w, c, 8) || kind_a(w, c, 0x19) || kind_a(w, c, 0x1a)) {
        d->element = w->harmony & 15;
        if (kind_a(w, c, 0x1a) || kind_b(w, c, 0x2c))
            d->element_aux = w->harmony >> 4;
        if (kind_a(w, c, 0x19) || kind_a(w, c, 0x1a) || kind_b(w, c, 0x2c))
            for (int i = 0; i < 5; i++)
                d->socket_count += w->sockets[i] != 0xff;
        if (kind_a(w, c, 0x19))
            for (int i = 3; i >= 0; i--) {
                int v = i ? w->extra[i - 1] : w->ancient;
                if (!i && !v)
                    continue;
#ifdef MU_SOCIAL2_MUTATION_RANK_ZERO
                if (!v)
                    continue;
#endif
                d->rank[i][3] = v < 0xfe ? 1 : v;
                if (v < 0xfe) {
                    d->rank[i][0] = v >> 5;
                    d->rank[i][1] = v & 15;
                    d->rank[i][2] = (v >> 4) & 1;
                }
            }
    } else if (kind_a(w, c, 0x1c)) {
        for (int i = 0; i < 3; i++)
            if (w->sockets[i * 2] != 0xff) {
                int *v = d->artifact[d->artifact_count++];
                v[0] = w->sockets[i * 2];
                v[1] = i < 2 ? w->sockets[i * 2 + 1] : w->harmony;
                v[2] = d->level;
            }
    } else if (kind_a(w, c, 0x14)) {
        d->guardian_base = c->base_level;
        for (int i = 0; i < 5; i++)
            d->guardian_keys[i] = w->sockets[i];
    } else if (kind_a(w, c, 0x1d)) {
        d->extra_word = (w->extra[1] << 8) | w->extra[2];
#ifdef MU_SOCIAL2_MUTATION_EXTRA_WORD
        d->extra_word = (w->extra[2] << 8) | w->extra[1];
#endif
    }
    if (!grade(w, c, 2) && !kind_b(w, c, 0x4c) && !kind_b(w, c, 0x6a) && !kind_a(w, c, 0x22) &&
        !kind_a(w, c, 0x19) && !kind_a(w, c, 0x1a) && !kind_b(w, c, 0x2c) && !kind_a(w, c, 0x1c))
        for (int i = 0; i < 3; i++)
            d->extra_excellent[i] = w->sockets[i];
    if (kind_a(w, c, 0x13))
        for (int i = 0; i < 5; i++)
            d->special_raw[i] = w->sockets[i];
    d->advanced_group = mu_social_item_advanced_group(w, c);
    if (mu_social_item_advanced_eligible(w, c, 0)) {
        d->advanced_level = w->extra[0] >> 4;
        if (d->advanced_level == 15)
            d->advanced_level = 0;
        if ((w->extra[0] & 15) != 15) {
            d->saved_group = d->advanced_group;
            d->advanced_slot = 0;
            d->advanced_option = w->extra[0] & 15;
        }
    } else if (kind_b(w, c, 0x6a) || kind_a(w, c, 0x22)) {
        d->extra_124[0] = w->extra[0];
        d->extra_124[1] = w->extra[1];
    }
}
int mu_social_item_trade_banned(const mu_social_item_wire *w, const mu_social_item_context *c) {
    if (!w || !c)
        return 1;
    if (kind_b(w, c, 0x2b) && !w->durability)
        return 1;
    if (!c->capability || period(w))
        return 1;
    if (w->code == 0x1c34)
        return !c->character_option && c->character_status != 0x20 && c->character_status != 8;
    int level = (w->level_word >> 3) & 15;
    if ((w->code == 0x1a14 && level) || (w->code == 0x1c0b && level == 13) || (w->code == 0x1c1a && level))
        return 1;
    if (w->code == 0x1c15 && level == 3)
        return 0;
#ifdef MU_SOCIAL2_MUTATION_TRADE_FLAG
    return 0;
#else
    return !c->can_trade;
#endif
}

static int32_t trunc_i32(double value) {
    return !isfinite(value) || value >= 2147483648.0 || value < -2147483648.0 ? INT32_MIN : (int32_t)value;
}
static void final_append(mu_social_item_finalized *f, int id, int value) {
    if (f->count < 8)
        f->options[f->count++] = (mu_social_item_option){(uint16_t)id, (uint16_t)value};
    else
        f->unresolved |= 1;
}
static int choose(int *bits, int mask, int yes, int no) {
    if (!(*bits & mask))
        return no;
#ifndef MU_SOCIAL2_MUTATION_FINAL_CONSUME
    *bits &= ~mask;
#endif
    return yes;
}
static int choose3(int *bits, int first, int second, int neither) {
    if (*bits & 0x10)
        return choose(bits, 0x10, first, neither);
    return choose(bits, 0x20, second, neither);
}
static int evaluate(const mu_social_item_final_env *e, mu_social_item_finalized *f, int family, int index,
                    int a, int b, double *out) {
    if (e->formula && e->formula(e->context, family, index, a, b, out))
        return 1;
    f->unresolved |= 2;
    return 0;
}
static void classify(const mu_social_item_wire *w, const mu_social_item_context *c,
                     mu_social_item_finalized *f) {
    if (f->family || !valid(w))
        return;
    switch (c->kind_a) {
    case 1:
    case 2:
    case 14:
    case 45:
        f->family = 1;
        f->category = 1;
        break;
    case 3:
    case 4:
    case 15:
    case 18:
    case 27:
    case 33:
    case 55:
    case 46:
    case 47:
    case 48:
    case 49:
    case 56:
        f->family = 1;
        f->category = 2;
        break;
    case 6:
        f->family = 2;
        f->category = c->kind_b;
        break;
    default:
        break;
    }
}
static void excellent_request(const mu_social_item_wire *w, const mu_social_item_context *c,
                              const mu_social_item_final_env *e, mu_social_item_finalized *f, int id,
                              int slot) {
    classify(w, c, f);
    if (e->excellent_row && e->excellent_row(e->context, f->family, f->category, id, slot)) {
        f->slots[slot] = id;
        if (!grade(w, c, 6) && !kind_a(w, c, 6) && !grade(w, c, 8))
            f->excellent = 1;
    }
}
void mu_social_item_finalize(const mu_social_item_wire *w, const mu_social_item_context *c,
                             const mu_social_item_final_env *e, mu_social_item_finalized *f) {
    f->count = 0;
    f->special_count = f->bonus_count = f->unresolved = 0;
    int rank = (w->level_word & 3) + ((w->excellent & 0x40) >> 4), remaining = w->excellent & 0x3f;
#ifdef MU_SOCIAL2_MUTATION_FINAL_RANK
    rank = w->level_word & 3;
#endif
    f->rank = rank;
    if ((w->level_word & 0x80) && c->skill)
        f->skill = c->skill;
    if (w->level_word & 4) {
        if (ordinary_category(w, c) || kind_a(w, c, 6))
            final_append(f, 5, 25);
        else if (category_extra(w, c))
            final_append(f, 5, 10);
    }
    if (rank) {
        if (w->code == 0x1a03) {
            if (rank & 1)
                final_append(f, 11, 5);
            if (rank & 2)
                final_append(f, 10, 50);
            if (rank & 4)
                final_append(f, 9, 5);
        } else if (!category_extra(w, c)) {
            int b = valid(w) ? c->kind_b : -1;
            if ((b >= 1 && b <= 11) || b == 0x4b || b == 0x51 || b == 0x7b)
                final_append(f, 0, 4 * rank);
            else if (b == 0x0c || b == 0x0d || b == 0x4e || b == 0x54 || b == 0x59 || b == 0x5a ||
                     b == 0x72 || b == 0x73)
                final_append(f, 1, 4 * rank);
            else if (b == 0x0e)
                final_append(f, 2, 4 * rank);
            else if (b == 0x0f)
                final_append(f, 3, 5 * rank);
            else if (b >= 0x10 && b <= 0x14)
                final_append(f, 4, 4 * rank);
            else if (kind_a(w, c, 4) || kind_a(w, c, 2))
                final_append(f, w->code == 0x1a18 ? 13 : w->code == 0x1a1c ? 14 : 6, rank);
            int id = -1;
            switch (w->code) {
            case 0x1800:
                id = 6;
                break;
            case 0x1801:
            case 0x1829:
            case 0x189b:
                id = 1;
                break;
            case 0x1802:
            case 0x18ac:
            case 0x18ad:
            case 0x2a00:
                id = 0;
                break;
            case 0x1803:
            case 0x19a8:
                id = choose(&remaining, 0x20, 6, 0);
                break;
            case 0x1804:
            case 0x19a6:
            case 0x189c:
            case 0x189d:
                id = choose(&remaining, 0x20, 1, 6);
                break;
            case 0x1805:
            case 0x19a7:
            case 0x18ae:
            case 0x18af:
                id = choose(&remaining, 0x20, 0, 6);
                break;
            case 0x1806:
            case 0x19a9:
                id = choose(&remaining, 0x20, 0, 1);
                break;
            case 0x1a1e:
            case 0x19aa:
            case 0x1917:
            case 0x191a:
                id = 0;
                break;
            case 0x1918:
                final_append(f, 0, 4 * rank);
                id = 1;
                break;
            case 0x1919:
                id = (e->class_byte & 15) == 5 ? 2 : 1;
                break;
            case 0x1831:
            case 0x190d:
            case 0x19ac:
            case 0x19ad:
                id = choose(&remaining, 0x20, 0, 6);
                break;
            case 0x182a:
            case 0x19ab:
                id = choose(&remaining, 0x20, 1, 2);
                break;
            case 0x1824:
            case 0x19af:
            case 0x199f:
            case 0x19b7:
            case 0x18b0:
            case 0x18b1:
            case 0x18b2:
            case 0x18b3:
            case 0x18b5:
            case 0x18c1:
            case 0x2a01:
            case 0x2a02:
            case 0x2a03:
            case 0x2a04:
            case 0x2a05:
                id = choose3(&remaining, 0, 4, 6);
                break;
            case 0x1825:
            case 0x19ae:
            case 0x199e:
            case 0x19b6:
            case 0x19d3:
            case 0x19d4:
            case 0x19d5:
            case 0x19d6:
            case 0x19e9:
            case 0x19f0:
            case 0x19ea:
            case 0x19f1:
            case 0x189e:
            case 0x189f:
            case 0x18a0:
            case 0x18a1:
            case 0x181b:
            case 0x181c:
            case 0x1898:
            case 0x1899:
            case 0x18b4:
            case 0x18bc:
            case 0x18be:
            case 0x18bf:
            case 0x18c0:
            case 0x18c2:
            case 0x18c3:
            case 0x18c4:
            case 0x18c5:
            case 0x18c6:
                id = choose3(&remaining, 1, 4, 6);
                break;
            case 0x1826:
            case 0x19b0:
            case 0x19a0:
            case 0x19b8:
            case 0x18b6:
                id = choose3(&remaining, 0, 4, 6);
                break;
            case 0x1827:
            case 0x19b1:
            case 0x19a1:
            case 0x19b9:
            case 0x18b7:
                id = choose3(&remaining, 0, 1, 6);
                break;
            case 0x1828:
            case 0x1832:
            case 0x190e:
            case 0x19b2:
            case 0x19b4:
            case 0x19b5:
            case 0x19a2:
            case 0x19a4:
            case 0x19a5:
            case 0x19ba:
            case 0x19bc:
            case 0x19bd:
            case 0x18b8:
            case 0x18ba:
            case 0x18bb:
                id = choose3(&remaining, 0, 4, 6);
                break;
            case 0x182b:
            case 0x19b3:
            case 0x19a3:
            case 0x19bb:
            case 0x18b9:
                id = choose3(&remaining, 1, 2, 6);
                break;
            case 0x19d8:
            case 0x19d9:
            case 0x19da:
            case 0x19db:
            case 0x18bd:
                id = choose3(&remaining, 0, 4, 6);
                break;
            default:
                if (kind_b(w, c, 0x1c))
                    id = (w->code == 0x1908 || w->code == 0x191e) ? choose(&remaining, 0x10, 1, 2)
                                                                  : choose(&remaining, 0x10, 0, 6);
                else if (w->code == 0x190a)
                    id = 6;
                else if (w->code == 0x190c)
                    id = choose3(&remaining, 0, 1, 6);
                break;
            }
            if (id >= 0)
                final_append(f, id, id == 6 ? rank : 4 * rank);
        }
    }
    int level = (e->level_word >> 3) & 15;
    if (category_extra(w, c) && (e->ancient & 0x33)) {
        int b = c->kind_b, id = -1, index = 0;
        if ((b >= 1 && b <= 11) || b == 0x4b || b == 0x51 || b == 0x7b) {
            id = 0;
            index = 25;
        } else if (b == 0x0c || b == 0x0d || b == 0x4e || b == 0x54 || b == 0x59 || b == 0x5a || b == 0x72 ||
                   b == 0x73) {
            id = 1;
            index = 27;
        } else if (b == 0x0e) {
            id = 2;
            index = 27;
        } else if (b >= 0x0f && b <= 0x14) {
            id = 4;
            index = 29;
        }
        double v, more;
        if (id >= 0 && evaluate(e, f, 1, index, level, rank, &v)) {
            int value = trunc_i32(v);
            if (level >= 10) {
                if (evaluate(e, f, 1, index + 1, level, rank, &more))
                    value = trunc_i32((double)value + more);
                else
                    id = -1;
            }
            if (id >= 0)
                final_append(f, id, value);
        }
    }
    if ((w->code == 0x1a04 || w->code == 0x28f7) && !e->state_known)
        f->unresolved |= 4;
    if (w->code == 0x1a04 && e->state_known)
        final_append(f, 15, e->character_stat / 20 + 2 * e->state_level + 5);
    if (w->code == 0x28f7 && e->state_known)
        for (int i = 0; i < 2; i++) {
            double value;
            if (evaluate(e, f, 16, 5 + i, e->state_level, e->state_level, &value))
                final_append(f, 17 + i, trunc_i32(10.0 * value));
        }
    if (w->code == 0x1a14 && (level == 0 || level == 3)) {
        final_append(f, 8, 10);
        final_append(f, 7, 10);
        final_append(f, 9, 10);
    }
    if (e->enabled) {
        for (int bit = 5; bit >= 0; bit--)
            if (remaining & (1 << bit))
                excellent_request(w, c, e, f, 5 - bit, 5 - bit);
        if (!(grade(w, c, 2) && kind_a(w, c, 2)))
            for (int i = 0; i < 3; i++)
                if (f->slots[6 + i] != 0xff)
                    excellent_request(w, c, e, f, f->slots[6 + i], 6 + i);
    }
    if (kind_a(w, c, 0x13)) {
        for (int i = 0; i < 5; i++)
            if (f->slots[i] != 0xff) {
                int *v = f->special[f->special_count++];
                v[0] = f->slots[i] >> 3;
                v[1] = f->slots[i] & 7;
                v[2] = e->special_tag;
            }
        for (int i = 0; i < 5; i++)
            f->slots[i] = 0;
        if (e->special_row && e->special_enabled)
            for (int i = 0; i < 3; i++) {
                int *v = f->bonus[f->bonus_count++];
                v[0] = e->special_bonus[i];
                v[1] = e->special_lows[i];
                v[2] = e->special_tag;
            }
    }
}

int mu_social_item_excellent_value(int category, int id, int value_type, int base, int level_word,
                                   int record_level, int hero_level, const mu_social_item_final_env *e,
                                   double *value) {
    if (value_type == 6) {
        *value = (int32_t)((uint32_t)base + (uint32_t)(5 * ((level_word >> 3) & 15)));
        return 1;
    }
    if (value_type != 100) {
        *value = base;
        return 1;
    }
    int index = -1;
    if (category == 1 && (id == 6 || id == 7))
        index = id - 6;
    else if (category == 2) {
        if (id >= 6 && id <= 10)
            index = id - 4;
        else if (id == 11 || id == 12)
            index = id - 2;
    }
    return e && e->formula && e->formula(e->context, 1, index, record_level, hero_level, value);
}
