# Claude's Mach profiling tools

Build with `make -C mac-play/machprof` on macOS. It compiles x86_64 tools only.
No tool runs, attaches to a task, signs code or changes a bottle during build.
`ent.plist` declares `com.apple.security.cs.debugger`. Signing and task access
remain owner-controlled prerequisites for future isolated profiling.

`stackprof PID THREAD_OR_-1 SECONDS LO_HEX HI_HEX [INTERVAL_US]` uses
thread_get_state flavor 1. In Claude's observed Rosetta configuration x0..x7
hold x86 EAX..EDI, so ESP=x4 and EBP=x5. This is an implementation observation,
not a stable Apple ABI. Use page-aligned, readable ranges for the existing tools.
`EBPWALK=1` follows saved EBP links instead of scanning nearby stack words.
`CHAINS` and `NPC` select private chain/native-PC output paths.

Stack scanning only finds plausible call-preceded return addresses. It previously
misattributed mesh samples to store8 helpers. EBP walks give better attribution
for this frame-pointer build, but still miss omitted/rewritten frames and are
not a precise current x86 instruction pointer. The profiler briefly suspends
and resumes the selected thread. No profiler was run for this publication.

`memdump` reads a PID/range into a private file; `flav` investigates thread-state
flavors. `bytarget.py`, `chain.py`, `fdis.py` and `callsite.py` consume a private
VA-0x00400000 dump selected by `MU_MEMORY_DUMP`. Disassembly helpers require
`i686-w64-mingw32-objdump`. Their scratch/output files must stay private.
