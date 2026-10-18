/* wicfix.c — let the launcher decode the server's custom skin under Wine 11 (MAC-APP-006).
 * Included by mscoree_proxy.c, so it runs only in MuTheMatrix.exe. Disable with MU_LAUNCHER_WICFIX=0.
 *
 * The skin (Data\Launcher\Design\Template.design) contains JPEG images that the launcher decodes with
 * WPF (BitmapDecoder.Create(stream, ..., OnLoad)). WPF hands WIC an IStream whose Read calls back into
 * managed code (System.Windows.Media.StreamAsIStream.Read), and that callback writes *pcbRead
 * unconditionally. Wine 11's JPEG decoder (CrossOver 26 / Wine CX 26.3) reads the metadata markers
 * with IStream_Read(stream, buf, 4, NULL), so the callback throws a NullReferenceException through
 * the native decoder; the launcher reports a Critical Error and then crashes with an access violation
 * in a WIC finalizer. Upstream Wine fixed this in windowscodecs (commit 111e5197, "Always pass a valid
 * pcbRead pointer to IStream::Read()"); this is the same fix applied from outside:
 * IWICImagingFactory_CreateDecoderFromStream_Proxy, the export WPF P/Invokes, is redirected (export
 * table entry, set when windowscodecs.dll loads) to a wrapper that gives the decoder a forwarding
 * IStream whose Read always passes a valid pcbRead (and, like upstream, reports a short read as
 * S_FALSE when the caller passed NULL). Nothing in the launcher, the skin or Wine is modified. */
#include <windows.h>
#include <objidl.h>
#include <stdio.h>
#include <string.h>

typedef HRESULT (WINAPI *WcCdfsFn)(void *, IStream *, const GUID *, DWORD, void **);
static WcCdfsFn wc_cdfs;
static volatile LONG wc_wrapped;

/* local copies: the build links no uuid library */
static const GUID wc_iid_unknown = {0x00000000, 0x0000, 0x0000, {0xc0, 0, 0, 0, 0, 0, 0, 0x46}};
static const GUID wc_iid_seqstream = {0x0c733a30, 0x2a1c, 0x11ce, {0xad, 0xe5, 0x00, 0xaa, 0x00, 0x44, 0x77, 0x3d}};
static const GUID wc_iid_stream = {0x0000000c, 0x0000, 0x0000, {0xc0, 0, 0, 0, 0, 0, 0, 0x46}};
typedef struct { IStream iface; LONG ref; IStream *inner; } WcStream;
static IStream *wc_wrap(IStream *inner);
#define WC_IN(This) (((WcStream *)(This))->inner)

