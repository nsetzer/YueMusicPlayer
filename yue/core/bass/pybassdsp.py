#! python $this
import os, sys, ctypes, platform
import math

if __name__ == "__main__":
    import pybass
else:
    from . import pybass

if sys.hexversion < 0x02060000:
	ctypes.c_bool = ctypes.c_byte
elif sys.hexversion > 0x03000000:
    long = int

try:
    # need libfftw3-3.dll and maybe libmp3lame-0.dll
    bassdsp_module,func_type = pybass.LoadLibrary("bassdsp");
except OSError as e:
    sys.stderr.write("%s\n"%str(e))
    raise ImportError("bassdsp")

int_p = ctypes.POINTER(ctypes.c_int)
double_p = ctypes.POINTER(ctypes.c_double)
float_p = ctypes.POINTER(ctypes.c_float)
double_pp = ctypes.POINTER(double_p)
DWORD_t = ctypes.c_ulong

# default values for certain dsps
zbfilter11_fc = (ctypes.c_double*11)(47.0,94.0,189.0,378.0,755.0,1511.0,3022.0,5115.0,6973.0,11264.0,16384.0);
zbfilter11_bw = (ctypes.c_double*11)(29.0,59.0,116.0,232.0,465.0, 929.0,1858.0,1858.0,1858.0, 4096.0, 4096.0);
zbfilter11_gdb = (ctypes.c_double*11)(0.0, 0.0,  0.0,  0.0,  0.0,   0.0,   0.0,   0.0,   0.0,    0.0,    0.0);

mod = lambda x : (x,bassdsp_module)
DSP_ZBPEQ_Proc = pybass.DSPPROC(('DSP_ZBPEQ_Proc', bassdsp_module))
DSP_ZBPEQ_New = func_type(ctypes.c_void_p,ctypes.c_int,double_p,double_p,double_p)(('DSP_ZBPEQ_New', bassdsp_module))
DSP_ZBPEQ_Delete = func_type(None,ctypes.c_void_p)(('DSP_ZBPEQ_Delete', bassdsp_module))
DSP_ZBPEQ_GetGain = func_type(ctypes.c_int,ctypes.c_void_p,double_p,ctypes.c_int)(('DSP_ZBPEQ_GetGain', bassdsp_module))
DSP_ZBPEQ_SetGain = func_type(None        ,ctypes.c_void_p,double_p,ctypes.c_int)(('DSP_ZBPEQ_SetGain', bassdsp_module))

DSP_ZBVIS_Proc = pybass.DSPPROC(mod('DSP_ZBVIS_Proc'))
DSP_ZBVIS_Proc_Mono = pybass.DSPPROC(mod('DSP_ZBVIS_Proc_Mono'))
DSP_ZBVIS_New = func_type(ctypes.c_void_p,ctypes.c_int,ctypes.c_int,double_p,double_p,ctypes.c_int)(mod('DSP_ZBVIS_New'))
DSP_ZBVIS_Delete = func_type(None,ctypes.c_void_p)(mod('DSP_ZBVIS_Delete'))
DSP_ZBVIS_Settings = func_type(int)(mod('DSP_ZBVIS_Settings'))
DSP_ZBVIS_GetData = func_type(ctypes.c_int,ctypes.c_void_p,double_p,ctypes.c_int)(mod('DSP_ZBVIS_GetData'))

DSP_ZBLOG_Proc = pybass.DSPPROC(mod('DSP_ZBLOG_Proc'))
DSP_ZBLOG_Proc_Mono = pybass.DSPPROC(mod('DSP_ZBLOG_Proc_Mono'))
DSP_ZBLOG_New = func_type(ctypes.c_void_p,ctypes.c_int,ctypes.c_int,double_p,double_p,ctypes.c_int,ctypes.c_int)(mod('DSP_ZBLOG_New'))
DSP_ZBLOG_Delete = func_type(None,ctypes.c_void_p)(mod('DSP_ZBLOG_Delete'))
DSP_ZBLOG_Reset = func_type(None,ctypes.c_void_p)(mod('DSP_ZBLOG_Reset'))
DSP_ZBLOG_Settings = func_type(int)(mod('DSP_ZBLOG_Settings'))
DSP_ZBLOG_GetMean = func_type(int,ctypes.c_void_p,ctypes.c_int,double_pp)(mod('DSP_ZBLOG_GetMean'))
DSP_ZBLOG_GetMaximum = func_type(int,ctypes.c_void_p,float_p,float_p)(mod('DSP_ZBLOG_GetMaximum'))

