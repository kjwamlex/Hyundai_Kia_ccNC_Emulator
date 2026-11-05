// Some HMIs register a listener even when obtainMediaPlayer returned nullptr.
// Keep the original backend failure; avoid a null dereference during UI startup.
#include <dlfcn.h>
#include <cstdio>
#include <memory>
#include <string>
namespace ccos { namespace media { class IHMediaPlayerListener; class HMediaPlayer; } }
using Player = std::shared_ptr<ccos::media::HMediaPlayer>;
static void *media_symbol(const char *name) {
    void *result = dlsym(RTLD_NEXT, name);
    // Some HMIs load libhmedia through an RTLD_LOCAL Qt plugin. It is then
    // outside the preload library's RTLD_NEXT scope; use its existing handle.
    if (!result) {
        void *library = dlopen("/ccos/lib/libhmedia.so.2.9.12", RTLD_LAZY | RTLD_NOLOAD);
        if (library) {
            result = dlsym(library, name);
            dlclose(library);
        }
    }
    if (!result) std::fprintf(stderr, "CCNC_MEDIA_SYMBOL_MISSING: %s\n", name);
    return result;
}
static constexpr const char *obtain_symbol =
    "_ZN4ccos5media20HMediaPlayerProvider17obtainMediaPlayerERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKNS0_16HMediaPlayerTypeERKNS_9HZoneTypeES9_";
Player obtain(void *, const std::string &, const int &, const int &, const std::string &) asm(
    "_ZN4ccos5media20HMediaPlayerProvider17obtainMediaPlayerERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEERKNS0_16HMediaPlayerTypeERKNS_9HZoneTypeES9_");
Player obtain(void *self, const std::string &client, const int &type,
              const int &zone, const std::string &options) {
    // Pet Care requests type 28. Its unavailable NVIDIA sink also leaves the
    // vendor media service in a broken state. Reject before crossing IPC, with
    // the same empty shared_ptr the original backend returns on failure.
    if (type == 28) {
        std::fprintf(stderr, "CCNC_MEDIA_UNAVAILABLE: player type=%d client=%s requires NVIDIA video sink\n",
                     type, client.c_str());
        return {};
    }
    auto original = reinterpret_cast<Player (*)(void *, const std::string &, const int &,
                                                const int &, const std::string &)>(media_symbol(obtain_symbol));
    return original ? original(self, client, type, zone, options) : Player{};
}
using Listener = std::shared_ptr<ccos::media::IHMediaPlayerListener>;
static constexpr const char *symbol =
    "_ZN4ccos5media12HMediaPlayer16setEventListenerESt10shared_ptrINS0_21IHMediaPlayerListenerEE";
void listener(void *, Listener) asm(
    "_ZN4ccos5media12HMediaPlayer16setEventListenerESt10shared_ptrINS0_21IHMediaPlayerListenerEE");
void listener(void *self, Listener value) {
    if (!self) {
        std::fprintf(stderr, "CCNC_MEDIA_UNAVAILABLE: no player; listener registration skipped\n");
        return;
    }
    auto original = reinterpret_cast<void (*)(void *, Listener)>(media_symbol(symbol));
    if (original) original(self, std::move(value));
}

int set_url(void *, const std::string &) asm(
    "_ZN4ccos5media12HMediaPlayer6setURLERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
int set_url(void *self, const std::string &url) {
    if (!self) {
        std::fprintf(stderr, "CCNC_MEDIA_UNAVAILABLE: no player; setURL rejected\n");
        return 1; // HMediaResult failure, matching the original IPC error path.
    }
    auto original = reinterpret_cast<int (*)(void *, const std::string &)>(media_symbol(
        "_ZN4ccos5media12HMediaPlayer6setURLERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE"));
    return original ? original(self, url) : 1;
}
