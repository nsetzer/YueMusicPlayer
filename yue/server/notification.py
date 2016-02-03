
"""
Java wrapper class for updating foreground service notification text.

based on notes from ./test/notification
"""
# TODO: test platform
try:
    from jnius import autoclass, cast
except:
    pass

class ServiceNotification(object):

    def __init__(self):
        super(ServiceNotification,self).__init__()

        # these autoclass functions seem to be very slow.
        self.Context = autoclass('android.content.Context')
        self.Intent = autoclass('android.content.Intent')
        self.PendingIntent = autoclass('android.app.PendingIntent')
        self.AndroidString = autoclass('java.lang.String')
        self.NotificationBuilder = autoclass('android.app.Notification$Builder')
        self.PythonService = autoclass('org.renpy.android.PythonService')
        service = self.PythonService.mService
        self.Drawable = autoclass("{}.R$drawable".format(service.getPackageName()))
        self.Dimen = autoclass("android.R$dimen")
        self.Bitmap = autoclass("android.graphics.Bitmap")

        self.large_icon = self.get_scaled_icon('icon')

    def setText(self,ustr):
        self.utext = ustr

    def setMessage(self,ustr):
        self.umessage = ustr

    def update(self):
        """ update app notification """

        text = self.AndroidString(self.utext.encode('utf-8'))
        message = self.AndroidString(self.umessage.encode('utf-8'))
        service = self.PythonService.mService

        contentIntent = self.PendingIntent.getActivity(service, 0, \
                        self.Intent(service, service.getClass()), 0)


        notification_builder = self.NotificationBuilder(service)
        notification_builder.setContentTitle(text)
        notification_builder.setContentText(message)
        notification_builder.setSmallIcon(self.Drawable.icon)
        notification_builder.setLargeIcon(self.large_icon)
        notification_builder.setContentIntent(contentIntent)

        notification = notification_builder.getNotification()

        notification_service = service.getSystemService(self.Context.NOTIFICATION_SERVICE)
        notification_service.notify(1, notification)

    def get_scaled_icon(self, icon):
        """
        icon : name of icon file (png) without extension from drawable dir

        Bitmap bm = BitmapFactory.decodeResource(getResources(), R.drawable.image);

        if a png is found in :
        .buildozer/android/platform/python-for-android/dist/kognitivo/res/drawable/
        file must be manually copied to this location prior to building

        it can be referenced as an Icon object using:
            getattr(self.Drawable, <base name>)

        it must be scaled and converted to a Bitmap. newer api versions
        can use the Icon type directly.

        it should be possible to create a bitmap dynamically, using a bitmap
        factory.


        """

        PythonService = autoclass('org.renpy.android.PythonService')
        service = PythonService.mService

        scaled_icon = getattr(self.Drawable, icon)
        scaled_icon = cast("android.graphics.drawable.BitmapDrawable",
                           service.getResources().getDrawable(scaled_icon))
        scaled_icon = scaled_icon.getBitmap()

        res = service.getResources()
        height = res.getDimension(self.Dimen.notification_large_icon_height)
        width = res.getDimension(self.Dimen.notification_large_icon_width)
        return self.Bitmap.createScaledBitmap(scaled_icon, width, height, False)
