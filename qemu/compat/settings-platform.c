/* Settings expects an update engine that is absent in the RAM-only guest.
 * Report the query as unavailable instead of letting libhswupdate assert on a
 * D-Bus error. This never starts or completes an update. Settings-only preload.
 */
extern int *__errno_location(void);
int qemu_update_status(void *self, int *type, int *status)
    __asm__("_ZN4ccos8swupdate9HSWUpdate21getUpdateEngineStatusERNS0_13HSWUpdateTypeERNS0_21HSWUpdateEngineStatusE");
int qemu_update_status(void *self, int *type, int *status) {
    (void)self;
    if (type) *type = 0;
    if (status) *status = 0;
    *__errno_location() = 19;
    return -1;
}

int qemu_current_update_status(void *self, int *status, unsigned *progress)
    __asm__("_ZN4ccos8swupdate9HSWUpdate15getUpdateStatusERNS0_15HSWUpdateStatusERj");
int qemu_current_update_status(void *self, int *status, unsigned *progress) {
    (void)self;
    if (status) *status = 0;
    if (progress) *progress = 0;
    *__errno_location() = 19;
    return -1;
}
