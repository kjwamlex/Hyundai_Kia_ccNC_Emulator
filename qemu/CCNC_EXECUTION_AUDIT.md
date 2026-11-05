# Original ccNC firmware: native script execution audit

Examined 2026-11-04. Build: `CCNC_SYSTEM_ALL_KOR_0000_00_001_002_260813_164608`.

## Finding

**The original ARM64 firmware contains a native USB file-picker and shell-script runner. However, this build's compiled engineering menu omits the Run script entry and its enum. An accessible, arbitrary script-execution route on a physical ccNC has not been established.**

This is stronger evidence than finding shell binaries or `system()` imports: recovered original QML supplies a selected file to an original native function, whose worker constructs `source <selected-path>` and calls `popen()`. It is also weaker than a working physical route: retained implementation and QML do not establish that a production user can invoke them.

Only firmware files are available. No physical unit was connected, no device was flashed, and no target execution is claimed. This investigation used read-only `debugfs` access to the original filesystem and static analysis of its original binaries. It did not use QEMU to establish these findings.

## Route assessment

| Route | Evidence in this build | Conclusion |
| --- | --- | --- |
| USB insertion autorun | Inspected udev rules, startup units/scripts, DeviceService mount flow | No script autorun found in this scope |
| Settings → Update through USB | Original update flow and package filtering; see `USB_UPDATE_AUDIT.md` | Package update interface; arbitrary loose-script execution not established |
| Engineering → Run script | Original file-picker QML, QML-callable native runner, shell-source worker | Implementation retained, ordinary menu entry omitted |
| Engineering fixed diagnostic scripts | Internal log-export and recording scripts, original manager/HMI policies | Fixed internal scripts exist; they do not prove caller-controlled execution |
| Serial root autologin | Enabled serial-getty link and `agetty -a root`; root shell `/bin/false` | Autologin configuration alone does not yield an interactive shell |
| SSH | Default and update-specific configs force internal SFTP | Shell access not offered by the inspected configurations |
| Test automation | Leftover unit links and AppArmor profiles; referenced units/binaries absent | Presence in policy/links does not establish a usable automation service |
| Recovery USB loader | Original recovery binary directly calls a fixed USB executable path | Native implementation present; startup, media mount, and recovery entry remain unproven |
| Recovery / secondary guest shells | Original recovery init and secondary ramdisk contain shell launches | Separate boot environments; no reachable physical console demonstrated |

## Native runner: actual call chain

Original library:

`/ccos/apps/hmi/engineeringmodehmi/qml/module/system/libmodule_system.so`

Recovered QML is under `artifacts/ccnc-exec-audit/system-resources/`. Resource names encode the compressed stream's offset in the original library; they are extraction labels, not original filenames. Source hashes are in `artifacts/ccnc-exec-audit/source-manifest.json`.

1. `resource-1737cf.qml` (original scene `ENGMODE_TestTuning.qml`), lines 459–461, retains a `MENU_INDEX_TAT_RUN_SCRIPT` case. It sets `FPUtils` mode to `run_script` and pushes the model's next scene.
2. `resource-171c00.qml` (original `ENGMODE_FilePicker.qml`), lines 138–143, initializes its folder from `TestAndTuningListModel.getUsbPath()`, falling back to the filesystem root.
3. The picker constructs a file URL from the selected directory and filename (lines 46–51). Confirmation is required by this UI (lines 223–229).
4. In modes other than `gpsdr_log`, it calls `TestAndTuningListModel.runScript(selectedFileName)` at line 229. In `gpsdr_log` mode, it instead calls the GPS/DR replay API. GPS replay is not itself proof that the script branch is reachable.
5. Original `TestAndTuningListModel::runScript(QString const&)`, ELF VA `0xc9b90`, copies the argument into a detached thread. Its thread-state vtable points to `_M_run` at `0xcc1e8`, which passes the captured string to the worker at `0xcbc70`.
6. The worker removes the first seven characters (`QString::remove(0,7)` at `0xcbcd4`–`0xcbce0`), consistent with removing `file://`. It converts the remaining path to UTF-8, prepends the literal `source ` at `0xcbe04`–`0xcbe14`, and calls `popen()` at `0xcbe80`. It reads the resulting output with `fgets` and feeds the result back to the model/UI.

The disassembler attributes some stripped worker instructions to the preceding exported `copyGuiderLogToUsb` symbol. The thread-state vtable and branch at `0xcc1e8`, rather than that nearest-symbol label, establish the connection to `runScript`.

Focused original instruction evidence is saved in `artifacts/ccnc-exec-audit/eng-system-key-disassembly.txt`; full disassembly, dynamic symbols, and relocations are also retained. The `.annotated` exploratory files use heuristic address tracking and are not authoritative for instructions that reuse a register.

The traced runner body contains no package signature/decryption step before the shell-source call. That observation applies to this function; it does not prove that an upstream access gate can be passed.

### Why this is not yet a usable Run script menu

