
"""
Scaling Strategies:

    0. scale prior to displaying
            scaling is 50-95% of the load->scale-display time
    1. precache default scale when loading
            shifts the burden still sluggish on display.
            precache may not be what we want
        1.a. update the cache when a new scaled image is created
    2. set the image to be displayed, but use a thread to do the scaling
        and the final display

    going with option 2 puts the slowest part of displaying an image
    after the user input, which seems to visually decrease lag
    the user is not waiting for the event, and the ui does not hang

    it seems that scaling a QImage + conversion to QPixmap is faster
    than scaling a QPixmap

"""

import os,sys
import sip

import time
import threading

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.qtcommon.ResourceManager import ResourceManager

def scale_pixmap(map,w,h):
    img = map.scaled(w,h,Qt.KeepAspectRatio, \
                          Qt.SmoothTransformation)
    return img

def scale_image_to_map_i(img,w,h):

    #return img.scaled(w,h,Qt.KeepAspectRatio,Qt.FastTransformation)
    return QPixmap.fromImage(img.scaled(w,h,Qt.KeepAspectRatio, \
                                            Qt.SmoothTransformation))

def scale_image_to_map(img,w,h,mode):

    iw,ih = img.width() , img.height()

    if (mode == ImageDisplay.SC_WINDOW) or \
       (mode == ImageDisplay.SC_LARGE and  (iw > w or ih > h)):
        map = scale_image_to_map_i(img,w,h)
    elif mode == ImageDisplay.SC_WIDTH and ih > h:
        # .9 is a fudge factor, so that the image is scaled to
        # the width of the screen with some margin on the left and right
        h2 = int( (.9*w/iw)*ih )
        map = scale_image_to_map_i(img,w,h2)
    else:
        map = QPixmap.fromImage(img);
    return map

