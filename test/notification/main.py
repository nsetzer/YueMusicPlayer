#! python2.7 $this
from os.path import dirname
from os.path import join
from os.path import realpath

import kivy
kivy.require('1.8.0')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.logger import Logger
from kivy.lib import osc
from kivy.clock import Clock

from plyer import notification
from plyer.utils import platform
from plyer.compat import PY2

from jnius import autoclass, cast

import sys
from subprocess import Popen

serviceport = 15123 # Todo select these at run time
activityport = 15124

class NotificationDemo(BoxLayout):

    def do_notify(self, mode='normal'):
        title = self.ids.notification_title.text
        message = self.ids.notification_text.text
        if PY2:
            title = title.decode('utf8')
            message = message.decode('utf8')
        kwargs = {'title': title, 'message': message}

        if mode == 'fancy':
            kwargs['app_name'] = "Plyer Notification Example"
            if platform == "win":
                kwargs['app_icon'] = join(dirname(realpath(__file__)),
                                          'plyer-icon.ico')
                kwargs['timeout'] = 4
            else:
                kwargs['app_icon'] = join(dirname(realpath(__file__)),
                                          'plyer-icon.png')
        notification.notify(**kwargs)

class NotificationDemoApp(App):
    def build(self):

        self.start_service()

        return NotificationDemo()

    def __init__(self,**kwargs):
        super(NotificationDemoApp,self).__init__(**kwargs)
        self.pid = None # popen service reference
        self.service = None # android service reference

    def start_service(self):

        if platform == "android":
            Logger.info("service: Creating Android Service")
            from android import AndroidService
            service = AndroidService('Yue Service', 'running')
            service.start('service started')
            self.service = service
        else:
            Logger.info("service: Creating Android Service as Secondary Process")
            self.pid = Popen([sys.executable, "service/main.py"])

        hostname = '127.0.0.1'
        osc.init()
        oscid = osc.listen(ipAddr=hostname, port=activityport)

        Clock.schedule_interval(lambda *x: osc.readQueue(oscid), 0)


    def stop_service(self):
        if self.pid is not None:
            Logger.info("example: stopping popen service")
            self.pid.kill()
        if self.service is not None:
            Logger.info("example: stopping android service")
            self.service.stop()
            self.service = None

    def on_stop(self):
        # TODO save current playlist to settings db

        Logger.info('example: on exit joining threads')

        self.stop_service()

        Logger.critical('example: exit')

def update_service():
    """
    http://cheparev.com/kivy-recipe-service-customization/

    this post demonstrates how it could be possible to update the
    default android foreground service notification.
    """

    Context = autoclass('android.content.Context')
    Intent = autoclass('android.content.Intent')
    PendingIntent = autoclass('android.app.PendingIntent')
    AndroidString = autoclass('java.lang.String')
    NotificationBuilder = autoclass('android.app.Notification$Builder')

    PythonService = autoclass('org.renpy.android.PythonService')
    service = PythonService.mService
    #Drawable = autoclass("{}.R$drawable".format(service.getPackageName()))
    text = AndroidString("Test Text".encode('utf-8'))
    message = AndroidString("Test Msg".encode('utf-8'))

    #small_icon = getattr(Drawable, 'tray_small')
    #large_icon_bitmap = get_scaled_icon('icon_filename_without_extension')

    contentIntent = PendingIntent.getActivity(service, 0, Intent(service, service.getClass()), 0)
    notification_builder = NotificationBuilder(service)
    notification_builder.setContentTitle(text)
    notification_builder.setContentText(message)
    #notification_builder.setSmallIcon(small_icon)
    #notification_builder.setLargeIcon(large_icon_bitmap)
    notification_builder.setContentIntent(contentIntent)

    notification = notification_builder.getNotification()

    notification_service = service.getSystemService(Context.NOTIFICATION_SERVICE)
    notification_service.notify(1, notification)


def get_scaled_icon(icon):
    """
    icon : name of icon file (png) without extension

    this function assumes that a 'Drawable' was regiseted, (see original post)
    it should be possible to create a bitmap dynamically, using a bitmap
    factory.

    Bitmap bm = BitmapFactory.decodeResource(getResources(), R.drawable.image);
    """
    Dimen = autoclass("android.R$dimen")
    Bitmap = autoclass("android.graphics.Bitmap")
    PythonService = autoclass('org.renpy.android.PythonService')
    service = PythonService.mService
    Drawable = autoclass("{}.R$drawable".format(service.getPackageName()))

    scaled_icon = getattr(Drawable, icon)
    scaled_icon = cast("android.graphics.drawable.BitmapDrawable",
                       service.getResources().getDrawable(scaled_icon))
    scaled_icon = scaled_icon.getBitmap()

    res = service.getResources()
    height = res.getDimension(Dimen.notification_large_icon_height)
    width = res.getDimension(Dimen.notification_large_icon_width)
    return Bitmap.createScaledBitmap(scaled_icon, width, height, False)


if __name__ == '__main__':
    NotificationDemoApp().run()