DSP_ZBVEQ_Proc = pybass.DSPPROC(mod('DSP_ZBVEQ_Proc'))
DSP_ZBVEQ_New = func_type(ctypes.c_void_p,ctypes.c_int)(mod('DSP_ZBVEQ_New'))
DSP_ZBVEQ_Delete = func_type(None,ctypes.c_void_p)(mod('DSP_ZBVEQ_Delete'))
DSP_ZBVEQ_Settings = func_type(int)(mod('DSP_ZBVEQ_Settings'))
DSP_ZBVEQ_GetVX = func_type(int,ctypes.c_void_p,double_pp)(mod('DSP_ZBVEQ_GetVX'))
DSP_ZBVEQ_GetVC = func_type(int,ctypes.c_void_p,double_pp)(mod('DSP_ZBVEQ_GetVC'))

DSP_VOLEQ_Proc = pybass.DSPPROC(mod('DSP_VOLEQ_Proc'))
DSP_VOLEQ_New = func_type(ctypes.c_void_p)(mod('DSP_VOLEQ_New'))
DSP_VOLEQ_Delete = func_type(None,ctypes.c_void_p)(mod('DSP_VOLEQ_Delete'))
DSP_VOLEQ_Settings = func_type(int)(mod('DSP_VOLEQ_Settings'))
DSP_VOLEQ_SetScale = func_type(None,ctypes.c_void_p,ctypes.c_float)(mod('DSP_VOLEQ_SetScale'))

#DSP_AudioIngest_New = func_type(ctypes.c_void_p,DWORD_t,DWORD_t,ctypes.c_char)(mod('DSP_AudioIngest_New'))
#DSP_AudioIngest_fromChannel = func_type(ctypes.c_int32, ctypes.c_void_p,DWORD_t,float_p,ctypes.c_int32)(mod('DSP_AudioIngest_fromChannel'))
#DSP_AudioIngest_fromSignal = func_type(DWORD_t, ctypes.c_void_p,float_p,DWORD_t,float_p,DWORD_t)(mod('DSP_AudioIngest_fromSignal'))
#DSP_AudioIngest_Delete = func_type(None,ctypes.c_void_p)(mod('DSP_AudioIngest_Delete'))
#
#DSP_FEATGEN_new    = func_type(ctypes.c_void_p,ctypes.c_ulong)(mod('DSP_FEATGEN_new'))  # deprecated
#DSP_FEATGEN_newMFCC           = func_type(ctypes.c_void_p,ctypes.c_ulong)(mod('DSP_FEATGEN_newMFCC'))
#DSP_FEATGEN_newMIDI           = func_type(ctypes.c_void_p,ctypes.c_ulong)(mod('DSP_FEATGEN_newMIDI'))
#DSP_FEATGEN_newSpectrogram    = func_type(ctypes.c_void_p,ctypes.c_ulong)(mod('DSP_FEATGEN_newSpectrogram'))
#DSP_FEATGEN_setLogOutput  = func_type(None,ctypes.c_void_p,ctypes.c_int,ctypes.c_double,ctypes.c_double,ctypes.c_double)(mod('DSP_FEATGEN_setLogOutput'))
#DSP_FEATGEN_setFFTOptions  = func_type(None,ctypes.c_void_p,ctypes.c_int,ctypes.c_int)(mod('DSP_FEATGEN_setFFTOptions'))
#DSP_FEATGEN_setMFCCOptions  = func_type(None,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_double,ctypes.c_double)(mod('DSP_FEATGEN_setMFCCOptions'))
#DSP_FEATGEN_setMIDIOptions  = func_type(None,ctypes.c_void_p,ctypes.c_int)(mod('DSP_FEATGEN_setMIDIOptions'))
#DSP_FEATGEN_init  = func_type(ctypes.c_int,ctypes.c_void_p)(mod('DSP_FEATGEN_init'))
#
#DSP_FEATGEN_delete  = func_type(None,ctypes.c_void_p)(mod('DSP_FEATGEN_delete'))
#DSP_FEATGEN_reset = func_type(None,ctypes.c_void_p)(mod('DSP_FEATGEN_reset'))
#
#DSP_FEATGEN_outputSize = func_type(None,ctypes.c_void_p,int_p)(mod('DSP_FEATGEN_outputSize'))
#DSP_FEATGEN_pushSample = func_type(ctypes.c_long,ctypes.c_void_p,double_p,ctypes.c_ulong)(mod('DSP_FEATGEN_pushSample'))
#DSP_FEATGEN_nextFrame  = func_type(ctypes.c_long,ctypes.c_void_p,double_p,ctypes.c_ulong)(mod('DSP_FEATGEN_nextFrame'))

