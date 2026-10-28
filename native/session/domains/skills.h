#ifndef MU_SESSION_SKILLS_H
#define MU_SESSION_SKILLS_H
#include "../../core/mu_skill.h"
#include "../../core/mu_skill_tree4.h"
struct mu_session;
/* Session owns both objects. Mutable access supports presentation caches and window callbacks only;
 * learned lists, saved keys and ranks are written by inbound handlers or submitted actions. */
mu_skill_book *mu_session_skills(const struct mu_session *s);
mu_skill_tree4 *mu_session_skills_tree4(const struct mu_session *s);
/* Bind static data before the first skill frame. Rebinding the same session never resets answers. */
int mu_session_skills_bind(struct mu_session *, const struct mu_lang *, const char *, const char *);
/* Context still owned by the hero/equipment domains, never a skill-list feed. */
void mu_session_skills_context(struct mu_session *, const mu_skill_stats *);
int mu_session_skills_last_cast(const struct mu_session *);
#endif