static HRESULT STDMETHODCALLTYPE wc_QueryInterface(IStream *This, REFIID riid, void **out)
{
    if (!out) return E_POINTER;
    if (IsEqualIID(riid, &wc_iid_unknown) || IsEqualIID(riid, &wc_iid_seqstream) || IsEqualIID(riid, &wc_iid_stream)) {
        *out = This; InterlockedIncrement(&((WcStream *)This)->ref); return S_OK;
    }
    return WC_IN(This)->lpVtbl->QueryInterface(WC_IN(This), riid, out);
}
static ULONG STDMETHODCALLTYPE wc_AddRef(IStream *This) { return InterlockedIncrement(&((WcStream *)This)->ref); }
static ULONG STDMETHODCALLTYPE wc_Release(IStream *This)
{
    WcStream *s = (WcStream *)This; ULONG r = InterlockedDecrement(&s->ref);
    if (!r) { s->inner->lpVtbl->Release(s->inner); HeapFree(GetProcessHeap(), 0, s); }
    return r;
}
static HRESULT STDMETHODCALLTYPE wc_Read(IStream *This, void *pv, ULONG cb, ULONG *pcbRead)
{
    ULONG n = 0;
    HRESULT hr = WC_IN(This)->lpVtbl->Read(WC_IN(This), pv, cb, pcbRead ? pcbRead : &n);
    if (!pcbRead && SUCCEEDED(hr) && n != cb) hr = S_FALSE;
    return hr;
}
static HRESULT STDMETHODCALLTYPE wc_Write(IStream *This, const void *pv, ULONG cb, ULONG *pcbWritten)
{
    ULONG n = 0;
    return WC_IN(This)->lpVtbl->Write(WC_IN(This), pv, cb, pcbWritten ? pcbWritten : &n);
}
static HRESULT STDMETHODCALLTYPE wc_Seek(IStream *This, LARGE_INTEGER move, DWORD origin, ULARGE_INTEGER *pos)
{
    ULARGE_INTEGER p;
    return WC_IN(This)->lpVtbl->Seek(WC_IN(This), move, origin, pos ? pos : &p);
}
static HRESULT STDMETHODCALLTYPE wc_SetSize(IStream *This, ULARGE_INTEGER size) { return WC_IN(This)->lpVtbl->SetSize(WC_IN(This), size); }
static HRESULT STDMETHODCALLTYPE wc_CopyTo(IStream *This, IStream *dst, ULARGE_INTEGER cb, ULARGE_INTEGER *rd, ULARGE_INTEGER *wr)
{
    ULARGE_INTEGER a, b;
    return WC_IN(This)->lpVtbl->CopyTo(WC_IN(This), dst, cb, rd ? rd : &a, wr ? wr : &b);
}
static HRESULT STDMETHODCALLTYPE wc_Commit(IStream *This, DWORD flags) { return WC_IN(This)->lpVtbl->Commit(WC_IN(This), flags); }
static HRESULT STDMETHODCALLTYPE wc_Revert(IStream *This) { return WC_IN(This)->lpVtbl->Revert(WC_IN(This)); }
static HRESULT STDMETHODCALLTYPE wc_LockRegion(IStream *This, ULARGE_INTEGER off, ULARGE_INTEGER cb, DWORD type) { return WC_IN(This)->lpVtbl->LockRegion(WC_IN(This), off, cb, type); }
static HRESULT STDMETHODCALLTYPE wc_UnlockRegion(IStream *This, ULARGE_INTEGER off, ULARGE_INTEGER cb, DWORD type) { return WC_IN(This)->lpVtbl->UnlockRegion(WC_IN(This), off, cb, type); }
static HRESULT STDMETHODCALLTYPE wc_Stat(IStream *This, STATSTG *st, DWORD flag) { return WC_IN(This)->lpVtbl->Stat(WC_IN(This), st, flag); }
static HRESULT STDMETHODCALLTYPE wc_Clone(IStream *This, IStream **out)
{
    IStream *c = NULL;
    if (!out) return E_POINTER;
    HRESULT hr = WC_IN(This)->lpVtbl->Clone(WC_IN(This), &c);
    *out = NULL;
    if (SUCCEEDED(hr) && c) { *out = wc_wrap(c); c->lpVtbl->Release(c); if (!*out) hr = E_OUTOFMEMORY; }
    return hr;
}
static IStreamVtbl wc_vtbl = {
    wc_QueryInterface, wc_AddRef, wc_Release, wc_Read, wc_Write, wc_Seek, wc_SetSize, wc_CopyTo,
    wc_Commit, wc_Revert, wc_LockRegion, wc_UnlockRegion, wc_Stat, wc_Clone
};
static IStream *wc_wrap(IStream *inner)
{
    WcStream *s = HeapAlloc(GetProcessHeap(), 0, sizeof *s);
    if (!s) return NULL;
    s->iface.lpVtbl = &wc_vtbl; s->ref = 1; s->inner = inner; inner->lpVtbl->AddRef(inner);
    return &s->iface;
}

static HRESULT WINAPI wc_CreateDecoderFromStream(void *factory, IStream *stream, const GUID *vendor, DWORD options, void **decoder)
{
    IStream *w = stream ? wc_wrap(stream) : NULL;
    HRESULT hr = wc_cdfs(factory, w ? w : stream, vendor, options, decoder);
    if (w) {
        w->lpVtbl->Release(w);                         /* the decoder keeps its own reference */
        if (!InterlockedExchange(&wc_wrapped, 1)) {
            FILE *lf = fopen("C:\\mutools\\winfix.log", "a");
            if (lf) { fprintf(lf, "  WIC stream fix used (first decoder hr=0x%08lx)\n", (unsigned long)hr); fclose(lf); }
        }
    }
    return hr;
}

