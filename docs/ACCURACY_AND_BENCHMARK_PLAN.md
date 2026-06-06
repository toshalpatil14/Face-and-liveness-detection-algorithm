# Accuracy And Benchmark Plan

## Why this is needed

The hackathon asks for:

- `>95%` face recognition accuracy
- reliable performance on Indian demographics
- robust behavior in outdoor lighting
- end-to-end verification under `1 second`

The current repository can estimate footprint and rough model latency, but the final claim must come from structured evaluation.

## Required Evaluation Dimensions

### Demographic coverage

Build an evaluation set that includes:

- different Indian skin tones
- different age groups
- male and female participants
- glasses and non-glasses users
- facial hair and clean-shaven users

### Lighting coverage

Capture samples in:

- indoor normal light
- low light
- harsh sunlight
- side lighting
- shadowed outdoor conditions

### Spoof coverage

Test:

- printed photograph
- phone screen replay
- tablet screen replay
- partial occlusion attempts

## Recognition Metrics

Measure:

- verification accuracy
- false accept rate
- false reject rate
- cosine similarity separation between genuine and impostor pairs

## Liveness Metrics

Measure:

- live accuracy
- spoof accuracy
- APCER
- BPCER
- ACER

## Performance Metrics

Run on actual target devices and report:

- cold start model load time
- average verification latency
- p95 verification latency
- memory usage during inference
- package footprint

## Minimum Device Test Matrix

At least:

- one Android mid-range device with 3 GB RAM
- one Android 4 GB RAM device
- one iPhone on iOS 12+ or later-compatible equivalent

## Repo Commands

Current repo commands:

```powershell
python app.py profile
python app.py benchmark --iterations 20
python register.py --name "Bhavesh"
python verify.py
```

## Honest Benchmarking Note

`python app.py benchmark` gives only rough local inference timing on the development machine. Final submission numbers must come from the target mobile devices.
