
from ..DSP.visualizer import Visualizer
from ...core.sound.device import MediaState

class BassVisualizer(Visualizer):

    def __init__(self, controller, parent=None):
        super(BassVisualizer,self).__init__(parent);
        self.controller = controller

    def getData(self):
        data = self.controller.device.getDspData("zbvis");
        if data == None:
            data = [ i/10.0 for i in range(11) ]
        return data

    def isActive(self):
        return self.controller.device.state() == MediaState.play

    def mouseReleaseEvent (self,event):
        if self.isRunning():
            self.stop();
        else:
            self.start();