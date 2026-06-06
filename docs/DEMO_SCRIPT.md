# Demo Script

Use this for your screen recording or live presentation.

## Demo Goal

Show that the solution:

- works offline
- performs face recognition locally
- uses anti-spoofing on every attempt
- stays compact and fast
- can fit into a React Native deployment path

## Demo Sequence

### Part 1: Open with results

Say:

`Our solution is an offline face recognition and liveness prototype designed for remote field operations. The package includes commands to verify model footprint and benchmark latency locally, and the React Native compatibility layer shows how the same workflow maps to Android and iOS native modules.`

### Part 2: Show model profile

Run:

```powershell
python app.py profile
```

Explain:

- detector, recognizer, and liveness model are all local
- total size is under the target
- stack is ready for mobile-oriented packaging

### Part 3: Show registration

Run:

```powershell
python register.py --name "Demo User"
```

Explain:

- the face embedding is generated and stored locally
- no internet is required

### Part 4: Show normal verification

Run:

```powershell
python verify.py
```

Explain:

- passive liveness is checked on every verification attempt
- when the user behaves normally and confidence is high, verification completes smoothly

### Part 5: Explain suspicious attempt handling

Say:

`If passive confidence becomes low or the interaction looks suspicious, the system escalates to an active challenge instead of blindly accepting the face.`

Explain:

- slight movement challenge
- same-face consistency check
- stronger protection against photo and screen replay fraud

### Part 6: Show benchmark

Run:

```powershell
python app.py benchmark --iterations 10
```

Explain:

- run `python app.py benchmark --iterations 10` to capture current prototype latency
- this supports sub-second feasibility for optimized mobile deployment

### Part 7: Close with integration path

Say:

`The current implementation validates the end-to-end offline logic in Python. The next step is to move the same ONNX inference path into native Android and iOS modules and expose it to the existing React Native architecture.`

### Part 8: Show sync and purge reliability

Run:

```powershell
python app.py queue-status
python app.py list-events
python app.py sync-events
python app.py purge-events
```

Explain:

- verification events are first stored locally as `pending_sync`
- sync moves them into the remote sink representation
- purge removes already-synced local entries to keep device storage clean
- this is the same lifecycle that would later point to AWS or another backend

## Key Lines To Repeat

- passive liveness runs on every verification attempt
- active challenge is triggered when confidence is low
- all core verification logic works offline
- model footprint should be copied from `python app.py profile` after `models/` is restored
- estimated pipeline latency should be copied from `python app.py benchmark --iterations 10`
- React Native integration is the next deployment step
