# Distribution notice

This repository distributes the independently written emulator integration,
compatibility source, build scripts, and documentation. It does not distribute
Hyundai/Kia/Mobis firmware, decrypted firmware, extracted vendor executables or
libraries, extracted image assets, animations, sound assets, or saved VM disks.

The README includes user-supplied screenshots of the running emulator for
documentation. These screenshots are separate from the firmware and its assets.

Users obtain and prepare compatible firmware independently. The setup scripts
expect local firmware files and do not download or decrypt them. The original
firmware image remains read-only; emulator changes use a separate writable layer.

Alpine, Debian, Mesa, LLVM, QEMU, and other third-party components retain their
respective licenses. Build dependencies are downloaded from their upstream
distribution sources, verified against the checked-in manifests, and generated
locally. Vendor trademarks and product names belong to their respective owners.
