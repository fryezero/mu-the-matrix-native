#include "help.h"
#include <string.h>

static int32_t row_id(const uint8_t *row)
{
    uint32_t value = (uint32_t)row[0] | (uint32_t)row[1] << 8 |
                     (uint32_t)row[2] << 16 | (uint32_t)row[3] << 24;
    int32_t id;
    memcpy(&id, &value, sizeof id);
    return id;
}

void mu_help_provider_init(mu_help_provider *provider)
{
    if (provider) memset(provider, 0, sizeof *provider);
}

int mu_help_build(mu_help_provider *provider, const mu_help_table *table)
{
    if (!provider || !table || provider->count[2] > MU_HELP_ROWS) return 0;
    uint32_t auxiliary = 0;
    for (size_t i = 0; i < MU_HELP_ROWS && row_id(table->rows[i]); ++i)
        if (table->rows[i][5] == 1 || table->rows[i][5] == 2) ++auxiliary;
    if (auxiliary > MU_HELP_ROWS - provider->count[2]) return 0;
    provider->count[0] = provider->count[1] = 0;
    for (size_t i = 0; i < MU_HELP_ROWS; ++i) {
        const uint8_t *row = table->rows[i];
        if (row_id(row) == 0) break;
        int list = row[4] == 0 || row[4] == 13 ? 0 : row[4] == 1 ? 1 : -1;
        if (list >= 0)
            memcpy(provider->list[list].rows[provider->count[list]++], row, MU_HELP_ROW_SIZE);
        if (row[5] == 1 || row[5] == 2)
            memcpy(provider->list[2].rows[provider->count[2]++], row, MU_HELP_ROW_SIZE);
    }
    return 1;
}

static int strings_valid(const mu_help_provider *provider, int list)
{
    if (!provider || provider->count[list] > MU_HELP_ROWS) return 0;
    for (uint32_t i = 0; i < provider->count[list]; ++i) {
        const uint8_t *row = provider->list[list].rows[i];
        if (!memchr(row + 6, 0, 64) || !memchr(row + 70, 0, 66)) return 0;
    }
    return 1;
}

int mu_help_hotkeys(const mu_help_provider *provider, int mode, mu_help_invoke_fn invoke, void *user)
{
    if (!invoke || !strings_valid(provider, 0)) return 0;
    for (uint32_t i = 0; i < provider->count[0]; ++i) {
        const uint8_t *row = provider->list[0].rows[i];
        int32_t id = row_id(row);
        if (id == 1 || (id == 2 && !mode) || (id == 3 && mode == 1)) {
            const char *args[] = {(const char *)row + 6, (const char *)row + 70};
            invoke(user, "SetHotKeyData", 2, args);
        }
    }
    return 1;
}

int mu_help_chatkeys(const mu_help_provider *provider, mu_help_invoke_fn invoke, void *user)
{
    if (!invoke || !strings_valid(provider, 1)) return 0;
    for (uint32_t i = 0; i < provider->count[1]; ++i) {
        const uint8_t *row = provider->list[1].rows[i];
        const char *args[] = {(const char *)row + 6, (const char *)row + 70};
        invoke(user, "SetChatHotKeyData", 2, args);
    }
    return 1;
}

int mu_help_reload(const mu_help_provider *provider, int mode, mu_help_invoke_fn invoke, void *user)
{
    if (!invoke || !strings_valid(provider, 0) || !strings_valid(provider, 1)) return 0;
    invoke(user, "ClearDataProvider", 0, NULL);
    return mu_help_hotkeys(provider, mode, invoke, user) && mu_help_chatkeys(provider, invoke, user);
}

int mu_help_load(mu_help_provider *provider, const mu_help_table *table, int base_loaded,
                 int mode, const char *const labels[5], mu_help_invoke_fn invoke, void *user)
{
    if (!base_loaded || !labels || !invoke || !mu_help_build(provider, table)) return 0;
    for (size_t i = 0; i < 5; ++i) if (!labels[i]) return 0;
    if (!strings_valid(provider, 0) || !strings_valid(provider, 1)) return 0;
    invoke(user, "InitText", 5, labels);
    invoke(user, "SetPosCenter", 0, NULL);
    return mu_help_reload(provider, mode, invoke, user);
}
