[app]
title = Astro Shutter IR
package.name = nd40astro
package.domain = org.nd40
source.dir = .
source.include_exts = py,kv,md,txt,svg,png
version = 0.1.0
requirements = python3,kivy==2.3.0,kivymd==1.1.1,pyjnius
orientation = portrait
fullscreen = 0
icon.filename = icon.png
presplash.filename = icon.png
android.api = 33
android.minapi = 21
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION
android.grant_permissions = 1
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 0
