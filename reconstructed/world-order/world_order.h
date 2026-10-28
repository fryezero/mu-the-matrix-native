#ifndef MU_WORLD_ORDER_H
#define MU_WORLD_ORDER_H
#include "../scene/scene.h"
/* WORLD-ORDER-001: order-only projection through the scene manager host.
 * routine identifies each direct call/import; virtual calls use MU_SC_VCALL
 * and args[0] = slot. Other argument words/ECX and non-order writes are not
 * reconstructed. Callees are opaque. No native runtime links this family.
 * peek reads original-address globals and scripted opaque object handles.
 * The first tick's packet-building interval is one MU_SCENE_NET_SEND record.
 */
void mu_world_order_tick(const mu_scenemgr_host *host);
int mu_world_order_draw(const mu_scenemgr_host *host);
#endif
