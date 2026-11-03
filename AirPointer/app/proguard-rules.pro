# Keep Bluetooth HID callback (invoked by the framework through binder).
-keep class * extends android.bluetooth.BluetoothHidDevice$Callback { *; }
