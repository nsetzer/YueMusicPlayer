#! python34 ../../../test/test_client.py $this
import os, sys, codecs

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from yue.core.song import Song
from yue.core.library import Library
from yue.core.playlist import PlaylistManager
from yue.core.sqlstore import SQLStore
from yue.core.sync import SyncManager
from yue.qtcommon.ProgressDialog import ProgressDialog

class QtSyncManager(SyncManager):
    """docstring for QtSyncManager"""
    def __init__(self,library,playlist,target,enc_path,
        transcode=0,
        player_directory=None,
        equalize=False,
        bitrate=0,
        dynamic_playlists=None,
        target_prefix="",
        playlist_format=1,
        no_exec=False,
        parent=None):
        super(QtSyncManager, self).__init__(library,playlist,target,enc_path, \
            transcode,player_directory,equalize,bitrate,dynamic_playlists, \
            target_prefix, playlist_format, no_exec)

        self.step_count = 0
        self.parent = parent

    def setOperationsCount(self,count):
        self.parent.setRange(0,count)

    def message(self,msg):
        self.parent.setMessage(msg)

    def getYesOrNo(self,msg,btn2="delete"):
        result = self.parent.getInput("Delete",msg,"cancel",btn2)
        return result==1

    def log(self,msg):
        try:
            sys.stdout.write(msg+"\n")
        except UnicodeEncodeError:
            sys.stdout.write("<>\n")

    def run_proc(self,proc):
        with proc:
            n = proc.begin()
            for i in range(n):
                if self.parent.alive == False:
                    return
                proc.step(i)
                self.step_count += 1
                self.parent.valueChanged.emit(self.step_count)

                if self.no_exec:
                    QThread.usleep(25000);
            proc.end()

class SyncDialog(ProgressDialog):

    def __init__(self, uids, settings, dynamic_playlists=None, parent=None):
        super().__init__("Sync", parent)

        self.uids = uids
        self.settings = settings # sync profile settings, (not db settings)
        self.dynamic_playlists = dynamic_playlists

    def setRange(self,a,b):
        self.pbar.setRange(a,b)

    def run(self):

        print(self.settings)
        target_path = self.settings["target_path"]
        bitrate  = self.settings.get("bitrate",0)
        no_exec  = self.settings.get("no_exec",False)
        equalize = self.settings.get("equalize",False)
        # TODO windows only
        encoder_path = self.settings.get("encoder_path","ffmpeg.exe")
        transcode = { "non" : SyncManager.T_NON_MP3,
          "all" : SyncManager.T_SPECIAL,
          "none" : SyncManager.T_NONE,
        }.get(self.settings.get("transcode","none"),SyncManager.T_NONE)

        dp = None
        if self.settings.get('save_playlists',False):
            dp = self.dynamic_playlists
        target_prefix= self.settings.get("target_prefix","")
        format = self.settings.get("playlist_format",SyncManager.P_M3U)
        #dp = [("limited","limited"),]
        # TODO: pass playlist_format to Sync Manager

        lib = Library.instance().reopen()
        sm = QtSyncManager(lib,self.uids,target_path,encoder_path, \
                transcode=transcode,
                equalize=equalize,
                dynamic_playlists=dp,
                target_prefix=target_prefix,
                playlist_format=format,
                no_exec=no_exec,
                parent=self)
        sm.run()

