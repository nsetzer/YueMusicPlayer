#! python2.7 ../../../test/test_widget.py tri

"""
a TriState CheckBox

User can toggle the checkbox between one of two states.
A third state can be set programmatically to show a partial check.

TODO:
    better ui, scale check line width relative to size

    partial inner box is not centered correctly

"""
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, NumericProperty, BooleanProperty
from kivy.graphics import Color, Ellipse, Line, Rectangle

from enum import Enum

class TriState(Enum):
    unchecked = 0
    partial = 1
    checked = 2

class TriStateCheckBox(Widget):
    state = ObjectProperty(TriState.unchecked)

    def __init__(self, **kwargs):
        super(TriStateCheckBox, self).__init__(**kwargs)
        self.bind(pos=self.update_canvas)
        self.bind(size=self.update_canvas)
        self.bind(state=self.update_canvas)

        # on user allows for distinguishing between
        # the STATE changing, and the USER changing the state.
        self.register_event_type('on_user')

    def update_canvas(self,*args):
        self.canvas.clear()
        with self.canvas:

            Color(.5,.5,.5,1.0)
            size = min(self.height,self.width)
            pad = size//6
            size -= 2*pad # outer rectangle size
            size2 = int(size*.8) # inner rectangle size

            x1 = self.x + pad # pos of outer rect
            y1 = self.y + pad

            x2 = self.x + pad + int(size*.1) # pos of inner rect
            y2 = self.y + pad + int(size*.1)

            Rectangle(pos=(x1,y1),size=(size,size))

            if self.state == TriState.partial:
                Color(.75,.75,.75,1.0)
                Rectangle(pos=(x2,y2),size=(size2,size2))

            elif self.state == TriState.checked:
                p1 = x1 + size//3
                p2 = y1 + size//3
                p3 = x1 + size//2
                p4 = y2
                p5 = x1 + size
                p6 = y1 + size
                Color(0,.75,0,1.0)
                Line(points=(p1,p2,p3,p4,p5,p6),width = 2)

    def on_user(self,*args):
        pass

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.state == TriState.unchecked:
                self.state = TriState.checked
            else:
                self.state = TriState.unchecked
            self.dispatch('on_user', None)
            self.update_canvas()

            return True
        return super(TriStateCheckBox, self).on_touch_down(touch)


class TriStateExpander(Widget):
    """
    expandable: true/False
        draw a background indicating 'expanded state'
    if true: expanded: true/flase
        determines background color
    check state:
        unchecked/partial/checked
    """
    expandable = BooleanProperty(True)
    expanded = BooleanProperty(False)
    state = ObjectProperty(TriState.unchecked)

    def __init__(self, **kwargs):
        super(TriStateExpander, self).__init__(**kwargs)
        self.bind(pos=self.update_canvas)
        self.bind(size=self.update_canvas)
        self.bind(state=self.update_canvas)

        self.register_event_type('on_user')

    def update_canvas(self,*args):
        self.canvas.clear()
        with self.canvas:

            size = min(self.height,self.width)
            pad = 0
            size -= 2*pad # outer rectangle size

            if self.expandable:
                if self.expanded:
                    Color(.75,.75,.75,1.0)
                else:
                    Color(.33,.33,.33,1.0)

                Rectangle(pos=(self.x,self.y),
                          size=(self.width,self.height))

            if self.state == TriState.checked:
                Color(.75,.10,.10,1.0)
            elif self.state == TriState.partial:
                Color(.10,.75,.10,1.0)
            else:
                Color(.10,.10,.75,1.0)

            m = self.y + self.height//2 - self.width//2
            Ellipse(pos=(self.x,m),
                      size=(self.width,self.width))

    def on_user(self,*args):
        pass

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.expanded = not self.expanded
            self.dispatch('on_user', None)
            self.update_canvas()

            return True
        return super(TriStateExpander, self).on_touch_down(touch)
