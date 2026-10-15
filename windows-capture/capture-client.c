/* MIT licensed read-only capture helper for the exact user-supplied client.
 * Does not inject, patch, suspend, debug, log in, or terminate a game process.
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>
#include <string.h>

static const char expected[] = "3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a";
static int interactive;

static int finish(int status) {
    if (interactive) { puts("\nPress Enter to close."); (void)getchar(); }
    return status;
}
static void hex(const unsigned char *bytes, char output[65]) {
    static const char digits[] = "0123456789abcdef";
    for (size_t i=0; i<32; ++i) { output[2*i]=digits[bytes[i]>>4]; output[2*i+1]=digits[bytes[i]&15]; }
    output[64]=0;
}
static int hash_bytes(const unsigned char *data, size_t size, char output[65]) {
    if (size>MAXDWORD) return 0;
    BCRYPT_ALG_HANDLE algorithm=NULL;
    BCRYPT_HASH_HANDLE hash=NULL;
    unsigned char digest[32];
    int ok=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)>=0;
    if (ok) ok=BCryptCreateHash(algorithm,&hash,NULL,0,NULL,0,0)>=0;
    if (ok) ok=BCryptHashData(hash,(PUCHAR)data,(ULONG)size,0)>=0;
    if (ok) ok=BCryptFinishHash(hash,digest,32,0)>=0;
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm,0);
    if (ok) hex(digest,output);
    return ok;
}
static int hash_file(const wchar_t *path, char output[65]) {
    FILE *file=_wfopen(path,L"rb");
    if (!file) return 0;
    BCRYPT_ALG_HANDLE algorithm=NULL;
    BCRYPT_HASH_HANDLE hash=NULL;
    unsigned char buffer[32768],digest[32];
    int ok=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,NULL,0)>=0;
    if (ok) ok=BCryptCreateHash(algorithm,&hash,NULL,0,NULL,0,0)>=0;
    size_t count;
    while (ok && (count=fread(buffer,1,sizeof buffer,file))!=0)
        ok=BCryptHashData(hash,buffer,(ULONG)count,0)>=0;
    if (ferror(file)) ok=0;
    if (fclose(file)) ok=0;
    if (ok) ok=BCryptFinishHash(hash,digest,32,0)>=0;
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm,0);
    if (ok) hex(digest,output);
    return ok;
}
static int exact_process(HANDLE process, wchar_t path[32768], char digest[65]) {
    DWORD size=32768,exit_code=0;
    if (!GetExitCodeProcess(process,&exit_code) || exit_code!=STILL_ACTIVE) return 0;
    if (!QueryFullProcessImageNameW(process,0,path,&size)) return 0;
    const wchar_t *name=wcsrchr(path,L'\\'); name=name ? name+1 : path;
    return !_wcsicmp(name,L"main.exe") && hash_file(path,digest) && !strcmp(digest,expected);
}
static int allowed(const wchar_t *name) {
    return !_wcsicmp(name,L"main.exe") || !_wcsicmp(name,L"IGC.dll") || !_wcsicmp(name,L"RGS.dll");
}
static int json_wide(FILE *file, const wchar_t *value) {
    int size=WideCharToMultiByte(CP_UTF8,0,value,-1,NULL,0,NULL,NULL);
    if (size<=0) return 0;
    char *text=malloc((size_t)size);
    if (!text) return 0;
    if (!WideCharToMultiByte(CP_UTF8,0,value,-1,text,size,NULL,NULL)) { free(text); return 0; }
    fputc('"',file);
    for (const unsigned char *p=(unsigned char *)text; *p; ++p) {
        if (*p=='"' || *p=='\\') { fputc('\\',file); fputc(*p,file); }
        else if (*p<32) fprintf(file,"\\u%04x",(unsigned)*p);
        else fputc(*p,file);
    }
    fputc('"',file); free(text); return !ferror(file);
}
static int write_new(const wchar_t *path, const unsigned char *data, size_t size) {
    if (size>MAXDWORD) return 0;
    HANDLE file=CreateFileW(path,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
    if (file==INVALID_HANDLE_VALUE) return 0;
    DWORD written=0;
    int ok=WriteFile(file,data,(DWORD)size,&written,NULL) && written==(DWORD)size;
    if (!CloseHandle(file)) ok=0;
    return ok;
}
static int executable(DWORD protection) {
    return !(protection & (PAGE_GUARD|PAGE_NOACCESS)) &&
           (protection & (PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY));
}
static int self_test(void) {
    char digest[65];
    if (!hash_bytes((const unsigned char *)"abc",3,digest) ||
        strcmp(digest,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")) return 1;
    unsigned char magic[2]; SIZE_T read=0;
    if (!ReadProcessMemory(GetCurrentProcess(),GetModuleHandleW(NULL),magic,2,&read) ||
        read!=2 || magic[0]!='M' || magic[1]!='Z') return 1;
    puts("SHA-256 known-vector and own-process memory-read smoke tests passed.");
    return 0;
}

int wmain(int argc, wchar_t **argv) {
    if (argc==2 && !wcscmp(argv[1],L"--self-test")) return self_test();
    if (argc==2 && !wcscmp(argv[1],L"--version")) { puts("MuMatrix read-only capture 1.0"); return 0; }
    interactive=argc==1;
    if (argc>3) { puts("Usage: capture-client.exe [PID [NEW_OUTPUT_DIRECTORY]]"); return 1; }
    puts("Mu The Matrix executable-region capture\nStart the original game and stay at the login screen before signing in.");
    DWORD pid=0;
    if (argc>=2) {
        wchar_t *end; unsigned long parsed=wcstoul(argv[1],&end,10);
        if (!parsed || *end) { puts("Invalid process ID."); return finish(1); }
        pid=(DWORD)parsed;
    } else {
        HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
        PROCESSENTRY32W entry={0}; entry.dwSize=sizeof entry;
        unsigned matches=0;
        if (snapshot!=INVALID_HANDLE_VALUE && Process32FirstW(snapshot,&entry)) do {
            if (_wcsicmp(entry.szExeFile,L"main.exe")) continue;
            HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,entry.th32ProcessID);
            wchar_t path[32768]; char digest[65];
            if (process && exact_process(process,path,digest)) { pid=entry.th32ProcessID; ++matches; }
            if (process) CloseHandle(process);
        } while (Process32NextW(snapshot,&entry));
        if (snapshot!=INVALID_HANDLE_VALUE) CloseHandle(snapshot);
        if (matches!=1) {
            printf("Found %u matching readable game processes. Keep one exact-version client running.\n",matches);
            puts("If the game runs elevated, run this helper as administrator too. No elevation is requested automatically.");
            return finish(1);
        }
    }
    HANDLE process=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,FALSE,pid);
    if (!process) { printf("Cannot read process, Windows error %lu.\n",GetLastError()); return finish(1); }
    wchar_t target[32768]; char target_hash[65];
    if (!exact_process(process,target,target_hash)) {
        puts("Process is not the exact supplied main.exe build, is unreadable, or has exited.");
        CloseHandle(process); return finish(1);
    }
    FILETIME created,exited,kernel,user;
    if (!GetProcessTimes(process,&created,&exited,&kernel,&user)) { CloseHandle(process); return finish(1); }
    ULARGE_INTEGER creation; creation.LowPart=created.dwLowDateTime; creation.HighPart=created.dwHighDateTime;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);
    if (snapshot==INVALID_HANDLE_VALUE) {
        printf("Cannot enumerate modules, Windows error %lu.\n",GetLastError()); CloseHandle(process); return finish(1);
    }
    wchar_t directory[32768]; SYSTEMTIME now; GetSystemTime(&now);
    if (argc==3) {
        if (wcslen(argv[2])>=32000) { CloseHandle(snapshot); CloseHandle(process); return finish(1); }
        wcscpy(directory,argv[2]);
    } else {
        if (!GetModuleFileNameW(NULL,directory,32768)) { CloseHandle(snapshot); CloseHandle(process); return finish(1); }
        wchar_t *slash=wcsrchr(directory,L'\\'); if (slash) *slash=0; else wcscpy(directory,L".");
        size_t length=wcslen(directory);
        if (length>32000) { CloseHandle(snapshot); CloseHandle(process); return finish(1); }
        swprintf(directory+length,32768-length,L"\\MuMatrixCapture-%04u%02u%02u-%02u%02u%02u-%lu",
                 now.wYear,now.wMonth,now.wDay,now.wHour,now.wMinute,now.wSecond,pid);
    }
    if (!CreateDirectoryW(directory,NULL)) {
        printf("Output must be a new directory. Windows error %lu.\n",GetLastError());
        CloseHandle(snapshot); CloseHandle(process); return finish(1);
    }
    wchar_t manifest_path[32768];
    swprintf(manifest_path,32768,L"%ls\\capture.json",directory);
    FILE *manifest=_wfopen(manifest_path,L"wbx");
    if (!manifest) { CloseHandle(snapshot); CloseHandle(process); return finish(1); }
    fprintf(manifest,"{\n\"format\":\"mu-executable-region-capture-v1\",\n\"pid\":%lu,\n\"process_creation_filetime\":\"%llu\",\n\"target_sha256\":\"%s\",\n\"target_path\":",
            pid,(unsigned long long)creation.QuadPart,target_hash);
    json_wide(manifest,target);
    fprintf(manifest,",\n\"captured_utc\":\"%04u-%02u-%02uT%02u:%02u:%02uZ\",\n\"regions\":[\n",
            now.wYear,now.wMonth,now.wDay,now.wHour,now.wMinute,now.wSecond);
    MODULEENTRY32W module={0}; module.dwSize=sizeof module;
    unsigned records=0,good=0,failures=0,matched_modules=0;
    if (Module32FirstW(snapshot,&module)) do {
        if (!allowed(module.szModule)) continue;
        ++matched_modules;
        uintptr_t start=(uintptr_t)module.modBaseAddr,limit=start+module.modBaseSize;
        if (limit<start || module.modBaseSize>512u*1024u*1024u) { ++failures; continue; }
        char module_hash[65]=""; hash_file(module.szExePath,module_hash);
        for (uintptr_t cursor=start; cursor<limit;) {
            MEMORY_BASIC_INFORMATION region;
            if (!VirtualQueryEx(process,(LPCVOID)cursor,&region,sizeof region)) { ++failures; break; }
            uintptr_t region_start=(uintptr_t)region.BaseAddress, end=region_start+region.RegionSize;
            if (end<=cursor) { ++failures; break; }
            if (end>limit) end=limit;
            if (region.State==MEM_COMMIT && region.Type==MEM_IMAGE && executable(region.Protect)) {
                SIZE_T length=end-cursor,read=0;
                unsigned char *buffer=malloc(length);
                int ok=buffer && ReadProcessMemory(process,(LPCVOID)cursor,buffer,length,&read) && read==length;
                DWORD error=ok ? 0 : GetLastError();
                char digest[65]="";
                wchar_t name[512],path[32768];
                swprintf(name,512,L"%ls-%016llx.bin",module.szModule,(unsigned long long)cursor);
                swprintf(path,32768,L"%ls\\%ls",directory,name);
                if (ok) ok=hash_bytes(buffer,length,digest) && write_new(path,buffer,length);
                if (!ok && !error) error=GetLastError();
                free(buffer);
                if (records++) fprintf(manifest,",\n");
                fprintf(manifest,"{\"module\":"); json_wide(manifest,module.szModule);
                fprintf(manifest,",\"module_base\":\"0x%llx\",\"module_file_sha256\":\"%s\",\"address\":\"0x%llx\",\"bytes\":%llu,\"protection\":%lu,\"status\":\"%s\",\"windows_error\":%lu,\"file\":",
                        (unsigned long long)start,module_hash,(unsigned long long)cursor,
                        (unsigned long long)length,region.Protect,ok?"captured":"failed",error);
                if (ok) json_wide(manifest,name); else fputs("null",manifest);
                fprintf(manifest,",\"sha256\":\"%s\"}",digest);
                if (ok) ++good; else ++failures;
            }
            cursor=end;
        }
    } while (Module32NextW(snapshot,&module));
    char after_hash[65]; DWORD exit_code=0;
    int unchanged=hash_file(target,after_hash) && !strcmp(target_hash,after_hash);
    int running=GetExitCodeProcess(process,&exit_code) && exit_code==STILL_ACTIVE;
    int complete=good>0 && !failures && unchanged && running;
    fprintf(manifest,"\n],\n\"captured_regions\":%u,\n\"matched_modules\":%u,\n\"failures\":%u,\n\"target_file_unchanged\":%s,\n\"process_still_running\":%s,\n\"complete_within_scope\":%s,\n\"limitations\":[\"Live unsuspended reads are not an atomic process snapshot.\",\"Only executable MEM_IMAGE regions in main.exe, IGC.dll and RGS.dll were selected.\",\"Private allocations, data-only pages, stacks, credentials, registers and other processes were not selected.\",\"The capture alone does not prove code was unpacked or behavior reconstructed.\"]\n}\n",
            good,matched_modules,failures,unchanged?"true":"false",running?"true":"false",complete?"true":"false");
    if (ferror(manifest)) complete=0;
    if (fclose(manifest)) complete=0;
    CloseHandle(snapshot); CloseHandle(process);
    printf("Captured %u executable regions; %u failures.\n",good,failures);
    wprintf(L"Output: %ls\n",directory);
    puts("The game was left running. Close it normally when finished.\nReturn the complete capture folder, including capture.json, for analysis.");
    return finish(complete?0:2);
}
