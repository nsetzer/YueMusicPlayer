

from kivy.lib import osc
from kivy.logger import Logger

from plyer import notification
from plyer.utils import platform
from plyer.compat import PY2

if platform == 'android':
    from jnius import autoclass, cast, PythonJavaClass, java_method
    from android.broadcast import BroadcastReceiver
import time

serviceport = 15123
activityport = 15124

class Callback(PythonJavaClass):
    __javainterfaces__ = ['org/renpy/android/GenericBroadcastReceiverCallback']
    __javacontext__ = 'app'

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        PythonJavaClass.__init__(self, *args, **kwargs)

    @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
    def onReceive(self, context, intent):
        self.callback(context, intent)

def update_notification(message, *args):

    Logger.info("service: recieved request: %s",message)

    if platform == "android":
        update_service(*message[2:])

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
    #registerReceiver = autoclass('android.content.registerReceiver')
    # Action is added in api 19. Action.Builder is added in 20
    # the current api used below was deprectated in 23.
    Action = autoclass('android.app.Notification$Action')

    PythonActivity = autoclass('org.renpy.android.PythonActivity')
    Logger.info("service: PA: %s %s"%(type(PythonActivity),hasattr(PythonActivity,'getClass')))
    PythonService = autoclass('org.renpy.android.PythonService')
    service = PythonService.mService

    # this currently fails because no icon is set.

    Drawable = autoclass("{}.R$drawable".format(service.getPackageName()))
    text = AndroidString(ptext.encode('utf-8'))
    message = AndroidString(pmessage.encode('utf-8'))

    # kivy doesnt have a tray icon by default
    Logger.info("> drawable icon %s"%hasattr(Drawable,'icon'))
    Logger.info("> drawable icon %s"%type(Drawable.icon))
    Logger.info("> drawable tray_small %s"%hasattr(Drawable,'tray_small'))
    #small_icon = getattr(Drawable, 'tray_small')
    # kivy puts this here by default
    large_icon_bitmap = get_scaled_icon('icon')
    Logger.info("> drawable large icon %s"%type(large_icon_bitmap))

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

    # this intent should start the main activity
    #Logger.info("service: create action intent")
    #appIntent = Intent(service, PythonActivity.getClass());
    #Logger.info("service: add flags")
    #appIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
    #Logger.info("service: create pending")
    #appContentIntent = PendingIntent.getActivity(service, 0, appIntent, 0)
    #Logger.info("service: create action")
    #action = ActionBuilder(Drawable.icon,actiontext,appContentIntent)
    actiontext = AndroidString("ACTION_GET_CONTENT".encode('utf-8'))
    act1msg = AndroidString("Act1".encode('utf-8'))
    act2msg = AndroidString("Act2".encode('utf-8'))
    act3msg = AndroidString("Act3".encode('utf-8'))

    #cbk = Callback(intent_callback)
    intentAct1 = Intent(service, service.getClass())
    intentAct1.setAction(actiontext)
    # must use intentAct1.setClass()  ???
    #intentAct1.setClass(cbk,Callback)
    contentIntent = PendingIntent.getBroadcast(service, 12345, intentAct1, PendingIntent.FLAG_UPDATE_CURRENT )
    Logger.error(">: cnti %s"%(type(contentIntent)))
    Logger.error(">: act1 %s"%(type(intentAct1)))
    notification_builder.addAction(Drawable.icon,act1msg,contentIntent)

    intentAct2 = Intent(service, service.getClass())
    intentAct2.setAction(actiontext)
    contentIntent = PendingIntent.getBroadcast(service, 12345, intentAct2, PendingIntent.FLAG_UPDATE_CURRENT )
    notification_builder.addAction(Drawable.icon,act2msg,contentIntent)

    intentAct3 = Intent(service, service.getClass())
    intentAct3.setAction(actiontext)
    contentIntent = PendingIntent.getBroadcast(service, 12345, intentAct3, PendingIntent.FLAG_UPDATE_CURRENT )
    notification_builder.addAction(Drawable.icon,act3msg,contentIntent)

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

def intent_callback(context, intent, *args):
    # context, intent
    Logger.warning("captured intent")
    Logger.warning("%s"%context)
    Logger.warning("%s"%intent)
    Logger.warning("%s"%args)


def main():

    oscid = osc.listen(ipAddr='127.0.0.1', port=serviceport)
    osc.init()

    osc.bind(oscid, update_notification, '/update')

    br = BroadcastReceiver(intent_callback,["GET_CONTENT",]) # no prefix ACTION_ required
    br.start()

    while True:
        osc.readQueue(oscid)
        #Logger.info("service: ping")
        time.sleep( .1 )

if __name__ == '__main__':
    main()