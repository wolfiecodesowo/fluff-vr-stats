plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Fluff Bot's PUBLIC key from the repo's trust.json (made by tools/make_keys.py). Empty = keys + safe chat off.
val fluffBotKey: String = run {
    val f = rootProject.file("../trust.json")
    if (!f.exists()) "" else ((groovy.json.JsonSlurper().parse(f) as Map<*, *>)["bot"] as? String) ?: ""
}

android {
    namespace = "com.wolfiecodesowo.fluffvr"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.wolfiecodesowo.fluffvr"
        minSdk = 29
        targetSdk = 32          // Quest-friendly, no extra foreground-service paperwork
        versionCode = 15
        versionName = "0.10.0-quest"
        ndk { abiFilters += listOf("arm64-v8a") }   // Quest + every modern phone are 64-bit ARM (keeps the camera tracker small)
        buildConfigField("String", "FLUFF_BOT_KEY", "\"$fluffBotKey\"")
    }
    buildFeatures { buildConfig = true }
    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    lint {
        disable += "ExpiredTargetSdkVersion"   // sideloaded Quest app, not a Play Store app
        abortOnError = false
    }
    // compress the pose model's native lib inside the APK (way smaller download)
    packaging { jniLibs { useLegacyPackaging = true } }
    // screenshot tests: `gradlew testDebugUnitTest` renders every tab to quest/screens/ (no headset needed)
    testOptions { unitTests { isIncludeAndroidResources = true } }
}

dependencies {
    // phone camera body tracker: Google's on-device pose model (bundled, no Play Services / account needed)
    implementation("com.google.mlkit:pose-detection:18.0.0-beta5")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.14.1")
}
