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
        versionCode = 14
        versionName = "0.9.0-quest"
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
}
