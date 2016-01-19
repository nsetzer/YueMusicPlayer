#! python2.7 ../../test/test_widget.py time
"""

"""
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import NumericProperty,BooleanProperty
from kivy.graphics import Color, Rectangle, Line
import random

def fmttime(s):
    m,s = divmod(int(s),60)
    h,m = divmod(m,60)
    return "%02d:%02d:%02d"%(h,m,s)


class TimeBar(Widget):
    value = NumericProperty(0)
    duration = NumericProperty(100)

    def __init__(self, **kwargs):
        super(TimeBar, self).__init__(**kwargs)

        self.lbl_value = Label(text='00:00:00',halign='left',valign='top')
        self.lbl_duration = Label(text='00:00:00',halign='right',valign='top')

        self.add_widget(self.lbl_value,canvas=self.canvas)
        self.add_widget(self.lbl_duration,canvas=self.canvas)

        h = self.height/5
        y = self.height//2 #- h//2
        with self.canvas.before:

            Color(.5,.5,.5,.5)
            self.rect_main = Rectangle(pos=(self.x,self.y+y),size=(self.width,h))
            Color(1,0,0,1)
            w = int(self.width * self.value / self.duration)
            self.rect_value = Rectangle(pos=(self.x,self.y+y),size=(w,h))

        self.bind(pos=self.update_canvas)
        self.bind(size=self.update_canvas)

        self.bind(value=self.update_value)
        self.bind(duration=self.update_duration)

        self.register_event_type('on_seek')

        self.margin = .05

    def update_canvas(self,*args):

        h = self.height/5
        y = self.height//2 #- h//2
        x = int(self.width*self.margin)
        w = self.width - 2*x

        self.lbl_value.x=self.x + x
        self.lbl_value.y=self.y
        self.lbl_value.width= self.width/2 - x
        self.lbl_value.height=y
        self.lbl_value.text_size = self.lbl_value.size

        self.lbl_duration.x=self.lbl_value.x + self.lbl_value.width
        self.lbl_duration.y=self.y
        self.lbl_duration.width=self.lbl_value.width
        self.lbl_duration.height=y
        self.lbl_duration.text_size = self.lbl_duration.size

        self.rect_main.size = w,h
        self.rect_main.pos = self.x+x,self.y+y

        w = int(w * self.value / self.duration)
        self.rect_value.size = w,h
        self.rect_value.pos = self.x+x,self.y+y

    def update_value(self,*args):
        self.lbl_value.text = fmttime(self.value)
        self.update_canvas()

    def update_duration(self,*args):
        self.lbl_duration.text = fmttime(self.duration)

    def on_touch_up(self, touch):
        if self.collide_point( *touch.pos ):

            x,y = self.to_widget(*touch.pos)
            w = self.width
            m = self.margin
            v =  (x - w*m) / (w*(1.0-2*m))
            v = min(1.0,max(0.0,v))
            self.dispatch('on_seek',v*self.duration)

    def on_seek(self,position):
        self.value = position


