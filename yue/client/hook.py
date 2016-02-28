

import os,sys

if os.name == 'nt':
    # pyHook-1.5.1
    try:
        import pyHook
    except ImportError:
        pyHook = None

class KeyHook(object):

    def __init__(self, controller,enabled=True):
        super(KeyHook,self).__init__();

        self.controller = controller

        # todo: need a way to set these
        self.k_LAUNCHMEDIA=181
        self.k_NEXT=176
        self.k_PLAYPAUSE=179
        self.k_PREV=178
        self.k_STOP=177

        if os.name == 'nt' and pyHook is not None:
            self.hm = pyHook.HookManager();
            self.hm.KeyDown = self.keyPressEvent
            if enabled:
                self.hm.HookKeyboard()
            self.enabled = enabled
            sys.stdout.write("Keyboard Hook enabled (enabled=%s)\n"%enabled)
        else:
            sys.stdout.write("Unable to initialize Keyboard Hook\n")
            self.hm = None
            self.enabled = False

        self.diag = False

    def keyPressEvent(self,event):

        # return false to capture the key press
        if event.KeyID == self.k_PLAYPAUSE :
            self.controller.device.playpause()
            return False
        elif event.KeyID == self.k_STOP :
            self.controller.toggleStop()
            return False
        elif event.KeyID == self.k_PREV :
            self.controller.device.prev()
            return False
        elif event.KeyID == self.k_NEXT :
            self.controller.device.next()
            return False
        elif self.diag :
            if event.Ascii > 0x20 or event.Ascii == 0xD:#any char or \n
                sys.stdout.write("%s"%chr(event.Ascii)),
            else:
                sys.stdout.write("{%02X}"%event.KeyID)
        return True

    def setEnabled(self,b):
        if os.name == 'nt':
            if not self.enabled and b:
                self.hm.HookKeyboard()
                self.enabled = b
            elif self.enabled and not b:
                self.hm.UnhookKeyboard()

    def setDiagEnabled(self,b):
        self.diag = b