c_void_p = ctypes.c_void_p
c_int = ctypes.c_int
c_ulong = ctypes.c_ulong
c_float = ctypes.c_float
c_char_p = ctypes.c_char_p
def cdef(cfunc,ret_type,*args):
    setattr(sys.modules[__name__],cfunc,func_type(ret_type,*args)(mod(cfunc)))

#cdef("DSP_Transcode_new",c_void_p,c_char_p,c_int,c_int,c_float)
#cdef("DSP_Transcode_new",c_void_p,DWORD_t,c_int,c_int,c_float)
#cdef("DSP_Transcode_setArtist",c_int,c_void_p,c_char_p)
#cdef("DSP_Transcode_setAlbum" ,c_int,c_void_p,c_char_p)
#cdef("DSP_Transcode_setTitle" ,c_int,c_void_p,c_char_p)
#cdef("DSP_Transcode_do" ,c_int,c_void_p,c_char_p)
#cdef("DSP_Transcode_do_w" ,c_int,c_void_p,c_char_p)


DSP_CHAN_MONO   = 1
DSP_CHAN_STEREO = 2

class DSP(object):
    """
        'virtual' base class DSP implements a basic
        wrapper class for the common features of a DSP block.
        you can Register() a single instance of this object to
        a single base channel at a time.
        A DSP block can be enabled/disabled. When disabled attempts
        to register it will fail silently.
        a DSP block can be added and removed in real time using setEnable

        variable 'self.data' is contractually important
            it must always contain a void pointer to an object
            that can be deleted by cbk_del.
    """
    def __init__(self,cbk_proc,cbk_set,cbk_del,priority=0):
        self.cbk_proc = cbk_proc;
        self.cbk_set = cbk_set;
        self.cbk_del  = cbk_del;
        self.cbk_reset = None;
        self.data = None;
        self._channel = 0;
        self._handle = 0;
        self._priority = priority;
        self.enabled = True
    def __del__(self):
        self.free()

    def Register(self,channel):
        self._channel  = channel

        if self.cbk_reset != None:
            self.cbk_reset(self.data);
        if self.isDisabled():
            return True;
        return self.doRegister();

    def doRegister(self):
        if self._channel != 0 and self.ChannelCheckSettings(self._channel):
            self._handle = pybass.BASS_ChannelSetDSP(self._channel,self.cbk_proc,self.data,self._priority);
            return self._handle != 0
        return False;

    def ChannelCheckSettings(self,channel):
        # todo check if callable
        if self.cbk_set == None :
            return True
        # get the channel information
        chaninfo = pybass.BASS_CHANNELINFO()
        if not pybass.BASS_ChannelGetInfo(self._channel,ctypes.byref(chaninfo)):

            return False

        # get the settings from the current DSP.
        s=0
        if self.cbk_set != None:
            s = long(self.cbk_set());

        r = True

        # check requirements for given flags
        #TODO chaninfo is not updating memory correctly.
        support_m = s&DSP_CHAN_MONO #and chaninfo.chans==1
        support_s = s&DSP_CHAN_STEREO #and chaninfo.chans==2
        #print chaninfo.chans, s,support_m , support_s
        r = support_m or support_s

        return True;

    def Remove(self):
        if self._handle != 0:
            pybass.BASS_ChannelRemoveDSP(self._channel,self._handle);
            self._handle = 0;
    def setEnabled(self,bEnable=True):
        if self.enabled and not bEnable: # going to disable:
            self.Remove()
        elif not self.enabled and bEnable:
            self.doRegister()
        self.enabled = bEnable
    def isEnabled(self):
        return self.enabled
    def isDisabled(self):
        return not self.enabled
    def free(self):
        if self.data != None and self.cbk_del!=None:
            self.cbk_del(self.data)
            self.data = None
    def impulseResponse(self,N=1024):
        #typedef void (CALLBACK DSPPROC)(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
        buf = (ctypes.c_float*N)()
        buf[0]=1
        for i in range(1,N):
            buf[0]=0
        size = ctypes.sizeof(ctypes.c_float)
        self.cbk_proc(0,self._channel,buf,N*size,self.data);
        return [ float(f) for f in buf ]
    def stepResponse(self,N=1024):
        #typedef void (CALLBACK DSPPROC)(HDSP handle, DWORD channel, void *buffer, DWORD length, void *user);
        buf = (ctypes.c_float*N)()
        for i in range(0,N):
            buf[0]=1
        size = ctypes.sizeof(ctypes.c_float)
        self.cbk_proc(0,self._channel,buf,N*size,self.data);
        return [ float(f) for f in buf ]

