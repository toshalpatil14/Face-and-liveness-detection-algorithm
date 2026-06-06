# ONNX Runtime Mobile Setup

This guide explains how the compatibility layer in `react-native-compat/` can be wired into a full React Native Android/iOS app.

## 1. Native Module Contract

Use:

- `react-native-compat/OfflineFaceModule.ts`
- `react-native-compat/android/OfflineFaceModule.kt`
- `react-native-compat/ios/OfflineFaceModule.swift`

The production app should implement the same methods with ONNX Runtime Mobile:

- `initializeModels`
- `getModelProfile`
- `registerFace`
- `verifyFace`
- `getPendingEvents`
- `syncPendingEvents`
- `purgeSyncedEvents`

## 2. React Native Dependencies

For a full app, install a native ONNX runtime package:

```powershell
npm install onnxruntime-react-native
```

Because this is a native module, use a native React Native build. Do not rely on Expo Go for final evaluation.

## 3. Model Asset Locations

Python prototype:

- `models/`

Android app:

- `android/app/src/main/assets/models/`

iOS app:

- app bundle `models/` group

Expected files:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec_int8bq.onnx` or `face_recognition_mobilefacenet_int8.onnx`
- `liveness_minifasnet_v2.onnx`

## 4. Android Wiring

In the Kotlin native module:

1. Load ONNX sessions from `assets/models`.
2. Decode camera frame bytes.
3. Run face detection.
4. Run liveness challenge/model.
5. Generate embedding.
6. Compare against local embeddings.
7. Queue the attendance event locally.

## 5. iOS Wiring

In the Swift native module:

1. Add model files to the app target.
2. Ensure the models appear under `Build Phases -> Copy Bundle Resources`.
3. Load sessions from the bundle.
4. Return the same result shape defined in `OfflineFaceModule.ts`.

## 6. Accuracy Note

Do not claim `>95%` accuracy until threshold tuning and validation are completed on representative Indian demographic and outdoor-lighting samples.
