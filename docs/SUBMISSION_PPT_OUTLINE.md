# Final Submission PPT Outline

Use this as the slide-by-slide structure for the evaluation committee.

## Slide 1: Title

**Offline Facial Recognition and Liveness Detection for Low-Connectivity Field Operations**

- team name
- problem statement ID or title
- submission date

## Slide 2: Problem Statement

- field operations may happen in remote and low-connectivity environments
- attendance or identity verification must work offline
- fraud must be reduced using liveness detection
- solution must stay compact, fast, and easy to integrate into React Native architecture

## Slide 3: Our Solution

- fully offline face recognition and liveness verification
- passive liveness on every verification attempt
- active challenge required before final verification acceptance
- compact ONNX model stack under 20 MB
- designed for later React Native native-module integration

## Slide 4: System Architecture

Show this flow:

`Camera -> Face Detection -> Liveness -> Embedding -> Local Match -> Offline Event Store -> Sync/Purge`

Talking points:

- all inference runs locally
- no cloud dependency during verification
- embeddings are matched against local storage
- attendance events can be queued locally until connectivity returns

## Slide 5: Model Stack

- Detector: `YuNet ONNX`
- Recognizer: `SFace INT8 ONNX`
- Liveness: `MiniFASNetV2 ONNX`

Key message:

- fully open-source compatible path
- compact and CPU-friendly
- suitable for mobile packaging

## Slide 6: Model Size and Efficiency

Show these numbers in large text:

- total model footprint: **paste output from `python app.py profile`**
- hackathon target: **<= 20 MB**
- status: **Pass**

Explain:

- quantized recognizer used to reduce footprint
- lightweight liveness model selected for offline anti-spoofing

## Slide 7: Liveness and Anti-Spoofing

State this clearly:

- passive liveness runs on every verification attempt
- if passive confidence is low, active challenge is triggered
- active challenge uses local motion cues such as slight movement
- this prevents simple fraud using photo or screen replay while keeping normal usage friction low

## Slide 8: Offline Verification Flow

1. camera captures frame locally
2. face detector finds the live user
3. liveness is checked offline
4. face embedding is generated locally
5. embedding is matched against local database
6. result is returned without internet dependency

## Slide 9: Performance Feasibility

Show these numbers:

- detector: `133.96 ms`
- embedding: `14.86 ms`
- liveness model: `11.37 ms`
- estimated end-to-end pipeline: **paste output from `python app.py benchmark --iterations 10`**

Message:

- strong evidence for sub-second feasibility on optimized mobile inference path

## Slide 10: React Native Integration Plan

Explain:

- current prototype is in Python for rapid validation
- final deployment uses the same ONNX models through native mobile inference
- React Native handles UI and data flow
- native Android/iOS modules handle model loading and inference

Recommended mobile API:

```ts
initializeModels()
getModelProfile()
registerFace(userId, frameBytes)
verifyFace(frameBytes)
getPendingEvents()
purgeSyncedRecords()
```

## Slide 11: Offline-to-Online Sync and Purge

Show the lifecycle:

1. event created locally
2. status marked `pending_sync`
3. network returns
4. event pushed to backend
5. success acknowledged
6. synced data purged according to retention rule

This slide supports scalability and sustainability marks.

## Slide 12: Validation Snapshot

Use a simple table:

| Scenario | Current Status |
| --- | --- |
| Indoor lighting | Pass in prototype demo |
| Outdoor lighting | Pass in informal prototype tests |
| Printed photo attack | Blocked or challenged |
| Screen replay attack | Challenged or blocked |
| Model size | Paste from `python app.py profile` |
| Estimated latency | Paste from `python app.py benchmark --iterations 10` |

Add a note:

- final field evaluation on representative Indian demographic data is the next step

## Slide 13: Innovation Highlights

- compact model stack below size budget
- passive liveness on every attempt
- strict active challenge before acceptance
- offline inference path with future mobile deployment alignment

## Slide 14: Current Limitations

- prototype currently runs in Python
- React Native native bridge is the next implementation step
- formal accuracy evaluation on field data is pending
- final mobile-device benchmarking is pending

This honesty builds credibility.

## Slide 15: Conclusion

- core offline recognition and anti-spoofing workflow is validated
- current prototype meets the compact model requirement
- benchmark numbers support feasibility
- next step is productization through React Native native integration

## Demo Sequence

If presenting live or via video, show this order:

1. registration
2. successful offline verification
3. passive liveness pass
4. suspicious interaction triggering active challenge
5. final match result
