
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

#from kivy.graphics.scissor_instructions import ScissorPush,ScissorPop
from kivy.graphics.stencil_instructions import StencilPush,StencilUse, \
    StencilUnUse,StencilPop

# https://kivy.org/docs/api-kivy.graphics.stencil_instructions.html

class TestWidget(Widget):

    def __init__(self, **kwargs):
        super(TestWidget, self).__init__(**kwargs)


        with self.canvas.before:
            StencilPush()
            self.rect_mask = Rectangle() # see self.resize()
            StencilUse()

        w,h = self.size
        with self.canvas:
            Color(.5,0,0,.5)
            self.rect_main = Rectangle(pos=(self.x,self.y),size=(w,h))

        with self.canvas.after:
            StencilUnUse()
            StencilPop()


        self.bind(size=self.resize)

    def resize(self,*args):

        x,y = self.pos
        x += self.width/4

        self.rect_mask.pos = (x,y)
        self.rect_mask.size = (self.width/2,self.height)

        self.rect_main.pos = self.pos
        self.rect_main.size = self.size


class TestApp(App):

    def build(self):
        return TestWidget()

def main():

    TestApp().run()

if __name__ == '__main__':
    main()