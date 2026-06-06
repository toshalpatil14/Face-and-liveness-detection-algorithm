# React Native Compatibility Layer

This folder is intentionally small. It does not replace the working Python prototype. It shows the Android and iOS bridge shape that lets the same offline recognition, liveness, queue, sync, and purge flow be integrated into the Datalake 3.0 React Native app.

## What It Demonstrates

- A stable TypeScript API for the React Native layer.
- Android native module method signatures in Kotlin.
- iOS native module method signatures in Swift.
- The required offline methods: model initialization, registration, verification, event listing, sync, and purge.

## How It Maps To The Python Prototype

| React Native method | Python prototype equivalent |
| --- | --- |
| `initializeModels()` | `OfflineFaceEngine()` and `LivenessDetector()` construction |
| `getModelProfile()` | `python app.py profile` |
| `registerFace(...)` | `python app.py register --name ...` |
| `verifyFace(...)` | `python app.py verify` |
| `getPendingEvents()` | `python app.py list-events` |
| `syncPendingEvents()` | `python app.py sync-events` |
| `purgeSyncedEvents()` | `python app.py purge-events` |

## Judge-Facing Position

The submitted Python executable proves the core offline AI behavior. This folder proves that the same behavior has a clear React Native Android/iOS integration boundary. The final production step is to replace the `NOT_WIRED` placeholders with ONNX Runtime Mobile calls inside the native Android and iOS modules.

## Model Assets

Expected production asset locations:

- Android: `android/app/src/main/assets/models/`
- iOS: app bundle `models/` group

Expected compact model files:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec_int8bq.onnx` or `face_recognition_mobilefacenet_int8.onnx`
- `liveness_minifasnet_v2.onnx`
