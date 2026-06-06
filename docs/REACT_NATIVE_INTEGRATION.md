# React Native Integration Guide

## Goal

Integrate the offline face recognition and liveness stack into a React Native app for:

- Android 8.0+
- iOS 12+
- offline field operation
- later sync with AWS when connectivity returns

## Recommended App Split

### React Native layer

Responsible for:

- camera screen
- registration screen
- verification screen
- local event queue
- sync status UI
- retry and purge controls

### Native inference layer

Responsible for:

- loading ONNX models
- face detection
- liveness scoring
- embedding extraction
- similarity scoring

## Suggested Native API

Expose a single native module to React Native with methods like:

- `initializeModels()`
- `getModelProfile()`
- `registerFace(userId, frameBytes)`
- `verifyFace(frameBytes)`
- `purgeSyncedRecords()`
- `getPendingEvents()`

## Return Shape

Recommended verification response:

```json
{
  "faceFound": true,
  "livenessPassed": true,
  "livenessScore": 0.91,
  "matchFound": true,
  "matchedUserId": "field_user_102",
  "similarity": 0.83,
  "backend": "sface_int8",
  "latencyMs": 312
}
```

## Local Storage

Store:

- enrolled user id
- face embedding vector
- enrollment backend version
- offline verification events
- sync state

Use:

- SQLite for structured audit/event storage
- MMKV for tiny config/state values

## Sync and Purge

1. Save verification event locally while offline.
2. Mark event as `pending_sync`.
3. When network returns, push to AWS API.
4. On server success, mark as `synced`.
5. Purge synced event data according to retention rules.

## Mobile Packaging

Preferred model set:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec_int8bq.onnx`
- `liveness_minifasnet_v2.onnx`

Why:

- compact footprint
- CPU-friendly
- open-source
- suitable for native ONNX deployment

## Important Note

The Python code in this repository is a prototype and benchmark layer. The final React Native submission should move inference into native Android/iOS code or a React Native-compatible inference runtime.
