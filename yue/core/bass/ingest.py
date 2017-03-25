
from .pybassdsp import *
from .pybass import *
from .bassplayer import BassPlayer, BassException
import ctypes

class SignalIngest(object):
    def __init__(self,Fs_in,Fs_out,isStereo=False):
        self.vpai = DSP_AudioIngest_New(Fs_in,Fs_out,isStereo);
        self.scale = int(math.ceil(Fs_out / Fs_in))

        if self.vpai == None:
            raise BufError()
    def next(self,seq):
        x = (ctypes.c_float*len(seq))(*seq)
        y = (ctypes.c_float*(len(seq)*self.scale))()
        n = DSP_AudioIngest_fromSignal(self.vpai,x,len(x),y,len(y))
        return y[:n];
    def __del__(self):
        DSP_AudioIngest_Delete(self.vpai)

class FileIngest(object):
    """
        Read in a file of any format and convert to mono at a
        specified sample rate
    """

    def __init__(self,filepath,Fs_out):
        self.vpai = None

        BassPlayer.init()

        self.bp = BassPlayer();

        if not self.bp.decode(filepath):
            raise BassPlayer.exception()
        #print(BassPlayer.error())

        Fs_in = self.bp.getSampleRate();

        if Fs_in == 0:
            raise BassException("input sample rate cannot be zero")
        if Fs_in > 200000:
            raise BassException("input sample rate is too large to comprehend: %d"%Fs_in)

        #print("opened rate: %d"%Fs_in)
        #print("output rate: %d"%Fs_out)
        is_stereo = ctypes.c_char(self.bp.isStereo())
        self.vpai = DSP_AudioIngest_New(Fs_in,Fs_out,is_stereo);
        self.scale = int(math.ceil(Fs_out / Fs_in))
        #print("scale",self.scale)

        self.buf_float = (ctypes.c_float*(Fs_out))()

        if self.vpai == None:
            raise BufError()

    def read(self):
        out = []
        temp = self.next()
        while len(temp) > 0:
            out += temp
            temp = self.next()
        return out

    def next(self):
        n = DSP_AudioIngest_fromChannel(self.vpai,self.bp.channel,self.buf_float,len(self.buf_float))
        #print(n,type(n),BassPlayer.error())
        if n <= 0:
            return []
        return self.buf_float[:n];

    def __del__(self):
        if self.vpai:
            DSP_AudioIngest_Delete(self.vpai)
        if self.bp.channelIsValid():
            self.bp.unload()