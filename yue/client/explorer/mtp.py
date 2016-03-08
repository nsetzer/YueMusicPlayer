#!  python34 $this

"""
windows (mingw):

build libusb:
    copy config.guess and config.sub from the automake directory
    into the libusb project directory. (replaing the original project
    version of the files). then run ./configure again

    ./configure --host=x86_64-w64-mingw32
    make
    make install
    cp libusb-1.0.9/libusb-1.0.pc libusb-1.0.9/libusb.pc
    PKG_CONFIG_PATH=$PKG_CONFIG_PATH:<>/libusb-1.0.9
    PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/c/msys64/home/Nick/sandbox/libusb-1.0.9

build libmtp
    require: libiconv-devel

    $ CFLAGS=-I/C/msys64/mingw64/include
    $ LIBS=-liconv
    $ LDFLAGS=-L/C/msys64/mingw64/lib

    ./configure LDFLAGS=-L/C/msys64/mingw64/bin \
                LIBS="-liconv-2 -lws2_32" \
                CFLAGS="-DHAVE_ICONV -I/C/msys64/mingw64/include"  \
                CPPFLAGS="-DHAVE_ICONV -I/C/msys64/mingw64/include"

    gcc -shared -o libmtp.dll \
        -Wl,--whole-archive libmtp.a -Wl,--no-whole-archive \
        -L/C/msys64/mingw64/bin -L/usr/local/lib \
        -liconv-2 -lws2_32 -lusb-1.0

"""
# https://github.com/guardianproject/keysync/blob/master/otrapps/util.py

# gracefully handle it when pymtp doesn't exist
import os,sys, ctypes

class MTPDummy():
    def detect_devices(self):
        return []
try:
    import pymtp
    mtp = pymtp.MTP()
except ImportError as e:
    mtp = MTPDummy()
    sys.stderr.write("MTP not supported: %s\n"%e)
except OSError as e:
    # OS error if all three libraries are not on the same path
    mtp = MTPDummy()
    sys.stderr.write("MTP not supported: %s\n"%e)
    sys.stderr.write("verify that libusb, libiconv, and libmtp are available\n")
except TypeError as e:
    # this is a bug in the current version of mtp on windows,
    # which tries to load a null path for the dll
    mtp = MTPDummy()
    sys.stderr.write("MTP not supported: (libmtp not found)\n")
# GNOME GVFS mount point for MTP devices

#if sys.platform != 'win32':
    # this crashes windows in the ntpath sys lib
#    mtp.gvfs_mountpoint = os.path.join(os.getenv('HOME'), '.gvfs', 'mtp')

def getDeviceNames():

    for i,dev in enumerate( mtp.detect_devices() ):
        entry = dev.device_entry
        vendor=entry.vendor.decode("utf-8")
        product=entry.product.decode("utf-8")
        yield i,"%s - %s"%(vendor,product)

for index,name in getDeviceNames():
    print(name)

mtp.connect()

print(mtp.get_devicename())    # b'LGL34C'
print(mtp.get_manufacturer())  # b'LGE'
print(mtp.get_modelname())     # b'LGL34C'
print(mtp.get_deviceversion()) # b'1.0'
print(mtp.get_deviceversion()) # b'1.0'

cbk=lambda t,s:sys.stdout.write("%d/%d\n"%(t,s))
res = mtp.get_filelisting()
print(len(res))
for f in res:
    print(type(f))
    print(f)

res = mtp.get_folder_list()
print(len(res))
for k,v in res.items():
    print(k,v)

mtp.disconnect()
