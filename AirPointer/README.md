# Air Pointer — gyroscope presentation pointer for Android

Air Pointer is a native Android app (Kotlin + Jetpack Compose). It turns a phone into a **real
Bluetooth HID mouse + keyboard**. The computer pairs with it like any other Bluetooth mouse, so
there is **no software, driver or receiver on the PC**. Move the phone in the air and the cursor
follows. Slide controls send real keystrokes to PowerPoint.

* Bluetooth: Android `BluetoothHidDevice` API (HID peripheral role, Android 9 / API 28+)
* Motion: `SensorManager` gyroscope at 200 Hz plus the accelerometer, with gravity-compensated air-mouse math
* Background operation: foreground service of type `connectedDevice`

---

## 1. Build

### Requirements
* JDK 17 or newer (the project targets Java 17 bytecode; tested with JDK 21)
* Android SDK Platform 35 and Build-Tools 35 (Android Studio Ladybug or newer installs these)
* Internet access the first time (Gradle downloads AGP 8.7.3, Kotlin 2.0.21 and Compose BOM 2024.12.01)

### Android Studio
1. *File → Open…* → select the `AirPointer/` folder.
2. Let Gradle sync, choose the `app` configuration, and press **Run** with a phone connected over USB
   (enable *Developer options → USB debugging*).

### Command line
```bash
cd AirPointer
# tell Gradle where the SDK is (or set ANDROID_HOME)
echo "sdk.dir=/path/to/Android/sdk" > local.properties

./gradlew testDebugUnitTest   # 24 JVM unit tests: motion pipeline + HID reports
./gradlew assembleDebug       # app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease     # app/build/outputs/apk/release/app-release.apk (R8-minified, ~2 MB)
./gradlew lintDebug           # Android Lint

adb install -r app/build/outputs/apk/release/app-release.apk
```
The release build is **signed with the debug key** so it installs out of the box. Before you
distribute it, replace `signingConfig` in `app/build.gradle.kts` with your own keystore.

A prebuilt APK is in `dist/AirPointer-1.0.4.apk`.

---

## 2. First use (Windows 10/11)

1. Install the APK, open **Air Pointer** and allow **Nearby devices** (and notifications).
2. Wait for the home screen to say **Ready**. That means the phone has registered as a HID mouse/keyboard.
3. **Devices & pairing → Make visible.**
4. On the PC, open *Settings → Bluetooth & devices → Add device → Bluetooth* and pick the phone.
   Confirm the code on both screens. Windows installs a mouse and a keyboard and connects.
5. Open **Presentation remote**. Point the phone at the screen and move it.
   *Settings → Calibrate* (phone flat on a table, about 1.5 s) removes gyro drift.

> **Upgrading from an earlier version?** The HID descriptor changed in 1.0.2 and again in 1.0.4. Windows caches the
> descriptor, so remove the phone in *Bluetooth & devices* (and the PC on the phone) and pair again.
>
> **Paired the phone with this PC before installing Air Pointer?** Remove the pairing on *both*
> sides and pair again while Air Pointer is running. Windows caches the old SDP service list
> from the earlier pairing, and without fresh pairing it never sees the HID service.

Later sessions: open the app and it reconnects to the last computer automatically. The connection
survives the app going to the background thanks to the foreground service, and the notification
offers *Previous / Next / Stop* controls.

---

## 3. Features

| Area | What it does |
|---|---|
| Bluetooth HID | Standard keyboard + mouse combo: keyboard (report ID 1, 6KRO, LED output) and mouse (ID 2, 3 buttons, 8-bit X/Y/wheel in the boot-mouse layout). Nothing else. Registers the SDP record, answers GET/SET_REPORT, tracks protocol mode, handles virtual-cable unplug. |
| Pairing | Make the phone discoverable, scan for computers, bond with them (`createBond`), list bonded devices, connect or disconnect. |
| Reconnection | Auto-connects to the last host after registration; after an unexpected drop it retries with back-off (2 s → 30 s, 6 attempts). Bluetooth on/off is handled. |
| Pointer | Gravity-compensated yaw/pitch, 1€ adaptive smoothing, soft dead zone, acceleration curve, sub-count accumulation, ~133 Hz report rate. |
| Drift | Manual calibration (rejects movement and restarts) plus automatic bias re-estimation whenever the phone is still. |
| Remote screen | Next / Previous, left / right click (press-and-hold to drag), pointer button (toggle or hold), recenter, pause/resume, black screen, start/end slideshow, gesture pad, scroll strip. |
| Configurable | Gestures (tap, double tap, long press, 4 swipes), volume up/down actions, slide keys (arrows / PgUp-PgDn), PowerPoint laser mode (Ctrl+L / Ctrl+A), recenter method, sensitivity, acceleration, smoothing, dead zone, inversion, haptics, keep screen on. |
| Diagnostics | HID profile support and registration state, host, protocol, report rate and failures, sensor model / rate / processing time, live yaw/pitch, bias and gravity, **local motion preview** (works without a PC), test square and test click, event log with copy. |

