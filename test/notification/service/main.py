

from kivy.lib import osc
from kivy.logger import Logger

from plyer import notification
from plyer.utils import platform
from plyer.compat import PY2

if platform == 'android':
    from jnius import autoclass, cast

import time

serviceport = 15123
activityport = 15124

def update_notification(message, *args):

    Logger.info("service: recieved request: %s",message)

    if platform == "android":
        update_service("","")

def update_service(ptext, pmessage):
    """
    http://cheparev.com/kivy-recipe-service-customization/

    this post demonstrates how it could be possible to update the
    default android foreground service notification.
    """
    Logger.info("service: got here")

    Context = autoclass('android.content.Context')
    Intent = autoclass('android.content.Intent')
    PendingIntent = autoclass('android.app.PendingIntent')
    AndroidString = autoclass('java.lang.String')
    NotificationBuilder = autoclass('android.app.Notification$Builder')
    NotificationAction = autoclass('android.app.Notification$Action')

    PythonService = autoclass('org.renpy.android.PythonService')
    service = PythonService.mService

    # this currently fails because no icon is set.

    Drawable = autoclass("{}.R$drawable".format(service.getPackageName()))
    text = AndroidString("Test Text".encode('utf-8'))
    message = AndroidString("Test Msg".encode('utf-8'))

    # kivy doesnt hace a tray icon by default
    Logger.info("> drawable icon %s"%hasattr(Drawable,'icon'))
    Logger.info("> drawable icon %s"%type(Drawable.icon))
    Logger.info("> drawable tray_small %s"%hasattr(Drawable,'tray_small'))
    #small_icon = getattr(Drawable, 'tray_small')
    # kivy puts this here by default
    large_icon_bitmap = get_scaled_icon('icon')
    #intent = Intent(service, service.getClass())
    intent = Intent(service, service.getClass())
    contentIntent = PendingIntent.getActivity(service, 0, intent, 0)
    notification_builder = NotificationBuilder(service)
    notification_builder.setContentTitle(text)
    notification_builder.setContentText(message)
    Logger.info("service: set small icon")
    notification_builder.setSmallIcon(Drawable.icon)
    Logger.info("service: set large icon")
    notification_builder.setLargeIcon(large_icon_bitmap)
    Logger.info("service: set intent")
    notification_builder.setContentIntent(contentIntent)
    # addAction(Notification.Action action)
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

def main():

    oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    osc.init()

    osc.bind(oscid, update_notification, '/update')

    while True:
        osc.readQueue(oscid)
        #Logger.info("service: ping")
        time.sleep( .1 )

if __name__ == '__main__':
    main()