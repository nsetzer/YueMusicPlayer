#! cd ../../.. && python34 test/test_client.py --eq

"""

    dialogVolEQLearn

    This dialog can be used to learn optimal volume settings for a list of songs.
    The input is a list of song objects.
    BASS audio is used to decode a wide array of media types.

    The learned number tries to set the MODE of the input sequence to 100.
    Each learned number is independent of all other given input songs.
    Target values where derived from an training corpus of 5000 songs.

    when comparing a number to 100:
        A Value of 50 means the song is "twice as loud",
        While a value of 200 means the song is "twice as quiet".

    To use this learned number as a scale factor:
        cPyBASS defines a VOLEQ DSP block. This block multiples a constant
        across all samples in an audio stream.

        Divide the learned number from this program by 250. This will scale
        the mean + 2 standards of deviation below a scale factor of 100.
        This will prevent clipping from occurring for about 90% of the songs.

        The remaining songs that have a scale factor above 1.0 may have clipping.
        Generally these songs are so quiet that a scale factor of 2.0 will not
        introduce clipping. It is uncommon to learn a number above a value of
        400. A final scale factor of 2.0+ is rare.

        Also, the method learns to place 90% of the sampled features at or below
        some threshold, chosen here to be .35. This is another way to guarantee
        that a minimal number of song cases can have any clipping.

    The use case implementation can be found in the file audio_BASS.py
    This file defines a method setEQ
    setEQ divides the learned number by 250, and sets the maximum value to 500.
    this means the scale factor can at most be 2.0, regardless of what is learned.

    Optionally, VOLEQ can be disabled for inputs between 90 and 110, which
    will be the vast majority of cases, as that scale factor will not change
    very much.
"""

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import time

from yue.core.song import Song
from yue.core.sqlstore import SQLStore
from yue.core.library import Library

import random
import itertools

import os,sys

try:
    from yue.core.bass.bassplayer import BassPlayer
    from yue.core.bass.pybassdsp import ZBLOG
except ImportError:
    BassPlayer = None
    ZBLOG = None

def pputf(s):
    g = lambda c : c if ord(c) < 128 else '?'
    return ''.join( g(c) for c in s )

def histogramGen(sequence,bins):
    hist = [0]*len(bins)
    for x in sequence:
        idx = 0;
        for i,b in enumerate(bins):
            if b>x:
                hist[idx] += 1
                break;
            idx = i
    return hist

class ProgressBar(QProgressBar):

    _text = ""
    textHeight = 0

    def __init__(self,parent=None):
        super(ProgressBar, self).__init__(parent)
        self.setTextVisible(False)

        fm = QFontMetrics(self.font())

        self.textHeight = fm.height()

    def paintEvent(self,event):
        w = self.width()
        h = self.height()

        y = h/2
        y_ = self.textHeight/2

        super(ProgressBar, self).paintEvent(event)

        painter = QPainter(self)
        painter.drawText(3,y-y_,w,y+y_,0,self._text)

    def setText(self,string):
        fm = QFontMetrics(self.font())
        self.textHeight = fm.height()

        self._text = str(string)
        self.update()

    def setValue(self,v):
        super(ProgressBar, self).setValue(v);

