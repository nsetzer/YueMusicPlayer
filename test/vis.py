
if __name__ == '__main__':

    sys.path.insert(0,r"D:\Dropbox\Scripting\PyModule\PyBass\bin")
    import PyBASS

    def toUTF16(string):
        """
            windows requires file paths to be in UTF-16 UNICODE encoding
        """
        return unicode(string).encode("utf-16")[2:]

    def music_init(file):

        filepath = toUTF16(file)
        #load_plugins("./plugins/");
        print(PyBASS.utf16_fexists(toUTF16(file)))
        print("LOAD:",PyBASS.load(toUTF16(file)))
        PyBASS.setDSPBlock( {"ZBVIS":True} )
        PyBASS.setVolume(.1)
        print("Volume: %d"%(PyBASS.getVolume() * 100))
        #begin playback of a song
        print(PyBASS.play(False));
        print(PyBASS.ready());
        print(PyBASS.play(True));

    def load_plugins(plugin_dir):
        # get each dll file in the given folder
        for file in [ p for p in os.listdir(plugin_dir) if p[-3:]=='dll' ]:

            val = PyBASS.load_plugin( os.path.join(plugin_dir,file) );
            # print the plugin that was found and if load was successful
            print("Loading file:",file, (val==0))

        class BassVis(Visualizer):
            def getData(self):
                return PyBASS.DSPgetInfo(u"ZBVIS");
            def isActive(self):
                return PyBASS.status() == PyBASS.P_PLAYING
            def mouseReleaseEvent (self,event):
                if PyBASS.status() == PyBASS.P_PLAYING:
                    PyBASS.pause();
                else:
                    PyBASS.play();

    def bassgetdata():
        # this function only accepts unicode strings
        return PyBASS.DSPgetInfo(u"ZBVIS");

    class BassVis(Visualizer):
        def getData(self):
            return PyBASS.DSPgetInfo(u"ZBVIS");
        def isActive(self):
            return PyBASS.status() == PyBASS.P_PLAYING
        def mouseReleaseEvent (self,event):
            if PyBASS.status() == PyBASS.P_PLAYING:
                PyBASS.pause();
            else:
                PyBASS.play();


    app = QApplication(sys.argv)

    window = Visualizer()
    window.start()
    window.resize(256,50)
    window.show()
    sys.exit(app.exec_())


