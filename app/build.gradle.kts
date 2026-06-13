plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    id("com.google.devtools.ksp")
}

val remoteLlmEnabled = (project.findProperty("REMOTE_LLM_ENABLED") as String?) ?: "false"
val remoteLlmProvider = (project.findProperty("REMOTE_LLM_PROVIDER") as String?) ?: "remote-disabled"
val remoteLlmBaseUrl = (project.findProperty("REMOTE_LLM_BASE_URL") as String?) ?: ""
val remoteLlmApiKey = (project.findProperty("REMOTE_LLM_API_KEY") as String?) ?: ""
val remoteLlmModel = (project.findProperty("REMOTE_LLM_MODEL") as String?) ?: ""
val remoteLlmTimeoutSeconds = (project.findProperty("REMOTE_LLM_TIMEOUT_SECONDS") as String?) ?: "45"
val vehicleQaBackendEnabled = (project.findProperty("VEHICLE_QA_BACKEND_ENABLED") as String?) ?: "false"
val vehicleQaBackendBaseUrl = (project.findProperty("VEHICLE_QA_BACKEND_BASE_URL") as String?) ?: ""
val vehicleQaBackendApiKey = (project.findProperty("VEHICLE_QA_BACKEND_API_KEY") as String?) ?: ""
val vehicleQaBackendTimeoutSeconds = (project.findProperty("VEHICLE_QA_BACKEND_TIMEOUT_SECONDS") as String?) ?: "45"

android {
    namespace = "com.example.myapplication"
    compileSdk = 36
    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    defaultConfig {
        applicationId = "com.example.myapplication"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        buildConfigField("boolean", "REMOTE_LLM_ENABLED", remoteLlmEnabled)
        buildConfigField("String", "REMOTE_LLM_PROVIDER", "\"${remoteLlmProvider}\"")
        buildConfigField("String", "REMOTE_LLM_BASE_URL", "\"${remoteLlmBaseUrl}\"")
        buildConfigField("String", "REMOTE_LLM_API_KEY", "\"${remoteLlmApiKey}\"")
        buildConfigField("String", "REMOTE_LLM_MODEL", "\"${remoteLlmModel}\"")
        buildConfigField("long", "REMOTE_LLM_TIMEOUT_SECONDS", "${remoteLlmTimeoutSeconds}L")
        buildConfigField("boolean", "VEHICLE_QA_BACKEND_ENABLED", vehicleQaBackendEnabled)
        buildConfigField("String", "VEHICLE_QA_BACKEND_BASE_URL", "\"${vehicleQaBackendBaseUrl}\"")
        buildConfigField("String", "VEHICLE_QA_BACKEND_API_KEY", "\"${vehicleQaBackendApiKey}\"")
        buildConfigField("long", "VEHICLE_QA_BACKEND_TIMEOUT_SECONDS", "${vehicleQaBackendTimeoutSeconds}L")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
}

dependencies {

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)
    testImplementation(libs.junit)
    testImplementation("org.robolectric:robolectric:4.11.1")
    testImplementation("androidx.room:room-testing:2.6.1")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    implementation("androidx.room:room-runtime:2.6.1")
    // Room Kotlin 协程支持
    implementation("androidx.room:room-ktx:2.6.1")
    // 使用 KSP 替代 kapt 处理 Room 注解
    ksp("androidx.room:room-compiler:2.6.1")
    implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

}
