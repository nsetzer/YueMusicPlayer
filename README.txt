
Collection of notes based on my experience with Arch Linux.

# --------------------------------------------------------------------------
# Installation, Dev Environment Setup
# --------------------------------------------------------------------------

These notes are incomplete, follow the instructions for installing kivy
for your platform

https://kivy.org/docs/installation/installation-windows.html#installation

    install python 2.7.11, which comes with pip

    python -m pip install --upgrade pip wheel setuptools
    python -m pip install docutils pygments pypiwin32 kivy.deps.sdl2 \
                  kivy.deps.glew kivy.deps.gstreamer \
                  --extra-index-url https://kivy.org/downloads/packages/simple/
    python -m pip install kivy
    python -m pip install cython, buildozer

This project also requires the enum package on python 2.X, skip this step
if you are running python 3.

    python -m pip install enum

Building for android requires linux and python2.7. follow the instructions
for you platform to enable this. It seems like it is sufficient to
install 'buildozer' for python. when buildozer is invoked to build
a buildozer.spec, it will download the target NDK, and SDK.


# --------------------------------------------------------------------------
# Building
# --------------------------------------------------------------------------

the buildozer.spec file was created using `buildozer init` and then modified.

invoke `./build.sh` to build the project.
    an .apk file will be placed in the ./bin directory

I had to symlink /usr/bin/cython2 to /usr/bin/cython for buildozer to work.

you may need to modify ./build.sh for your environment


# --------------------------------------------------------------------------
# Testing
# --------------------------------------------------------------------------

start the avd tool in the background:
    ./start-avd.sh &

Create a new Device:
    you MUST check 'use Host GPU' in the device configuration menu

    I'm currently testing with the following settings:
        Galaxy Nexus (4.65", 720 x 1280)
        API 20
        Android Wear ARM (armeabi-v7a)

After creating a device, click start

    select 'scale display to real size' if you have a small monitor.
        My monitor is 1080 pixels tall, and my selected device has a screen
        height of 1280 pixels, so the full image cannot be displayed unless
        I scale the device.

Once the device is running and the desktop is shown run install.sh
    There is a brief tutorial you will need to swipe through.

    ./install.sh

Once the install finished start the application
    TODO: black magic
    click / swipe to open a menu,
    scroll down to 'Start ...'
    Select the app 'Yue'

the app will take a couple seconds to load.

you may need to modify ./install.sh or start-avd.sh for your environment

# --------------------------------------------------------------------------
# Android AVD Emulator
# --------------------------------------------------------------------------

open the SDK manager:
    on linux, if you let buildozer install the sdk the location will be:
        ~/.buildozer/android/platform/android-sdk-20/tools/android
    choose the correct version for the sdk version you installed.

TODO: this part is black magic

In the SDK Manager make sure the following is installed:
    Android 4.4W.2 (API 20)
    Android SDK Build-Tools (I'm not sure what version)


# --------------------------------------------------------------------------
# Additional Notes
# --------------------------------------------------------------------------

The kivy app is tested using python3.4, python 2.7.11 on windows.
On linux only python2.7 is currently tested. This is the version used
to build the android apk.

buildozer fails for many sdk versions. 14,15,16,19 all failed.
20 is the first version that succeeded. error is from running:
    ./android list sdk
the '-a' flag that is given is invalid.
There is a closed ticket on buildozer with no information about this problem
ticket number #241


