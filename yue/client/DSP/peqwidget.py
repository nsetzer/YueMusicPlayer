
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import math,cmath

import yue.client.DSP.zbdesign as zbdesign
import yue.client.DSP.linalg as linalg
# proof
# in the time domain:
# x*h1 + x*h2 + x*h3 = y
# x*(h1 + h2 + h3)
# in the freq domain
# X(H1 + H2 + H2)

binary_ranges = [
        [   32,   64],
        [   64,  128],
        [  128,  256],
        [  256,  512],
        [  512, 1024],
        [ 1024, 2048],
        [ 2048, 4096],

        [ 4096, 6144],
        [ 6144, 8192],
        [ 9216,13312],
        [14336,18432],
    ]
# octave ranges splits the 8th octave into 2 ranges
# and adds 2 additional at the end.
octave_ranges = [
        [33,   62],
        [65,  124],
        [131,  247],
        [262,  494],
        [523,  988],
        [1047, 1976],
        [2093, 3951],
        [4186, 6044],
        [6044, 7902],
        [9216,13312],
        [14336,18432],
    ]

def frange(s,e,step):
    # range doesnt take floats, this is all i need.
    i = s;
    while i < e:
        yield i
        i += step;

"""
    convert frequency to a bin index or the reverse of.
    size was chosen to divide evenly with 8
    i evenly plot the range from 2^5 to 2^13, and 13-5 = 8
"""
def mag(b,a,fc,fs=16000):
    # return the magnitude of coefficients b,a at frequency fc in db.
    # TODO it would be interesting to find a way that
    # i could write this in C. only thing stoping me is
    # I need to know the runtime on cost of exp
    z = cmath.exp(-complex(0,1)*2.0*math.pi*fc/fs)
    c=1.0;
    n=d=0.0;
    for i,j in zip(b,a):
        n += i*c;
        d += j*c;
        c = c*z;
    if d == 0.0: return 0.0;
    return 20.0*math.log( abs(n/d), 10 )

def magz(b,a,z):
    # return the magnitude of coefficients b,a at frequency fc in db.
    # TODO it would be interesting to find a way that
    # i could write this in C. only thing stoping me is
    # I need to know the runtime on cost of exp
    c=1.0;
    n=d=0.0;
    for i,j in zip(b,a):
        n += i*c;
        d += j*c;
        c = c*z;
    if d == 0.0: return 0.0;
    return 20.0*math.log( abs(n/d), 10 )

