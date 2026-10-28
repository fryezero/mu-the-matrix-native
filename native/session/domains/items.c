#include "../session_internal.h"
#include "items_wire.h"
#include <stddef.h>
#include <string.h>
mu_items_view mu_session_items(const mu_session *s)
{
    mu_items_view v = {s->items.pool, s->items.used, s->items.creates, s->items.deletes, s->items.pending};
    return v;
}
void mu_session_items_bind(mu_session *s, mu_items_present_fn fn, void *ctx)
{
    s->items.present = fn; s->items.context = ctx;
    if (fn) for (int i = 0; i < MU_GI_ITEMS; ++i)
        if (s->items.used[i]) fn(ctx, i, s->items.entries[i]);
}
mu_apply items_viewport(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc2 || f->length < 5) return MU_APPLY_IGNORED;
    unsigned n = f->bytes[4] > 75 ? 75 : f->bytes[4];
    if (f->length < 5 + n * 19) return MU_APPLY_IGNORED;
    mu_gi_viewport_entry parsed[75];
    n = (unsigned)mu_gi_viewport_parse(f->bytes, parsed, 75);
    for (unsigned i = 0; i < n; ++i) {
        int slot = parsed[i].index;
        memcpy(s->items.entries[slot], f->bytes + 5 + i*19, 19);
        s->items.used[slot] = 1;
        memset(&s->items.pool[slot], 0, sizeof s->items.pool[slot]);
        s->items.pool[slot].key = (uint16_t)slot;
        if (s->items.present) s->items.present(s->items.context, slot, s->items.entries[slot]);
        ++s->items.creates;
    }
    if (n) mu_session_touch(s, MU_DOMAIN_ITEMS);
    return n ? MU_APPLY_DONE : MU_APPLY_IGNORED;
}
mu_apply items_delete(mu_session *s, const mu_frame *f)
{
    if (f->head != 0xc2) return MU_APPLY_IGNORED;
    uint16_t slots[255]; int n = mu_items_delete_parse(f->bytes, f->length, slots);
    if (n <= 0) return MU_APPLY_IGNORED;
    for (int i = 0; i < n; ++i) {
        int slot = slots[i];
        /* Reset ITEM and SetLive(0). Other object/label bytes survive in the client. */
        memset(&s->items.pool[slot].data, 0, sizeof s->items.pool[slot].data);
        s->items.pool[slot].object.live = 0;
        s->items.used[slot] = 0;
        memset(s->items.entries[slot], 0, 19);
        if (s->items.pending == slot) s->items.pending = -1;
        ++s->items.deletes;
    }
    mu_session_touch(s, MU_DOMAIN_ITEMS); return MU_APPLY_DONE;
}
mu_submit items_pickup(mu_session *s, const mu_intent *in)
{
    int slot = in->u.item_pickup.slot;
    mu_submit r = {MU_SUBMIT_REFUSED, -1};
    if (slot < 0 || slot >= MU_GI_ITEMS || !s->items.used[slot] || s->items.pending != -1) return r;
    uint8_t b[5]; size_t n = mu_items_pickup_request(b, (uint16_t)slot, s->items.pending);
    s->items.pending = slot;
    /* Send(1,0) needs NET-DECODE. Never deliver this as a plaintext request. */
    mu_packet p; mu_packet_begin(&p,b[0],b[2]); mu_packet_add(&p,b+3,n-3,0); mu_packet_finish(&p);
    mu_journal_frame_out(s->cfg.journal,s->tick,s->now,s->conn_main,p.obj+2,(uint32_t)n,MU_SEND_NEEDS_CRYPTO,1);
    ++s->unsent; r.status = MU_SUBMIT_NOT_NOW; return r;
}
void mu_dom_items_init(mu_session *s) { memset(&s->items,0,sizeof s->items); s->items.pending=-1; }
void mu_dom_items_free(mu_session *s) { (void)s; }
void mu_dom_items_step(mu_session *s,const mu_sim *sim) { (void)s; (void)sim; }
void mu_dom_items_zones(const mu_session *s,mu_audit_zones *z)
{
    mu_audit_add(z,"items.used",s->items.used,0,sizeof s->items.used,MU_ZONE_REPLICATED,"server slots");
    mu_audit_add(z,"items.entries",(const uint8_t *)s->items.entries,0,sizeof s->items.entries,MU_ZONE_REPLICATED,"viewport bytes");
    for (int i=0;i<MU_GI_ITEMS;++i) {
        const uint8_t *p=(const uint8_t *)&s->items.pool[i];
        mu_audit_add(z,"items.pool",p,0,offsetof(mu_gi_item,object),MU_ZONE_REPLICATED,"key and item data");
        mu_audit_add(z,"items.pool",p,offsetof(mu_gi_item,object),sizeof(mu_gi_object),MU_ZONE_MOTION,"MoveItems and render plan");
    }
}
#ifdef MU_SESSION_SEED
void mu_dom_items_seed(mu_session *s,const struct mu_session_seed *seed) { (void)s; (void)seed; }
#endif
