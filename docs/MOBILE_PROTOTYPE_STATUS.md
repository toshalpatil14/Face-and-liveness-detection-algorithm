# Mobile Compatibility Status

## Current Status

This repository does not include a complete React Native Android/iOS app build.

It does include `react-native-compat/`, which displays the required compatibility boundary requested in the NHAI clarification email:

- TypeScript API contract for the React Native layer.
- Android Kotlin native module method surface.
- iOS Swift native module method surface.
- Registration, verification, liveness, event listing, sync, and purge methods.

## Why This Matters

The Python prototype proves the offline recognition and liveness workflow. The compatibility layer shows how that workflow maps into the Datalake 3.0 React Native app without shipping Python inside the mobile app.

## Pending To Become A Full Mobile Prototype

- Add ONNX Runtime Mobile dependencies in Android and iOS.
- Bundle compact ONNX files in Android/iOS assets.
- Replace `NOT_WIRED` placeholders with native inference calls.
- Add mobile local storage for embeddings and event queue.
- Run benchmarks on Android 8.0+ and iOS 12+ target devices.

## Judge-Facing Wording

`The current submission includes a working Python executable for the core offline AI flow and a React Native compatibility layer that defines the Android/iOS native module boundary. A complete React Native app build is preferred by the problem statement and remains the next implementation step.`