/* Point the module's export-table entry for name at hook; returns the previous address or NULL.
   GetProcAddress (the CLR's P/Invoke binding) then resolves the export to the hook. */
static void *wc_eat(HMODULE m, const char *name, void *hook)
{
    unsigned char *b = (unsigned char *)m;
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(b + ((IMAGE_DOS_HEADER *)b)->e_lfanew);
    IMAGE_DATA_DIRECTORY dir = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
    if (!dir.VirtualAddress) return NULL;
    IMAGE_EXPORT_DIRECTORY *e = (IMAGE_EXPORT_DIRECTORY *)(b + dir.VirtualAddress);
    DWORD *names = (DWORD *)(b + e->AddressOfNames), *funcs = (DWORD *)(b + e->AddressOfFunctions);
    WORD *ords = (WORD *)(b + e->AddressOfNameOrdinals);
    for (DWORD i = 0; i < e->NumberOfNames; i++) {
        if (strcmp((const char *)(b + names[i]), name)) continue;
        DWORD *slot = &funcs[ords[i]], old;
        if (*slot >= dir.VirtualAddress && *slot < dir.VirtualAddress + dir.Size) return NULL;   /* forwarder */
        void *prev = b + *slot;
        if (!VirtualProtect(slot, sizeof *slot, PAGE_READWRITE, &old)) return NULL;
        *slot = (DWORD)((ULONG_PTR)hook - (ULONG_PTR)b);
        VirtualProtect(slot, sizeof *slot, old, &old);
        return prev;
    }
    return NULL;
}

static void wc_patch(HMODULE m)
{
    if (wc_cdfs || !m) return;
    void *prev = wc_eat(m, "IWICImagingFactory_CreateDecoderFromStream_Proxy", (void *)wc_CreateDecoderFromStream);
    if (prev) wc_cdfs = (WcCdfsFn)prev;
    FILE *lf = fopen("C:\\mutools\\winfix.log", "a");
    if (lf) { fprintf(lf, "  WIC stream fix %s\n", prev ? "on" : "off (export not found)"); fclose(lf); }
}

/* ntdll loader notifications (not in all MinGW headers) */
typedef struct { USHORT Length, MaximumLength; PWSTR Buffer; } WcUStr;
typedef struct { ULONG Flags; const WcUStr *FullDllName, *BaseDllName; PVOID DllBase; ULONG SizeOfImage; } WcDllData;
typedef VOID (CALLBACK *WcDllCb)(ULONG, const WcDllData *, PVOID);
typedef LONG (NTAPI *WcRegFn)(ULONG, WcDllCb, PVOID, PVOID *);

static VOID CALLBACK wc_dll_loaded(ULONG reason, const WcDllData *d, PVOID ctx)
{
    static const WCHAR want[] = L"windowscodecs.dll";
    (void)ctx;
    if (reason != 1 || !d || !d->BaseDllName || !d->BaseDllName->Buffer) return;          /* 1 = loaded */
    if (d->BaseDllName->Length != sizeof want - sizeof(WCHAR)) return;
    if (CompareStringOrdinal(d->BaseDllName->Buffer, d->BaseDllName->Length / sizeof(WCHAR), want, -1, TRUE) != CSTR_EQUAL) return;
    wc_patch((HMODULE)d->DllBase);
}

/* returns 1 when the fix is armed (applied now, or when windowscodecs.dll loads) */
static int wicfix_install(void)
{
    char v[8]; static PVOID cookie;
    if (GetEnvironmentVariableA("MU_LAUNCHER_WICFIX", v, sizeof v) && v[0] == '0') return 0;
    HMODULE w = GetModuleHandleA("windowscodecs.dll");
    if (w) { wc_patch(w); return wc_cdfs != NULL; }
    WcRegFn reg = (WcRegFn)GetProcAddress(GetModuleHandleA("ntdll.dll"), "LdrRegisterDllNotification");
    return reg && reg(0, wc_dll_loaded, NULL, &cookie) >= 0;
}
