plugins { id("com.android.application") }

android {
    namespace = "it.gestioneturni.tv"
    compileSdk = 36
    defaultConfig {
        applicationId = "it.gestioneturni.tv"
        minSdk = 23
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    // Supply a private keystore through environment variables for a distributable
    // release. Never commit that keystore. Debug is independently installable.
    val store = System.getenv("TV_KEYSTORE")
    if (!store.isNullOrBlank()) {
        signingConfigs {
            create("distribution") {
                storeFile = file(store)
                storePassword = System.getenv("TV_STORE_PASSWORD")
                keyAlias = System.getenv("TV_KEY_ALIAS")
                keyPassword = System.getenv("TV_KEY_PASSWORD")
            }
        }
        buildTypes { getByName("release") { signingConfig = signingConfigs.getByName("distribution") } }
    }
}

dependencies { testImplementation("junit:junit:4.13.2") }
