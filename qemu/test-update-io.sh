#!/bin/sh
# Exercise USB I/O in a disposable VM, then the original Settings button path.
set -e
ccnc -ec 'python3 - <<"PY"
import errno
import hashlib
import os
from pathlib import Path

usb = Path("/run/media/USB_Front")
assert Path("/sys/block/sda/ro").read_text().strip() == "1"
assert Path("/sys/block/vda/ro").read_text().strip() == "1"
source = usb / "README.txt"
content = source.read_bytes()
assert content
print("CCNC_USB_READ_OK", len(content), hashlib.sha256(content).hexdigest(), flush=True)
for path, flags in [
    (usb / ".qemu-write-probe", os.O_WRONLY | os.O_CREAT | os.O_EXCL),
    (source, os.O_WRONLY | os.O_TRUNC),
    (Path("/dev/sda"), os.O_RDWR),
]:
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as error:
        assert error.errno == errno.EROFS, (str(path), error)
        print("CCNC_USB_WRITE_BLOCKED", str(path), errno.errorcode[error.errno], flush=True)
    else:
        os.close(fd)
        raise AssertionError("Unexpected writable USB: " + str(path))
destination = Path("/ccos/data/update/.qemu-usb-io-probe")
destination.write_bytes(content)
assert destination.read_bytes() == content
assert source.read_bytes() == content
print("CCNC_USB_TO_INTERNAL_COPY_OK", str(destination), flush=True)
destination.unlink()
PY'
test ! -e /firmware/ccos/data/update/.qemu-usb-io-probe
update_status=0
/bin/sh /ccnc/opt/ccnc-qemu/test-update-original.sh || update_status=$?
ccnc -ec '
echo CCNC_USB_SCANNER_DETAILS_BEGIN
grep -E "findPackageName|scanUsbFile|findUsbGroup|MAINCONFIG|NoPkgFile|EMPTY-G|FIND.-G|USB.*PKG|UsbPkgList|Parse|parse|extract|Extract|\.zip|\.enc|\.Img" /tmp/ccnc-qemu/dlt.log | tail -160
echo CCNC_USB_INTERNAL_FILES_BEGIN
find /ccos/data/update -maxdepth 2 -type f
echo CCNC_USB_SYSCALLS_BEGIN
for trace in /tmp/ccnc-qemu/usb-hmi.strace /tmp/ccnc-qemu/usb-service.strace; do
    if [ -f "$trace" ]; then
        echo "$trace"
        grep -E "USB_Front|/ccos/data/update" "$trace" | tail -100
    fi
done
echo CCNC_USB_SCANNER_DETAILS_END
'
exit "$update_status"