### Gesture pad defaults
Swipe ← = next slide, swipe → = previous slide. Tap, double tap and long press do **nothing** by
default: the gripping thumb rests on the pad, and a click there would land wherever the moving
cursor happens to be. Use the dedicated Left/Right click buttons for clicks.

### Stuck-input protection
Key and button *release* reports are retried if the Bluetooth stack rejects them. An "everything
released" report is sent after every (re)connection, when tracking pauses and when the remote
screen closes. This way Windows can never be left with a held Ctrl/Shift/arrow key or mouse button.

### Default key mapping
| Action | Sent to PC |
|---|---|
| Next / Previous slide | → / ← (or Page Down / Page Up) |
| Start slideshow | F5 · from current slide: Shift+F5 |
| End slideshow | Esc |
| Black / white screen | B / W |
| Laser pointer | Ctrl+L (on) · Ctrl+A (back to arrow) |

---

## 4. Architecture

```
app/src/main/java/com/airpointer/remote/
├── core/               Pure Kotlin, no Android deps → unit-tested on the JVM
│   ├── AirMouseProcessor   gyro+accel → mouse deltas (bias, gravity, 1€, accel curve)
│   ├── TiltPointerProcessor  fallback for phones with no gyroscope
│   ├── OneEuroFilter, Vec3, MotionConfig
├── hid/
│   ├── HidDescriptor       report descriptor (keyboard ID1, mouse ID2)
│   ├── HidReports          report encoders, key codes
│   ├── ReportAccumulator   coalesces 200 Hz motion into rate-limited reports
│   ├── BluetoothHidController  BluetoothHidDevice proxy, registerApp, connect, reconnect, sendReport
│   └── BluetoothPairingManager discovery, bonding, bonded list
├── motion/SensorMotionSource   SensorManager registration (200 Hz gyro on the I/O thread)
├── presenter/PresenterController  orchestration: gate, clicks, keys, scroll, recenter, calibration
├── service/AirPointerService   foreground service (connectedDevice) + notification controls
├── settings/                   SharedPreferences-backed StateFlow settings
├── diagnostics/DiagnosticsLog  ring-buffer event log
└── ui/                         Compose screens: Home, Pairing, Remote, Settings, Diagnostics
```

**Report rate.** Mouse reports are capped at 60 Hz by default (*Settings → Connection → Report
rate*). The HID QoS requests about 800 bytes/s, and one report is about 10 bytes on air. Streaming
faster overruns the link: Android's `sendReport()` still returns success while the stack silently
queues or drops reports, so the cursor freezes. If the cursor freezes or lags, lower the rate.

**Latency path.** Sensor events, motion processing and `sendReport` all run on one
`HandlerThread` at `THREAD_PRIORITY_URGENT_DISPLAY`, so there are no thread hops between them.
The gyroscope runs at 200 Hz, processing takes a few µs per sample, and reports go out every
≥16.7 ms (60 Hz, configurable). End-to-end latency is mostly the Bluetooth link: the QoS requests an 11.25 ms latency,
and typical total latency is about 15–30 ms.

**Motion math.** The processor tracks the world "up" vector in the device frame with a
complementary filter: it is propagated by the gyro and slowly corrected by the accelerometer,
trusting the accelerometer less while the phone accelerates. Horizontal motion is
`ω · up` (rotation about the world vertical). Vertical motion is `ω · normalize(Y × up)`.
As a result, the cursor responds the same however the phone is rolled or tilted in the hand.
Rotation is integrated into angles and smoothed by a 1€ filter: low cutoff when slow (removes
tremor), high cutoff when fast (no lag). Then the acceleration curve and gain apply, with
fractional counts carried over.

**Click stability.** Pressing an on-screen button shakes the phone slightly, so motion is
suppressed for 140 ms around every click. The filter is re-primed whenever output is gated,
so nothing jumps afterwards.

