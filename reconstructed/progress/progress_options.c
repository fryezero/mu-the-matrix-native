/* The options window winOption (NATIVE-PROGRESS-001).  See progress.h.
 *
 * Lines (env->emit):
 *   invoke METHOD JSON            the movie's invokes (InitText, setDatas, MainSceneVisiableSetup, useHelpText)
 *   call 00b6b21e                 the window hidden (KeyWindow); call 00c76b02 FLAG the scene's windows
 *   call 00be7079                 the window opened
 *   call 00c83c86 FLAG            hudPlayerName's monster info
 *   call 00c435b4 MINUTES / call 00c435f1   the auto switch on (minutes) / off */
#include <string.h>

#include "progress_internal.h"

static int32_t ini(const mu_prg_options_env *e, const char *section, const char *key, int32_t fallback)
{
    return e->ini_int ? e->ini_int(e->user, section, key, fallback) : fallback;
}

void mu_prg_options_load(const mu_prg_options_env *e, mu_prg_options *o)
{
    o->auto_attack = ini(e, "DEFAULT", "IsAutoAttack", 1) != 0;
    o->whisper_sound = ini(e, "DEFAULT", "IsWhisperSound", 0) != 0;
    o->slide_help = ini(e, "DEFAULT", "IsSlideHelp", 1) != 0;
    o->player_info = ini(e, "DEFAULT", "IsPlayerInfo", 1) != 0;
    o->monster_info = ini(e, "DEFAULT", "IsMonsterInfo", 1) != 0;
    o->music_play = ini(e, "DEFAULT", "IsMusicPlay", 1) != 0;
    o->volume = ini(e, "DEFAULT", "Volum", MU_PROGRESS_MUTATION == 13 ? 9 : 5);
    o->mute = ini(e, "DEFAULT", "IsMute", 0) != 0;
    o->update = ini(e, "DEFAULT", "IsUpdateData", 0) != 0;
    o->switch_mode = ini(e, "DEFAULT", "IsSwitchMode", 0) != 0;
    o->switch_time = ini(e, "DEFAULT", "SwitchModeTime", 10);
}

void mu_prg_options_load_effect(const mu_prg_options_env *e, mu_prg_options *o)
{
    o->effect = ini(e, "OPTION", "Effect", 4);
    if (o->effect > 4)
        o->effect = 4;
    else if (o->effect < 0)
        o->effect = 0;
}

static const char *gtext(const mu_prg_options_env *e, int32_t index)
{
    const char *t = e->global_text ? e->global_text(e->user, index) : NULL;
    return t ? t : "";
}

void mu_prg_options_init_text(const mu_prg_options_env *e)
{
    static const struct { const char *member; int32_t gt; } TEXT[] = {
        {"Title", 0x927}, {"Volume", 0x185}, {"Effect", 0x730}, {"AutoAtk", 0x182}, {"Whisper", 0x183},
        {"Slide", 0x397}, {"CharacterInfo", 0xef8}, {"MonsterInfo", 0xef9}, {"Close", 0x3ea}, {"Music", 0x1178},
        {"Mute", 0x1314}, {"SwitchModeTitle", 0x1530}, {"SwitchModeMinutesTitle", 0x1531}};
    char json[2048], q[512];
    size_t n = 0;
    json[n++] = '{';
    for (size_t i = 0; i < sizeof TEXT / sizeof TEXT[0] && n + 600 < sizeof json; i++) {
        mu_prg_json(q, sizeof q, gtext(e, TEXT[i].gt));
        n += (size_t)snprintf(json + n, sizeof json - n, "%s\"%s\":%s", i ? "," : "", TEXT[i].member, q);
    }
    json[n++] = '}';
    json[n] = 0;
    if (e->emit) {
        char line[2100];
        snprintf(line, sizeof line, "invoke InitText %s", json);
        e->emit(e->user, line);
    }
}

