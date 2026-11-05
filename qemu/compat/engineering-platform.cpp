// The OEM version display writes to version[size-1] without checking for an
// empty reply. There is no physical DSP in QEMU; preserve real replies and label
// missing ones explicitly instead of letting the display corrupt its string.
#include <dlfcn.h>
#include <string>

using Getter = std::string (*)(const void *);
static std::string version(const void *self, const char *symbol) {
    auto original = reinterpret_cast<Getter>(dlsym(RTLD_NEXT, symbol));
    auto value = original ? original(self) : std::string();
    return value.empty() ? "Unavailable" : value;
}
std::string software(const void *)
    asm("_ZNK4ccos5audio11engineering21HAudioEngineeringMode18getSoftwareVersionB5cxx11Ev");
std::string hardware(const void *)
    asm("_ZNK4ccos5audio11engineering21HAudioEngineeringMode18getHardwareVersionB5cxx11Ev");
std::string software(const void *self) {
    return version(self, "_ZNK4ccos5audio11engineering21HAudioEngineeringMode18getSoftwareVersionB5cxx11Ev");
}
std::string hardware(const void *self) {
    return version(self, "_ZNK4ccos5audio11engineering21HAudioEngineeringMode18getHardwareVersionB5cxx11Ev");
}
