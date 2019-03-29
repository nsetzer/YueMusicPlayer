
from . import pybass

import os
import sys
import math
import ctypes
import traceback

isPosix = os.name == 'posix'

if sys.version > '3':
    unicode = str

class BassException(Exception):
    pass

class StreamPlayer(object):
    """
        modified StreamPlayer (which doesnt exist yet),
        that plays a signal stream that has been loaded into memory.

        provide a buffer with data...
    """

    def __init__(self,Fs,use_float=True, chan=1):

        flags = 0;
        if use_float:
            flags = pybass.BASS_SAMPLE_FLOAT
        proc = pybass.STREAMPROC_PUSH

        channel = pybass.BASS_StreamCreate(int(Fs),chan,flags,proc,None);
        self.channel = channel;

        buffer = []
        length = 0;
        pybass.BASS_StreamPutData(self.channel,buffer,length)

class BassPlayer(object):

    UNKNOWN = 1
    STOPPED = 2
    PLAYING = 3
    PAUSED  = 4
    STALLED = 5
    ERROR   = 6
    isINIT = False

    default_flags = 0

    @staticmethod
    def init(sampleRate=44100):

        if BassPlayer.isINIT:
            return
        # float dsp is needed for my custom dsp blocks
        pybass.BASS_SetConfig(pybass.BASS_CONFIG_FLOATDSP, True)
        # enable automatic switching to the default device
        # used when someone plugs in / unplugs headphones, etc.
        pybass.BASS_SetConfig(pybass.BASS_CONFIG_DEV_DEFAULT, True)

        if not pybass.BASS_Init(-1, sampleRate, 0, 0, 0):
            print('BASS_Init error %s' % pybass.get_error_description(pybass.BASS_ErrorGetCode()))

        if BassPlayer.supportsFloat() :
            #raise FloatingPointError("BASS does not support Floating Point DSP.")
            BassPlayer.default_flags = pybass.BASS_SAMPLE_FLOAT
        else:
            sys.stderr.write('BASS init error: Floating Point DSP unsupported')

        BassPlayer.isINIT = True

        BassPlayer.fft_n = {
            8 : pybass.BASS_DATA_FFT256,
            9 : pybass.BASS_DATA_FFT512,
            10: pybass.BASS_DATA_FFT1024,
            11: pybass.BASS_DATA_FFT2048,
            12: pybass.BASS_DATA_FFT4096,
            13: pybass.BASS_DATA_FFT8192,
            14: pybass.BASS_DATA_FFT16384,
        }

    @staticmethod
    def free():
        if not pybass.BASS_Free():
            print('BASS_Free error %s' % pybass.get_error_description(pybass.BASS_ErrorGetCode()))
        BassPlayer.isINIT = False

    @staticmethod
    def loadPlugin(plugpath):
        # TODO: plugins with unicode paths may not work on windows.
        # but giving the unicode flag here did not work at all for windows.
        plugpath = unicode(plugpath);
        pybass.BASS_PluginLoad(plugpath.encode("utf-8"),0);
        if BassPlayer.errorCode()!=0:
            print("path exists: %s"%os.path.exists(plugpath),plugpath)
            print(BassPlayer.error())
        return pybass.BASS_ErrorGetCode()

    @staticmethod
    def errorCode():
        return pybass.BASS_ErrorGetCode()

    @staticmethod
    def errorMessage(code):
        return pybass.get_error_description(code)

    @staticmethod
    def error():
        c = pybass.BASS_ErrorGetCode()
        return "%d:%s" % (c, pybass.get_error_description(c))

    @staticmethod
    def exception():
        c = pybass.BASS_ErrorGetCode()
        return BassException("%d:%s" % (c, pybass.get_error_description(c)))

    @staticmethod
    def check_exception():
        if BassPlayer.errorCode() != 0:
            raise BassPlayer.exception()

    @staticmethod
    def supportsFloat():
        l = lambda a, b, c, d: 0
        r = pybass.BASS_StreamCreate(44100, 2,
            pybass.BASS_SAMPLE_FLOAT, pybass.STREAMPROC(l), 0)
        pybass.BASS_StreamFree(r)
        return r != 0

    @staticmethod
    def statusMessage(status):
        if status == BassPlayer.STOPPED:
            return "Stopped"
        elif status == BassPlayer.PLAYING:
            return "Playing"
        elif status == BassPlayer.PAUSED:
            return "Paused"
        elif status == BassPlayer.STALLED:
            return "Stalled"
        return "Unknown"

    def __init__(self, use_capi=False):
        self.use_capi = use_capi  # use stream callbacks

        self.channel = 0
        self.dsp_blocks = {}
        # on error set this flag.
        self.flagError = 0

        self._volume = 75

        ptr = ctypes.pointer(ctypes.py_object(self))
        self.cptr_self = ctypes.cast(ptr, ctypes.c_void_p)

        g = lambda x : sys.stdout.write("stream end\n")
        self.sync_callbacks = {"stream_end" : g}

    def setStreamEndCallback(self, cbk):
        """ def cbk( player ) """
        self.sync_callbacks['stream_end'] = cbk

    def setStreamSetPosCallback(self, cbk):
        """ def cbk( player ) """
        self.sync_callbacks['stream_setpos'] = cbk

    def setStreamPosCallback(self, cbk):
        """
        this callback is not strictly useful,

        it is called when the stream reaches a specific position, in bytes
        currently I do not support setting what position for the callback
        to trigger on.
        """
        self.sync_callbacks['stream_pos'] = cbk

    def load(self, filepath):

        lFlags = self.default_flags | pybass.BASS_STREAM_AUTOFREE
        if isPosix:
            # lFlags |= pybass.BASS_UNICODE
            filepath = unicode(filepath).encode("utf-8")
        else:
            # don't change this.
            lFlags |= pybass.BASS_UNICODE
            filepath = unicode(filepath)

        self.unload()

        channel = pybass.BASS_StreamCreateFile(False,filepath,0,0,lFlags)
        self.flagError = BassPlayer.errorCode()

        if channel == 0 or self.flagError != 0:
            print("BASS LOAD: %s" % BassPlayer.error())
            return False
            #print BassPlaerroryer.error()
            #raise IOError( "load song: " + BassPlayer.error() )

        #lFlags = lFlags|pybass.BASS_MUSIC_AUTOFREE|pybass.BASS_MUSIC_RAMPS
        #channel = pybass.BASS_MusicLoad(False,filepath,0,0,lFlags,1)
        #if channel==0:
        #    print('error BASS_MusicLoad %s' % BassPlayer.error() )
        #    return 1

        self.channel = channel
        # volume is set per channel, and not globally.
        # (the BASS_SETVOLUME function sets the DEVICE volume.)
        self.volume(self._volume)
        # each dsp keeps track of whether or not it is enabled.
        for _, dsp in self.dsp_blocks.items():
            dsp.Register(self.channel)

        position = pybass.BASS_ChannelGetPosition(
            self.channel, pybass.BASS_POS_BYTE)
        if position != 0:
            print("BASS LOAD: position in bytes %d." % position)

        #
        # this causes a segfault on android :(
        if self.use_capi:
            pybass.BASS_ChannelSetSync(self.channel,
                pybass.BASS_SYNC_END, 0, syncStreamEnd, self.cptr_self)
            #pybass.BASS_ChannelSetSync(self.channel,pybass.BASS_SYNC_SETPOS,0,syncStreamSetPos, self.cptr_self )
            #pybass.BASS_ChannelSetSync(self.channel,pybass.BASS_SYNC_POS,0,syncStreamPos, self.cptr_self )

        return True

    def decode(self, filepath):

        self.unload()

        dFlags = self.default_flags | pybass.BASS_STREAM_DECODE

        if isPosix:
            filepath = unicode(filepath).encode("utf-8")
        else:
            dFlags |= pybass.BASS_UNICODE
            filepath = unicode(filepath)  # .encode("utf-16")

        channel = pybass.BASS_StreamCreateFile(False, filepath, 0, 0, dFlags)

        self.flagError = BassPlayer.errorCode()
        if channel == 0 or self.flagError != 0:
            print("BASS LOAD: %s" % BassPlayer.error())
            return False

        self.channel = channel

        for _, dsp in self.dsp_blocks.items():
            dsp.Register(channel)

        return True

    def stream(self, rate=44100, chans=2):

        self.unload()

        dFlags = self.default_flags
        dProc  = pybass.STREAMPROC_PUSH
        print("create stream %d %d"%(rate,chans))
        channel = pybass.BASS_StreamCreate(rate,chans,dFlags,dProc,0)
        print(BassPlayer.error())
        self.flagError = BassPlayer.errorCode()
        if channel==0 or self.flagError!=0:
            return False;

        self.channel = channel

        #for _,dsp in self.dsp_blocks.items():
        #    dsp.Register(channel);

        return True

    def streamPush(self, data):
        length = len(data)
        buf = (ctypes.c_float*length)(*data)
        print(length, len(buf))
        dw_size  = pybass.BASS_StreamPutData(self.channel, buf, length)
        print(BassPlayer.error())

    def unload(self):
        if self.channelIsValid():
            # TODO: determine whether check for error is needed
            #pybass.BASS_MusicFree(self.channel);
            pybass.BASS_StreamFree(self.channel)
            self.channel = 0
        return True

    def play(self, restart=False):

        if self.channelIsValid():
            print("bass: channel play", self.channel)
            bytes = pybass.BASS_ChannelGetPosition(self.channel, pybass.BASS_POS_BYTE);
            #print "bytes@PLAY:%d"%bytes
            #traceback.print_stack();
            try:
                if pybass.BASS_ChannelPlay(self.channel, restart):
                    return True
            finally:
                print("bass: channel play +: ", BassPlayer.error(), self.status())
        print("bass: channel play -: ", BassPlayer.error())
        return False

    def pause(self):

        if self.channelIsValid():
            print("bass: channel pause", self.channel)
            pybass.BASS_ChannelPause(self.channel)
            # todo check for errors
            return True
        return False

    def stop(self):
        print("bass: channel stop", self.channel)
        pybass.BASS_ChannelStop(self.channel)
        pybass.BASS_ChannelSetPosition(self.channel, 0, pybass.BASS_POS_BYTE)

    def getSamples(self, sampleCount=44100):
        """
            if opened for decoding returns N samples
            returns sampleCount samples.
            for Stereo the samples alternate left,right,left.
            if sampleCount%#channels!=0 the number of samples returns
            may be different.
            sampleCount defaults to the sample rate.
            returns an indexable object containing float data.
        """
        buffer = (ctypes.c_float*sampleCount)()
        voidbuf = ctypes.cast(buffer,ctypes.c_void_p)

        flag = (ctypes.sizeof(ctypes.c_float)*sampleCount)|pybass.BASS_DATA_FLOAT
        res = pybass.BASS_ChannelGetData(self.channel,voidbuf,flag);

        if BassPlayer.errorCode() not in [pybass.BASS_OK, pybass.BASS_ERROR_ENDED]:
            raise ValueError("Bass %d %s"%(BassPlayer.errorCode() , BassPlayer.error()) )

        if res==ctypes.c_ulong(-1).value:
            return None
        return buffer;

    def fft(self, logn):
        """
            return the fft from the sample data.
            channel must be a decode channel
            logn must be from 8 to 14.
                corresponds to the size of the fft.
            returns None on error
        """
        buffer = (ctypes.c_float*sampleCount)()
        voidbuf = ctypes.cast(buffer,ctypes.c_void_p)
        flag = BassPlayer.fft_n.get(logn,pybass.BASS_DATA_FFT1024);
        flag |= pybass.BASS_DATA_FLOAT|pybass.BASS_DATA_FFT_REMOVEDC
        res = pybass.BASS_ChannelGetData(self.channel,voidbuf,flag);
        if BassPlayer.errorCode() not in [pybass.BASS_OK, pybass.BASS_ERROR_ENDED]:
            raise ValueError("Bass %d %s"%(BassPlayer.errorCode() , BassPlayer.error()) )
        if res==ctypes.c_ulong(-1).value:
            return None
        return buffer

    def spin(self):
        """ push all samples thru all dsp blocks. """
        idx = 0;
        while True:
            if self.getSamples()==None:
                break;
            idx += 1
        return idx

    def volume(self, vol=None):
        """
            set the volume to 'vol'.
            valid range is from 0 to 100.
        """

        self._volume = vol;

        ft = lambda x : x*x           # experiment, non linear curve
        rt = lambda x : math.sqrt( x )#

        if vol != None:
            vol = min(100,max(0,vol))/100.0
            pybass.BASS_ChannelSetAttribute( self.channel ,pybass.BASS_ATTRIB_VOL,ft(vol));
        flt = ctypes.c_float(0)
        pybass.BASS_ChannelGetAttribute( self.channel,pybass.BASS_ATTRIB_VOL,ctypes.byref(flt));
        return int(100*rt( flt.value ))

    def duration(self):
        length = pybass.BASS_ChannelGetLength(self.channel, pybass.BASS_POS_BYTE);
        seconds = pybass.BASS_ChannelBytes2Seconds(self.channel, length);
        return seconds

    def position(self, seconds=None):
        """ get/set current position, in seconds.
        """
        if seconds is not None:
            bytes = pybass.BASS_ChannelSeconds2Bytes(self.channel,seconds);
            length=pybass.BASS_ChannelGetLength(self.channel, pybass.BASS_POS_BYTE);
            if bytes > length:
                bytes = length
            pybass.BASS_ChannelSetPosition(self.channel,bytes,pybass.BASS_POS_BYTE);
        else:
            bytes = pybass.BASS_ChannelGetPosition(self.channel,pybass.BASS_POS_BYTE);

        seconds = pybass.BASS_ChannelBytes2Seconds(self.channel,bytes);
        return float( seconds )

    def status(self):

        if self.flagError != 0:
            return BassPlayer.ERROR

        status = pybass.BASS_ChannelIsActive(self.channel)

        if status == pybass.BASS_ACTIVE_STOPPED:
            return BassPlayer.STOPPED
        elif status == pybass.BASS_ACTIVE_PLAYING:
            return BassPlayer.PLAYING
        elif status == pybass.BASS_ACTIVE_PAUSED:
            return BassPlayer.PAUSED
        elif status == pybass.BASS_ACTIVE_STALLED:
            return BassPlayer.STALLED
        return BassPlayer.UNKNOWN

    def channelIsValid(self):
        """ returns true if play() will succeed """
        return self.channel != 0

    def isStereo(self):
        chaninfo = pybass.BASS_CHANNELINFO()
        if not pybass.BASS_ChannelGetInfo(self.channel,chaninfo):
            return False
        return chaninfo.chans==2

    def getSampleRate(self):
        chaninfo = pybass.BASS_CHANNELINFO()
        if not pybass.BASS_ChannelGetInfo(self.channel,chaninfo):
            return 0
        BassPlayer.check_exception()
        print(chaninfo.freq)
        print(chaninfo.chans)
        print(chaninfo.origres)
        return chaninfo.freq

    def addDsp(self, name, oDsp):
        self.dsp_blocks[name] = oDsp

    def getDspData(self, dspname):
        """
            abstraction later for dsps
            context dependent getter function for dsps
            that provide get data functions.
        """
        if dspname not in self.dsp_blocks:
            return None;
        if dspname == "zbvis":
            return self.dsp_blocks["zbvis"].getData()
        return None

    def setDspData(self,dspname,data):
        """ abstraction layer for dsps
            context dependent setter function for dsps that
            provide set data functions
        """
        if dspname not in self.dsp_blocks:
            return;
        if dspname == "zbpeq":
            self.dsp_blocks["zbpeq"].setGain(data);

    def enableDsp(self,dspname,enabled=True):
        """
            disabling/enabling takes effect when the song is loaded.
        """
        if dspname in self.dsp_blocks:
            self.dsp_blocks[dspname].setEnabled(enabled)


P_PY_OBJECT = ctypes.POINTER(ctypes.py_object)

@pybass.SYNCPROC
def syncStreamEnd( handle, buffer, length, user):
    player =  ctypes.cast(user,P_PY_OBJECT)[0]
    #print(" *** stream end event : calling callback\n")
    cbk = player.sync_callbacks.get("stream_end",None)
    if cbk is not None:
        cbk( player )

@pybass.SYNCPROC
def syncStreamSetPos( handle, buffer, length, user):
    player =  ctypes.cast(user,P_PY_OBJECT)[0]
    cbk = player.sync_callbacks.get("stream_setpos",None)
    if cbk is not None:
        cbk( player )

@pybass.SYNCPROC
def syncStreamPos( handle, buffer, length, user):
    player =  ctypes.cast(user,P_PY_OBJECT)[0]
    cbk = player.sync_callbacks.get("stream_pos",None)
    if cbk is not None:
        cbk( player )