class SyncProfileDialog(QDialog):

    def __init__(self,parent=None):
        super(SyncProfileDialog,self).__init__(parent);
        self.setWindowTitle("Sync Profile")

        # --------------------------
        # Widgets

        self.edit_target_path = QLineEdit(self)
        self.btn_target_path = QPushButton("...",self)

        self.rad_transcode_all  = QRadioButton("All")
        self.rad_transcode_non  = QRadioButton("Non-MP3")
        self.rad_transcode_none = QRadioButton("None")
        self.grp_transcode = QButtonGroup(self)
        self.grp_transcode.addButton(self.rad_transcode_all)
        self.grp_transcode.addButton(self.rad_transcode_non)
        self.grp_transcode.addButton(self.rad_transcode_none)

        self.edit_transcode_path = QLineEdit(self)
        self.btn_transcode_path = QPushButton("...",self)

        self.cbox_bitrate = QComboBox(self)
        self.cbox_bitrate.addItem("default" ,0)
        self.cbox_bitrate.addItem("128 kbps",128)
        self.cbox_bitrate.addItem("192 kbps",192)
        self.cbox_bitrate.addItem("256 kbps",256)
        self.cbox_bitrate.addItem("320 kbps",320)

        self.cbox_equalize = QCheckBox("Equalize")
        self.cbox_noexec = QCheckBox("Dry Run")

        # todo: add combo box for format
        # need: COWON, M3U
        self.cbox_savedp = QCheckBox("Save Dynamic Playlists")
        self.cbox_dpfmt = QComboBox(self)
        self.cbox_dpfmt.addItem("M3U"  ,SyncManager.P_M3U)
        self.cbox_dpfmt.addItem("Cowon",SyncManager.P_COWON)

        self.edit_prefix = QLabel(self)

        self.btn_accept  = QPushButton("Sync",self)
        self.btn_cancel  = QPushButton("Cancel",self)

        self.btn_save  = QPushButton(QIcon(':/img/app_save.png'),"",self)
        self.btn_load  = QPushButton(QIcon(':/img/app_open.png'),"",self)

        # --------------------------
        # HELP

        self.cbox_equalize.setToolTip("use bassdsp equalizer to adjust volume during transcode")
        self.cbox_noexec.setToolTip("run without syncing files.")

        self.btn_target_path.setToolTip("Select local Directory")
        self.btn_target_path.setToolTip("Select Executable Path")
        self.btn_save.setToolTip("Save current configuration")
        self.btn_load.setToolTip("Load configuration")

        self.edit_target_path.setToolTip("Copy files to destination")
        self.edit_target_path.setWhatsThis("Destination can be a local path or ftp"+
                "\nF:\\Music"+
                "\nftp://hostname//storage/emulated/0/Music"+
                "\nftp://username:password@hostname:port/Music")

        self.edit_transcode_path.setToolTip("Path to FFMPEG executable")

        self.rad_transcode_all.setToolTip("Transcode All Files to MP3")
        self.rad_transcode_non.setToolTip("Transcode Non-MP3 Files to MP3")
        self.rad_transcode_none.setToolTip("Do not transcode files")
        self.cbox_bitrate.setToolTip("Transcode MP3 bitrate"+
                                     "\ndefault uses encoders default bitrate.")

        self.cbox_savedp.setToolTip("Save Preset Playlists as m3u files")

        # --------------------------
        # Defaults

        self.rad_transcode_none.setChecked(True)
        self.disable_transcode(True)

        # --------------------------
        # Layout

        self.grid = QGridLayout(self)
        row = 0

        row+=1
        self.grid.addWidget(self.btn_save,row,2)
        self.grid.addWidget(self.btn_load,row,3)

        row+=1
        self.grid.addWidget(QLabel("Target Sync Directory:",self),row,0,1,3,Qt.AlignLeft)
        self.grid.addWidget(self.cbox_noexec,row,3,1,1,Qt.AlignLeft)

        row+=1
        self.grid.addWidget(self.edit_target_path,row,0,1,3)
        self.grid.addWidget(self.btn_target_path,row,3)

        row+=1
        self.grid.addWidget(self.cbox_savedp,row,0,1,2,Qt.AlignLeft)
        self.grid.addWidget(self.cbox_dpfmt,row,2,1,2,Qt.AlignRight)

        row+=1
        # im not ready to fully expose this feature
        self.grid.addWidget(self.edit_prefix,row,0,1,4,Qt.AlignLeft)

        row+=1
        self.grid.addWidget(QLabel("Transcode:",self),row,0,Qt.AlignLeft)
        self.grid.addWidget(self.rad_transcode_all,row,1,Qt.AlignLeft)
        self.grid.addWidget(self.rad_transcode_non,row,2,Qt.AlignLeft)
        self.grid.addWidget(self.rad_transcode_none,row,3,Qt.AlignLeft)

        row+=1
        self.grid.addWidget(QLabel("Encoder Path (ffmpeg):",self),row,0,1,4,Qt.AlignLeft)

        row+=1
        self.grid.addWidget(self.edit_transcode_path,row,0,1,3)
        self.grid.addWidget(self.btn_transcode_path,row,3)

        row+=1
        self.grid.addWidget(QLabel("Bitrate:",self),row,0,1,1,Qt.AlignLeft)
        self.grid.addWidget(self.cbox_bitrate,row,1,1,1,Qt.AlignRight)
        self.grid.addWidget(self.cbox_equalize,row,3,1,1,Qt.AlignRight)

        row+=1
        self.grid.addWidget(self.btn_accept,row,3,1,1,Qt.AlignLeft)
        self.grid.addWidget(self.btn_cancel,row,2,1,1,Qt.AlignLeft)

        # --------------------------
        # Signals

        self.rad_transcode_all.clicked.connect(lambda :self.disable_transcode(False))
        self.rad_transcode_non.clicked.connect(lambda :self.disable_transcode(False))
        self.rad_transcode_none.clicked.connect(lambda :self.disable_transcode(True))

        self.btn_target_path.clicked.connect(self.getTargetPath)
        self.btn_transcode_path.clicked.connect(self.getEncoderPath)

        self.btn_accept.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save.clicked.connect(self.save)
        self.btn_load.clicked.connect(self.load)

    def disable_transcode(self,b):
        self.edit_transcode_path.setDisabled(b)
        self.btn_transcode_path.setDisabled(b)
        self.cbox_bitrate.setDisabled(b)
        self.cbox_equalize.setDisabled(b)

    def import_settings(self, settings):

        self.edit_target_path.setText(settings.get("target_path",""))

        t = settings.get("transcode","none")
        rad= {"none":self.rad_transcode_none,
              "non-mp3":self.rad_transcode_non,
              "all":self.rad_transcode_all}.get(t,self.rad_transcode_none)
        rad.setChecked(True)
        self.disable_transcode( rad is self.rad_transcode_none )

        self.edit_transcode_path.setText(settings.get("encoder_path",""))

        self.cbox_equalize.setChecked(settings.get("equalize",False))
        self.cbox_noexec.setChecked(settings.get("no_exec",False))

        idx = {   0 : 0,
                128 : 1,
                192 : 2,
                256 : 3,
                320 : 4, }.get(settings.get('bitrate',0),0)
        self.cbox_bitrate.setCurrentIndex(idx)

        self.cbox_savedp.setChecked( settings.get('save_playlists',False))
        idx = { SyncManager.P_M3U   : 0,
                SyncManager.P_COWON : 1}.get( \
                    settings.get('playlist_format',SyncManager.P_M3U),0)
        self.cbox_dpfmt.setCurrentIndex(idx)

        self.edit_prefix.setText(settings.get('target_prefix',""))

    def export_settings(self):

        s = {}

        s['target_path'] = self.edit_target_path.text()

        s['transcode'] = "none"
        if self.rad_transcode_all.isChecked():
            s['transcode'] = 'all'
        if self.rad_transcode_non.isChecked():
            s['transcode'] = 'non-mp3'

        s['encoder_path'] = self.edit_transcode_path.text()

        s['equalize'] = self.cbox_equalize.isChecked()
        s['no_exec'] = self.cbox_noexec.isChecked()

        s['bitrate'] = self.cbox_bitrate.itemData( self.cbox_bitrate.currentIndex() )

        s['save_playlists'] = self.cbox_savedp.isChecked()
        s['playlist_format'] = self.cbox_dpfmt.itemData( self.cbox_dpfmt.currentIndex() )
        s['target_prefix'] = self.edit_prefix.text()

        return s

    def getTargetPath(self):
        path = QFileDialog.getExistingDirectory(self,"Select Sync Directory",os.getcwd())
        self.edit_target_path.setText( path )

    def getEncoderPath(self):
        # TODO: windows only
        path,filter = QFileDialog.getOpenFileName(self,"Select Encoder","ffmpeg.exe","Exe (*.exe)")
        self.edit_transcode_path.setText( path )

    def save(self):
        path,filter = QFileDialog.getSaveFileName(self,"Save Configuration","sync.ini","Config (*.ini)")
        s = self.export_settings()
        settings_save(path,s)

    def load(self):
        path,filter = QFileDialog.getOpenFileName(self,"Load Configuration","sync.ini","Config (*.ini)")
        try:
            s = settings_load( path )
            self.import_settings(s)
        except Exception as e:
            sys.stdout.write("%s\n"%e)

    def accept(self):

        s = self.export_settings()

        print(s)

        if (not s['target_path'].startswith("ftp") and \
            not s['target_path'].startswith("ssh")) and \
           not os.path.exists(s['target_path']):
            msg ="Target Path Does Not Exist\n`%s`"%s['target_path']
            QMessageBox.critical(self,"Error",msg)
            return

        if s['transcode'] != "none":
            if not os.path.exists(s['encoder_path']):
                msg ="Encoder Path Does Not Exist\n`%s`"%s['encoder_path']
                QMessageBox.critical(self,"Error",msg)
                return

        super().accept()

