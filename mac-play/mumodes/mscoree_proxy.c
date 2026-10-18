/* mscoree.dll proxy for the Mu The Matrix launcher (a .NET exe imports only mscoree, resolved from
   its own folder first): forwards every export by ordinal to the real system32 mscoree.dll and
   installs the curated display-mode list (modehook.c), which also tolerates dmSize == 0, and the
   macOS window fixes (winfix.c: no floating news panel, minimize to the Dock, Dock click restores) and
   the WIC stream fix that lets the server's custom skin load under Wine 11 (wicfix.c). */
#include <windows.h>
#include "mnames.h"
#include "modehook.c"
#include "winfix.c"
#include "wicfix.c"
BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID res)
{
    (void)res;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        HMODULE real = LoadLibraryA("C:\\windows\\system32\\mscoree.dll");
        if (!real || real == inst) return FALSE;
        for (size_t i = 0; i < sizeof ms_ords / sizeof ms_ords[0]; i++) *ms_slots[i] = (void *)GetProcAddress(real, MAKEINTRESOURCEA(ms_ords[i]));
        modehook_install();
        int wf = winfix_install();
        char exe[MAX_PATH]; GetModuleFileNameA(NULL, exe, MAX_PATH);
        FILE *lf = fopen("C:\\mutools\\winfix.log", "a");
        if (lf) { fprintf(lf, "%s: window fix %s\n", exe, wf ? "on" : "off"); fclose(lf); }
        int wc = wicfix_install();
        if ((lf = fopen("C:\\mutools\\winfix.log", "a"))) { fprintf(lf, "  WIC stream fix %s\n", wc ? "armed" : "off"); fclose(lf); }
    }
    return TRUE;
}
