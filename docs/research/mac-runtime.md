# Runtime recovery entirely on the Mac

Research checked 2026-10-15. This note proposes an experiment; it does not report a successful client launch.

## Decision

Try an emulated x86-64 Linux computer inside QEMU, then run the exact x86 client under Linux Wine. Use QEMU's TCG CPU emulator explicitly. This route avoids the Mac Rosetta execution path that currently stops at `invalid gdt selector index 6`. It needs neither a physical Windows PC nor a Windows guest.

QEMU documents x86 system emulation on supported hosts, and lists Arm among its supported host architectures. TCG provides CPU emulation, whereas the platform hypervisors accelerate compatible guest architectures. These facts support the experiment, but do not establish compatibility with this protected executable. [QEMU emulation](https://www.qemu.org/docs/master/about/emulation.html), [supported hosts](https://www.qemu.org/docs/master/about/build-platforms.html), [accelerators](https://www.qemu.org/docs/master/system/introduction.html).

QEMU's x86 TCG implementation has explicit GDT/LDT descriptor lookup and protected-mode segment loading. That is why a full x86 guest is a useful next test for the observed selector failure. It does not prove that the selector error was the only startup problem. [QEMU segment implementation](https://github.com/qemu/qemu/blob/master/target/i386/tcg/seg_helper.c).

## Local observations

Read-only checks on this Mac returned `arm64`, macOS 27.0.1 build 26A434, 16 GiB RAM, 10 logical CPUs and about 74 GiB free on the project volume. Neither `qemu-system-x86_64` nor `qemu-img` was on the command search path. Those values are a point-in-time capacity check, not requirements.

Start with 4 GiB guest RAM, two emulated CPUs and a sparse 24 GiB working disk. These are proposed limits. Measure actual disk growth and boot time before increasing them. Full CPU emulation and software rendering may be slow enough to make interactive gameplay impractical. The immediate goal is a startup observation and useful process-memory evidence.

## Pinned guest image

Use the official Debian 12 **generic amd64** cloud image. The broader generic kernel is a conservative initial choice for an emulated PC. Debian publishes both generic and genericcloud variants; either requires testing with the actual devices selected.

- Image: [debian-12-generic-amd64-20261015-2632.qcow2](https://cloud.debian.org/images/cloud/bookworm/20261015-2632/debian-12-generic-amd64-20261015-2632.qcow2).
- Manifest: [SHA512SUMS](https://cloud.debian.org/images/cloud/bookworm/20261015-2632/SHA512SUMS).
- Metadata: [image JSON](https://cloud.debian.org/images/cloud/bookworm/20261015-2632/debian-12-generic-amd64-20261015-2632.json).
- Expected SHA-512, read from that manifest:

```text
c2ffec728a10586010bd2a2edfde80d890326066fd4abb06ef98deefa29a8bfe8963c2a13046cda1cb00a275a486e740087851d2c89333c8a1dde1b1234b8e5f
```

The moving `latest` metadata resolved to build `20261015-2632` during research. Use the dated URL and verify the downloaded image against the pinned digest. The image URL returned HTTP 200 after the official mirror redirect. No image was downloaded by this research task.

Preserve the verified base read-only. Create a separate qcow2 overlay with an explicit backing format, then enlarge only the overlay. Record QEMU version, image digest, installed guest package versions and the complete launch arguments in ignored evidence.

## Setup outline

The host needs QEMU, `qemu-img`, an ISO authoring tool and an SSH client. On this Mac, `hdiutil` can create ISO media, so a second ISO package is optional. Create a NoCloud seed ISO with a `CIDATA` volume label, `user-data` and `meta-data`, including an instance ID and a locally generated SSH public key. Cloud-init documents local labeled ISO configuration without a metadata web service. [NoCloud documentation](https://docs.cloud-init.io/en/latest/reference/datasources/nocloud.html#source-2-drive-with-labeled-filesystem).

Use temporary guest package access only during installation. Proposed guest packages:

Define the login explicitly instead of depending on the image's default user. A suitable seed contains the following, with the locally generated public key substituted. Keep the private key in ignored local storage and use a unique instance ID per new overlay. Cloud-init supports declared users, authorized keys and disabled password login. [Cloud-init module reference](https://docs.cloud-init.io/en/latest/reference/modules.html).

```yaml
#cloud-config
users:
  - name: recovery
    shell: /bin/bash
    groups: [sudo]
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    lock_passwd: true
    ssh_authorized_keys:
      - '<LOCAL_SSH_PUBLIC_KEY>'
ssh_pwauth: false
disable_root: true
```

The separate `meta-data` file needs `instance-id: mu-recovery-001` and `local-hostname: mu-recovery`. Attach the ISO at first boot. Wait for SSH, then check `cloud-init status --wait` before installing packages. The amd64 generic image includes cloud-init and its normal cloud networking configuration; the proposed virtio network receives DHCP from QEMU user networking. Confirm the interface and default route inside the guest rather than assuming a device name.

```sh
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install --no-install-recommends \
  wine wine64 wine32:i386 xvfb xauth x11-utils mesa-utils \
  libgl1-mesa-dri:amd64 libgl1-mesa-dri:i386 \
  libglx-mesa0:amd64 libglx-mesa0:i386 fonts-wine
```

Debian Bookworm packages provide Wine 8.0 with separate 32-bit and 64-bit loaders. Install both because the game is PE32 x86 while the current capture helper is PE32+ x64. Use a single new `WINEARCH=win64` prefix for both programs. A pure win32 prefix cannot host the x64 helper. Verify the actual mixed-bitness behavior before attempting a real capture. [Debian wine32](https://packages.debian.org/bookworm/wine32), [Debian wine64](https://packages.debian.org/bookworm/wine64).

Boot shape, with paths supplied by the runner:

```sh
qemu-system-x86_64 \
  -machine q35 -accel tcg,thread=single -cpu max -smp 2 -m 4096 \
  -drive file=working.qcow2,if=virtio,format=qcow2 \
  -drive file=seed.iso,media=cdrom,format=raw,readonly=on \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:22222-:22 \
  -device virtio-net-pci,netdev=net0 \
  -display none -serial file:serial.log \
  -qmp unix:qmp.sock,server=on,wait=off
```

This command is a proposal, not a recorded successful launch. `thread=single` avoids relying on multi-threaded TCG support for this host/guest pair. Check the installed QEMU help and record its selected machine version. The fixed QMP socket and forwarded port must be unique per experiment. QEMU documents these options and user-mode networking. [QEMU invocation](https://www.qemu.org/docs/master/system/invocation.html).

After package setup, shut down and restart with `restrict=on` added to the user network backend. QEMU documents that this blocks guest traffic to the host and outside networks while preserving explicit forwarding. Keep only the SSH forwarding bound to `127.0.0.1`. Verify an outbound connection fails before starting the game. Transfer a disposable game copy through SSH or read-only media; never run from the original installation.

A read-only 9p export is another transfer option if the installed host build supports `virtio-9p-pci`. Check `qemu-system-x86_64 -device help` first; this research did not inspect an installed QEMU build. Add `-virtfs local,path=TRANSFER_DIRECTORY,mount_tag=transfer,security_model=none,readonly=on` and mount it in the guest with `mount -t 9p -o trans=virtio,version=9p2000.L,ro transfer /mnt/transfer`. Export a dedicated transfer directory, then copy its game files into the guest's working disk before launch. Confirm the mount is read-only and keep Wine's prefix/output off that share. A missing host device or guest module is a transfer failure, not a game failure; use SSH copying if necessary. QEMU documents `-virtfs` as the shortcut for a virtio-9p filesystem export. [QEMU filesystem options](https://www.qemu.org/docs/master/system/invocation.html).

## Graphics and capture gates

Xvfb supplies an X server without display hardware. Use a 1280x1024x24 screen and check `glxinfo -B` inside it before launching Wine. Xvfb alone does not prove OpenGL works. [Xvfb manual](https://manpages.debian.org/bookworm/xvfb/Xvfb.1.en.html).

Set `LIBGL_ALWAYS_SOFTWARE=true` and `GALLIUM_DRIVER=llvmpipe`. Mesa documents these software-renderer selections, and LLVMpipe implements rasterization on CPU. Install the i386 Mesa libraries as well as amd64 ones. Keep actual renderer and GL version output in evidence. Do not force a reported GL version to conceal a missing capability. [Mesa environment variables](https://docs.mesa3d.org/envvars.html), [LLVMpipe](https://docs.mesa3d.org/drivers/llvmpipe.html).

Run each gate with a wall-clock timeout and logs:

1. Linux boots, SSH works and package initialization finishes. Establish a five-minute initial boot budget; extend once if logs show real progress.
2. Xvfb starts, software GL creates a context and Wine creates the prefix. Run a trivial 32-bit program and the x64 helper's `--self-test` in the same prefix.
3. Add a synthetic 32-bit target with known mapped bytes and check that an x64 reader can enumerate/read it. The existing helper intentionally accepts only the pinned main.exe, so this needs a separate test fixture or narrowly scoped helper test mode, not removal of the production hash check.
4. Start the disposable exact client in its game directory with guest egress blocked, capture errors and any displayed window. Initial bound is two minutes, extend to five only if it continues making measurable progress. No login or server connection is part of this gate.
5. If main.exe survives, invoke the capture helper under the same prefix and user. Preserve manifests and hashes. Compare executable-region output against the previous protector snapshot before claiming that gameplay code was recovered.

Keep VM images, copies of game data, screenshots, Wine logs and memory bytes under ignored `runtime/` or `evidence/`. Publish only authored scripts, fixtures independent of the game, and reviewed summaries. A successful Wine helper self-test does not validate real Windows behavior. A Wine runtime capture is evidence from this compatibility environment and must be labeled accordingly.

## Failure interpretation

If this guest reaches beyond the Rosetta selector stop, the experiment establishes progress without a Windows PC. It does not establish native macOS compatibility or completeness of source recovery. Other plausible stops include Wine API differences, a missing dependency, software GL, anti-debug or VM detection and server-dependent startup. Attribute each only after observing its failure evidence.

If the same stage fails under full x86 emulation, preserve the exact instruction/address, exception, guest/Wine versions and CPU model before changing anything. Test one cause at a time. A full Windows x86 guest under QEMU remains a later option if Linux Wine is the boundary; it requires separately sourced Windows installation media and setup. No Windows guest is needed for this first experiment.

## Provenance and unresolved work

Target main.exe SHA-256 remains `3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a`. Existing CrossOver failure evidence is in [code recovery](../code-recovery.md). This research read official documentation, package records and QEMU source, and inspected host capacity. It did not install QEMU, boot a guest, modify original inputs or validate game startup. The next deliverable is an automated, bounded runner with the gates above and an honest result report.
