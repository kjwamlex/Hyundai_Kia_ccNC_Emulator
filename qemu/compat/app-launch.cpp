// Supply the missing vendor preload graph before forwarding the OEM intent.
#include <dlfcn.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cstdio>
#include <cstring>
#include <string>

using Launch = int (*)(void *, const std::string &);
static constexpr const char *symbol =
    "_ZN4ccos4core3app22HAppServiceProxyGlibmm9launchAppERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE";
int launch(void *, const std::string &) asm(
    "_ZN4ccos4core3app22HAppServiceProxyGlibmm9launchAppERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
int launch(void *self, const std::string &intent) {
    auto original = reinterpret_cast<Launch>(dlsym(RTLD_NEXT, symbol));
    if (!original) return -1;
    int fd = socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0) return -1;
    timeval timeout{40, 0};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    std::strcpy(address.sun_path, "/run/ccnc-qemu/app-launcher.sock");
    std::string request = intent + "\n";
    bool ok = connect(fd, reinterpret_cast<sockaddr *>(&address), sizeof(address)) == 0;
    size_t sent = 0;
    while (ok && sent < request.size()) {
        auto count = send(fd, request.data() + sent, request.size() - sent, MSG_NOSIGNAL);
        if (count <= 0) ok = false;
        else sent += count;
    }
    char response[512]{};
    auto count = ok ? recv(fd, response, sizeof(response) - 1, 0) : -1;
    close(fd);
    if (count < 1 || response[0] != '0') {
        std::fprintf(stderr, "CCNC_APP_LAUNCH_ERROR: %s\n", count > 0 ? response : "launcher unavailable");
        return -1;
    }
    return original(self, intent);
}