def settings_save( path, settings ):
    with codecs.open(path,"w","utf-8") as wf:
        for key,value in sorted(settings.items()):
            wf.write("%s=%s\n"%(key,value))

def settings_load( path ):
    s = {}
    with codecs.open(path,"r","utf-8") as rf:
        for line in rf:
            line = line.strip()
            if line:
                k,v = line.split('=')
                s[k] = v
    s['save_playlists'] = s.get('save_playlists',"false").lower() == 'true'
    s['equalize'] = s.get('equalize',"false").lower() == 'true'
    s['no_exec'] = s.get('no_exec',"false").lower() == 'true'
    try:
        s['bitrate'] = int(s.get('bitrate',0))
    except ValueError:
        s['bitrate'] = 0
    try:
        s['playlist_format'] = int(s.get('playlist_format',0))
    except ValueError:
        s['playlist_format'] = 0
    return s

def main():

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    db_path = "./yue.db"
    sqlstore = SQLStore(db_path)
    Library.init( sqlstore )
    PlaylistManager.init( sqlstore )

    #playlist = Library.instance().search("(.abm 0 limited execution)")
    #uids = [s[Song.uid] for s in playlist]

    uids = list(PlaylistManager.instance().openPlaylist("Nexus5x").iter())
    dp = None # [("limited","limited"),]

    pdialog = SyncProfileDialog()
    if pdialog.exec_():
        s = pdialog.export_settings()
        #s['no_exec'] = True
        sdialog = SyncDialog(uids,s,dp)
        sdialog.start()
        sdialog.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()