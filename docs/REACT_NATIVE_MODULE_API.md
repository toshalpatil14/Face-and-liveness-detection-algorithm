# React Native Module API Proposal

This document strengthens the feasibility story for evaluation by showing a concrete mobile integration boundary.

## Design Goal

The current Python prototype validates the inference logic and user flow. In final deployment, the same ONNX models should run inside native Android and iOS modules, while React Native manages the UI and app state.

## Proposed React Native Boundary

React Native is responsible for:

- camera screen
- enrollment screen
- verification screen
- local queue display
- sync status UI
- retry and purge controls

Native inference is responsible for:

- loading ONNX models
- face detection
- passive liveness scoring
- active challenge state
- embedding extraction
- similarity scoring

## Proposed API

```ts
type ModelProfile = {
  detectorModel: string | null
  recognizerModel: string | null
  livenessModel: string | null
  backend: string
  totalBytes: number
  meetsTarget: boolean
  reactNativeReady: boolean
  note: string
}

type RegisterResult = {
  success: boolean
  userId: string
  backend: string
  message: string
}

type VerifyResult = {
  faceFound: boolean
  livenessPassed: boolean
  challengeRequired: boolean
  riskLevel: "Low" | "Medium" | "High"
  matchFound: boolean
  matchedUserId: string | null
  similarity: number
  backend: string
  latencyMs: number
  message: string
}

type PendingEvent = {
  eventId: string
  userId: string
  eventType: "attendance" | "verification"
  timestamp: string
  syncState: "pending_sync" | "synced" | "failed"
}

initializeModels(): Promise<void>
getModelProfile(): Promise<ModelProfile>
registerFace(userId: string, frameBytes: Uint8Array): Promise<RegisterResult>
verifyFace(frameBytes: Uint8Array): Promise<VerifyResult>
getPendingEvents(): Promise<PendingEvent[]>
purgeSyncedRecords(): Promise<void>
retryFailedSync(): Promise<void>
```

## Why This Helps in Evaluation

- proves the solution can map cleanly into Datalake 3.0 React Native architecture
- separates UI and inference responsibilities clearly
- shows that the prototype is already organized around deployable interfaces
- reduces perceived engineering risk for production integration

## Judge-Facing Summary

`The Python prototype is only the validation layer. The final mobile implementation keeps the same compact ONNX model stack and exposes it through a minimal native bridge to React Native for enrollment, verification, queue management, and purge flow.`
