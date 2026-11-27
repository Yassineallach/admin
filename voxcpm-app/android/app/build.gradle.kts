plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "app.voxcpm.studio"
    compileSdk = 35

    defaultConfig {
        applicationId = "app.voxcpm.studio"
        minSdk = 26
        targetSdk = 35
        versionCode = 17
        versionName = "2.6"
    }

    // The app's own signing key, kept out of git: VOXCPM_KEYSTORE, or app/voxcpm-studio.keystore.
    // Android only installs an update signed with the same key as the installed app, so keep that file
    // and use it for every build. Without it, builds fall back to this machine's debug key.
    val studioKeystore = file(System.getenv("VOXCPM_KEYSTORE") ?: "voxcpm-studio.keystore")
    signingConfigs {
        if (studioKeystore.exists()) {
            create("studio") {
                storeFile = studioKeystore
                storePassword = "voxcpm-studio"
                keyAlias = "voxcpm-studio"
                keyPassword = "voxcpm-studio"
            }
        }
    }
    val appSigning = signingConfigs.findByName("studio") ?: signingConfigs.getByName("debug")

    buildTypes {
        debug {
            signingConfig = appSigning
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = appSigning
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