---

## 5. Testing

`./gradlew testDebugUnitTest` runs 24 JVM tests. `MotionSimulator` integrates a real phone
orientation and generates the gyro + accelerometer samples that phone would produce. The tests
check that:

* yaw 0.5 rad → −550 counts horizontally, with no vertical leak (and the reverse for pitch);
* the same yaw with the phone **rolled 50°** or **tilted 40°** gives the same horizontal motion;
* calibration recovers an injected gyro bias to within 1e-3 rad/s and zero drift over 10 s; it restarts when the phone is bumped;
* uncalibrated bias drifts > 80 counts in 10 s, while with automatic compensation it stays ≤ 3 counts;
* Gaussian hand tremor (σ = 0.008 rad/s) moves the cursor ≤ 6 counts in 5 s;
* very slow motion is not lost to rounding; acceleration boosts only fast moves;
* gating off/on and sensor gaps never cause a jump;
* the HID descriptor is parsed and each report's declared bit size matches its encoder; encoders produce correct little-endian bytes; overflow carries over between reports.

**On-device checks**

1. *Diagnostics → Preview pointer locally*: exercises the full sensor pipeline without a PC.
2. Once connected, *Diagnostics → Test square / Test click*: exercises the HID link without sensors.

**Not tested in this environment:** the Bluetooth link to a real Windows PC. It needs physical
hardware, and Android emulators do not implement the HID Device role. Run the on-device checks
above after installing.

---

## 6. Hardware and OS limitations (read this)

1. **Android 9+ is required.** `BluetoothHidDevice` does not exist before API 28 (`minSdk = 28`).
2. **Not every phone supports HID peripheral mode.** The profile is optional in AOSP
   (`bluetooth.profile.hid.device.enabled`), and some manufacturers and custom ROMs ship with it
   disabled. Older Huawei/Honor builds, some Xiaomi/Oppo builds, some Android Go devices and some
   Android 9 builds are known cases. The app detects this at runtime (`getProfileProxy` fails or
   never answers within 5 s) and shows **Not supported** with an explanation. No app can turn the
   profile on without root. Google Pixel and Samsung Galaxy phones (Android 9+) generally work.
3. **Only one app at a time** can hold the HID Device role. If another keyboard/mouse emulator is
   registered, Air Pointer's registration is rejected. Close the other app and press *Retry*.
4. **Stale pairing on the PC.** See the note in section 2. Windows must pair while Air Pointer is
   registered.
5. **Windows may show the phone with a phone icon.** The device's Bluetooth Class of Device belongs
   to the OS, not the app. The mouse and keyboard still work.
6. **Windows "Enhance pointer precision"** adds its own acceleration on top of Air Pointer's.
   For the most predictable feel, turn it off (*Mouse settings → Additional mouse settings →
   Pointer options*) or set Air Pointer's acceleration to Off.
7. **Recenter** pushes the cursor to the top-left corner, then moves it half a screen (set your
   resolution in Settings). It lands exactly in the centre only with Windows "Enhance pointer
   precision" turned off. An earlier build used a second, absolute mouse collection for an exact
   centre, but Windows then ignored the main mouse, so it was removed.
8. **Volume keys** can only be intercepted while the remote screen is in the foreground with the
   screen on. Android does not deliver hardware keys to background apps without an accessibility
   service, which this app deliberately does not use.
9. **Screen off.** The Bluetooth connection stays alive (foreground service). Many phones throttle
   or suspend non-wake-up motion sensors while the screen is off, so the remote keeps the screen on
   by default. Notification controls (Prev / Next) work regardless.
10. **Gyroscope required for air-mouse pointing.** Phones without a gyroscope fall back to
    accelerometer tilt control (joystick-like, less precise). Without any motion sensor, only the
    buttons, gestures and keys work.
11. **200 Hz sensor cap.** Android 12+ limits apps without `HIGH_SAMPLING_RATE_SENSORS` to 200 Hz,
    which is what the app uses.
12. **Boot protocol.** Report IDs follow the Android stack's convention (keyboard = 1, mouse = 2),
    and the mouse report is byte-identical to the boot-mouse format. Input therefore reads correctly
    whether the host uses REPORT or BOOT protocol.
13. **Other hosts.** macOS, Linux and ChromeOS accept the same composite descriptor. Keynote and
    Google Slides also respond to the arrow keys. Pairing steps differ per OS.