static void emit(const mu_prg_options_env *e, const char *fmt, ...)
{
    char line[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    if (e->emit)
        e->emit(e->user, line);
}

static const char *b(int v)
{
    return v ? "true" : "false";
}

void mu_prg_options_set_datas(const mu_prg_options_env *e, mu_prg_options *o)
{
    float v = e->group_volume ? e->group_volume(e->user, 2) : 0.0f;
    int32_t level = (int32_t)(v * 9.0f + (MU_PROGRESS_MUTATION == 14 ? 0.0f : 0.5f));
    if (level == 0) {
        o->mute = 1;
    } else {
        o->mute = 0;
        o->volume = level;
    }
    o->music_play = !(e->group_muted && e->group_muted(e->user, 0));
    if (!(e->visible && e->visible(e->user)))
        return;
    emit(e, "invoke setDatas {\"isAutoAttack\":%s,\"isWhisperSound\":%s,\"isSlideHelp\":%s,\"isPlayerInfo\":%s,"
            "\"isMonsterInfo\":%s,\"isMusicPlay\":%s,\"isSwitchMode\":%s,\"switchModeTime\":%d,\"effectLimit\":%d,"
            "\"volum\":%d,\"isMute\":%s}",
         b(o->auto_attack), b(o->whisper_sound), b(o->slide_help), b(o->player_info), b(o->monster_info),
         b(o->music_play), b(o->switch_mode), o->switch_time, o->effect + 1, o->volume, b(o->mute));
}

void mu_prg_options_apply(const mu_prg_options_env *e, const mu_prg_options *o)
{
    char value[32];
    snprintf(value, sizeof value, "%d", o->effect);   /* boost::format("%d") % effect */
    if (e->ini_write)
        e->ini_write(e->user, "OPTION", "Effect", value);
    if (e->window && e->window(e->user, 0x0095c5da))
        emit(e, "invoke useHelpText [%s]", b(o->slide_help));
    if (e->window && e->window(e->user, 0x009a19ae))
        emit(e, "call 00c83c86 %x", o->monster_info);
    if (e->set_group_volume)
        e->set_group_volume(e->user, 2, o->mute == 1 ? 0.0f : (float)o->volume / 9.0f);
    if (e->set_group_mute)
        e->set_group_mute(e->user, 0, o->music_play == 0);
    float minutes = 0.0f;
    int on = e->switch_state ? e->switch_state(e->user, &minutes) : 0;
    if ((on != o->switch_mode) || !(minutes == (float)o->switch_time)) {
        if (o->switch_mode)
            emit(e, "call 00c435b4 %x", (uint32_t)o->switch_time);
        else
            emit(e, "call 00c435f1");
    }
}

void mu_prg_options_event(const mu_prg_options_env *e, mu_prg_options *o, const char *name, int32_t scene)
{
    if (!strcmp(name, "onLoad")) {
        mu_prg_options_init_text(e);
        mu_prg_options_set_datas(e, o);
        emit(e, "call 00b6b21e");
        emit(e, "invoke MainSceneVisiableSetup [%d]", scene);
        return;
    }
    if (!strcmp(name, "onUnload"))
        return;
    if (!strcmp(name, "close")) {
        if (e->visible && e->visible(e->user)) {   /* 0x00c75fe2 (shown: 0x00acd949) */
            emit(e, "call 00b6b21e");
            emit(e, "call 00c76b02 1");
        } else {
            emit(e, "call 00c76b02 0");
            emit(e, "call 00be7079");
        }
        return;
    }
    if (!strcmp(name, "onChange")) {
        int (*mb)(void *, const char *) = e->member_bool;
        int32_t (*mi)(void *, const char *) = e->member_int;
        o->auto_attack = mb && mb(e->user, "isAutoAttack");
        o->whisper_sound = mb && mb(e->user, "isWhisperSound");
        o->slide_help = mb && mb(e->user, "isSlideHelp");
        o->player_info = mb && mb(e->user, "isPlayerInfo");
        o->monster_info = mb && mb(e->user, "isMonsterInfo");
        o->music_play = mb && mb(e->user, "isMusicPlay");
        o->switch_mode = mb && mb(e->user, "isSwitchMode");
        o->switch_time = mi ? mi(e->user, "switchModeTime") : 0;
        o->effect = (mi ? mi(e->user, "effectLimit") : 0) - (MU_PROGRESS_MUTATION == 15 ? 0 : 1);
        o->mute = mb && mb(e->user, "isMute");
        o->volume = mi ? mi(e->user, "volum") : 0;
        mu_prg_options_apply(e, o);
        return;
    }
}

void mu_prg_options_tick(const mu_prg_options_env *e, mu_prg_options *o)
{
    if (!o->update)
        return;
    if (!(e->visible && e->visible(e->user)))
        return;
    o->update = 0;
    mu_prg_options_set_datas(e, o);
}

void mu_prg_options_set(mu_prg_options *o, int32_t index, int32_t value)
{
    switch (index) {
    case 0: o->auto_attack = (uint8_t)value; break;
    case 1: o->whisper_sound = (uint8_t)value; break;
    case 2: o->slide_help = (uint8_t)value; break;
    case 3: o->player_info = (uint8_t)value; break;
    case 4: o->monster_info = (uint8_t)value; break;
    case 5: o->music_play = (uint8_t)value; break;
    case 6: o->switch_mode = (uint8_t)value; break;
    case 7: o->switch_time = value; break;
    case 8: o->effect = value; break;
    default: return;
    }
    o->update = 1;
}
