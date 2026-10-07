plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.wolfiecodesowo.fluffvr"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.wolfiecodesowo.fluffvr"
        minSdk = 29
        targetSdk = 32          // Quest-friendly, no extra foreground-service paperwork
        versionCode = 1
        versionName = "0.1.0-quest"
    }
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
}
