/* The audio service subscribes to the unavailable camera controller during
 * startup. Its original request retries until the service watchdog aborts.
 * Report absence immediately, without synthesizing camera state. Scoped to
 * audioservice's preload; other applications retain the vendor implementation.
 */
extern int *__errno_location(void);
int qemu_camera_request(void *self)
    __asm__("_ZN19CamRemoteController21requestAssiatanceModeEv");
int qemu_camera_request(void *self) {
    (void)self;
    *__errno_location() = 19; /* ENODEV */
    return -1;
}