class SystemSettings(object):

    def __init__(self,max_gain,filter_ranges):
        self.bins = []
        self.gdb_list = []
        self.max_gdb = max_gain
        self.flogfactor=2.0
        self.fmin_offset=5#math.log(32,self.flogfactor)
        self.fmax_offset=math.log(22050.0,self.flogfactor)
        self.frange = float(self.fmax_offset-self.fmin_offset);  # or, set =  fmax_offset- self.fmin_offset
        self.fbincount=256; # controls the resolution of the graph

        self.fsample = 44100.0
        self.parameters = self.system_parameters(filter_ranges);
        self.fc_list,self.bw_list = self.parameters

        _fmax = self.flogfactor**(self.fmin_offset+self.frange);
        _fmin = self.flogfactor**(self.fmin_offset);
        self.flut = [ self.i2f(i) for i in range(self.fbincount) ]

        self.zlut = [ cmath.exp(-complex(0,1)*2.0*math.pi*f/self.fsample) for f in self.flut ]


    def f2i(self,f):
        return int(self.fbincount/self.frange*(math.log(f,self.flogfactor)-self.fmin_offset))
    def i2f(self,i):
        return self.flogfactor**( self.fmin_offset + (i)*self.frange/self.fbincount)

    def get_linear_coeff(self,fs,fc,bw,fc_list,gain=1.0):
        # scaling by 3.0 then dividing by 3.0 gives
        # a better output than using 1.0, but it's not significant
        # when the range is -6 to 6, the average is ~3 *waves hands* over logic
        gain = int(gain)
        gain = 1 if gain == 0 else gain
        p = zbdesign.zbpeak_param(fs,fc,bw,gain)
        return  [ mag(p.b_num,p.a_den,f,fs)/gain for f in fc_list ]

    def solve_linear_system(self,fs,fc_list,bw_list,gdb_list,max_gdb=6):
        # return the gain coefficients that will better represent the
        # system that the user input
        # build a row matrix with coeffcients for a representative
        F = [ self.get_linear_coeff(fs,f,bw,fc_list,gain) for f,bw,gain in zip(fc_list,bw_list,gdb_list) ]
        #print gdb_list
        G0 = linalg.solve(F,gdb_list)

        G0 = [ min(max_gdb,max(-max_gdb,g)) for g in G0 ]
        #print G0
        return G0

    def system_parameters(self,ranges):
        """
        returns a pair of center frequencies and bandwidth
        each roughly covering a musical octave.
        """
        # roughly matches the octaves
        fc_list = []
        bw_list = []
        for s,e in ranges:
            w = e-s;
            fa = s + (1.0/2)*w
            fc_list.append(fa)
            bw_list += [w,]

        return fc_list,bw_list

    def solve(self,gdb_list):
        """
            return a set of bins that can be plotted.
        """
        fc_list,bw_list = self.parameters

        g0_list = self.solve_linear_system(self.fsample,fc_list,bw_list,gdb_list,self.max_gdb)

        #print g0_list
        bins = [0]*self.fbincount

        for fc,bw,gdb in zip(fc_list,bw_list,g0_list):
        #for fc,bw,gdb in ( (fc_list[3],bw_list[3],g0_list[3]), ):

            # 3/ag cuts the bw by .5 at a |gdb|=6, .25 at |gdb|=12, and .125 at |gdb|=24.
            # approximatley, the zbpeak filter
            #ag = abs(gdb);
            #bw = bw if ag < 3 else bw*(6.0/ag);
            for i in range(self.fbincount):
                p = zbdesign.zbpeak_param(self.fsample,fc,bw,gdb)
                # this regression provides a value f
                # distributed evenly on a logarithmic scale
                # across all of the octaves
                bins[i] += magz(p.b_num,p.a_den,self.zlut[i])
        self.bins = bins;
        self.gdb_list = g0_list;

