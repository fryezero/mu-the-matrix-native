/* modehook.c — present an exact, curated display-mode list to this process.
 * C:\mutools\mu-modes.txt lists modes ("960x600 1024x640 1280x800 1600x1000 1728x1080").
 * EnumDisplaySettingsA/W then enumerate exactly those (32 bpp, 60 Hz, attributes copied from a
 * real 60 Hz mode), so the launcher's Settings list and the game's DevModeIndex refer to the same
 * sizes. ENUM_CURRENT/REGISTRY_SETTINGS and named devices pass through unchanged. */
#include <windows.h>
#include <stdio.h>

typedef struct { DWORD w, h; } MhMode;
static MhMode mh_modes[16]; static int mh_n;
typedef BOOL (WINAPI *MhEdsExA)(LPCSTR, DWORD, DEVMODEA *, DWORD);
typedef BOOL (WINAPI *MhEdsExW)(LPCWSTR, DWORD, DEVMODEW *, DWORD);
static MhEdsExA mh_exa; static MhEdsExW mh_exw;
static DWORD mh_tmpl = (DWORD)-1;

static DWORD mh_template(void)
{   /* first real 32 bpp 60 Hz mode (fall back to mode 0) */
    if (mh_tmpl != (DWORD)-1) return mh_tmpl;
    DEVMODEA dm; mh_tmpl = 0;
    for (DWORD i = 0;; i++) {
        dm.dmSize = sizeof dm; dm.dmDriverExtra = 0;
        if (!mh_exa(NULL, i, &dm, 0)) break;
        if (dm.dmBitsPerPel == 32 && dm.dmDisplayFrequency == 60) { mh_tmpl = i; break; }
    }
    return mh_tmpl;
}
static BOOL WINAPI mh_EnumA(LPCSTR dev, DWORD i, DEVMODEA *dm)
{
    if (dm && dm->dmSize == 0) dm->dmSize = sizeof(DEVMODEA);   /* callers that forget dmSize work on Windows; Wine rejects them */
    if (dev || i == ENUM_CURRENT_SETTINGS || i == ENUM_REGISTRY_SETTINGS) return mh_exa(dev, i, dm, 0);
    if ((int)i >= mh_n || !mh_exa(NULL, mh_template(), dm, 0)) return FALSE;
    dm->dmPelsWidth = mh_modes[i].w; dm->dmPelsHeight = mh_modes[i].h; dm->dmBitsPerPel = 32; dm->dmDisplayFrequency = 60;
    dm->dmDisplayFixedOutput = 0;   /* Wine reports DMDFO_CENTER; the launcher keeps only DMDFO_DEFAULT modes */
    return TRUE;
}
static BOOL WINAPI mh_EnumW(LPCWSTR dev, DWORD i, DEVMODEW *dm)
{
    if (dm && dm->dmSize == 0) dm->dmSize = sizeof(DEVMODEW);
    if (dev || i == ENUM_CURRENT_SETTINGS || i == ENUM_REGISTRY_SETTINGS) return mh_exw(dev, i, dm, 0);
    if ((int)i >= mh_n || !mh_exw(NULL, mh_template(), dm, 0)) return FALSE;
    dm->dmPelsWidth = mh_modes[i].w; dm->dmPelsHeight = mh_modes[i].h; dm->dmBitsPerPel = 32; dm->dmDisplayFrequency = 60;
    dm->dmDisplayFixedOutput = 0;
    return TRUE;
}
static void mh_jmp(void *from, void *to)
{
    DWORD old; unsigned char *p = (unsigned char *)from;
    if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old)) return;
    p[0] = 0xE9; *(int *)(p + 1) = (int)((unsigned char *)to - (p + 5));
    VirtualProtect(p, 5, old, &old); FlushInstructionCache(GetCurrentProcess(), p, 5);
}
/* returns number of modes installed (0 = no config / not hooked) */
static int modehook_install(void)
{
    FILE *f = fopen("C:\\mutools\\mu-modes.txt", "r");
    if (!f) return 0;
    unsigned w, h;
    while (mh_n < 16 && fscanf(f, " %ux%u", &w, &h) == 2) { mh_modes[mh_n].w = w; mh_modes[mh_n].h = h; mh_n++; }
    fclose(f);
    if (!mh_n) return 0;
    HMODULE u = GetModuleHandleA("user32.dll"); if (!u) u = LoadLibraryA("user32.dll");
    mh_exa = (MhEdsExA)GetProcAddress(u, "EnumDisplaySettingsExA");
    mh_exw = (MhEdsExW)GetProcAddress(u, "EnumDisplaySettingsExW");
    void *a = (void *)GetProcAddress(u, "EnumDisplaySettingsA"), *wp = (void *)GetProcAddress(u, "EnumDisplaySettingsW");
    if (!mh_exa || !mh_exw || !a || !wp || a == (void *)mh_exa || wp == (void *)mh_exw) return 0;
    mh_jmp(a, (void *)mh_EnumA); mh_jmp(wp, (void *)mh_EnumW);
    { char exe[MAX_PATH]; GetModuleFileNameA(NULL, exe, MAX_PATH); FILE *lf = fopen("C:\\mutools\\modehook.log", "a");
      if (lf) { fprintf(lf, "%s: %d modes hooked\n", exe, mh_n); fclose(lf); } }
    return mh_n;
}
