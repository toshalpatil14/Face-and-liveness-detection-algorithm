export type ModelProfile = {
  detectorModel: string | null;
  recognizerModel: string | null;
  livenessModel: string | null;
  totalBytes: number;
  meetsTarget: boolean;
  backend: string;
};

export type RegisterResult = {
  personId: string;
  name: string;
  backend: string;
};

export type VerifyResult = {
  matched: boolean;
  name: string | null;
  score: number;
  percentage: number;
  confidenceBand: "Low" | "Medium" | "High";
  livenessPassed: boolean;
  riskLevel: "Low" | "Medium" | "High";
  challengeRequired: boolean;
  eventId: string | null;
  message: string;
};

export type PendingEvent = {
  eventId: string;
  createdAt: number;
  personName: string | null;
  matched: boolean;
  syncState: "pending_sync" | "synced" | "failed";
  retryCount: number;
};

export interface OfflineFaceModule {
  initializeModels(): Promise<void>;
  getModelProfile(): Promise<ModelProfile>;
  registerFace(name: string, frameBytes: Uint8Array): Promise<RegisterResult>;
  verifyFace(frameBytes: Uint8Array, requireActiveChallenge: boolean): Promise<VerifyResult>;
  getPendingEvents(): Promise<PendingEvent[]>;
  syncPendingEvents(): Promise<{ syncedNow: number; failedNow: number }>;
  purgeSyncedEvents(): Promise<{ purged: number }>;
}
