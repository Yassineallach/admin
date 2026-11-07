# Keep Bluetooth HID callback (invoked by the framework through binder).
-keep class * extends android.bluetooth.BluetoothHidDevice$Callback { *; }

# MediaPipe Tasks (hand tracking) is driven from native code via JNI and protobuf reflection.
-keep class com.google.mediapipe.** { *; }
-keep class com.google.protobuf.** { *; }
-dontwarn com.google.mediapipe.**
-dontwarn com.google.protobuf.**
-dontwarn javax.annotation.**
-dontwarn com.google.auto.value.**
# AutoValue (pulled in by MediaPipe) references compile-time-only annotation-processing APIs.
-dontwarn javax.lang.model.**
-dontwarn autovalue.shaded.**
