#! python2.7 ../../test/test_widget.py expand
"""
Expander Button

a 2-state button which displays a + sign when contents can be explanded
and a - sign when contents can be minimized.

the 'expanded' value is True when the contents are expanded,
the 'on_user' signal is emitted whenever the user changes the current state.
This allows for a distinction between the user and the program changing the
state of the button

"""
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty
from kivy.graphics import Color, Rectangle, Line
import random

class Expander(Widget):
    expanded = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(Expander, self).__init__(**kwargs)
        self.bind(pos=self.update_canvas)
        self.bind(size=self.update_canvas)
        self.bind(expanded=self.update_canvas)

        # on user allows for distinguishing between
        # the STATE changing, and the USER changing the state.
        self.register_event_type('on_user')

    def update_canvas(self,*args):
        self.canvas.clear()
        with self.canvas:
            """    _
                __| |__
                |_   _|
                  |_|

                four critical points on each axis, numbered
                1-4 from left to right
            """

            Color(.5,.5,.5,1.0)
            tmp = min(self.height,self.width)
            pad = tmp//6
            wid = (tmp-2*pad)//3

            vertices = []
            x2 = self.x+self.width//2-wid//2
            x1 = x2 - wid
            x3 = x2 + wid
            x4 = x3 + wid

            y2 = self.y+self.height//2-wid//2
            y1 = y2 - wid
            y3 = y2 + wid
            y4 = y3 + wid

            if not self.expanded:
                Rectangle(pos=(x2,y1),size=(wid,3*wid))
            Rectangle(pos=(x1,y2),size=(3*wid,wid))

    def on_user(self,*args):
        pass

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.expanded = not self.expanded
            self.dispatch('on_user', None)
            self.update_canvas()

            return True
        return super(Expander, self).on_touch_down(touch)