class DualDSP(DSP):
    """
        DSP base class for supporting one DSP proc function for
        stereo and another DSP proc function for mono
    """
    def __init__(self,cbk_proc_stereo,cbk_proc_mono,cbk_set,cbk_del,priority=0):
        super(DualDSP,self).__init__(None,cbk_set,cbk_del,priority)
        self.cbk_proc_stereo = cbk_proc_stereo
        self.cbk_proc_mono = cbk_proc_mono

    def doRegister(self):

        if self._channel==0:
            print("failed to register DSP block <> because the channel is invalid")
        elif not self.ChannelCheckSettings(self._channel):
            print("failed to register DSP block <> because the channel does not support it")
        else:

            chaninfo = pybass.BASS_CHANNELINFO()
            if not pybass.BASS_ChannelGetInfo(self._channel,chaninfo):
                return False

            proc = self.cbk_proc_stereo
            if chaninfo.chans==1:
                proc = self.cbk_proc_mono
            if proc != None:
                self._handle = pybass.BASS_ChannelSetDSP(self._channel,proc,self.data,self._priority);

            return self._handle != 0
        return False;

    def stepResponse(self,N=1024):
        raise NotImplementedError("undefined")
    def impulseResponse(self,N=1024):
        raise NotImplementedError("undefined")

class ZBPEQ(DSP):
    def __init__(self,sampleRate=44100,priority=0):
        super(ZBPEQ,self).__init__(DSP_ZBPEQ_Proc,None,DSP_ZBPEQ_Delete,priority)
        self.size = len(zbfilter11_fc);
        self.data = DSP_ZBPEQ_New(self.size,zbfilter11_fc,zbfilter11_bw,zbfilter11_gdb);

    def setGain(self,gaindata):
        buf = (ctypes.c_double*len(gaindata))(*gaindata)
        DSP_ZBPEQ_SetGain(self.data,buf,len(gaindata));

    def getGain(self):
        buf = (ctypes.c_double*self.size)()
        DSP_ZBPEQ_GetGain(self.data,buf,self.size)
        return [ float(buf[i]) for i in range(self.size) ]