class Viewport(QScrollArea):
    """docstring for Viewport"""

    displayNext = pyqtSignal()
    displayPrev = pyqtSignal()
    videoScroll = pyqtSignal(int)
    scaleChanged = pyqtSignal(int)

    DISPLAY_SCROLLBAR_VERTICAL_STEP = 30
    DISPLAY_SCROLLBAR_HORIZONTAL_STEP = 30
    DISPLAY_SCROLLBAR_WIDTH_TIMEOUT_END = 200
    DISPLAY_SCROLLBAR_WIDTH_TIMEOUT_LOAD = 250

    def __init__(self,parent):
        super(Viewport, self).__init__(parent)

        self.screen = QLabel(self);
        self.screen.setSizePolicy(QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
        self.screen.setAlignment(Qt.AlignCenter)

        #self.viewport = QScrollArea()
        self.setWidget(self.screen)
        self.setWidgetResizable(True)
        #self.wheelEvent = self.wheelEvent
        self.setBackgroundColor( Qt.black )

        vbar = self.verticalScrollBar()
        vbar.setSingleStep(Viewport.DISPLAY_SCROLLBAR_VERTICAL_STEP)
        hbar = self.horizontalScrollBar()
        hbar.setSingleStep(Viewport.DISPLAY_SCROLLBAR_HORIZONTAL_STEP)

        self.scroll_enabled = True
        self.scroll_past_count = 0;
        self.scroll_endof = False # if true, on image load set scroll bar to max
        self.lk_scrollwheel = QMutex()

        self.scale = ImageDisplay.SC_LARGE

    def setBackgroundColor(self,qcolor):
        p = self.palette()
        p.setColor(self.backgroundRole(), qcolor)
        self.setPalette(p)

    def setMovie(self,mov):
        # read: gif
        self.screen.setMovie(mov)

    def setPixmap(self,map):
        self.screen.setPixmap(map)


    def FIXME_autoscroll(self):
        # this code needs to be called after the image is displayed
        # and after the scroll bar is updated, when in SC_WIDTH mode
        # trouble is, i can't find the best place for that
        # so for now i am using a timer
        if self.getScaleMode() == ImageDisplay.SC_WIDTH:
            vbar = self.verticalScrollBar()
            if self.scrollBarAtEnd():
                vbar.setValue(vbar.maximum())
            else:
                vbar.setValue(vbar.minimum())

    def scrollBarAtEnd(self):
        return self.scroll_endof

    def getScaleMode(self):
        return self.scale

    def setScale(self,sc):
        if sc!=self.scale:
            self.scaleChanged.emit(sc)
        self.scale = sc
        self.update()

    def setScrollEnabled(self,b=True):
        self.lk_scrollwheel.lock()
        self.scroll_enabled = b
        self.lk_scrollwheel.unlock()

    def getScrollEnabled(self):
        self.lk_scrollwheel.lock()
        b = self.scroll_enabled
        self.lk_scrollwheel.unlock()
        return b

    def wheelEvent_width(self,event):

        velocity = (event.angleDelta()/120)
        # d is 1 if scrolling down and -1 otherwise.
        # also not sure on OSX... ha
        d = 1 if velocity.y() < 0 else -1

        vbar = self.verticalScrollBar()

        if self.scroll_past_count==0 or \
           (self.scroll_past_count<0 and d>0) or \
           (self.scroll_past_count>0 and d<0):
            super(QScrollArea,self).wheelEvent(event)
            self.scroll_past_count = 0

        if vbar.value()==vbar.maximum():
            self.wheelEvent_width_main( d )
            event.accept()
        elif vbar.value()==vbar.minimum():
            self.wheelEvent_width_main( d )
            event.accept()
        #else:
        #    self.scroll_past_count = 0

    def wheelEvent_width_main(self,direction):
        """ when the scale is `Width` the scroll event has special meaning
        scroll the image up and down, automatically go to the next/prev image
        when scrolling down/up after the bar reaches the end of the range
        """
        # direction ==  1 : forward
        # direction == -1 : reverse
        end_timeout = Viewport.DISPLAY_SCROLLBAR_WIDTH_TIMEOUT_END
        load_timeout = Viewport.DISPLAY_SCROLLBAR_WIDTH_TIMEOUT_LOAD

        if self.scroll_past_count == 1*direction:
            self.setScrollEnabled(False)
            QTimer.singleShot(end_timeout,self.setScrollEnabled)

        if self.scroll_past_count == 2*direction:
            if direction > 0:
                self.scroll_endof = False
                self.displayNext.emit()
            else:
                self.scroll_endof = True
                self.displayPrev.emit()
            self.scroll_past_count=0
            self.setScrollEnabled(False)
            QTimer.singleShot(load_timeout,self.setScrollEnabled)
            QTimer.singleShot(30,self.FIXME_autoscroll)
        else:
            self.scroll_past_count += direction

    def wheelEvent(self,event):

        if not self.getScrollEnabled():
            return

        velocity = (event.angleDelta()/120)

        if self.scale == ImageDisplay.SC_WIDTH:
            self.wheelEvent_width(event)
        elif self.scale != ImageDisplay.SC_NONE:

            if velocity.y() < 0 :
                self.displayNext.emit()
            elif velocity.y() > 0 :
                self.displayPrev.emit()

            event.accept()
        else:
            super(QScrollArea,self).wheelEvent(event)

class ImageDisplay(QWidget):
    """implements a widget for displaying images
    """

    SC_NONE=0x01    # do not perform scaling
    SC_LARGE=0x02   # scale down only large images
    SC_WINDOW=0x04  # scale only everything to the window
    SC_WIDTH=0x05   # scale large images to window width

    # current API does not emit these signals when the appropriate
    # setters are called, as the setters are provided so that the UI
    # can update the values, if these values change outside of that
    # role, these should be emitted to update the UI
    #scaleChanged = pyqtSignal(int)
    speedChanged    = pyqtSignal(int)
    resourceChanged = pyqtSignal(object)
    imageChanged    = pyqtSignal(object)
    displayResource = pyqtSignal(str, object)

    def __init__(self,parent):
        super(ImageDisplay, self).__init__()

        self.img = None # primary image source
        self.map = None # a prescaled copy of img
        self.map_params = (0,0,0) # cached parameters that produced self.map
        self.mov = None
        self._buf = None
        self.paused = True
        self.speed = 100
        self.speed_max = 500
        self.speed_tick_snap = 25
        self.parent = parent

        self.viewport = Viewport(parent)

        self.thread = DisplayThread(self)
        self.thread.start()

        self.threadScale = ScaleImageThread(self)
        self.threadScale.start()

        self.displayResource.connect(self.load)

        #self.viewport.wheelEvent = self.wheelEvent
        self.viewport.displayNext.connect(self.next)
        self.viewport.displayPrev.connect(self.prev)

        self.vbox = QVBoxLayout(self)
        self.vbox.addWidget(self.viewport)
        self.vbox.setContentsMargins(0,0,0,0)
        self.vbox.setSpacing(0)

        self._init_default_resource()

        self.perf_start = 0
        self.perf_update = 0
        self.perf_scale_s = 0
        self.perf_scale_e = 0
        self.perf_end = 0

        self.source = None

    def close(self):
        self.thread.kill()
        self.thread.wait()

        self.threadScale.kill()
        self.threadScale.wait()

    def _init_default_resource(self):
        default_path = ':/img/icon.png'
        qf = QFile(default_path)
        qf.open(QIODevice.ReadOnly)
        self.default_resource_data = bytes(qf.readAll())
        self.default_resource = QImage.fromData(self.default_resource_data)
        qf.close()

    def setSource(self,src):
        self.source = src

    def getSource(self):
        # TODO: this should be a PUSH instead of a PULL
        return self.source

    #def loadResource(self,res):
    #    if res != None :
    #        self.resourceChanged.emit( res )
    #        if res.kind in (ResourceManager.IMAGE,ResourceManager.GIF):
    #            self.load(res.kind,res.file.read())

    def load(self, path, item):
        # called by the display thread

        if isinstance(item,QImage):
            self.img = item
            self.map = None
            self.map_params = (0,0,0)
            #self.map = QPixmap.fromImage(self.img)
            self._post_load_image()

        elif isinstance(item,tuple):
            self.img,self.map,self.map_params = item
            self._post_load_image()

        elif isinstance(item,QByteArray):

            # Qt will crash if the QByteArray is garbage collected.
            # QMovie needs both a QByteArray and QBuffer as input
            # QMovie starts a timer, and must be created by the main thread

            # ----------------------------
            # this prevents a crash from close buffer
            # it prevents _data from being garbage collected before close()
            if self._buf is not None:
                self._buf.close()
            self._data = item
            # ----------------------------
            self._buf = QBuffer(item)
            self._buf.open(QIODevice.ReadOnly)
            self.mov = QMovie(self._buf,item)

            self._post_load_movie()

        else:
            raise ValueError(item)

        self.viewport.update()
        self.update()

        #self.show_perf_stats()
        return

    def show_perf_stats(self):
        """
        print performance for load / scale / display

        current limitingg factor is scaling
        I now pre scale images when they are loaded which offsets
        a resonably amount of the burden

        """
        self.perf_end = time.perf_counter()
        ldtime = self.perf_update-self.perf_start
        sctime = self.perf_scale_e - self.perf_scale_s;
        dptime = self.perf_end - self.perf_scale_e
        total  = self.perf_end-self.perf_start
        ldpercent = 0
        scpercent = 0
        dppercent = 0
        if total > 0:
            ldpercent = ldtime/total*100
            scpercent = sctime/total*100
            dppercent = dptime/total*100
        s = "  load:%.4fs %.2f%%"%(ldtime,ldpercent) + \
            "  scale:%.4fs %.2f%%"%(sctime,scpercent) + \
            "  post:%.4fs %.2f%%"%(dptime,dppercent)
        print("perf time | total:%.4f%s"%(total, s))

    def _post_load_movie(self):

        self.mov.scaledSize()
        self.mov.setCacheMode(QMovie.CacheAll)
        self.mov.setSpeed( self.speed )

        self.img = None
        self.map = None

        self.paused = True
        self.viewport.setMovie(self.mov)

    def _post_load_image(self):

        # clear movie data
        self.mov = None
        if self.getScaleMode() == ImageDisplay.SC_WIDTH:
            self.scroll_past_count = 0;
            vbar = self.viewport.verticalScrollBar()
            vbar.setValue(vbar.minimum())

    def update(self):

        if self.img:

            # option 1, scale in main thread
            self.perf_scale_s = time.perf_counter()
            #map = self.__get_scaled_map()
            #self.viewport.setPixmap(map)
            self.perf_scale_e = time.perf_counter()

            # option 2, scale in secondary thread
            self.threadScale.setImage( self.img )

            self.imageChanged.emit( self.img )

        elif self.mov:
            if self.paused:
                self.paused = False
                self.mov.start()
                #self.mov_ar = self.mov.currentImage().size()
            #w,h = self.__get_scale_size()
            #f = int( h/self.mov_ar.height()/.05 ) * .05
            #print(f,h/self.mov_ar.height())
            #w = self.mov_ar.width()*h/self.mov_ar.height()
            #w = self.mov_ar.width()*f
            #h = self.mov_ar.height()*f
            #self.mov.setScaledSize(QSize(w,h))
            self.mov.setSpeed( self.speed )
            self.imageChanged.emit( self.mov )

    def getScaleMode(self):

        return self.viewport.getScaleMode()

    def getScaleSize(self):
        w = self.viewport.width()
        h = self.viewport.height()

        # remove the contents margins so that NO scroll bar will show
        # when scaled.
        l,t,r,b = self.viewport.getContentsMargins()
        w -= l + r
        h -= t + b

        return w,h

    def __get_scaled_map(self):


        if not self.img:
            raise ValueError("Image Not Set")

        w,h = self.getScaleSize()
        mode = self.getScaleMode()
        if (w,h,mode) != self.map_params:
            self.map = scale_image_to_map(self.img,w,h,self.getScaleMode())


        return self.map

    def setScale(self,sc):
        self.viewport.setScale(sc)
        self.update()

    def getMaxSpeed(self):

        return self.speed_max//self.speed_tick_snap

    def getSpeed(self):

        return self.speed//self.speed_tick_snap

    def setSpeed(self,spd):
        self.speed = spd * self.speed_tick_snap
        self.update()

    def rotate(self,angle):
        if self.img is not None:
            tr = QTransform()
            tr.rotate(angle)
            self.img = self.img.transformed(tr);
            #self.map = QPixmap.fromImage(self.img)
            self._post_load_image()
            self.update()

    def current(self):
        self.perf_start = time.perf_counter()
        self.thread.current()

    def next(self):
        self.perf_start = time.perf_counter()
        self.thread.next()

    def prev(self):
        self.perf_start = time.perf_counter()
        self.thread.prev()

    @staticmethod
    def supportedScaleFactors():
        return [ ImageDisplay.SC_NONE,
                 ImageDisplay.SC_LARGE,
                 ImageDisplay.SC_WINDOW,
                 ImageDisplay.SC_WIDTH]

    @staticmethod
    def scaleFactorToString(sc):
        if sc==ImageDisplay.SC_NONE:
            return "None"
        elif sc==ImageDisplay.SC_LARGE:
            return "Large"
        elif sc==ImageDisplay.SC_WINDOW:
            return "Window"
        elif sc==ImageDisplay.SC_WIDTH:
            return "Window Width"
        return "Unknown"

class DisplayThread(QThread):
    """docstring for DisplayThread

        when ready to display, emits parent.displayResource
    """

    def __init__(self,parent):
        super(DisplayThread, self).__init__()

        self.parent = parent
        self.alive = True

        self.resource_path = None # resource to load
        self.resource_next = None # resource to load in background

        # two state system:
        #   accepting : wait for signal for a resource to load
        #   else: reject new signals while loading a resource
        self.lk_accept = threading.Lock()
        self.cv_accept = threading.Condition(self.lk_accept)
        self.accepting = True
        self.resource_path = None

        # cache prevents accessing disk for recently used items.
        self.lk_cache = threading.Lock()
        self.item_cache = {}
        self.item_paths = []
        self.cache_size = 32;

    def current(self):
        with self.lk_accept:
            if self.accepting:
                self.accepting = False
                self.resource_path = self.parent.getSource().getResource()
                self.resource_next = None
                self.cv_accept.notify()
                return

    def next(self):
        with self.lk_accept:
            if self.accepting:
                self.accepting = False
                self.resource_path = self.parent.getSource().next()
                self.resource_next = self.parent.getSource().peakResource( 1)
                self.cv_accept.notify()
                return

    def prev(self):
        with self.lk_accept:
            if self.accepting:
                self.accepting = False
                self.resource_path = self.parent.getSource().prev()
                self.resource_next = self.parent.getSource().peakResource(-1)
                self.cv_accept.notify()
                return

    def run(self):

        """
        todo
            1. peek and auto load the next image when done loading current
               set accepting to true before loading next image
            2. depending on how that works, use a timer, if a fraction of
               a second passes without a new request load the next image.
               or load the next+1 image, etc.
            3. cache size should be 2*N+C where N is how far we try to
               predict and load images

            a timer that fires after ~.05 seconds and loads the next image
            into the cache, as long as set accepting is True.
        """
        while self.alive:
            with self.lk_accept:
                self.accepting = True
                self.cv_accept.wait()
                if not self.alive:
                    return;
            self.update()
            self.preload()

    def update(self):
        item = None
        if self.resource_path is not None:
            item = self.cache_get( self.resource_path )
            if item is None:
                item = self.load_resource( self.resource_path )
                # load resource here
                self.cache_insert(self.resource_path,item)

        if item is None:
            item = self.parent.default_resource

        self.parent.displayResource.emit( self.resource_path, item )

        self.parent.perf_update = time.perf_counter()

    def preload(self):
        if self.resource_next is not None:
            item = self.cache_get( self.resource_next )
            if item is None:
                item = self.load_resource( self.resource_next )
                self.cache_insert( self.resource_next, item )
                self.resource_next = None

    def load_resource(self,path):
        """return a in-memory representation of path"""

        ext = os.path.splitext(path)[1]
        kind =  ResourceManager.instance().getExtType( ext )
        # todo read the first few bytes to check the kind
        source = self.parent.getSource()

        # this actually speeds up  DirectorySource>EBFSSource>ZipSource
        # cases. I believe because there are more sequence points for
        # the threading system to preempt this thread.
        data = b""
        with source.open(path,"rb") as rb:
            buf = rb.read(32*1024)
            while buf:
                data += buf
                buf = rb.read(32*1024)

        if kind == ResourceManager.GIF:
            return QByteArray( data )
        elif kind == ResourceManager.IMAGE:
            img = QImage.fromData( data )

            # note:
            # return (img, None, (0,0,0))
            # to disable pre-scaling
            return (img, None, (0,0,0))

            # prescale the image
            #w,h = self.parent.getScaleSize()
            #mode = self.parent.getScaleMode()
            #map = scale_image_to_map(img,w,h,mode)
            #params = (w,h,mode)
            #if img.width()*img.height() > 1920*1080:
            #    img = scale_image(img,1920,1080)
            #map = QPixmap.fromImage(img)
            #return (img,map,params)
        else:
            return None

    def cache_insert(self,path,item):
        with self.lk_cache:
            if path in self.item_cache:
                return
            # add item to cache
            self.item_paths.append(path)
            self.item_cache[path] = item
            # remove oldest from cache
            if len(self.item_paths) > self.cache_size:
                path = self.item_paths.pop(0)
                del self.item_cache[path]

    def cache_get(self,path):

        with self.lk_cache:
            if path in self.item_cache:
                return self.item_cache[path]
        return None;

    def kill(self):
        with self.lk_accept:
            self.alive = False
            self.cv_accept.notify()

class ScaleImageThread(QThread):
    """ scales an image then displays it
    """

    displayPixmap = pyqtSignal(QPixmap)

    def __init__(self,parent):
        super(ScaleImageThread, self).__init__()

        self.parent = parent
        self.alive = True

        self.lk_scale = QMutex()
        self.cv_scale = QWaitCondition()

        self.img_src = None
        self.img_scale_src = None

        self.displayPixmap.connect(self.parent.viewport.setPixmap)

    def setImage(self,img):

        with QMutexLocker(self.lk_scale):
            self.img_src = img
            self.cv_scale.wakeOne()

    def run(self):

        map = None

        while self.alive:
            img = None

            with QMutexLocker(self.lk_scale):

                # check for a successful scale and display
                if map and self.img_src is self.img_scale_src:
                    self.displayPixmap.emit(map)
                    map = None

                self.cv_scale.wait(self.lk_scale)
                img = self.img_src
                self.img_scale_src = self.img_src

            # scale the image outside the lock
            if img:
                w,h = self.parent.getScaleSize()
                mode = self.parent.getScaleMode()
                map = scale_image_to_map(img,w,h,mode)

    def kill(self):
        with QMutexLocker(self.lk_scale):
            self.alive = False
            self.img_src = None
            self.cv_scale.wakeOne()




