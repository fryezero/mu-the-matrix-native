/* Private state for the offline item-service windows. Included after item. */
#define SERVICE_PRODUCTS 8
#define SERVICE_BUNDLE 5
struct service_product { int ids[SERVICE_BUNDLE], n; uint32_t price[3]; };
struct item_services {
    int pending, outcome, request_product, shop_open, browsing;
    int repair_mode, npc_repair, draft_active, selected, bundle;
    double due;
    int64_t cost;
    int repair_ids[MAX_ITEMS], repair_max[MAX_ITEMS], nrepair;
    struct service_product products[SERVICE_PRODUCTS], draft;
    float slots[2][SERVICE_BUNDLE][4];
    int have_slot[2][SERVICE_BUNDLE];
    char title[64];
};