class VOLEQ(DSP):
    def __init__(self,sampleRate=44100,priority=0):
        super(VOLEQ,self).__init__(DSP_VOLEQ_Proc,DSP_VOLEQ_Settings,DSP_VOLEQ_Delete,priority)
        self.data = DSP_VOLEQ_New();
        self.cbk_reset = self.reset
    def setScale(self,scale):
        DSP_VOLEQ_SetScale(self.data,float(scale));
    def reset(self,data):
        self.setEnabled(False)

class ZBVIS(DualDSP):
    def __init__(self,sampleRate=44100,priority=0):
        super(ZBVIS,self).__init__(DSP_ZBVIS_Proc,DSP_ZBVIS_Proc_Mono,DSP_ZBVIS_Settings,DSP_ZBVIS_Delete,priority)
        self.size = len(zbfilter11_fc);
        self.filter_size = 4410 # number of samples to average over

        s=2 # scale factor for number of bins
        r = [ 2**(x/s) for x in range(5*s,15*s) ]
        fc =  list(map(lambda x,y : (x+y)/2,[0,]+r[:-1],r))
        bw =  list(map(lambda x,y : x-y,fc,[0,]+fc[:-1]))
        c_fc = (ctypes.c_double*len(fc))(*fc)
        c_bw = (ctypes.c_double*len(bw))(*bw)
        #c_fc = zbfilter11_fc
        #c_bw = zbfilter11_bw


        self.size = len(c_fc)
        self.data = DSP_ZBVIS_New(sampleRate,self.size,c_fc,c_bw,self.filter_size);

    def getData(self):
        buf = (ctypes.c_double*self.size)()
        DSP_ZBVIS_GetData(self.data,buf,self.size)

        y = [ float(buf[i]) for i in range(self.size) ]
        return y;

class ZBLOG(DualDSP):
    """
        zblog is similar to zbvis
        it logs to a file the RMS average over a given period for a file.
        it always logs the total RMS average as well as additional column
        for the RMS average over a selected frequency range.
    """
    def __init__(self,sampleRate=44100,priority=0,fc=None,bw=None,filter_size=None,lograte=None):


        super(ZBLOG,self).__init__(DSP_ZBLOG_Proc,DSP_ZBLOG_Proc_Mono,DSP_ZBLOG_Settings,DSP_ZBLOG_Delete,priority)
        self.cbk_reset = DSP_ZBLOG_Reset

        c_fc = None
        c_bw = None
        self.size = 0;
        if isinstance(fc,list) and isinstance(bw,list):
            assert len(fc)==len(bw), "List of center frequencies must match th bandwidth list"
            self.size = len(fc);
            c_fc = (ctypes.c_double*self.size)(*fc)
            c_bw = (ctypes.c_double*self.size)(*bw)

        # number of samples to average over
        if filter_size != None:
            self.filter_size = filter_size
        else:
            self.filter_size = sampleRate
        # how often a sample is added to the stored vector
        if lograte != None:
            self.lograte = lograte
        else:
            self.lograte = sampleRate//4
        #print self.filter_size, self.lograte
        #c_int,c_int,double_p,double_p,c_int,c_int
        print(sampleRate,self.size,c_fc,c_bw,self.filter_size,self.lograte)
        self.data = DSP_ZBLOG_New(sampleRate,self.size,c_fc,c_bw,self.filter_size,self.lograte);

    def GetMean(self):
        """
            returns the mean of the overall signal
        """
        buf = double_p();
        size = DSP_ZBLOG_GetMean(self.data,0,ctypes.byref(buf));
        if size > 0:
            return [ float(buf[i]) for i in range(size) ]
        return []

    def GetFilterMean(self,idx):
        assert 0<=idx<=self.size, "invalid index range"
        buf = double_p();
        size = DSP_ZBLOG_GetMean(self.data,1+idx,ctypes.byref(buf));
        if size > 0:
            return [ float(buf[i]) for i in range(size) ]
        return []

    def getMaximum(self):
        """
            returns a dictionary with two keys
            "neg" : the negative number farthest from zero
            "pos" : the largest positive number.
        """
        p = ctypes.c_float(0);
        n = ctypes.c_float(0);
        DSP_ZBLOG_GetMaximum(self.data,ctypes.byref(p),ctypes.byref(n))
        return {"pos":p.value,"neg":n.value}

