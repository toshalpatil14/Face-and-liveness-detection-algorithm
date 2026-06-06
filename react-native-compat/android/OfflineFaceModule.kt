package com.datalake.offlineface

import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class OfflineFaceModule(private val context: ReactApplicationContext) :
    ReactContextBaseJavaModule(context) {

    override fun getName(): String = "OfflineFaceModule"

    @ReactMethod
    fun initializeModels(promise: Promise) {
        // Load ONNX assets from android/app/src/main/assets/models.
        promise.resolve(null)
    }

    @ReactMethod
    fun getModelProfile(promise: Promise) {
        // Return detector, recognizer, liveness model names and total bytes.
        promise.reject("NOT_WIRED", "Native ONNX runtime wiring is pending.")
    }

    @ReactMethod
    fun registerFace(name: String, frameBase64: String, promise: Promise) {
        // Decode frame, run detector + embedding, store encrypted local embedding.
        promise.reject("NOT_WIRED", "Native ONNX runtime wiring is pending.")
    }

    @ReactMethod
    fun verifyFace(frameBase64: String, requireActiveChallenge: Boolean, promise: Promise) {
        // Decode frame, run liveness + recognition, queue offline event.
        promise.reject("NOT_WIRED", "Native ONNX runtime wiring is pending.")
    }

    @ReactMethod
    fun getPendingEvents(promise: Promise) {
        promise.reject("NOT_WIRED", "Local mobile event store is pending.")
    }

    @ReactMethod
    fun syncPendingEvents(promise: Promise) {
        promise.reject("NOT_WIRED", "AWS sync endpoint integration is pending.")
    }

    @ReactMethod
    fun purgeSyncedEvents(promise: Promise) {
        promise.reject("NOT_WIRED", "Purge integration is pending.")
    }
}
