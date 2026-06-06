# Validation Summary

This document is designed for quick reuse in the final presentation, PDF, or submission note.

## Metrics To Verify Before Final Submission

Run these commands after adding the `models/` folder and building/running the package:

| Metric | Value | Source |
| --- | --- | --- |
| Total model footprint | Verify locally | `python app.py profile` |
| Meets 20 MB target | Verify locally | `python app.py profile` |
| React Native compatibility evidence | Present as bridge contract | `react-native-compat/` |
| Detector latency | Verify locally | `python app.py benchmark --iterations 10` |
| Embedding latency | Verify locally | `python app.py benchmark --iterations 10` |
| Liveness latency | Verify locally | `python app.py benchmark --iterations 10` |
| Estimated pipeline latency | Verify locally | `python app.py benchmark --iterations 10` |

## Submission-Friendly Validation Table

| Test Area | Current Status | How To Explain It |
| --- | --- | --- |
| Offline inference | Pass | All recognition and liveness logic run locally without internet |
| Model size constraint | Prepared | Add ONNX files in `models/`, then confirm with `python app.py profile` |
| Basic liveness detection | Pass | Passive liveness runs on every attempt and strict mode requires an active challenge before final acceptance |
| Printed photo spoof attempt | Expected blocked/challenged | Photo-based fraud should fail passive liveness or trigger active challenge |
| Screen replay spoof attempt | Expected challenged/blocked | Replay attacks should trigger active validation or fail liveness |
| Mid-range device feasibility | Prototype indicator | Use benchmark output as desktop evidence; mobile device benchmark remains pending |
| React Native integration readiness | Partial | `react-native-compat/` displays Android/iOS bridge contract; full app build remains pending |
| Offline sync/purge workflow | Working prototype | Verification events are queued locally, synced to a backend sink file, retried on failure, and purged after sync |
| Demographic and lighting validation | Pending formal study | Must be validated on representative Indian field samples for final claim |

## Recommended Judge-Facing Wording

Use this wording consistently:

`Our submission mode performs passive liveness on every verification attempt and requires an active challenge before final acceptance. This strengthens protection against photo and screen replay attacks while keeping the enforcement policy explicit.`

## Honest Boundaries

These points should be stated clearly:

- current implementation is a validated prototype
- final React Native app packaging is not included
- mobile-device benchmarking is the next validation step
- structured field accuracy evaluation is still pending
- model-size claims must be verified after the `models/` folder is restored

## Quick Copy for Submission Note

`The current prototype validates end-to-end offline face recognition, active liveness, local event queueing, sync, and purge behavior. The React Native compatibility folder shows the Android/iOS native module boundary for Datalake 3.0 integration. Final model-size, mobile latency, and field-accuracy numbers should be confirmed after the ONNX model files and target devices are available.`
