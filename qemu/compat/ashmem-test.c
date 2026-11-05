extern long syscall(long, ...);
int ashmem_create_region(const char *, unsigned long);
int ashmem_valid(int);
int ashmem_get_size_region(int);
int ashmem_set_prot_region(int, int);
int ashmem_equal(int, int);

static int check(int condition, const char *text) {
    if (condition) return 0;
    unsigned long length = 0;
    while (text[length]) ++length;
    syscall(64L, 2, text, length);
    return 1;
}

int main(void) {
    int fd = ashmem_create_region("ccnc-test", 4096);
    if (check(fd >= 0, "FAIL create\n")) return 1;
    int duplicate = (int)syscall(23L, fd);
    int other = ashmem_create_region("ccnc-test", 4096);
    int failures = 0;
    failures += check(ashmem_valid(fd) && !ashmem_valid(-1), "FAIL valid\n");
    failures += check(ashmem_get_size_region(fd) == 4096, "FAIL size\n");
    failures += check(ashmem_equal(fd, duplicate) == 0, "FAIL duplicate identity\n");
    failures += check(ashmem_equal(fd, other) == -1, "FAIL distinct identity\n");
    char *writer = (char *)syscall(222L, 0L, 4096L, 3L, 1L, fd, 0L);
    char *reader = (char *)syscall(222L, 0L, 4096L, 1L, 1L, duplicate, 0L);
    if (check(writer != (void *)-1 && reader != (void *)-1, "FAIL mmap\n")) return 1;
    writer[0] = 42;
    failures += check(reader[0] == 42, "FAIL shared mapping\n");
    failures += check(ashmem_set_prot_region(fd, 1) == 0, "FAIL read seal\n");
    char *forbidden = (char *)syscall(222L, 0L, 4096L, 3L, 1L, duplicate, 0L);
    failures += check(forbidden == (void *)-1, "FAIL future write protection\n");
    writer[0] = 43;
    failures += check(reader[0] == 43, "FAIL existing mapping after seal\n");
    failures += check(ashmem_set_prot_region(fd, 3) == -1, "FAIL protection increase\n");
    syscall(57L, fd);
    syscall(57L, duplicate);
    syscall(57L, other);
    if (!failures) syscall(64L, 1, "CCNC_ASHMEM_OK\n", 15L);
    return failures != 0;
}