class ZBVEQ(DSP):
    def __init__(self,sampleRate=44100,priority=0):
        super(ZBVEQ,self).__init__(DSP_ZBVEQ_Proc,DSP_ZBVEQ_Settings,DSP_ZBVEQ_Delete,priority)
        self.data = DSP_ZBVEQ_New(sampleRate);
    def GetVX(self):
        buf = double_p();
        size = DSP_ZBVEQ_GetVX(self.data,ctypes.byref(buf));
        if size > 0:
            return [ float(buf[i]) for i in range(size) ]
        return []
    def GetVC(self):
        buf = double_p();
        size = DSP_ZBVEQ_GetVC(self.data,ctypes.byref(buf));
        if size > 0:
            return [ float(buf[i]) for i in range(size) ]
        return []

class PyDSP(DSP):
    def __init__(self,sampleRate=44100,priority=0):
        proc =  pybass.DSPPROC(self._proc)
        super(PyDSP,self).__init__(proc,self.Settings,None,priority)
    def _proc(self,handle, channel, voiddata, voiddatasize, voiduser):
        """ hidden function which matches the DSP callback signature
            this function translates voiddata and voiddatasize into
            a floating point buffer, and calls proc().
            This gives a more pythonic interface to python DSP blocks.
        """
        buffer = ctypes.cast(voiddata,ctypes.POINTER(ctypes.c_float))
        length = voiddatasize // ctypes.sizeof( ctypes.c_float )
        return self.proc(buffer,length)
    def proc(self,buffer,buffer_length):
        """ overload this function in a sub-class
            you must use indexing to access elements in the float buffer

            Example Swap Left and Right:
            for i in xrange(0,buffer_length,2):
                buffer[i],buffer[i+1] = buffer[i+1],buffer[i]
        """
        return;

    def Settings(self):
        return 0;

class PySwap(PyDSP):
    # [i]   is the left channel
    # [i+1] is the right channel
    def proc(self,buffer,buffer_length):
        """ swap the left and the right channels"""
        for i in xrange(0,buffer_length,2):
            buffer[i],buffer[i+1] = buffer[i+1],buffer[i]
    def Settings(self):
        # provide a hint that this is a stereo only DSP
        return DSP_CHAN_STEREO;

class PyLeft(PyDSP):
    def proc(self,buffer,buffer_length):
        """ merge both channels onto the left side"""
        for i in xrange(0,buffer_length,2):
            buffer[i] = (buffer[i+1]+buffer[i])/2
            buffer[i+1] = 0
    def Settings(self):
        # provide a hint that this is a stereo only DSP
        return DSP_CHAN_STEREO;

class PyRight(PyDSP):
    def proc(self,buffer,buffer_length):
        """ merge both channels onto the right side"""
        for i in xrange(0,buffer_length,2):
            buffer[i+1] = (buffer[i+1]+buffer[i])/2
            buffer[i] = 0
    def Settings(self):
        # provide a hint that this is a stereo only DSP
        return DSP_CHAN_STEREO;

class PyDspDynRng(PyDSP):
    """
    Calculate the Dynamic Range for Stereo Input.

    Dynamic range is
        20 * log10( Vmax / Vmin )
        ~90db if Vmax is 1.0 and Vmin is 1.0/2**15

    This module computes dynamic range as the ratio
        of the maximum value to the RMS average


    """
    def __init__(self):
        super(PyDspDynRng,self).__init__()

        self.max = 0
        self.rms = 0
        self.cnt = 0

    def proc(self,buffer,buffer_length):

        for i in range(0,buffer_length,2):
            v = (buffer[i]+buffer[i+1])/2
            self.rms += v*v
            self.cnt += 1
            self.max = max(v,self.max)

    def finalize(self):

        self.rms /= self.cnt
        self.rms = self.rms**.5

        return 20*math.log( self.max / self.rms, 10)

    def Settings(self):
        # provide a hint that this is a stereo only DSP
        return DSP_CHAN_STEREO;

