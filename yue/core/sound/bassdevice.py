
import os,sys


from yue.core.sound.device import SoundDevice, MediaState

from yue.core.song import Song
from yue.core.bass.bassplayer import BassPlayer, BassException

try:
    from ..bass.pybassdsp import ZBPEQ, ZBVIS, VOLEQ
except ImportError as e:
    print("dsp import",e)
    ZBPEQ = None
    ZBVIS = None
    VOLEQ = None

bass_states = {
    BassPlayer.PLAYING : MediaState.play,
    BassPlayer.PAUSED  : MediaState.pause,
    BassPlayer.STOPPED  : MediaState.end,
    BassPlayer.UNKNOWN  : MediaState.error,
    }

class BassSoundDevice(SoundDevice):
    """Playback implementation of Sound Device"""
    __instance = None
    def __init__(self, playlist, libpath, use_capi=False, cbkfactory=None):
        super(BassSoundDevice, self).__init__(playlist, cbkfactory)
        self.volume = 0.5
        self.error_state = False
        self.current_song = None
        self.enable_equalizer = False

        BassPlayer.init()

        self.load_plugin(libpath, "bass_aac")
        self.load_plugin(libpath, "bass_alac")
        self.load_plugin(libpath, "bassflac")
        self.load_plugin(libpath, "bassmidi")
        self.load_plugin(libpath, "bassopus")
        self.load_plugin(libpath, "basswma")
        self.load_plugin(libpath, "basswv")

        self.use_capi = use_capi

        self._createDevice()

    def _createDevice(self):

        self.device = BassPlayer(use_capi=self.use_capi)

        if ZBPEQ is not None:
            self.zbpeq = ZBPEQ(priority=250)
            self.zbpeq.setEnabled(False)
            self.device.addDsp("zbpeq", self.zbpeq)

            self.voleq = VOLEQ(priority=500)
            self.voleq.setEnabled(False)
            self.device.addDsp("voleq", self.voleq)

            self.zbvis = ZBVIS(priority=1000)
            self.zbvis.setEnabled(True)
            self.device.addDsp("zbvis", self.zbvis)

            sys.stdout.write("successfully enabled DSP processes.\n")
        else:
            self.zbpeq = None
            self.voleq = None
            self.zbvis = None
            sys.stderr.write("error enabling DSP processes.\n")

        # this feature causes a segfault on android.
        if self.use_capi:
            self.device.setStreamEndCallback(self.on_bass_end)

    def refresh(self):
        BassPlayer.free()
        BassPlayer.init()
        self._createDevice()

    def name(self):
        return "Bass Audio"

    def on_bass_end(self, *args):
        self.on_song_end.emit( self.current_song )

    def load_plugin(self,libpath,name):

        try:

            plugin_path = os.path.join(libpath,"lib%s.so"%name)
            if os.path.exists( plugin_path ):
                return BassPlayer.loadPlugin( plugin_path )

            plugin_path = os.path.join(libpath,"lib%s.dylib"%name)
            if os.path.exists( plugin_path ):
                return BassPlayer.loadPlugin( plugin_path )

            plugin_path = os.path.join(libpath,"%s.dll"%name)
            if os.path.exists( plugin_path ):
                return BassPlayer.loadPlugin( plugin_path )

            print("Plugin: Plugin not found '%s' in %s."%(name,libpath))

        except OSError as e:
            print(e)
        except Exception as e:
            print(e)

    def unload(self):
        self.device.unload()

    def load(self, song):
        path = song[Song.path]
        path = self.check_path( path )
        self.current_song = song
        try:
            self.device.unload()
            if self.device.load( path ):
                self.error_state = False

                self.setEQ( song )

                self.on_load.emit(song)
            else:
                self.error_state = True

        except UnicodeDecodeError as e:
            print(e)
            self.error_state = True

    def equalizerEnabled(self):
        return self.enable_equalizer

    def toggleEQ(self):
        self.setEQEnabled( not self.enable_equalizer )

    def setEQEnabled(self,b):
        if b and not self.enable_equalizer:
            self.enable_equalizer = True
            self.voleq.setEnabled(True);
        elif not b and self.enable_equalizer:
            self.enable_equalizer = False
            self.voleq.setEnabled(False);
        sys.stdout.write("EQ: %s\n"%(self.enable_equalizer))

    def setEQ(self, song):

        factor = Song.getEqFactor( song )
        if self.voleq != None:
            self.voleq.setScale(factor);
            if factor > 0 and self.enable_equalizer:
                self.voleq.setEnabled(True);
            else:
                self.voleq.setEnabled(False);

    def play(self):

        if self.device.play():
            try:
                idx,key = self.playlist.current()
                self.on_state_changed.emit(idx,key,self.state())
            except IndexError:
                sys.stderr.write("error: No Current Song\n")

    def pause(self):
        if self.device.pause():
            try:
                idx,key = self.playlist.current()
                self.on_state_changed.emit(idx,key,self.state())
            except IndexError:
                sys.stderr.write("error: No Current Song\n")

    def seek(self, seconds):
        self.device.position(seconds)

    def position(self):
        """ return current position in seconds (float)"""
        return self.device.position()

    def duration(self):
        return self.device.duration()

    def setVolume(self, volume):
        """ volume: in range 0.0 - 1.0"""
        self.device.volume(max(0, min(100, int(volume*100))))

    def getVolume(self):
        """ volume: in range 0.0 - 1.0"""
        return self.device.volume()/100

    def state(self):
        if self.error_state:
            return MediaState.error
        bass_state = self.device.status()
        return bass_states.get(bass_state, MediaState.not_ready)

    def getDspData(self, dspproc):
        if dspproc == 'zbvis' and self.zbvis is not None:
            return self.zbvis.getData()

    def updateDSP(self, proc):
        if "ZBPEQ" in proc and self.zbpeq is not None:
            seq = proc["ZBPEQ"]
            if all(map(lambda x: x == 0.0, seq)):
                self.zbpeq.setEnabled(False)
                sys.stdout.write("ZBPEQ disabled")
            else:
                self.zbpeq.setEnabled(True)
            self.device.setDspData("zbpeq", seq)
