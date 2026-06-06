# Hackathon 7.0 Solution Brief

## Problem Restatement

Build a mobile-based secure offline facial recognition and liveness detection system for remote locations that:

- works fully offline
- integrates with React Native on Android and iOS
- keeps the AI footprint around 20 MB
- finishes recognition plus liveness in under 1 second on mid-range devices
- uses only open-source technologies

## Recommended Production Architecture

This repository now has two layers:

1. `Python prototype layer`
   - Used to validate the offline workflow, registration flow, verification flow, and liveness flow.
   - Good for fast experimentation and demo logic.

2. `React Native compatibility layer`
   - TypeScript API contract
   - Native Android/iOS bridge method surfaces
   - ONNX Runtime Mobile integration boundary
   - Offline storage, sync, and purge methods represented for Datalake 3.0 integration

## Model Stack

### Current prototype profile

- Detector: `face_detection_yunet_2023mar.onnx`
- Recognizer: `face_recognition_sface_2021dec.onnx`
- Liveness: heuristic head-motion based offline check

This profile is good for prototyping but is not ideal for the final hackathon constraint because the recognizer is too large for the `~20 MB` target.

### Current improved compact profile

- Detector: `face_detection_yunet_2023mar.onnx`
- Recognizer: `face_recognition_sface_2021dec_int8bq.onnx`
- Liveness: `liveness_minifasnet_v2.onnx` plus motion cue fallback

This is the best profile currently wired into the repository because it stays within the same official OpenCV model family while reducing footprint significantly.

### Recommended final mobile profile

- Detector: `YuNet ONNX`
- Recognizer: `MobileFaceNet INT8 ONNX`
- Liveness: `MiniFASNetV2 ONNX` or similarly small anti-spoofing model

Why this profile:

- small enough for mobile packaging
- open-source friendly
- fast enough for CPU inference
- much easier to integrate into React Native than Python code

## Offline Flow

1. App opens camera locally on device.
2. Face detector finds the largest visible face.
3. Liveness check validates the user with local cues such as slight head turn, blink, or anti-spoof classification.
4. Recognizer converts the aligned face crop into an embedding vector.
5. The embedding is compared with embeddings stored locally on the device.
6. If the score crosses threshold, the user is verified.
7. Attendance or authentication event is stored locally.
8. When network returns, pending events are synced to AWS.
9. After successful sync, local event queue is purged.

## Storage Strategy

Store only:

- user identifier
- compact face embedding
- timestamp
- sync state

Avoid storing raw face photos permanently unless required by policy. This keeps storage smaller and reduces privacy risk.

## React Native Compatibility Plan

Recommended integration:

1. Camera frames captured in React Native.
2. Frames passed to native module on Android and iOS.
3. Native module runs ONNX models locally.
4. Native module returns:
   - face found
   - liveness status
   - similarity score
   - matched identity
5. React Native handles UI, local queue, sync status, and purge flow.

Suggested native stack:

- React Native
- Kotlin / Java bridge for Android
- Swift / Objective-C bridge for iOS
- ONNX Runtime Mobile
- SQLite or MMKV for local data

## Constraints Mapping

### React Native compatibility

The final deployable solution should not ship Python inside the mobile app. Python here is for prototyping. Final inference should use ONNX models through native mobile bindings.

### Model footprint

The repository now exposes a `profile` command so you can measure whether the currently selected model stack is under the target.

### Processing speed

To stay under 1 second:

- use 112x112 or similar face crops
- keep one detector and one recognizer pass per verification
- use quantized ONNX models
- run only CPU inference

### Hardware requirements

Target:

- Android 8.0+
- iOS 12+
- 3 GB RAM devices

This is realistic with a quantized mobile recognizer and lightweight liveness model.

### Accuracy goal

The `>95%` target will depend on:

- high-quality enrollment captures
- threshold tuning
- Indian demographic coverage in training or evaluation data
- outdoor-lighting validation

The current prototype code alone does not prove this accuracy. Final evaluation must be done on a representative test set.

### Open-source only

Use only open-source models and runtimes. Keep licenses documented for:

- ONNX Runtime
- OpenCV / YuNet
- MobileFaceNet source
- MiniFASNet or chosen liveness source

## Honest Status

Current repo status:

- offline prototype: yes
- source code: yes
- face registration and verification: yes
- learned offline liveness model path: yes
- React Native compatibility display: yes, through `react-native-compat/`
- final React Native app: not included
- compact quantized recognizer path: prepared, requires model file in `models/`
- compact learned liveness model path: prepared, requires model file in `models/`
- final under-20-MB verified model pack: verify with `python app.py profile` after restoring `models/`
- >95% benchmark on Indian demographic field data: not yet validated

## Next Practical Step

To align this repo with the final hackathon ask:

1. restore the compact ONNX files under `models/`
2. run `python app.py profile` and `python app.py benchmark --iterations 10`
3. build the portable executable with `build_portable.ps1`
4. replace the `react-native-compat/` placeholders with ONNX Runtime Mobile calls for a full mobile app
5. benchmark latency on target Android/iOS devices
6. validate thresholding on Indian demographic field samples
