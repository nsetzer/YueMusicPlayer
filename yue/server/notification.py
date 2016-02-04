
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
        # api 19
        #self.Action = autoclass('android.app.Notification$Action')
        # api 20, uncertain on autoclass syntax for double nested class
        #self.ActionBuilder = autoclass('android.app.Notification$Action$Builder')

        self.large_icon = self.get_scaled_icon('icon')

        self.actions = [None,None,None]

    def setText(self,ustr):
        self.utext = ustr

    def setMessage(self,ustr):
        self.umessage = ustr

    def setAction(self,index,ustr,icon="icon"):
        """
        ustr : python unicode string
        icon : name of Drawable, without extension
               (unimplemented)
        """
        self.actions[index] = (ustr,icon)

    def update(self):
        """ update app notification """

        text = self.AndroidString(self.utext.encode('utf-8'))
        message = self.AndroidString(self.umessage.encode('utf-8'))
        service = self.PythonService.mService

        intent = self.Intent(service, service.getClass())
        contentIntent = self.PendingIntent.getActivity(service, 0, intent, 0)

        notification_builder = self.NotificationBuilder(service)
        notification_builder.setContentTitle(text)
        notification_builder.setContentText(message)
        # must be a java Icon
        notification_builder.setSmallIcon(self.Drawable.icon)
        # must be a java Bitmap
        notification_builder.setLargeIcon(self.large_icon)
        notification_builder.setContentIntent(contentIntent)

        for act in self.actions:
            if act is not None:
                ptext,icon = act
                text = self.AndroidString(ptext.encode('utf-8'))
                intent = self.Intent(service, service.getClass())
                intent.setAction(text) # TODO not sure what value to use
                # 12345 is an arbitrary number, need to check documentation
                # on what that field is
                contentIntent = self.PendingIntent.getBroadcast( \
                    service, 12345, intent, \
                    self.PendingIntent.FLAG_UPDATE_CURRENT )
                # this method is deprecated in api 23, but the alternative
                # does not exist until api 20 (using Action.Builder)
                notification_builder.addAction( \
                    self.Drawable.icon,text,contentIntent)

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