The compiled `TestAndTuningHandler` constructor starts at `0x86ba8`. Its menu setup at `0x86c50`–`0x86d50` builds five `ItemInfo` records (allocation `0x1e0`, five records of `0x60` bytes):

1. Performance measurement (`ENGMODE_PerformanceMeasure.qml`)
2. Screen capture (`scSwitch`)
3. LCD test image (`ENGMODE_LcdTest.qml`)
4. Factory mode (`fmSwitch`)
5. Keyboard (`ENGMODE_KeyBoard.qml`)

The exported Qt enum strings likewise contain only:

```text
MENU_INDEX_TAT_PERFORMANCE_MEASURE
MENU_INDEX_TAT_SCREEN_CAPTURE
MENU_INDEX_TAT_LCD_TEST_IMAGE
MENU_INDEX_TAT_FACTORY_MODE
MENU_INDEX_TAT_KEYBOARD
```

Direct decoding of the original Qt metadata confirms that `tatMenuIndex` has exactly these five values, numbered 0 through 4. The static metaobject is at `0x1b7778`, its metadata at `0x17fa68`, and its enum header is `(117,117,0,5,729)`. Decoded evidence is saved in `artifacts/ccnc-exec-audit/eng-system-qt-enums.json`.

`MENU_INDEX_TAT_RUN_SCRIPT` is absent from that compiled enum. `getMenuTitle()` at `0xc6b98` also handles the five corresponding indices. Consequently, the retained QML switch case is not sufficient evidence of a visible selectable row in this build. No ordinary menu entry leading to the runner was found.

The picker remains used by GPS/DR replay (`resource-177cc7.qml`, lines 196–198), which explicitly selects `gpsdr_log` mode before opening it. That path takes the GPS replay branch, not `runScript`.

### Execution identity and limits

`/lib/systemd/system/engineeringmodehmi.service` specifies `User=ccos-app` and `Group=ccos`. The traced script worker belongs to that HMI library. It is not the privileged engineering manager's fixed log-export script path.

If invoked in the normal HMI process, the runner's child would ordinarily inherit the app user's identity and applicable security restrictions. The original AppArmor profile includes read/write access to `/run/media/**` and execution permission for `/bin/busybox.nosuid`; the image's `/bin/sh` is a symlink to `/bin/busybox.nosuid`. The original BusyBox binary contains the `source` builtin string. Exact runtime AppArmor attachment, effective capabilities, and allowed operations remain unverified on hardware.

Thus even a reachable runner would not, by itself, establish unrestricted root execution, unrestricted executable loading, or persistence.

## Original USB read/write policy

`DeviceService::StorageVolume::requestMount()` starts at `0x7d158` in `/ccos/services/deviceservice/deviceservice`.

Static instruction tracing shows:

| Filesystem type | Options constructed by this function |
| --- | --- |
| `vfat`, `ntfs`, `exfat` | `noatime,nodiratime,noexec,sync` |
| Other types, including `ext4` | `ro,noatime,nodiratime,noexec,sync` |

Relevant literals are at `0x88588` (`ntfs`), `0x88590` (`exfat`), `0x885a0` (`vfat`), `0x885a8` (`ro,`), and `0x885b0` (`noatime,nodiratime,noexec,sync`). Branches at `0x7d264`–`0x7d29c` and `0x7d4fc`–`0x7d53c` select the prefix. The function passes its options to `udisks_filesystem_call_mount` at `0x7d310`.

This describes the application's mount request, not a physical mount observation. Filesystem support, UDisks policy, errors, and media write protection may further affect the result. In particular, the absence of a forced `ro` option for FAT/NTFS/exFAT is not proof every physical drive is writable.

`noexec` prevents ordinary direct execution from that mount. It does not prevent an already executable interpreter from reading a script there. The retained runner's `source` design is therefore compatible with `noexec`, assuming the interpreter is allowed to read the file.

Original log/recording scripts copy data to USB; those are evidence of intended write functionality. The emulator's extra read-only block-device/mount settings are separate and must not be attributed to the physical firmware.

A supplementary literal search over the entire original main filesystem image found one `autorun.sh` occurrence. `debugfs icheck`/`ncheck` mapped its containing block to `/usr/share/mime/treemagic`: it is a MIME content-classification pattern, not an execution hook. The same search found no literal `forcedUpdateManager`, `/usb/forced_update/forced_update`, or `source /run/media` in the main image. These exact-string results do not exclude differently named, compressed, or indirectly constructed behavior. Search offsets and context are retained in `artifacts/ccnc-exec-audit/main-raw-reference-search.json`.

## Other access paths checked

### Serial

`serial-getty@.service` runs `agetty -nNi -a root -8 -L %I 115200 $TERM`, and the image includes the enabled `serial-getty@ttyS0.service` link. However, `/etc/passwd` assigns root `/bin/false`, and `/bin/false` links to the coreutils false program. The inspected PAM/startup files did not establish a boot-time replacement with an interactive root shell. No serial wiring, runtime port state, or login behavior was tested.

