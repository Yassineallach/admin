import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// ---- AdMob configuration -------------------------------------------------------------------
// Production IDs live in admob.properties (git-ignored; see admob.properties.example) or -P flags.
// Debug builds ALWAYS use Google's official test IDs (AdMob policy: never serve live ads in development).
val admobProps = Properties().apply {
    rootProject.file("admob.properties").takeIf { it.exists() }?.inputStream()?.use { load(it) }
}
fun admob(key: String): String? =
    (admobProps.getProperty(key) ?: project.findProperty(key) as String?)?.trim()?.takeIf { it.isNotEmpty() }
val testAppId = "ca-app-pub-3940256099942544~3347511713"     // Google sample App ID
val testNativeUnit = "ca-app-pub-3940256099942544/2247696110" // Google test Native Advanced unit
val releaseAppId = admob("admob.appId")
fun releaseUnit(placement: String) = admob("admob.native.$placement") ?: admob("admob.native")
if (releaseAppId == null) logger.warn("AdMob: admob.appId not set — release builds use Google TEST ads (no revenue). See admob.properties.example.")

android {
    namespace = "com.airpointer.remote"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.airpointer.remote"
        // BluetoothHidDevice (HID peripheral role) was added in API 28 (Android 9).
        minSdk = 28
        targetSdk = 35
        versionCode = 10
        versionName = "2.3.0"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a", "x86_64") }
        manifestPlaceholders["admobAppId"] = releaseAppId ?: testAppId
        for (placement in listOf("home", "connection", "settings")) {
            buildConfigField("String", "ADMOB_NATIVE_${placement.uppercase()}", "\"${releaseUnit(placement) ?: testNativeUnit}\"")
        }
        buildConfigField("boolean", "ADMOB_TEST_IDS", "${releaseAppId == null}")
        // Optional: hashed device id (from logcat) to test the EEA consent form on a real phone.
        buildConfigField("String", "UMP_TEST_DEVICE", "\"${admob("ump.testDeviceHashedId") ?: ""}\"")
    }

    buildTypes {
        debug {
            manifestPlaceholders["admobAppId"] = testAppId
            for (placement in listOf("home", "connection", "settings")) {
                buildConfigField("String", "ADMOB_NATIVE_${placement.uppercase()}", "\"$testNativeUnit\"")
            }
            buildConfigField("boolean", "ADMOB_TEST_IDS", "true")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Signed with the debug key so the release APK is installable out of the box.
            // Replace with your own signingConfig before distributing.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    androidResources {
        noCompress += "task" // the hand model is memory-mapped by MediaPipe
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
        unitTests.isIncludeAndroidResources = true // Robolectric screenshot tests
        // Optional mirror for Robolectric's runtime download of android-all (e.g. behind a rate-limited proxy).
        unitTests.all { t ->
            System.getenv("ROBOLECTRIC_REPO_URL")?.let { t.systemProperty("robolectric.dependency.repo.url", it) }
            // ./gradlew testDebugUnitTest -Pscreenshots  → writes PNGs to app/build/screenshots
            if (project.hasProperty("screenshots")) t.systemProperty("roborazzi.test.record", "true")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-service:2.8.7")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.animation:animation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    // HTTP (VLC web interface) and WebSocket (Samsung / LG TVs)
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    // Air mouse: camera + on-device hand landmark tracking (MediaPipe Hand Landmarker)
    val camerax = "1.4.1"
    implementation("androidx.camera:camera-core:$camerax")
    implementation("androidx.camera:camera-camera2:$camerax")
    implementation("androidx.camera:camera-lifecycle:$camerax")
    implementation("androidx.camera:camera-view:$camerax")
    implementation("com.google.mediapipe:tasks-vision:0.10.14")
    // Monetisation: AdMob Native Advanced + Google User Messaging Platform (consent)
    implementation("com.google.android.gms:play-services-ads:25.5.0")
    implementation("com.google.android.ump:user-messaging-platform:4.0.0")
    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303") // real org.json on the JVM (Android's is a stub)
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
    // JVM screenshot tests of the real Compose UI (Robolectric native graphics + Roborazzi)
    testImplementation("org.robolectric:robolectric:4.14.1")
    testImplementation("io.github.takahirom.roborazzi:roborazzi:1.39.0")
    testImplementation("io.github.takahirom.roborazzi:roborazzi-compose:1.39.0")
    testImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
