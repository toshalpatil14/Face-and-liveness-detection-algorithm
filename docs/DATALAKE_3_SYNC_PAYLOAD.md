# Datalake 3.0 Sync Payload

Use this as the host-app contract example for NHAI Datalake 3.0 integration.

## Mobile Bridge Contract

The host React Native app can call a verification module shaped like this:

```ts
initializeModels(): Promise<void>
verifyPersonnel(imageUri: string, activeChallengeType: "blink" | "smile" | "turn_head"): Promise<MobileVerificationResult>
getQueuedEvents(): Promise<PendingEvent[]>
syncAndPurge(): Promise<SyncSummary>
```

## Attendance Record Payload Example

```json
{
  "eventId": "evt_1717601000000",
  "eventType": "attendance",
  "userId": "field_1717600000000",
  "personName": "Demo Field User",
  "matchFound": true,
  "similarity": 0.88,
  "passiveLiveScore": 0.91,
  "activeChallengeType": "blink",
  "activeChallengePassed": true,
  "challengeIssuedAt": 1717601000123,
  "challengeEvaluatedAt": 1717601000820,
  "syncState": "pending_sync",
  "deviceMode": "offline",
  "capturedAt": "2026-06-05T09:10:00.000Z"
}
```

## Sync Lifecycle

1. Verification succeeds offline.
2. Event is stored locally with `pending_sync`.
3. Datalake host app detects connectivity.
4. Records are pushed to backend.
5. On successful acknowledgement, local event state changes to `synced`.
6. `syncAndPurge()` removes synced local entries.

## Why This Fits Datalake 3.0

- React Native friendly
- clean offline-first queue
- explicit sync state
- strict purge after successful transmission
- challenge and liveness metadata preserved for auditability
