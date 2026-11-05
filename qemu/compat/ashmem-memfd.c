/* ARM64 Linux replacement for the five exported ccOS libashmem functions.
 * Build without a host sysroot; these declarations use the AArch64 Linux ABI.
 * No ashmem ioctl or NVIDIA device is emulated. */
typedef unsigned long size_t;
typedef unsigned long u64;
typedef unsigned int u32;
extern long syscall(long number, ...);
extern int *__errno_location(void);

struct linux_stat {
    u64 dev, ino;
    u32 mode, nlink, uid, gid;
    u64 rdev, pad1;
    long size;
    int blksize, pad2;
    long blocks, atime;
    u64 atime_nsec;
    long mtime;
    u64 mtime_nsec;
    long ctime;
    u64 ctime_nsec;
    u32 unused[2];
};

static int fail(int error) { *__errno_location() = error; return -1; }

int ashmem_create_region(const char *name, size_t size) {
    char label[250];
    size_t i = 0;
    if (!name) name = "ccnc-shared";
    while (name[i] && i < sizeof(label) - 1) { label[i] = name[i]; ++i; }
    label[i] = 0;
    int fd = (int)syscall(279L, label, 3U); /* memfd_create: CLOEXEC | ALLOW_SEALING */
    if (fd < 0) return -1;
    if (syscall(46L, fd, (long)size) < 0) { /* ftruncate */
        int error = *__errno_location();
        syscall(57L, fd); /* close */
        return fail(error);
    }
    return fd;
}

int ashmem_valid(int fd) {
    return syscall(25L, fd, 1034, 0L) >= 0; /* fcntl F_GET_SEALS */
}

int ashmem_get_size_region(int fd) {
    struct linux_stat st;
    if (!ashmem_valid(fd)) return fail(25); /* ENOTTY */
    if (syscall(80L, fd, &st) < 0) return -1; /* fstat */
    if (st.size > 2147483647L) return fail(75); /* EOVERFLOW */
    return (int)st.size;
}

int ashmem_set_prot_region(int fd, int prot) {
    long seals = syscall(25L, fd, 1034, 0L);
    if (seals < 0) return -1;
    /* memfd can preserve existing writers while denying future writable maps.
     * It cannot restrict reads or executable maps; reject unsupported masks. */
    if (prot != 1 && prot != 3) return fail(95); /* EOPNOTSUPP */
    if (prot & 2) return (seals & 0x10) ? fail(22) : 0; /* cannot restore writes */
    return (int)syscall(25L, fd, 1033, 0x10L); /* F_ADD_SEALS F_SEAL_FUTURE_WRITE */
}

int ashmem_equal(int first, int second) {
    struct linux_stat a, b;
    if (!ashmem_valid(first) || !ashmem_valid(second)) return fail(25);
    if (syscall(80L, first, &a) < 0 || syscall(80L, second, &b) < 0) return -1;
    return (a.dev == b.dev && a.ino == b.ino) ? 0 : -1;
}
