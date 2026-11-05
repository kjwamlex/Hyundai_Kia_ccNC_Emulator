// ALSA is loaded from the original firmware. No host or NVIDIA audio library.
#include <dlfcn.h>
#include <cmath>
#include <thread>
#include <vector>
struct Alsa {
    void *library = dlopen("libasound.so.2", RTLD_NOW | RTLD_LOCAL);
    template<class F> F symbol(const char *name) { return reinterpret_cast<F>(dlsym(library,name)); }
    int (*pcmOpen)(void**,const char*,int,int) = symbol<decltype(pcmOpen)>("snd_pcm_open");
    int (*pcmClose)(void*) = symbol<decltype(pcmClose)>("snd_pcm_close");
    int (*pcmParams)(void*,int,int,unsigned,unsigned,int,unsigned) = symbol<decltype(pcmParams)>("snd_pcm_set_params");
    long (*pcmWrite)(void*,const void*,unsigned long) = symbol<decltype(pcmWrite)>("snd_pcm_writei");
    int (*pcmDrain)(void*) = symbol<decltype(pcmDrain)>("snd_pcm_drain");
    int (*ctlOpen)(void**,const char*,int) = symbol<decltype(ctlOpen)>("snd_ctl_open");
    int (*ctlClose)(void*) = symbol<decltype(ctlClose)>("snd_ctl_close");
    int (*valueNew)(void**) = symbol<decltype(valueNew)>("snd_ctl_elem_value_malloc");
    void (*valueFree)(void*) = symbol<decltype(valueFree)>("snd_ctl_elem_value_free");
    void (*valueIface)(void*,int) = symbol<decltype(valueIface)>("snd_ctl_elem_value_set_interface");
    void (*valueName)(void*,const char*) = symbol<decltype(valueName)>("snd_ctl_elem_value_set_name");
    void (*valueInt)(void*,unsigned,long) = symbol<decltype(valueInt)>("snd_ctl_elem_value_set_integer");
    int (*ctlWrite)(void*,void*) = symbol<decltype(ctlWrite)>("snd_ctl_elem_write");
    bool ready() const { return library && pcmOpen && pcmClose && pcmParams && pcmWrite && pcmDrain && ctlOpen && ctlClose && valueNew && valueFree && valueIface && valueName && valueInt && ctlWrite; }
    bool prime(const String& endpoint) {
        void *pcm=nullptr;
        if (!ready() || pcmOpen(&pcm,("qemu_"+endpoint).c_str(),0,0)<0) return false;
        pcmClose(pcm); return true;
    }
    bool gain(const String& endpoint,int value) {
        void *ctl=nullptr,*setting=nullptr;
        if (!ready() || ctlOpen(&ctl,"hw:0",0)<0) return false;
        bool ok=false;
        if (valueNew(&setting)>=0) {
            valueIface(setting,2); // MIXER
            valueName(setting,("QEMU_"+endpoint).c_str());
            valueInt(setting,0,value); valueInt(setting,1,value);
            ok=ctlWrite(ctl,setting)>=0; valueFree(setting);
        }
        ctlClose(ctl); return ok;
    }
    bool beep(int type) {
        if (!ready() || type<0 || type>3) return false;
        std::thread([this,type] {
            void *pcm=nullptr;
            if (pcmOpen(&pcm,"qemu_beep",0,0)<0) return;
            if (pcmParams(pcm,2,3,2,48000,1,100000)>=0) {
                unsigned frames=type==2 ? 5760 : 2640;
                std::vector<short> samples(frames*2);
                double frequency=type==1 ? 880 : (type==2 ? 660 : 1000);
                for (unsigned i=0;i<frames;++i) {
                    double envelope=std::min(1.0,std::min(i/240.0,(frames-1-i)/240.0));
                    short value=short(4000*envelope*std::sin(6.283185307179586*frequency*i/48000));
                    samples[2*i]=samples[2*i+1]=value;
                }
                unsigned written=0;
                while (written<frames) {
                    long n=pcmWrite(pcm,samples.data()+2*written,frames-written);
                    if (n<=0) break;
                    written+=unsigned(n);
                }
                pcmDrain(pcm);
            }
            pcmClose(pcm);
        }).detach(); return true;
    }
};