### SSH/SFTP

Both `/etc/ssh/sshd_config` and the extracted update-specific `/home/ccos-sftp/.ssh/sshd_config` disable root login, password authentication, forwarding and tunnels, and force internal SFTP for the allowed accounts. The update-specific configuration listens on port 2022 and allows `ccos-sftp` and `ccos-sftp-ccu` within `/sftp_root`.

The default enabled `sshd.socket` link has no matching unit at the inspected `/lib/systemd/system` or `/usr/lib/systemd/system` path. This does not prove SSH never runs: update components may start their own daemon using the update-specific config. Neither configuration supplies an interactive command shell. Credentials were not recovered or tested.

### Privileged engineering manager

The original manager unit has no `User=` setting, so its systemd launch defaults to root absent another runtime mechanism. Its binary calls fixed internal diagnostic tools, including `/ccos/apps/hmi/engineeringmodehmi/exportlog.sh`. This script validates its security/log-count choices and packages internal logs. Finding `system()`/`popen()` or broad policy permissions in this process does not establish control of an arbitrary command or script path.

### Test automation and update verification

The image has test-automation policy files and enabled-unit links, but direct original-image checks did not find `/ccos/daemons/testautomationdaemon`, `/ccos/apps/manager/testautomationmanager`, or the referenced daemon unit. Treat these as leftovers unless another supplied partition/runtime source supplies them.

The inspected factory-automation and diagnosis binaries did not reveal an additional USB script path. `/etc/systemd/scripts/check-ss-update.sh` delegates to `check_ss_update`; its presence is not evidence of a USB shell-script launcher. The normal update-package trust path remains a separate issue documented in `USB_UPDATE_AUDIT.md`.

## Separate recovery and secondary-guest findings

These findings must not be merged with normal ccNC HMI access.

### Recovery-rootfs USB executable launcher

The supplied `system/1_recovery_rootfs_9_ext4.img` contains `/bin/forcedUpdateManager`. Its unstripped `main` at VA `0x4009c0`:

- Polls for `/usb/forced_update/forced_update` using `access(path, F_OK)` for about 30 seconds.
- On finding it, prints a start message and passes that exact path to `system()` at `0x400a2c`.
- If it does not find the path, executes `echo y > /proc/sysrq-trigger` at `0x400aa4`, following a message about rebooting recovery and retrying.

No signature/decryption check appears in this short function before `system()`. An executable supplied at that path could therefore be a script or an ARM64 program, **conditional on this manager actually being started in recovery and the file being executable on its mounted filesystem**. Those prerequisites have not been established. It is not a normal-mode USB autorun finding.

The recovery image's `/bin/init` does not invoke `forcedUpdateManager`: it initializes mounts, starts an internal UFS maintenance script, performs a write intended to start UFS refresh, and eventually runs `exec /bin/sh`. Its `/etc/profile` also does not start the manager. A raw reference search of this recovery image found the manager's filename/debug information but no additional textual startup command. Raw searches are corroborating evidence, not proof of absence of indirect invocation.

Original recovery copies and instruction evidence are under `artifacts/ccnc-exec-audit/recovery/` and `recovery-forced-update.disasm`. The manifest maps the recovery filesystem image to `/dev/vblkdev2p3`; that mapping alone does not show how a user enters it or which process starts the loader.

### Secondary ramdisk console

The original `system/2_6_ramdisk_zerosign.img` decompresses exactly to the existing inspection artifact `qemu/artifacts/vendor/initramfs-recovery.cpio`. The identity was checked again against the original compressed file; hashes are in `artifacts/ccnc-exec-audit/secondary-ramdisk-provenance.json`.

The artifact's name was chosen by `qemu/prepare.py`. It does not itself establish that this is the recovery-rootfs boot path. Its original `etc/inittab` contains:

```text
ttyTGRHVC0::respawn:/sbin/getty -n -l /bin/sh 115200 ttyTGRHVC0
::once:/bin/sh
```

Its startup also launches display/early-boot services, and its root account has `/bin/sh`. This is evidence of a shell configured in a separate supplied guest environment. `ttyTGRHVC0` is a guest console name; no connection from an accessible physical port to this console was established. It does not change the normal rootfs account's `/bin/false` setting.

## Remaining evidence needed

- A legitimate reachable caller of the retained native runner in this exact production build, or a different original build that actually includes its menu entry.
- The physical unit's active process identity, AppArmor policy, USB mount options, and harmless execution output if that caller is available.
- A verified recovery boot/startup path that invokes `forcedUpdateManager`, or a physical endpoint for the separate guest/recovery shells.
- Any runtime overlays or additional partition contents that change the inspected units, menus, accounts, or service availability.

The current evidence supports **native script-runner implementation present, normal menu omitted, physical reachability unproven**. It does not support either “USB arbitrary execution works” or “arbitrary execution is impossible.”
