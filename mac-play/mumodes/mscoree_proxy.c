/* mscoree.dll proxy for the Mu The Matrix launcher (a .NET exe imports only mscoree, resolved from
   its own folder first): forwards every export by ordinal to the real system32 mscoree.dll and
   installs the curated display-mode list (modehook.c), which also tolerates dmSize == 0. */
#include <windows.h>
#include "mnames.h"
#include "modehook.c"
BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID res)
{
    (void)res;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        HMODULE real = LoadLibraryA("C:\\windows\\system32\\mscoree.dll");
        if (!real || real == inst) return FALSE;
        for (size_t i = 0; i < sizeof ms_ords / sizeof ms_ords[0]; i++) *ms_slots[i] = (void *)GetProcAddress(real, MAKEINTRESOURCEA(ms_ords[i]));
        modehook_install();
    }
    return TRUE;
}
