import React, { useEffect, useMemo, useState } from "react";
import {
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";
import * as ImagePicker from "expo-image-picker";
import {
  ActiveChallengeType,
  DemoScenario,
  EnrolledUser,
  MobileQueueCounts,
  MobileVerificationResult,
  PendingEvent,
} from "./src/types";
import {
  createEnrollment,
  generateRandomChallenge,
  getEnrollment,
  getModelProfile,
  getQueueCounts,
  getQueuedEvents,
  initializeModels,
  purgeSyncedRecords,
  retryFailedRecords,
  runVerification,
  syncAndPurge,
} from "./src/lib/offlineFaceService";

const scenarios: { id: DemoScenario; title: string; body: string }[] = [
  {
    id: "live_match",
    title: "Live match",
    body: "Expected to pass passive checks and then clear the mandatory active challenge.",
  },
  {
    id: "unknown_user",
    title: "Unknown user",
    body: "Liveness can pass, but identity match should fail after the challenge.",
  },
  {
    id: "replay_attack",
    title: "Replay attack",
    body: "Passive signals may look promising, but strict mode should reject it during challenge flow.",
  },
];

export default function App() {
  const [name, setName] = useState("Demo Field User");
  const [enrolledUser, setEnrolledUser] = useState<EnrolledUser | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<DemoScenario>("live_match");
  const [result, setResult] = useState<MobileVerificationResult | null>(null);
  const [queueCounts, setQueueCounts] = useState<MobileQueueCounts>({
    total: 0,
    pendingSync: 0,
    synced: 0,
    failed: 0,
  });
  const [events, setEvents] = useState<PendingEvent[]>([]);
  const [modelProfile, setModelProfile] = useState<Awaited<ReturnType<typeof getModelProfile>> | null>(null);
  const [syncMessage, setSyncMessage] = useState("Queue idle.");
  const [busy, setBusy] = useState(false);
  const [challenge, setChallenge] = useState<ActiveChallengeType>("blink");
  const [modelsReady, setModelsReady] = useState(false);
  const [selectedEnrollmentImageUri, setSelectedEnrollmentImageUri] = useState<string | null>(null);
  const [selectedVerificationImageUri, setSelectedVerificationImageUri] = useState<string | null>(null);

  async function refreshQueue() {
    const [counts, queueEvents] = await Promise.all([getQueueCounts(), getQueuedEvents()]);
    setQueueCounts(counts);
    setEvents(queueEvents);
  }

  useEffect(() => {
    async function boot() {
      const [profile, storedEnrollment] = await Promise.all([getModelProfile(), getEnrollment()]);
      setModelProfile(profile);
      setEnrolledUser(storedEnrollment);
      try {
        await initializeModels();
        setModelsReady(true);
      } catch (error) {
        setSyncMessage(
          `Model initialization is pending native build setup. ${error instanceof Error ? error.message : "Unknown error."}`,
        );
      }
      await refreshQueue();
    }
    void boot();
  }, []);

  const strictModeText = useMemo(
    () =>
      "Strict liveness mode is enabled. Every verification runs passive liveness and must also clear an active challenge before final acceptance.",
    [],
  );

  async function handleEnroll() {
    setBusy(true);
    try {
      if (!selectedEnrollmentImageUri) {
        setSyncMessage("Select or capture an enrollment image first.");
        return;
      }
      const created = await createEnrollment(name.trim() || "Demo Field User", selectedEnrollmentImageUri);
      setEnrolledUser(created);
      setSyncMessage(`Enrolled ${created.name} locally for offline matching.`);
    } finally {
      setBusy(false);
    }
  }

  async function handleVerify() {
    setBusy(true);
    try {
      const nextChallenge = generateRandomChallenge();
      setChallenge(nextChallenge);
      const verification = await runVerification({
        scenario: selectedScenario,
        enrolledUser,
        imageUri: selectedVerificationImageUri ?? enrolledUser?.imageUri ?? "",
        activeChallengeType: nextChallenge,
      });
      setResult(verification);
      setSyncMessage(`Verification complete. Event ${verification.eventId} queued for sync.`);
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  }

  async function handlePickImage(target: "enrollment" | "verification", source: "camera" | "gallery") {
    setBusy(true);
    try {
      if (source === "camera") {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          setSyncMessage("Camera permission was not granted.");
          return;
        }
        const result = await ImagePicker.launchCameraAsync({
          mediaTypes: ["images"],
          quality: 0.8,
        });
        if (!result.canceled && result.assets[0]?.uri) {
          if (target === "enrollment") {
            setSelectedEnrollmentImageUri(result.assets[0].uri);
            setSyncMessage("Captured a real enrollment image.");
          } else {
            setSelectedVerificationImageUri(result.assets[0].uri);
            setSyncMessage("Captured a real verification image.");
          }
        }
        return;
      }

      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        setSyncMessage("Gallery permission was not granted.");
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        quality: 0.8,
      });
      if (!result.canceled && result.assets[0]?.uri) {
        if (target === "enrollment") {
          setSelectedEnrollmentImageUri(result.assets[0].uri);
          setSyncMessage("Selected a real enrollment image.");
        } else {
          setSelectedVerificationImageUri(result.assets[0].uri);
          setSyncMessage("Selected a real verification image.");
        }
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleSync(simulateFailure: boolean) {
    setBusy(true);
    try {
      const summary = await syncAndPurge({ simulateFailure, keepLocalSyncedCopies: true });
      setSyncMessage(
        simulateFailure
          ? `Simulated failure: ${summary.failedNow} event(s) moved to failed state.`
          : `Synced ${summary.syncedNow} event(s). Remote sink total is now ${summary.remoteTotal}.`,
      );
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  }

  async function handleRetry() {
    setBusy(true);
    try {
      const reset = await retryFailedRecords();
      setSyncMessage(`Moved ${reset} failed event(s) back to pending_sync.`);
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  }

  async function handlePurge() {
    setBusy(true);
    try {
      const removed = await purgeSyncedRecords();
      setSyncMessage(`Purged ${removed} synced local event(s).`);
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ExpoStatusBar style="dark" />
      <StatusBar barStyle="dark-content" />
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.hero}>
          <Text style={styles.eyebrow}>NHAI Hackathon 7.0</Text>
          <Text style={styles.title}>Offline Face Verification Mobile Prototype</Text>
          <Text style={styles.subtitle}>
            A cross-platform React Native shell for strict liveness, offline attendance queueing, and sync/purge flow.
          </Text>
        </View>

        <Card title="Strict Liveness Policy" accent="amber">
          <Text style={styles.body}>{strictModeText}</Text>
          <Text style={styles.metricLine}>Current randomized prompt: {challenge.replace("_", " ")}</Text>
        </Card>

        <Card title="Model Profile" accent="teal">
          <Text style={styles.metricLine}>Footprint: {modelProfile?.totalMb ?? "10.99"} MB</Text>
          <Text style={styles.metricLine}>Latency target story: {modelProfile?.pipelineMs ?? "160.20"} ms prototype path</Text>
          <Text style={styles.metricLine}>Runtime sessions: {modelsReady ? "Initialized" : "Pending native build setup"}</Text>
          <Text style={styles.body}>Stack: YuNet + SFace INT8 + MiniFASNetV2. The native inference bridge is intentionally isolated behind one service contract.</Text>
        </Card>

        <Card title="Offline Enrollment" accent="coral">
          <Text style={styles.label}>Enrolled user name</Text>
          <TextInput
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Enter user name"
            placeholderTextColor="#7d7670"
          />
          <View style={styles.actionRow}>
            <PrimaryButton
              label="Capture Enrollment"
              onPress={() => void handlePickImage("enrollment", "camera")}
              disabled={busy}
              compact
              secondary
            />
            <PrimaryButton
              label="Pick Enrollment"
              onPress={() => void handlePickImage("enrollment", "gallery")}
              disabled={busy}
              compact
              secondary
            />
          </View>
          <Text style={styles.body}>
            Enrollment file: {selectedEnrollmentImageUri ?? "No enrollment image selected yet"}
          </Text>
          <PrimaryButton
            label={busy ? "Working..." : "Enroll User"}
            onPress={handleEnroll}
            disabled={busy || !selectedEnrollmentImageUri}
          />
          {enrolledUser ? (
            <Text style={styles.successText}>
              Enrolled: {enrolledUser.name} ({enrolledUser.userId})
            </Text>
          ) : null}
          {!selectedEnrollmentImageUri ? <Text style={styles.warningText}>Select an enrollment image first.</Text> : null}
        </Card>

        <Card title="Verification Demo" accent="slate">
          <Text style={styles.body}>Choose the scenario you want to demonstrate to judges. All scenarios enforce the active challenge before final decision.</Text>
          <View style={styles.scenarioList}>
            {scenarios.map((scenario) => (
              <Pressable
                key={scenario.id}
                onPress={() => setSelectedScenario(scenario.id)}
                style={[
                  styles.scenarioCard,
                  selectedScenario === scenario.id ? styles.scenarioCardActive : null,
                ]}
              >
                <Text style={styles.scenarioTitle}>{scenario.title}</Text>
                <Text style={styles.scenarioBody}>{scenario.body}</Text>
              </Pressable>
            ))}
          </View>
          <View style={styles.actionRow}>
            <PrimaryButton
              label="Capture Image"
              onPress={() => void handlePickImage("verification", "camera")}
              disabled={busy}
              compact
              secondary
            />
            <PrimaryButton
              label="Pick From Gallery"
              onPress={() => void handlePickImage("verification", "gallery")}
              disabled={busy}
              compact
              secondary
            />
          </View>
          <Text style={styles.body}>
            Verification file: {selectedVerificationImageUri ?? enrolledUser?.imageUri ?? "No verification image selected yet"}
          </Text>
          <PrimaryButton
            label={busy ? "Working..." : "Run Strict Verification"}
            onPress={handleVerify}
            disabled={busy || !enrolledUser || !(selectedVerificationImageUri ?? enrolledUser?.imageUri)}
          />
          {!enrolledUser ? <Text style={styles.warningText}>Enroll a user first to demo identity matching.</Text> : null}
          {!(selectedVerificationImageUri ?? enrolledUser?.imageUri) ? <Text style={styles.warningText}>Capture or pick a real verification image before verification.</Text> : null}
          {result ? (
            <View style={styles.resultBox}>
              <Text style={styles.resultHeadline}>{result.decisionLabel}</Text>
              <Text style={styles.metricLine}>Challenge: {result.activeChallengeType.replace("_", " ")}</Text>
              <Text style={styles.metricLine}>Passive liveness: {result.passiveLiveScore.toFixed(2)}</Text>
              <Text style={styles.metricLine}>Active challenge: {result.activeChallengePassed ? "Passed" : "Failed"}</Text>
              <Text style={styles.metricLine}>Identity match: {result.matchFound ? result.matchedUserId : "No match"}</Text>
              <Text style={styles.metricLine}>Similarity: {(result.similarity * 100).toFixed(1)}%</Text>
              <Text style={styles.body}>{result.message}</Text>
            </View>
          ) : null}
        </Card>

        <Card title="Offline Queue, Sync, and Purge" accent="olive">
          <View style={styles.countGrid}>
            <CountBadge label="Total" value={queueCounts.total} />
            <CountBadge label="Pending" value={queueCounts.pendingSync} />
            <CountBadge label="Synced" value={queueCounts.synced} />
            <CountBadge label="Failed" value={queueCounts.failed} />
          </View>
          <Text style={styles.body}>{syncMessage}</Text>
          <View style={styles.actionRow}>
            <PrimaryButton label="Sync Pending" onPress={() => void handleSync(false)} disabled={busy} compact />
            <PrimaryButton label="Simulate Failure" onPress={() => void handleSync(true)} disabled={busy} compact secondary />
          </View>
          <View style={styles.actionRow}>
            <PrimaryButton label="Retry Failed" onPress={() => void handleRetry()} disabled={busy} compact secondary />
            <PrimaryButton label="Purge Synced" onPress={() => void handlePurge()} disabled={busy} compact secondary />
          </View>
          <View style={styles.queueList}>
            {events.map((event) => (
              <View key={event.eventId} style={styles.queueItem}>
                <Text style={styles.queueTitle}>{event.eventType.toUpperCase()} · {event.syncState}</Text>
                <Text style={styles.queueBody}>
                  {event.personName ?? "Unknown"} · {event.matchFound ? "Matched" : "No match"} · {event.activeChallengePassed ? "Challenge passed" : "Challenge failed"}
                </Text>
              </View>
            ))}
            {events.length === 0 ? <Text style={styles.body}>No queued events yet.</Text> : null}
          </View>
        </Card>

        <Card title="Native Bridge Boundary" accent="ink">
          <Text style={styles.body}>
            This app is already structured around a single inference service. The service layer now attempts to boot real ONNX Runtime sessions from bundled assets and accepts saved file URIs instead of risky live frame buffers.
          </Text>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function Card({
  title,
  accent,
  children,
}: {
  title: string;
  accent: "amber" | "teal" | "coral" | "slate" | "olive" | "ink";
  children: React.ReactNode;
}) {
  return (
    <View style={[styles.card, accentStyles[accent]]}>
      <Text style={styles.cardTitle}>{title}</Text>
      {children}
    </View>
  );
}

function PrimaryButton({
  label,
  onPress,
  disabled,
  compact,
  secondary,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  compact?: boolean;
  secondary?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.button,
        compact ? styles.buttonCompact : null,
        secondary ? styles.buttonSecondary : null,
        disabled ? styles.buttonDisabled : null,
      ]}
    >
      <Text style={[styles.buttonText, secondary ? styles.buttonTextSecondary : null]}>{label}</Text>
    </Pressable>
  );
}

function CountBadge({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.countBadge}>
      <Text style={styles.countValue}>{value}</Text>
      <Text style={styles.countLabel}>{label}</Text>
    </View>
  );
}

const accentStyles = StyleSheet.create({
  amber: { borderTopColor: "#d97706" },
  teal: { borderTopColor: "#0f766e" },
  coral: { borderTopColor: "#c2410c" },
  slate: { borderTopColor: "#334155" },
  olive: { borderTopColor: "#4d7c0f" },
  ink: { borderTopColor: "#1f2937" },
});

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f4efe7",
  },
  container: {
    padding: 20,
    paddingBottom: 44,
    gap: 16,
  },
  hero: {
    backgroundColor: "#fef8ee",
    borderRadius: 24,
    padding: 24,
    borderWidth: 1,
    borderColor: "#e7dccd",
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.2,
    color: "#8a5a1f",
    textTransform: "uppercase",
    marginBottom: 8,
  },
  title: {
    fontSize: 30,
    lineHeight: 36,
    fontWeight: "800",
    color: "#1f2937",
  },
  subtitle: {
    marginTop: 12,
    fontSize: 15,
    lineHeight: 22,
    color: "#4b5563",
  },
  card: {
    backgroundColor: "#fffdfa",
    borderRadius: 22,
    padding: 18,
    borderWidth: 1,
    borderColor: "#e8ddd1",
    borderTopWidth: 5,
    gap: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#16202d",
  },
  body: {
    fontSize: 14,
    lineHeight: 21,
    color: "#4b5563",
  },
  metricLine: {
    fontSize: 14,
    lineHeight: 21,
    color: "#16202d",
    fontWeight: "700",
  },
  label: {
    fontSize: 13,
    fontWeight: "700",
    color: "#46505b",
  },
  input: {
    borderWidth: 1,
    borderColor: "#d9cec2",
    borderRadius: 14,
    backgroundColor: "#fffaf4",
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: "#1f2937",
  },
  button: {
    backgroundColor: "#1f2937",
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 16,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonCompact: {
    flex: 1,
  },
  buttonSecondary: {
    backgroundColor: "#edf1f5",
  },
  buttonDisabled: {
    opacity: 0.55,
  },
  buttonText: {
    color: "#fffdf9",
    fontSize: 14,
    fontWeight: "800",
  },
  buttonTextSecondary: {
    color: "#1f2937",
  },
  successText: {
    fontSize: 13,
    color: "#166534",
    fontWeight: "700",
  },
  warningText: {
    fontSize: 13,
    color: "#b45309",
    fontWeight: "700",
  },
  scenarioList: {
    gap: 10,
  },
  scenarioCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#d6dbe2",
    backgroundColor: "#f7f9fb",
    padding: 14,
    gap: 6,
  },
  scenarioCardActive: {
    borderColor: "#1f2937",
    backgroundColor: "#eef3f7",
  },
  scenarioTitle: {
    fontSize: 14,
    fontWeight: "800",
    color: "#1f2937",
  },
  scenarioBody: {
    fontSize: 13,
    lineHeight: 18,
    color: "#5b6572",
  },
  resultBox: {
    borderRadius: 16,
    backgroundColor: "#f8f3eb",
    padding: 14,
    gap: 6,
  },
  resultHeadline: {
    fontSize: 16,
    fontWeight: "800",
    color: "#1f2937",
  },
  countGrid: {
    flexDirection: "row",
    gap: 10,
    flexWrap: "wrap",
  },
  countBadge: {
    minWidth: 72,
    backgroundColor: "#faf6ef",
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 10,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e4dacc",
  },
  countValue: {
    fontSize: 20,
    fontWeight: "800",
    color: "#1f2937",
  },
  countLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#66707d",
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
  },
  queueList: {
    gap: 10,
  },
  queueItem: {
    borderRadius: 14,
    backgroundColor: "#f7f2ea",
    padding: 12,
    borderWidth: 1,
    borderColor: "#e3d8cc",
  },
  queueTitle: {
    fontSize: 13,
    fontWeight: "800",
    color: "#243041",
  },
  queueBody: {
    marginTop: 4,
    fontSize: 12,
    lineHeight: 18,
    color: "#5f6b78",
  },
});
