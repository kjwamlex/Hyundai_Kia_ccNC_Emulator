// Output-only replacement for the firmware's IHALAudio binary interface.
// Slots/layout were checked against this firmware's HAL and PluginProxy.
// The OEM route/focus service and media decoder remain unchanged.
#include <string>
#include <list>
#include <map>
#include <cstdio>
#include <cstddef>
#include <functional>
extern "C" unsigned g_idle_add_full(int, int(*)(void*), void*, void(*)(void*));
static void defer(std::function<void()> fn) {
    auto *work = new std::function<void()>(std::move(fn));
    g_idle_add_full(0, [](void *p) -> int { (*static_cast<std::function<void()>*>(p))(); return 0; },
                    work, [](void *p) { delete static_cast<std::function<void()>*>(p); });
}
using String = std::string;
using Settings = std::map<int,int>;
#include "audiohal-alsa.h"
struct Capability { int channels, format; unsigned rate, reserved; };
struct Stream { int type; String name; std::list<Capability> capabilities; };
static_assert(sizeof(Stream)==64, "firmware ABI");
struct StreamsResult { int status; std::list<Stream> streams; };
static_assert(sizeof(StreamsResult)==32, "firmware result ABI");
class QemuAudio {
    void *listener = nullptr;
    Alsa alsa;
    struct Output { int volume=75; bool muted=false; bool primed=false; };
    std::map<String,Output> outputs;
    static String endpoint(const String& src) {
        if (src=="beep" || src=="main") return "beep";
        if (src.find("navi")!=String::npos) return "navi";
        return "media";
    }
    bool apply(const String& src) {
        String key=endpoint(src);
        auto& output=outputs[key];
        if (!output.primed) output.primed=alsa.prime(key);
        int level=output.muted ? 0 : std::max(0,std::min(100,output.volume*100/(key=="beep" ? 5 : 75)));
        bool ok=output.primed && alsa.gain(key,level);
        std::fprintf(stderr,"QEMU_HAL_GAIN %s level=%d ok=%d\n",key.c_str(),level,ok);
        return ok;
    }
    template<class... T> void event(unsigned slot, T... args) {
        if (listener) reinterpret_cast<void(*)(void*,T...)>((*reinterpret_cast<void***>(listener))[slot])(listener,args...);
    }
    void route(unsigned slot,const String& src,const String& sink,const unsigned& request) {
        const int success=1;
        std::fprintf(stderr,"QEMU_HAL_ROUTE slot=%u %s -> %s request=%u\n",slot,src.c_str(),sink.c_str(),request);
        defer([=] { event(slot,&src,&sink,&success,&request); });
    }
public:
    virtual ~QemuAudio() = default;
    virtual String getPluginName() { return "audiohal"; }
    virtual bool initialize(void *p) { listener=p; if (!alsa.ready()) return false; apply("beep"); std::fprintf(stderr,"QEMU_HAL_READY: stereo ALSA output\n"); return true; }
    virtual void release() { listener=nullptr; }
    virtual int getDeviceStatus() { return 1; }
    virtual int getSrcStatus(const String&) { return 1; }
    virtual int getSinkStatus(const String&) { return 1; }
    virtual std::list<String> getAvailableSources() { return {}; }
    virtual std::list<String> getAvailableSinks() { return {}; }
    virtual bool isLinkable(const String&,const String&) { return true; }
    virtual bool prelink(const String& a,const String& b,const unsigned& r) { route(6,a,b,r);  return true; }
    virtual bool link(const String& a,const String& b,const unsigned& r) { route(7,a,b,r);  return true; }
    virtual bool postlink(const String& a,const String& b,const unsigned& r) { route(8,a,b,r);  return true; }
    virtual bool unlink(const String& a,const String& b,const unsigned& r) { route(9,a,b,r);  return true; }
    virtual bool mute(const String& src,const String&,const unsigned& r) {
        outputs[endpoint(src)].muted=true; const int ok=apply(src) ? 1 : 0;
        defer([=] { event(3,&ok,&r); }); return true;
    }
    virtual bool unmute(const String& src,const String&,const unsigned& r) {
        outputs[endpoint(src)].muted=false; const int ok=apply(src) ? 1 : 0;
        defer([=] { event(4,&ok,&r); }); return true;
    }
    virtual bool setVolume(const String& src,const String&,int volume,const unsigned& r) {
        outputs[endpoint(src)].volume=volume; const int ok=apply(src) ? 1 : 0;
        defer([=] { event(5,volume,&ok,&r); }); return true;
    }
    virtual bool setSoundSettings(const int& type,int value,const unsigned& r) { const int ok=0; defer([=] { event(10,&type,value,&ok,&r); });  return true; }
    virtual bool setSoundSettings(const Settings& values,const unsigned& r) { const int ok=0; defer([=] { event(11,&values,&ok,&r); });  return true; }
    virtual bool setEQ(const String& a,const String& b,int value,int eq,const unsigned& r) { const int ok=0; defer([=] { event(12,&a,&b,value,eq,&ok,&r); });  return true; }
    virtual StreamsResult getSrcAvailableStreams(const String& src) {
        String name="qemu_"+endpoint(src);
        if (!apply(src)) return {-1,{}};
        std::fprintf(stderr,"QEMU_HAL_STREAM source=%s -> %s\n",src.c_str(),name.c_str());
        return {0,{{0,name,{{2,2,48000,0}}}}};
    }
    virtual StreamsResult getSinkAvailableStreams(const String&) { return {-1,{}}; }
    virtual bool configureAudioStream(String name,int channels,int format,unsigned rate) {
        std::fprintf(stderr,"QEMU_HAL_CONFIG %s channels=%d format=%d rate=%u\n",name.c_str(),channels,format,rate);
        return channels==2 && format==2 && rate==48000;
    }
    virtual bool playSound(const String& name,int type) { std::fprintf(stderr,"QEMU_HAL_SOUND %s type=%d\n",name.c_str(),type); return alsa.beep(type); }
    virtual bool getInfo(const String&,String&) { return false; }
    virtual bool setEngineeringMode(const String&,const String&) { return false; }
    virtual bool getEngineeringMode(const String&,String&) { return false; }
    virtual bool reserved28() { return false; }
    virtual bool reserved29() { return false; }
    virtual bool sendInitialValues(Settings&) { return true; }
};
extern "C" { QemuAudio CCOSHALINSTANCE; void *__dso_handle = nullptr; }