class LearnThread(QThread):
    def __init__(self,parent,songList):
        super(LearnThread, self).__init__()
        self.parent = parent

        self.songList = songList

        self.estimates = []
        self.start_time = 0;

        self.alive = True
        self.errors = 0;

    def kill(self):
        self.alive = False;

    def loadPlugins(plugin_path):
        ext = "so" if isPosix else "dll"
        for plugin in [ p for p in os.listdir(plugin_path) \
                        if fileGetExt(p).lower()==ext ]:
            path = os.path.join(plugin_path,plugin);
            val = BassPlayer.loadPlugin(path);
            print("Loading Plugin: %s %s"%(plugin,val==0))

    def run(self):
        BassPlayer.init()
        bp = BassPlayer();

        if len(self.songList)==0:
            self.update_progress(-1);
            return;

        for _,dsp in bp.dsp_blocks.items():
            dsp.setEnabled(False);

        zblog = ZBLOG(priority = 500,filter_size=44100//8,lograte=44100//4);
        bp.addDsp("zblog",zblog);

        self.start_time = time.time()

        library = Library.instance().reopen()

        self.idx = 0;
        for song in self.songList:
            path = song[Song.path]
            #print pputf(path)
            try :
                #dt.timer_start()
                scale,samples = self.learn_one(bp,zblog,path)
                if scale != 0:
                    # update time estimate
                    ms = 0 # dt.timer_end();
                    self.update_estimate(ms,len(samples))
                    iscale = int(scale * 100);

                    avg = sum(samples)/len(samples)
                    iscale = max(0,min(1000,iscale));
                    #avgs = .35/avg;
                    #print "iscale is %d; avg=%.3f midpoint=%d"%(iscale,avg,int(avgs*100))
                    song[Song.equalizer]=iscale
                    library.update(song[Song.uid],**{Song.equalizer:iscale})
                    #print iscale
                else:
                    self.errors += 1
            except Exception as e:
                print("ERROR:"+str(e))
                self.errors += 1;

            self.display_estimate()

            bp.unload()

            self.update_progress(self.idx);

            if not self.alive:
                break;
            self.idx += 1;

        self.display_estimate()

        # experimental code follows
        seq = [ song[Song.equalizer] for song in self.songList]
        bin = range(0,600,5);
        h = histogramGen(seq,bin)
        p = list(zip(bin,h));
        p.sort(key=lambda x:x[1],reverse=True)
        print("top 5 results:")
        for i in range(5):
            print("%d: %s "%(i+1,p[i]))
        print("bottom 5 results:")
        for i in range(5):
            print("%d: %s "%(i+1,p[-i]))
        avg = sum(seq)/float(len(seq))
        print("avg:", avg)

        if self.alive:
            self.update_progress(-1);
            self.parent.sync_set_done.emit()

    def learn_one(self,bp,zblog,path):

        scale = 0;
        samples = []
        if bp.decode(path):

            bp.spin()

            samples = zblog.GetMean()

            if len(samples)!=0:

                # for a non-random set of 5000 songs:
                # .33/.35 puts the mean value at 100.
                # .2 puts ~80% below 100.

                target_volume = 0.25
                #target_volume  = 0.35 # for learn
                target_percent = 0.90
                avg = sum(samples)/len(samples)
                scale = target_volume/avg
                #target_factor = 100.0/250.0 # this scales 2 standard deviations below 100
                #scale = cPyBASS.learn_scale(samples,target_volume,target_percent);
                # if any sample is greater than 1.0
                #d = zblog.getMaximum();
                #m1 = abs(d["pos"]*scale)
                #m2 = abs(d["neg"]*scale)
                #mm = max(abs(d["pos"]),abs(d["neg"]))
                #if m1>1.0 or m2>1.0:
                #    print "learned scale is %.3f but maximum is %.3f <%.3f>"%(scale,1.0/mm,mm);
                #print d,,d["neg"]*scale
                #if any(map(lambda x : x >= 1.0, [ scale*f for f in samples ])):
                #    nscale = cPyBASS.learn_scale(samples,1.0,1.0,initial=scale);
                    #print....
                #    scale = nscale
                #print scale
            else:
                raise ValueError("No samples")
        else:
            print("decode error for %s"%path)
        return scale,samples;

    def update_progress(self,idx):
        percent = 0;
        if idx < 0:
            percent = 100;
        else:
            percent = int(100*float(idx)/len(self.songList));

        self.parent.sync_set_value.emit(percent)

    def update_estimate(self,ms,length):
        # add another ms estimate to the clock
        tps = ms/float(length)
        est1 = tps*4*4*60
        self.estimates.append(est1);
        self.estimates = self.estimates[-20:]

    def display_estimate(self):
        if len(self.estimates)==0:
            return;
        est1 = sum(self.estimates)/len(self.estimates);
        est  = int(est1 * (len(self.songList)-self.idx) / 1000.0)

        etrs = "???"#DateTime.formatTimeDelta(est);
        elaps= "???"#DateTime.formatTimeDelta(time.time() - self.start_time);
        msg = "[%d/%d Err:%d] Estimate Time Remaining: %s Elapsed: %s"%(self.idx,len(self.songList),self.errors,etrs,elaps)
        self.parent.sync_set_text.emit(msg)

class DialogVolEqLearn(QDialog):
    """
        dialog manages learning an eq scale for songs;

    """

    sync_set_text = pyqtSignal(str)
    sync_set_value = pyqtSignal(float)
    sync_set_done = pyqtSignal()

    def __init__(self,parent=None):

        super(DialogVolEqLearn, self).__init__(parent)
        self.vbox = QVBoxLayout(self)
        self.vbox.setSpacing(3)
        self.setWindowTitle("Volume Equalizer Learn")
        self.pbar = ProgressBar(self)
        self.btn_start = QPushButton("Start",self)
        self.btn_stop = QPushButton("Stop",self)
        self.btn_stop.hide()

        self.btn_start.clicked.connect(self.learn)
        self.btn_stop.clicked.connect(self.stop)

        self.gbox_opt = QGroupBox("Select",self)
        self.gbox_vbox = QVBoxLayout(self.gbox_opt);
        self.rbtn_lib = QRadioButton("Lib")
        self.rbtn_new = QRadioButton("New")
        self.rbtn_new.setChecked(True)

        self.gbox_vbox.addWidget( self.rbtn_lib )
        self.gbox_vbox.addWidget( self.rbtn_new )


        self.vbox.addWidget(self.gbox_opt)
        self.vbox.addWidget(self.pbar)
        self.vbox.addWidget(self.btn_start)
        self.vbox.addWidget(self.btn_stop)

        self.thread = None;

        self.sync_set_text.connect(self.sync_setText)
        self.sync_set_value.connect(self.sync_setValue)
        self.sync_set_done.connect(self.sync_done)

        self.songList = []
        self.songListNew = []

        self.cbk_close = None

        self.setLibrary( Library.instance().search(None) )

        self.resize(500,60)

    def sync_setValue(self,value):
        self.pbar.setValue(value)

    def sync_setText(self,string):
        self.pbar.setText(string)

    def sync_done(self):
        self.thread_done()

    def setLibrary(self,songList):
        self.songList = songList;
        self.songListNew = list(filter( lambda s: s[Song.equalizer]==0, songList ));

        self.rbtn_lib.setText("Library (%d)"%len(self.songList))
        self.rbtn_new.setText("New Songs (%d)"%len(self.songListNew))

        if len(self.songListNew)==0:
            self.songListNew = random.sample(songList,500)
            self.rbtn_new.setText("Random Partition (%d)"%len(self.songListNew))

    def learn(self):

        if BassPlayer == None:
            print("DSP not initialized")
            return

        if self.thread == None:
            if self.rbtn_lib.isChecked():
                self.thread = LearnThread(self,self.songList)
            else:
                self.thread = LearnThread(self,self.songListNew)
            self.thread.start()
            self.btn_start.hide();
            self.btn_stop.show();
            self.gbox_opt.setEnabled(False)

    def stop(self):
        if self.thread != None:
            self.btn_stop.hide()
            self.thread.kill();
            self.thread.wait()
            self.thread = None
            self.btn_start.show();
            self.gbox_opt.setEnabled(True)
            # updates the gui / songListNew
            self.setLibrary(self.songList)

    def thread_done(self):
        print("thread done")
        self.btn_start.hide();
        self.btn_stop.hide();

    def done(self,nil):
        if self.cbk_close !=None:
            self.cbk_close();
        super(DialogVolEqLearn,self).done(nil)
    def setCloseFunc(self,cbk):
        self.cbk_close = cbk

def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)


    db_path = "./libimport.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )

    window = DialogVolEqLearn()
    window.show()


    sys.exit(app.exec_())