def BufError():
    return BufferError("underlying c structure is not initialized");

#class FeatureGenerator(object):
#    def __init__(self,FS):
#        self.vpfg = DSP_FEATGEN_newMFCC(FS);
#        if self.vpfg == None:
#            raise BufError()
#    # todo getters / setters for feature gen settings
#    def init(self):
#
#        if self.vpfg == None:
#            raise BufError()
#        DSP_FEATGEN_setLogOutput(self.vpfg,1,0,20,1e-16);
#        #DSP_FEATGEN_setMIDIOptions(self.vpfg,12);
#        x = DSP_FEATGEN_init(self.vpfg)
#        if x != 0:
#            print("error",x)
#            raise BufError()
#
#        c_y_size = ctypes.c_int()
#        DSP_FEATGEN_outputSize(self.vpfg,ctypes.byref(c_y_size))
#        self.y_size = c_y_size.value
#        self.y = (ctypes.c_double*self.y_size)()
#
#    def push(self,seq):
#        if self.vpfg == None:
#            raise BufError()
#
#        x_size = len(seq)
#        x = (ctypes.c_double*x_size)(*seq)
#
#        return DSP_FEATGEN_pushSample(self.vpfg,x,x_size);
#
#    def getFrame(self):
#        if self.vpfg == None:
#            raise BufError()
#
#        #c_y_size = ctypes.c_int()
#        #DSP_FEATGEN_outputSize(self.vpfg,ctypes.byref(c_y_size))
#        #y_size = c_y_size.value
#        #y = (ctypes.c_double*y_size)()
#
#        n = DSP_FEATGEN_nextFrame(self.vpfg,self.y,self.y_size);
#        if n > 0:
#            return [ float(self.y[i]) for i in range(n)  ]
#        return None;


#class BassTranscoder(object):
#
#    def __init__(self,channel,bitrate,quality,scale):
#        self.data = DSP_Transcode_new(channel,bitrate,quality,scale)
#
#    def setArtist(self,artist):
#        if self.data:
#            DSP_Transcode_setArtist(self.data,artist.encode("utf-8"))
#    def setAlbum(self,album):
#        if self.data:
#            DSP_Transcode_setAlbum(self.data,album.encode("utf-8"))
#    def setTitle(self,title):
#        if self.data:
#            DSP_Transcode_setTitle(self.data,title.encode("utf-8"))
#    def doTranscode(self,outFile):
#        if self.data:
#            if os.name=="nt":
#                DSP_Transcode_do_w(self.data,outFile.encode("utf-16-le"))
#            else:
#                DSP_Transcode_do(self.data,outFile)
"""
typedef unsigned int   uint;
typedef unsigned short word;
typedef unsigned char  byte;
http://stackoverflow.com/questions/4676327/how-to-open-a-file-with-wchar-t-containing-non-ascii-string-in-linux
int UTF16to8( wchar_t* w, char* s ) {
  uint  c;
  word* p = (word*)w;
  byte* q = (byte*)s; byte* q0 = q;
  while( 1 ) {
    c = *p++;
    if( c==0 ) break;
    if( c<0x080 ) *q++ = c; else
      if( c<0x800 ) *q++ = 0xC0+(c>>6), *q++ = 0x80+(c&63); else
        *q++ = 0xE0+(c>>12), *q++ = 0x80+((c>>6)&63), *q++ = 0x80+(c&63);
  }
  *q = 0;
  return q-q0;
}

int UTF8to16( char* s, wchar_t* w ) {
  uint  cache,wait,c;
  byte* p = (byte*)s;
  word* q = (word*)w; word* q0 = q;
  while(1) {
    c = *p++;
    if( c==0 ) break;
    if( c<0x80 ) cache=c,wait=0; else
      if( (c>=0xC0) && (c<=0xE0) ) cache=c&31,wait=1; else
        if( (c>=0xE0) ) cache=c&15,wait=2; else
          if( wait ) (cache<<=6)+=c&63,wait--;
    if( wait==0 ) *q++=cache;
  }
  *q = 0;
  return q-q0;
}
"""