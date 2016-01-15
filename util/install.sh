
# build the app using:
#  buildozer -v android debug

# start the avd tool with:
#  ./android avd
#   'android' is found in ~/.buildozer/android/platform/android-sdk-20/tools

sdk_ver=20
adbpath=~/.buildozer/android/platform/android-sdk-$sdk_ver/platform-tools/adb

# -r for reinstall

$adbpath install -r bin/Yue-0.1-debug.apk