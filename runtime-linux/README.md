# Recover runtime evidence on an Apple Silicon Mac

This route runs an emulated x86-64 Linux computer with Wine. It avoids Rosetta
and needs no physical Windows PC. It is an analysis environment, not the future
native macOS game.

The local experiment booted Debian 12, installed Wine 8.0 for both architectures,
created a software OpenGL 4.5 context, ran an authored 32-bit console probe, and
passed the x64 capture helper's own-memory/hash self-test. The exact client ran
far enough to restore its first executable section. No login or gameplay was
demonstrated. [The research note](../docs/research/mac-runtime.md) has primary
sources, the pinned guest image digest and the cloud-init configuration.

## Prepare a disposable guest

Install the host tools with `brew install qemu xorriso`. Download the pinned
Debian image from the research note, verify its SHA-512 and make the base file
read-only. Keep all VM files and the locally generated SSH private key under
the ignored `runtime/x86/` directory. Never overwrite an existing working disk.

Create a 24 GiB qcow2 overlay with `qemu-img create -f qcow2 -F qcow2 -b
ABSOLUTE_BASE_PATH runtime/x86/working.qcow2 24G`. The base path must be absolute.
Create the `CIDATA` seed ISO using the research note's explicit recovery user,
a locally generated SSH public key, and a unique instance ID. Disable password
login. The private key stays on the host.

The tested launch uses these arguments from the repository root:

```sh
qemu-system-x86_64 \
  -machine q35 -accel tcg,thread=multi -cpu max -smp 2 -m 4096 \
  -drive file=runtime/x86/working.qcow2,if=virtio,format=qcow2 \
  -drive file=runtime/x86/seed.iso,media=cdrom,format=raw,readonly=on \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:22222-:22 \
  -device virtio-net-pci,netdev=net0 \
  -display none -serial file:runtime/x86/serial.log -monitor none \
  -qmp unix:runtime/x86/qmp.sock,server=on,wait=off \
  -pidfile runtime/x86/qemu.pid -daemonize
```

The loopback port and socket must be free. `-daemonize` keeps the VM independent
of an interrupted terminal/tool session. Use the existing guest when available;
do not start two instances against the same disk. Shut down with `sudo poweroff`
inside the guest before changing launch arguments or backing up the disk.

Install the Wine, Xvfb and both Mesa architectures listed in the research note.
The tested guest had `wine`, `wine32:i386`, `wine64` version `8.0~repack-4`, and
Mesa `22.3.6-1+deb12u2`. Verify package installation rather than trusting a marker
file after a multi-command setup. Copy a separately supplied matching client
into the guest's own writable disk and verify main.exe's pinned SHA-256.

A read-only `virtio-9p-pci` transfer mount was tested with this Homebrew QEMU
build. A sequential tar transfer avoided copying thousands of files one by one.
Keep the source share read-only and run from the guest copy. Preserve filesystem
paths and data files; do not publish the archive or VM disk.

After installation and transfer, shut down and restart with `restrict=on` in
the `-netdev user,...` argument. Omit the seed ISO and source share when no longer
needed. The explicit SSH forward still works. Verify a guest outbound TCP
connection fails before running the client. No game account is needed.

## Check graphics and bitness

Start Xvfb inside the guest, using a free display number:

```sh
Xvfb :99 -screen 0 1280x1024x24 +extension GLX -nolisten tcp
```

Run `glxinfo -B` with `DISPLAY=:99`, `LIBGL_ALWAYS_SOFTWARE=true` and
`GALLIUM_DRIVER=llvmpipe`. The actual result must report a working context.
Create a new `WINEARCH=win64` prefix so the x86 client and x64 helper can share it.
Use the same user, `WINEPREFIX` and display for both. The tested setup used
`WINEDLLOVERRIDES="mscoree,mshtml="` during initialization and configured Wine's
version as Windows 10.

An authored 32-bit console program ran successfully. The x64 helper's
`--self-test` passed. Actual x64 module enumeration against the game returned
Windows error 998. A same-bitness helper built with `i686-w64-mingw32-gcc` read
seven executable regions, but its manifest was incomplete with two failures
and the target no longer running by completion. Neither result is a complete
native Windows capture.

## Capture the restored first section

Start the copied client in its own directory with outbound networking blocked.
Use a wall-clock timeout. A 150-second run restored the first executable region;
an early 10-second capture was still packed. A later 92-second observation
contained the same restored region digest as the first capture. Timings are
observations from this configuration, not readiness guarantees.

Copy `capture_text.py` into the guest. Select the Linux PID of the actual
`main.exe` process, not the surrounding timeout or shell. Run it with read
permission for `/proc/PID/mem`, typically through `sudo` inside this isolated VM:

```sh
sudo python3 capture_text.py \
  --pid LINUX_MAIN_PID \
  --target /home/recovery/client/main.exe \
  --output /home/recovery/NEW_CAPTURE_DIRECTORY
```

The tool accepts only the pinned main.exe hash, requires the selected process
to run from its directory, and reads only the first executable image section at
`0x00401000`, length 23,572,480. It checks mapped coverage, process start identity,
the PE signature, mapped header device/inode against the selected file before
and after reading, post-read mapping/identity and the unchanged source file.
It flushes the payload and manifest before returning. Review
`complete_within_scope`, hash and length before importing. A capture still does
not prove execution or behavioral equivalence of every captured function.

Transfer the complete output directory back to ignored local evidence and
recompute its digest. Keep logs, manifests, snapshots and decompiler outputs
private. The current next task is mapping restored functions with REA/Ghidra
and reconstructing bounded behaviors through tests.