class WidgetOctaveEqualizer(QWidget):
    """ Widget that allows choosing gain values.

        This widget provides a set of sliders for picking gain
        for a set of digital filters.

        This is a work in progress widget, there is a loose definition
        of a settings object which maintains all working knowledge of the
        filter system, along with the current gain coefficients
        and a bin list for graphing. This allows the widget
        to only worrry about plotting the bin list, it needs
        a lot more work to be properly generalized.
    """
    gain_updated = pyqtSignal(list)

    def __init__(self,parent=None,ranges=None):
        """
            ranges : as list of 2-tupples.
                for each entry, a slider wil be posittioned at the center
                of the range, controlling a zb-filter of bandwidth equal
                to the range specified
        """
        super(WidgetOctaveEqualizer, self).__init__(parent)

        self.max_value = 10 # scale value to this
        self.max_gdb = 10

        if ranges == None:
            ranges = octave_ranges

        self.settings = SystemSettings(self.max_gdb,ranges);
        self.gain = [0,]*len(self.settings.fc_list)
        self.settings.solve(self.gain)
        # the ctrl_index list is built from the ranges list in the settings.
        # it controls where to draw the sliders in the widget
        self.ctrl_index = [ self.settings.f2i(f) for f in self.settings.fc_list]

        self.color_log_line  = self.palette().mid()#QColor(44,44,44);
        self.color_bg_line   = self.palette().mid()#QColor(64,64,88);
        self.color_zero_line = self.palette().mid()#QColor(64,64,88);
        self.color_gain_line = self.palette().mid()#QColor(12,192,64);

        self.borderl=0;
        self.borderr=0;
        self.bordert=0;
        self.borderb=32;

        self.slider_width = 5;
        self.slider_radius = 5;

        self.log_scale = list(range(10,100,10)) + \
                         list(range(100,1100,100)) + \
                         list(range(2000,10000,1000)) + [20000,]

        self.setColors()

    def setColors(self):
        app_palette =QApplication.instance().palette()

        bg = app_palette.window().color()

        bgr,bgg,bgb = bg.red(),bg.green(),bg.blue();
        factor = .50
        r = int( min(255,bgr*(1.0+factor)) if bgr < 127 else bgr*(1.0-factor) )
        g = int( min(255,bgg*(1.0+factor)) if bgg < 127 else bgg*(1.0-factor) )
        b = int( min(255,bgb*(1.0+factor)) if bgb < 127 else bgb*(1.0-factor) )
        self.color_bg_line = QColor(r,g,b);

        factor = .15
        r = int( min(255,bgr*(1.0+factor)) if bgr < 127 else bgr*(1.0-factor) )
        g = int( min(255,bgg*(1.0+factor)) if bgg < 127 else bgg*(1.0-factor) )
        b = int( min(255,bgb*(1.0+factor)) if bgb < 127 else bgb*(1.0-factor) )
        self.color_log_line = QColor(r,g,b);

        factor = .75
        r = int( min(255,bgr*(1.0+factor)) if bgr < 127 else bgr*(1.0-factor) )
        g = int( min(255,bgg*(1.0+factor)) if bgg < 127 else bgg*(1.0-factor) )
        b = int( min(255,bgb*(1.0+factor)) if bgb < 127 else bgb*(1.0-factor) )
        self.color_zero_line = QColor(r,g,b);

        self.color_gain_line = app_palette.text().color()

    def get_yscale(self):
        return (.5*(self.height()-self.bordert-self.borderb)*1.0)/self.max_value

    def paintEvent(self, event= None):
        w = self.width()
        h = self.height()
        m = h/2
        p = QPainter(self)
        size = float(len(self.settings.bins))

        p.translate(QPointF(self.borderl,self.bordert))
        self.draw_main(p,w-self.borderl-self.borderr,h-self.bordert-self.borderb,size);

        p.translate(QPointF(-self.borderl,-self.bordert))


        # 260 is a magic number where the text stops overlapping
        # (self.width() - self.borderl - self.borderr) > 260:
        self.draw_text(p,w,h,size)

    def draw_main(self,p,w,h,size):
        m = h/2
        yscale = self.get_yscale();

        ####################################################################
        # draw the log scale in the background
        p.setPen(self.color_log_line)
        for f in self.log_scale:
            x = self.settings.f2i(f)*w/size
            if x > 0:
                p.drawLine(x,0,x,h)

        ####################################################################
        # draw the gain axis: lines are 3db apart
        p.setPen(self.color_bg_line)
        for y in range(5,int(math.ceil(self.max_gdb/5.0)*5+1),5):
            p.drawLine(0,m-y*yscale,w,m-y*yscale)
            p.drawLine(0,m+y*yscale,w,m+y*yscale)

        ####################################################################
        # draw slider guidelines for each filter
        step_size = 1
        for i in self.ctrl_index:
            x = i*w/size
            p.drawRoundedRect(x-self.slider_width,
                              m-self.max_gdb*yscale+1,
                              self.slider_width*2,
                              (2*self.max_gdb*yscale-2),
                              self.slider_radius, self.slider_radius)
            k=-self.max_gdb + step_size;
            while k < self.max_gdb:
                p.drawLine(x-self.slider_width,m-k*yscale,x+self.slider_width,m-k*yscale)
                k += step_size

        ####################################################################
        # draw the zero line
        p.setPen(self.color_zero_line)
        p.drawLine(0,m,w,m)
        ####################################################################
        # paint the graph, starting with the second point
        # draw a line from that point to the previous point
        # scale all of the bins across the width of the object
        # this will produce a continuous line
        pen = QPen(self.color_gain_line)
        pen.setWidth(2)
        p.setPen(pen)
        i=1;
        p.setRenderHint(QPainter.Antialiasing)
        while i < size:
            a = (i-1)*w/size # scales bin index across x axis of widget
            b = yscale*self.settings.bins[i-1] #bins hold gain values
            c = (i)*w/size
            d = yscale*self.settings.bins[i]
            p.drawLine(a,m-b,c,m-d)
            i += 1

        ####################################################################
        # draw the handles for the current user selection
        # not that the line may not pass through the handles.
        pen = QPen(QColor(0,0,0))
        pen.setWidth(2)
        p.setPen(pen)

        grad =  QLinearGradient()
        grad.setSpread(QGradient.ReflectSpread ,)
        grad.setStops(
                    [(0.0,QColor(72,72,72)),
                     (0.5,QColor(192,192,192)),
                     (1.0,QColor(72,72,72))]
                     );
        brush = QBrush(grad)

        p.setBrush(brush)
        for i,j in enumerate(self.ctrl_index):
            a=(j)*w/size-6
            b=m-yscale*self.gain[i]-4
            p.drawRoundedRect(a,b,12,8,3,3)


        # draw text if w > 12*4*8, wid per char, num char, num words
        return

    def draw_text(self,p,w,h,size):
        font = p.font()

        font.setPointSize(7)
        p.setFont(font)
        FM = QFontMetrics(p.font())
        text_height = FM.height();
        p.setPen(QApplication.instance().palette().text().color())
        j = 0;
        for i,fc in zip(self.ctrl_index,self.settings.fc_list):
            x = i*(w-self.borderl-self.borderr)/size
            text = self.freqfmt(fc)
            text_width = FM.width(text);
            p.drawText(
                        x-(text_width/2.0)+self.borderl,
                        h - text_height*(j%2) - text_height/2,
                        text);
            j+=1;
    def get_ctrl_from_x(self,x):
        t = len(self.settings.bins)*float(x-self.borderl)/(self.width()-self.borderl-self.borderr)

        # get the index of which grip was selected
        # x = i*width/size
        i=-1;
        for ci in self.ctrl_index:
            if ci-5 < t < ci+5:
                i = self.ctrl_index.index(ci)
        return i;
    def get_gain_from_y(self,y):
        h = self.height() - self.bordert - self.borderb
        m = h/2 + self.bordert
        s = self.get_yscale();
        g=(m-y)/s;

        g = .5*(round((g)/.5)) # step size
        g = min(self.max_gdb,max(-self.max_gdb,g))
        return g
    def mouseReleaseEvent(self,event=None):
        x = event.x()
        y = event.y()
        i = self.get_ctrl_from_x(x)
        g = self.get_gain_from_y(y);

        if i != -1:
            #print i,g
            self.gain[i] = g
            self.settings.solve(self.gain)
            self.gain_updated.emit(self.settings.gdb_list)
            self.update()
    def wheelEvent(self,event):
        x = event.x()
        velocity = ((event.angleDelta()/120.0))
        i = self.get_ctrl_from_x(x)

        if i >= 0:
            g = self.gain[i]
            g += velocity.y()/5.0
            g = min(self.max_gdb,max(-self.max_gdb,g))
            self.gain[i] = g
            self.settings.solve(self.gain)
            self.gain_updated.emit(self.settings.gdb_list)
            self.update()
    def freqfmt(self,f):
        """ format a number as a string """
        if f < 1000:
            return "%d"%f
        else:
            return "%.1fK"%float(f/1000.0)
    def getGain(self):
        """ return the current gain coefficients """
        return self.settings.gdb_list
if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)

    window = WidgetOctaveEqualizer()
    window.show()
    sys.exit(app.exec_())