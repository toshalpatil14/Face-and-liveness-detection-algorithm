# Mobile Prototype

This folder contains a minimal React Native prototype shell for the NHAI submission.

## What It Demonstrates

- cross-platform React Native structure for Android and iOS
- strict liveness policy as the default UX
- offline enrollment and verification flow at the app layer
- local queue with `pending_sync`, `failed`, and `synced` states
- sync, retry, and purge actions
- a clean bridge boundary where native ONNX inference can replace the current mock service

## Important Boundaries

This shell is intentionally honest:

- the UI and queue flow are implemented in React Native
- the current inference service is a mock/mobile-contract layer
- the final native Android and iOS ONNX bridge still needs to be wired underneath `src/lib/offlineFaceService.ts`

## Run

Install dependencies and start Expo:

```powershell
npm install
npm run start
```

Then open:

- Android emulator or device
- iOS simulator or device

important

`The Python layer validated the models and strict liveness behavior. This React Native prototype demonstrates the cross-platform product flow, offline queue management, and sync/purge lifecycle expected by the hackathon. The remaining step is replacing the mock inference contract with native ONNX runtime bindings on Android and iOS.`
