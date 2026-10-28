/* SESSION-QUEST-001: session-owned quest handler state and window intents. */
#ifndef MU_SESSION_QUEST_H
#define MU_SESSION_QUEST_H
#include "../../../reconstructed/quest/quest.h"
struct mu_session;
const mu_quest_client *mu_session_quest(const struct mu_session *s);
/* Bind static tables/host services before applying frames. Rebinding preserves all quest state. */
int mu_session_quest_bind(struct mu_session *s, const char *dir, const mu_quest_host *host);
long mu_session_quest_classic(struct mu_session *s, const char *root);
typedef enum mu_quest_action
{
    MU_Q_TOGGLE,
    MU_Q_PROGRESS_LOAD,
    MU_Q_INFO_LOAD,
    MU_Q_SUMMARY,
    MU_Q_NOTICE_LOAD,
    MU_Q_CLASSIC_LOAD,
    MU_Q_PROGRESS_CLOSE,
    MU_Q_PROGRESS_CALLBACK,
    MU_Q_INFO_CALLBACK,
    MU_Q_GIVEUP,
    MU_Q_DIALOG_TEXT,
    MU_Q_PROGRESS_SELECT,
    MU_Q_INFO_CLOSE,
    MU_Q_CONFIRM,
    MU_Q_GUIDE_GO,
    MU_Q_MOVE,
    MU_Q_CLASSIC_CALLBACK,
    MU_Q_CLASSIC_COMPLETE,
    MU_Q_GUIDE_BOX,
    MU_Q_DIALOG_CHOICE,
    MU_Q_SUMMARY_REFRESH,
    MU_Q_CLASSIC_REFRESH,
    MU_Q_DIALOG_VISIBLE,
    MU_Q_HERO_NAME,
    MU_Q_NPC_LIST,
    MU_Q_CLASSIC_KEY,
    MU_Q_TARGET,
    MU_Q_DIALOG_RESET,
    MU_Q_SUMMARY_LOAD
} mu_quest_action;
/* Convenience constructor for the generated QUEST_WINDOW intent. */
int mu_session_quest_window(struct mu_session *s, mu_quest_action action, const char *event, const char *text,
                            double a, double b);
void mu_session_quest_services(struct mu_session *, void (*)(void *, uint8_t), const char *(*)(void *, int32_t));
#endif
