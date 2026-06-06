from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import random
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SOURCE_DIR = Path(__file__).resolve().parent
_RUNTIME_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else _SOURCE_DIR
os.environ.setdefault("MPLCONFIGDIR", str((_RUNTIME_DIR / ".cache" / "matplotlib")))

import cv2
import numpy as np
import onnxruntime as ort


def _asset_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _SOURCE_DIR


ASSET_BASE_DIR = _asset_base_dir()
RUNTIME_BASE_DIR = _runtime_base_dir()
DATABASE_DIR = RUNTIME_BASE_DIR / "database"
EMBEDDINGS_PATH = DATABASE_DIR / "embeddings.pkl"
EVENTS_PATH = DATABASE_DIR / "events.json"
SYNC_SINK_PATH = DATABASE_DIR / "synced_events.json"
MODELS_DIR = ASSET_BASE_DIR / "models"

SFACE_MODEL = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
SFACE_INT8_MODEL = MODELS_DIR / "face_recognition_sface_2021dec_int8bq.onnx"
YUNET_MODEL = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
MOBILEFACE_MODEL = MODELS_DIR / "face_recognition_mobilefacenet_int8.onnx"
MINIFASNET_MODEL = MODELS_DIR / "liveness_minifasnet_v2.onnx"

HAAR_MODEL = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
HAAR_ALT_MODEL = Path(cv2.data.haarcascades) / "haarcascade_frontalface_alt.xml"
HAAR_ALT2_MODEL = Path(cv2.data.haarcascades) / "haarcascade_frontalface_alt2.xml"
EYE_MODEL = Path(cv2.data.haarcascades) / "haarcascade_eye.xml"
MODEL_TARGET_BYTES = 20 * 1024 * 1024


@dataclass
class FaceRecord:
    person_id: str
    name: str
    embedding: List[float]
    backend: str
    created_at: float


@dataclass
class VerificationResult:
    matched: bool
    name: Optional[str]
    score: float
    percentage: float
    threshold: float
    confidence_band: str
    backend: str
    liveness_passed: bool
    risk_level: str
    challenge_required: bool
    message: str
    event_id: Optional[str] = None


@dataclass
class AttendanceEvent:
    event_id: str
    event_type: str
    created_at: float
    person_name: Optional[str]
    matched: bool
    score: float
    percentage: float
    backend: str
    liveness_passed: bool
    risk_level: str
    challenge_required: bool
    device_mode: str
    sync_state: str
    synced_at: Optional[float]
    retry_count: int
    last_error: Optional[str]
    message: str


@dataclass
class SyncSummary:
    total_pending: int
    synced_now: int
    failed_now: int
    remote_total: int


@dataclass
class ModelProfile:
    detector_model: Optional[str]
    recognizer_model: Optional[str]
    liveness_model: Optional[str]
    backend: str
    detector_bytes: int
    recognizer_bytes: int
    liveness_bytes: int
    total_bytes: int
    meets_target: bool
    react_native_ready: bool
    note: str


@dataclass
class LiveSessionResult:
    passed: bool
    frame: Optional[np.ndarray]
    risk_level: str
    challenge_required: bool
    message: str


class EmbeddingStore:
    def __init__(self, path: Path = EMBEDDINGS_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            self._write({"version": 1, "records": []})

    def _read(self) -> Dict[str, Any]:
        with self.path.open("rb") as handle:
            return pickle.load(handle)

    def _write(self, payload: Dict[str, Any]) -> None:
        with self.path.open("wb") as handle:
            pickle.dump(payload, handle)

    def list_records(self) -> List[FaceRecord]:
        payload = self._read()
        return [FaceRecord(**record) for record in payload.get("records", [])]

    def add_record(self, record: FaceRecord) -> None:
        payload = self._read()
        payload.setdefault("records", []).append(asdict(record))
        self._write(payload)


class EventStore:
    def __init__(self, path: Path = EVENTS_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            self._write({"version": 1, "events": []})

    def _read(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def list_events(self) -> List[AttendanceEvent]:
        payload = self._read()
        return [AttendanceEvent(**event) for event in payload.get("events", [])]

    def add_event(self, event: AttendanceEvent) -> None:
        payload = self._read()
        payload.setdefault("events", []).append(asdict(event))
        self._write(payload)

    def replace_events(self, events: List[AttendanceEvent]) -> None:
        self._write({"version": 1, "events": [asdict(event) for event in events]})

    def counts(self) -> Dict[str, int]:
        events = self.list_events()
        return {
            "total": len(events),
            "pending_sync": sum(event.sync_state == "pending_sync" for event in events),
            "synced": sum(event.sync_state == "synced" for event in events),
            "failed": sum(event.sync_state == "failed" for event in events),
        }


class SyncSink:
    def __init__(self, path: Path = SYNC_SINK_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            self._write({"version": 1, "events": []})

    def _read(self) -> Dict[str, Any]:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def append_events(self, events: List[AttendanceEvent]) -> int:
        payload = self._read()
        bucket = payload.setdefault("events", [])
        existing_ids = {item.get("event_id") for item in bucket}
        for event in events:
            if event.event_id not in existing_ids:
                bucket.append(asdict(event))
                existing_ids.add(event.event_id)
        self._write(payload)
        return len(bucket)


class SyncManager:
    def __init__(self, store: Optional[EventStore] = None, sink: Optional[SyncSink] = None) -> None:
        self.store = store or EventStore()
        self.sink = sink or SyncSink()

    def queue_verification_event(self, result: VerificationResult, event_type: str = "attendance") -> AttendanceEvent:
        event = AttendanceEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            created_at=time.time(),
            person_name=result.name,
            matched=result.matched,
            score=result.score,
            percentage=result.percentage,
            backend=result.backend,
            liveness_passed=result.liveness_passed,
            risk_level=result.risk_level,
            challenge_required=result.challenge_required,
            device_mode="offline",
            sync_state="pending_sync",
            synced_at=None,
            retry_count=0,
            last_error=None,
            message=result.message,
        )
        self.store.add_event(event)
        result.event_id = event.event_id
        return event

    def list_pending_events(self) -> List[AttendanceEvent]:
        return [event for event in self.store.list_events() if event.sync_state == "pending_sync"]

    def sync_pending_events(self, simulate_failure: bool = False) -> SyncSummary:
        events = self.store.list_events()
        pending = [event for event in events if event.sync_state == "pending_sync"]
        if not pending:
            remote_total = len(self.sink._read().get("events", []))
            return SyncSummary(total_pending=0, synced_now=0, failed_now=0, remote_total=remote_total)

        synced_now = 0
        failed_now = 0
        now = time.time()
        batch: List[AttendanceEvent] = []
        for event in pending:
            if simulate_failure:
                event.sync_state = "failed"
                event.retry_count += 1
                event.last_error = "Simulated network failure."
                failed_now += 1
                continue
            event.sync_state = "synced"
            event.synced_at = now
            event.last_error = None
            batch.append(event)
            synced_now += 1

        if batch:
            remote_total = self.sink.append_events(batch)
        else:
            remote_total = len(self.sink._read().get("events", []))

        self.store.replace_events(events)
        return SyncSummary(
            total_pending=len(pending),
            synced_now=synced_now,
            failed_now=failed_now,
            remote_total=remote_total,
        )

    def retry_failed_events(self) -> int:
        events = self.store.list_events()
        reset = 0
        for event in events:
            if event.sync_state == "failed":
                event.sync_state = "pending_sync"
                event.last_error = None
                reset += 1
        self.store.replace_events(events)
        return reset

    def purge_synced_events(self) -> int:
        events = self.store.list_events()
        kept = [event for event in events if event.sync_state != "synced"]
        removed = len(events) - len(kept)
        self.store.replace_events(kept)
        return removed


class OfflineFaceEngine:
    def __init__(self) -> None:
        self.store = EmbeddingStore()
        self.event_store = EventStore()
        self._haars = [
            cv2.CascadeClassifier(str(HAAR_MODEL)),
            cv2.CascadeClassifier(str(HAAR_ALT_MODEL)),
            cv2.CascadeClassifier(str(HAAR_ALT2_MODEL)),
        ]
        self._sface = None
        self._mobileface = None
        self._yunet = None
        self.backend = "lbp_histogram"
        self._try_init_models()

    def _try_init_models(self) -> None:
        if MOBILEFACE_MODEL.exists():
            self._mobileface = cv2.dnn.readNetFromONNX(str(MOBILEFACE_MODEL))
            self.backend = "mobilefacenet_int8"
        elif SFACE_INT8_MODEL.exists():
            self._sface = cv2.FaceRecognizerSF_create(str(SFACE_INT8_MODEL), "")
            self.backend = "sface_int8"
        elif SFACE_MODEL.exists():
            self._sface = cv2.FaceRecognizerSF_create(str(SFACE_MODEL), "")
            self.backend = "sface"
        if YUNET_MODEL.exists():
            self._yunet = cv2.FaceDetectorYN_create(
                str(YUNET_MODEL),
                "",
                (320, 320),
                score_threshold=0.85,
                nms_threshold=0.3,
                top_k=5000,
            )

    def detect_face_data(self, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        if self._yunet is not None:
            height, width = frame.shape[:2]
            self._yunet.setInputSize((width, height))
            _, detections = self._yunet.detect(frame)
            if detections is not None and len(detections) > 0:
                best = max(detections, key=lambda row: float(row[2] * row[3]))
                x, y, w, h = best[:4].astype(int)
                return {
                    "box": self._clip_box(x, y, w, h, width, height),
                    "yunet_face": best.astype(np.float32),
                }

        box = self._detect_face_with_haar(frame)
        if box is None:
            return None
        return {"box": box, "yunet_face": None}

    def detect_face(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        face_data = self.detect_face_data(frame)
        return None if face_data is None else face_data["box"]

    def _detect_face_with_haar(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variants = [
            gray,
            cv2.equalizeHist(gray),
            cv2.GaussianBlur(cv2.equalizeHist(gray), (5, 5), 0),
        ]

        best_box = None
        best_area = 0
        min_face = max(60, min(frame.shape[0], frame.shape[1]) // 8)

        for cascade in self._haars:
            if cascade.empty():
                continue
            for variant in variants:
                faces = cascade.detectMultiScale(
                    variant,
                    scaleFactor=1.08,
                    minNeighbors=3,
                    minSize=(min_face, min_face),
                )
                for x, y, w, h in faces:
                    area = int(w * h)
                    if area > best_area:
                        best_box = (int(x), int(y), int(w), int(h))
                        best_area = area

        if best_box is None:
            return None

        x, y, w, h = best_box
        pad_w = int(w * 0.12)
        pad_h = int(h * 0.18)
        return self._clip_box(
            x - pad_w,
            y - pad_h,
            w + 2 * pad_w,
            h + 2 * pad_h,
            frame.shape[1],
            frame.shape[0],
        )

    @staticmethod
    def _clip_box(x: int, y: int, w: int, h: int, width: int, height: int) -> Tuple[int, int, int, int]:
        x = max(0, x)
        y = max(0, y)
        w = min(w, width - x)
        h = min(h, height - y)
        return x, y, w, h

    def extract_embedding(self, frame: np.ndarray, face_box: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        detected = None if face_box is not None else self.detect_face_data(frame)
        box = face_box or (detected["box"] if detected is not None else None) or self._fallback_center_crop(frame)
        if box is None:
            raise ValueError("No face detected in frame.")

        x, y, w, h = box
        face = frame[y : y + h, x : x + w]
        if face.size == 0:
            raise ValueError("Detected face crop is empty.")

        if min(w, h) < 50:
            raise ValueError("Detected face is too small. Move closer to the camera.")

        if self._mobileface is not None:
            return self._mobilefacenet_embedding(face)

        if self._sface is not None:
            if detected is not None and detected.get("yunet_face") is not None:
                aligned = self._sface.alignCrop(frame, detected["yunet_face"])
            else:
                aligned = cv2.resize(face, (112, 112))
            embedding = self._sface.feature(aligned)
            embedding = embedding.flatten().astype(np.float32)
            norm = np.linalg.norm(embedding)
            return embedding if norm == 0 else embedding / norm

        return self._lbp_histogram_embedding(face)

    def _mobilefacenet_embedding(self, face: np.ndarray) -> np.ndarray:
        resized = cv2.resize(face, (112, 112))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        blob = cv2.dnn.blobFromImage(
            rgb,
            scalefactor=1.0 / 127.5,
            size=(112, 112),
            mean=(127.5, 127.5, 127.5),
            swapRB=False,
            crop=False,
        )
        self._mobileface.setInput(blob)
        embedding = self._mobileface.forward().flatten().astype(np.float32)
        norm = np.linalg.norm(embedding)
        return embedding if norm == 0 else embedding / norm

    @staticmethod
    def _fallback_center_crop(frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        height, width = frame.shape[:2]
        crop_w = int(width * 0.42)
        crop_h = int(height * 0.58)
        if crop_w < 50 or crop_h < 50:
            return None
        x = (width - crop_w) // 2
        y = max(0, int(height * 0.16))
        if y + crop_h > height:
            crop_h = height - y
        return x, y, crop_w, crop_h

    def register_frame(self, name: str, frame: np.ndarray) -> FaceRecord:
        embedding = self.extract_embedding(frame)
        person_id = f"{name.lower().replace(' ', '_')}_{int(time.time())}"
        record = FaceRecord(
            person_id=person_id,
            name=name,
            embedding=embedding.tolist(),
            backend=self.backend,
            created_at=time.time(),
        )
        self.store.add_record(record)
        return record

    def identify_frame(self, frame: np.ndarray, liveness_passed: bool = True) -> VerificationResult:
        records = self.store.list_records()
        active_records = [record for record in records if record.backend == self.backend]
        if not records:
            return VerificationResult(
                matched=False,
                name=None,
                score=0.0,
                percentage=0.0,
                threshold=0.0,
                confidence_band="Low",
                backend=self.backend,
                liveness_passed=True,
                risk_level="Low",
                challenge_required=False,
                message="No registered identities found.",
            )
        if not active_records:
            return VerificationResult(
                matched=False,
                name=None,
                score=0.0,
                percentage=0.0,
                threshold=0.0,
                confidence_band="Low",
                backend=self.backend,
                liveness_passed=True,
                risk_level="Low",
                challenge_required=False,
                message=f"No registrations found for active backend '{self.backend}'. Please register again.",
            )

        probe = self.extract_embedding(frame)
        best_name = None
        best_score = -1.0

        for record in active_records:
            candidate = np.asarray(record.embedding, dtype=np.float32)
            score = self._compare_embeddings(probe, candidate)
            if score > best_score:
                best_score = score
                best_name = record.name

        threshold = 0.50 if self.backend in {"sface", "sface_int8", "mobilefacenet_int8"} else 0.82
        matched = best_score >= threshold and best_name is not None
        percentage = float(max(0.0, min(100.0, best_score * 100.0)))
        confidence_band = self._confidence_band(percentage, matched)
        message = "Verified successfully." if matched else "Face not recognized with enough confidence."
        return VerificationResult(
            matched=matched,
            name=best_name if matched else None,
            score=float(best_score),
            percentage=percentage,
            threshold=float(threshold),
            confidence_band=confidence_band,
            backend=self.backend,
            liveness_passed=True,
            risk_level="Low",
            challenge_required=False,
            message=message,
        )

    def _compare_embeddings(self, probe: np.ndarray, candidate: np.ndarray) -> float:
        if self.backend in {"sface", "sface_int8", "mobilefacenet_int8"}:
            probe_norm = np.linalg.norm(probe)
            candidate_norm = np.linalg.norm(candidate)
            if probe_norm == 0 or candidate_norm == 0:
                return 0.0
            return float(np.dot(probe, candidate) / (probe_norm * candidate_norm))

        distance = cv2.compareHist(
            probe.astype(np.float32),
            candidate.astype(np.float32),
            cv2.HISTCMP_BHATTACHARYYA,
        )
        return float(max(0.0, 1.0 - distance))

    @staticmethod
    def _lbp_histogram_embedding(face: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        gray = cv2.resize(gray, (128, 128))

        center = gray[1:-1, 1:-1]
        lbp = np.zeros_like(center, dtype=np.uint8)
        offsets = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
            (1, 0),
            (1, -1),
            (0, -1),
        ]
        for bit, (dy, dx) in enumerate(offsets):
            neighbor = gray[1 + dy : gray.shape[0] - 1 + dy, 1 + dx : gray.shape[1] - 1 + dx]
            lbp |= ((neighbor >= center) << bit).astype(np.uint8)

        hist = cv2.calcHist([lbp], [0], None, [256], [0, 256]).flatten()
        hist /= (hist.sum() + 1e-6)
        return hist.astype(np.float32)

    @staticmethod
    def _model_size(path: Path) -> int:
        return path.stat().st_size if path.exists() else 0

    @staticmethod
    def _confidence_band(percentage: float, matched: bool) -> str:
        if not matched:
            if percentage >= 45.0:
                return "Medium"
            return "Low"
        if percentage >= 80.0:
            return "High"
        if percentage >= 65.0:
            return "Medium"
        return "Low"

    def get_model_profile(self) -> ModelProfile:
        detector_name = YUNET_MODEL.name if YUNET_MODEL.exists() else None
        if self.backend == "mobilefacenet_int8":
            recognizer_name = MOBILEFACE_MODEL.name
            note = "Preferred mobile profile. Intended for React Native native-module integration via ONNX Runtime Mobile."
        elif self.backend == "sface_int8":
            recognizer_name = SFACE_INT8_MODEL.name
            note = "Compact official SFace profile. Strong submission base when paired with a compact learned liveness model."
        elif self.backend == "sface":
            recognizer_name = SFACE_MODEL.name
            note = "Prototype profile. Accurate, but the recognizer alone is above the 20 MB hackathon target."
        else:
            recognizer_name = None
            note = "Fallback prototype only. Not suitable for the >95% target or production mobile deployment."

        detector_bytes = self._model_size(YUNET_MODEL)
        if self.backend == "mobilefacenet_int8":
            recognizer_path = MOBILEFACE_MODEL
        elif self.backend == "sface_int8":
            recognizer_path = SFACE_INT8_MODEL
        else:
            recognizer_path = SFACE_MODEL
        recognizer_bytes = self._model_size(recognizer_path)
        liveness_bytes = self._model_size(MINIFASNET_MODEL)
        total = detector_bytes + recognizer_bytes + liveness_bytes
        react_native_ready = (
            self.backend in {"mobilefacenet_int8", "sface_int8"}
            and YUNET_MODEL.exists()
            and MINIFASNET_MODEL.exists()
        )

        return ModelProfile(
            detector_model=detector_name,
            recognizer_model=recognizer_name,
            liveness_model=MINIFASNET_MODEL.name if MINIFASNET_MODEL.exists() else None,
            backend=self.backend,
            detector_bytes=detector_bytes,
            recognizer_bytes=recognizer_bytes,
            liveness_bytes=liveness_bytes,
            total_bytes=total,
            meets_target=total > 0 and total <= MODEL_TARGET_BYTES,
            react_native_ready=react_native_ready,
            note=note,
        )


class LivenessDetector:
    def __init__(self, engine: OfflineFaceEngine) -> None:
        self.engine = engine
        self.eye_cascade = cv2.CascadeClassifier(str(EYE_MODEL))
        self.model = None
        self.model_kind: Optional[str] = None
        if MINIFASNET_MODEL.exists():
            if "quantized" in MINIFASNET_MODEL.name or "minifasnet" in MINIFASNET_MODEL.name:
                self.model = ort.InferenceSession(str(MINIFASNET_MODEL), providers=["CPUExecutionProvider"])
                self.model_kind = "onnxruntime"
            else:
                try:
                    self.model = cv2.dnn.readNetFromONNX(str(MINIFASNET_MODEL))
                    self.model_kind = "opencv_dnn"
                except cv2.error:
                    self.model = ort.InferenceSession(str(MINIFASNET_MODEL), providers=["CPUExecutionProvider"])
                    self.model_kind = "onnxruntime"
        self.reset()

    def reset(self) -> None:
        self.reference_center: Optional[Tuple[float, float]] = None
        self.reference_center_norm: Optional[Tuple[float, float]] = None
        self.max_center_shift = 0.0
        self.motion_score = 0.0
        self.max_live_score = 0.0
        self.last_live_score = 0.0
        self.prev_face_gray: Optional[np.ndarray] = None
        self.frames_with_face = 0
        self.min_center_x: Optional[float] = None
        self.max_center_x: Optional[float] = None
        self.min_center_y: Optional[float] = None
        self.max_center_y: Optional[float] = None
        self.min_face_area: Optional[float] = None
        self.max_face_area: Optional[float] = None
        self.challenge_sequence = [random.choice(["turn_left", "turn_right", "move_closer"])]
        self.challenge_index = 0
        self.challenge_completed = False
        self.challenge_enabled = False
        self.eye_open_frames = 0
        self.eye_closed_frames_after_open = 0
        self.eye_reopened_after_blink = False

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        box = self.engine.detect_face(frame)
        if box is None:
            self.prev_face_gray = None
            return {
                "face_found": False,
                "movement": self.max_center_shift,
                "motion": self.motion_score,
                "live_score": self.last_live_score,
            }

        x, y, w, h = box
        self.frames_with_face += 1
        center = (x + w / 2.0, y + h / 2.0)
        if self.reference_center is None:
            self.reference_center = center
        frame_h, frame_w = frame.shape[:2]
        center_x_norm = center[0] / max(frame_w, 1)
        center_y_norm = center[1] / max(frame_h, 1)
        if self.reference_center_norm is None:
            self.reference_center_norm = (center_x_norm, center_y_norm)
        face_area_norm = float((w * h) / max(frame_w * frame_h, 1))
        self.min_center_x = center_x_norm if self.min_center_x is None else min(self.min_center_x, center_x_norm)
        self.max_center_x = center_x_norm if self.max_center_x is None else max(self.max_center_x, center_x_norm)
        self.min_center_y = center_y_norm if self.min_center_y is None else min(self.min_center_y, center_y_norm)
        self.max_center_y = center_y_norm if self.max_center_y is None else max(self.max_center_y, center_y_norm)
        self.min_face_area = face_area_norm if self.min_face_area is None else min(self.min_face_area, face_area_norm)
        self.max_face_area = face_area_norm if self.max_face_area is None else max(self.max_face_area, face_area_norm)
        center_shift = math.dist(self.reference_center, center) / max(w, h)
        self.max_center_shift = max(self.max_center_shift, center_shift)

        face_gray = cv2.cvtColor(frame[y : y + h, x : x + w], cv2.COLOR_BGR2GRAY)
        face_gray = cv2.GaussianBlur(face_gray, (5, 5), 0)
        eyes_open = self._eyes_open(face_gray)
        if eyes_open:
            self.eye_open_frames += 1
            if self.eye_closed_frames_after_open >= 1:
                self.eye_reopened_after_blink = True
        elif self.eye_open_frames >= 2:
            self.eye_closed_frames_after_open += 1
        if self.prev_face_gray is not None and self.prev_face_gray.shape == face_gray.shape:
            frame_delta = cv2.absdiff(self.prev_face_gray, face_gray)
            normalized_motion = float(frame_delta.mean() / 255.0)
            self.motion_score = max(self.motion_score, normalized_motion)
        self.prev_face_gray = face_gray
        self.last_live_score = self._predict_live_score(frame[y : y + h, x : x + w])
        self.max_live_score = max(self.max_live_score, self.last_live_score)
        if self.challenge_enabled:
            self._update_challenge(center_x_norm)

        return {
            "face_found": True,
            "movement": self.max_center_shift,
            "motion": self.motion_score,
            "live_score": self.last_live_score,
            "horizontal_range": self.horizontal_range,
            "vertical_range": self.vertical_range,
            "scale_change": self.scale_change,
            "challenge_text": self.current_challenge_text,
            "challenge_step": min(self.challenge_index + 1, len(self.challenge_sequence)),
            "challenge_total": len(self.challenge_sequence),
            "challenge_done": self.challenge_completed,
            "challenge_enabled": self.challenge_enabled,
            "eyes_open": eyes_open,
            "box": box,
        }

    def is_live(self) -> bool:
        passive_ok = self.passive_ok()
        if not self.challenge_enabled:
            return passive_ok
        enough_tracking = self.frames_with_face >= 5
        blink_ok = self.eye_open_frames >= 2 and self.eye_closed_frames_after_open >= 1
        movement_ok = (
            self.horizontal_range >= 0.012
            or self.vertical_range >= 0.012
            or self.scale_change >= 0.035
            or self.max_center_shift >= 0.015
        )
        texture_ok = self.motion_score >= 0.001
        heuristic_pass = enough_tracking and (blink_ok or movement_ok) and texture_ok and self.challenge_completed
        if self.model is None:
            return heuristic_pass
        model_support = self.max_live_score >= 0.35
        strong_motion = self.motion_score >= 0.001 or self.max_center_shift >= 0.015
        return enough_tracking and heuristic_pass and (model_support or strong_motion)

    def passive_ok(self) -> bool:
        enough_tracking = self.frames_with_face >= 4
        motion_ok = self.motion_score >= 0.001 or self.max_center_shift >= 0.010
        if self.model is not None:
            return enough_tracking and motion_ok and self.max_live_score >= 0.35
        return enough_tracking and motion_ok

    def enable_challenge(self) -> None:
        self.challenge_enabled = True

    @property
    def current_challenge_text(self) -> str:
        if not self.challenge_enabled:
            return "Look naturally at camera"
        if self.challenge_completed:
            return "Challenge complete"
        current = self.challenge_sequence[self.challenge_index]
        labels = {
            "turn_left": "Turn your head right",
            "turn_right": "Turn your head left",
            "move_closer": "Move slightly closer",
            "move_slightly": "Move slightly",
            "blink": "Blink once",
        }
        return labels[current]

    @property
    def horizontal_range(self) -> float:
        if self.min_center_x is None or self.max_center_x is None:
            return 0.0
        return float(self.max_center_x - self.min_center_x)

    @property
    def vertical_range(self) -> float:
        if self.min_center_y is None or self.max_center_y is None:
            return 0.0
        return float(self.max_center_y - self.min_center_y)

    @property
    def scale_change(self) -> float:
        if self.min_face_area is None or self.max_face_area is None or self.min_face_area <= 0:
            return 0.0
        return float((self.max_face_area - self.min_face_area) / self.min_face_area)

    def _update_challenge(self, center_x_norm: float) -> None:
        if self.challenge_completed or self.reference_center_norm is None:
            return

        reference_x_norm = self.reference_center_norm[0]
        current = self.challenge_sequence[self.challenge_index]
        passed = False
        if current == "turn_left":
            passed = center_x_norm <= (reference_x_norm - 0.025)
        elif current == "turn_right":
            passed = center_x_norm >= (reference_x_norm + 0.025)
        elif current == "move_closer":
            passed = self.scale_change >= 0.08
        elif current == "move_slightly":
            passed = (
                self.horizontal_range >= 0.012
                or self.vertical_range >= 0.012
                or self.scale_change >= 0.035
                or self.max_center_shift >= 0.015
                or self.motion_score >= 0.001
            )
        elif current == "blink":
            passed = (
                self.eye_open_frames >= 2
                and self.eye_closed_frames_after_open >= 1
                and self.eye_reopened_after_blink
            )

        if passed:
            self.challenge_index += 1
            if self.challenge_index >= len(self.challenge_sequence):
                self.challenge_completed = True

    def _eyes_open(self, face_gray: np.ndarray) -> bool:
        if self.eye_cascade.empty() or face_gray.size == 0:
            return False
        upper_face = face_gray[: max(1, int(face_gray.shape[0] * 0.62)), :]
        eyes = self.eye_cascade.detectMultiScale(
            upper_face,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(12, 12),
        )
        return len(eyes) >= 1

    def _predict_live_score(self, face_bgr: np.ndarray) -> float:
        if self.model is None:
            return 0.0

        resized = cv2.resize(face_bgr, (128, 128))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        output: np.ndarray
        if self.model_kind == "opencv_dnn":
            blob = cv2.dnn.blobFromImage(
                rgb,
                scalefactor=1.0 / 255.0,
                size=(128, 128),
                mean=(0.0, 0.0, 0.0),
                swapRB=False,
                crop=False,
            )
            self.model.setInput(blob)
            output = self.model.forward().flatten().astype(np.float32)
        else:
            tensor = rgb.astype(np.float32) / 255.0
            tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
            input_name = self.model.get_inputs()[0].name
            output = self.model.run(None, {input_name: tensor})[0].flatten().astype(np.float32)
        if output.size == 1:
            return float(output[0])
        output = output - np.max(output)
        probs = np.exp(output)
        probs /= float(np.sum(probs) + 1e-6)
        if probs.size >= 2:
            return float(probs[1])
        return float(probs[0])


def capture_single_frame(camera_index: int = 0) -> np.ndarray:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    try:
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Could not read frame from webcam.")
        return frame
    finally:
        cap.release()


def capture_face_frame(camera_index: int = 0, window_title: str = "Capture Face", allow_manual_capture: bool = True) -> np.ndarray:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    engine = OfflineFaceEngine()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue

            box = engine.detect_face(frame)
            if box is not None:
                x, y, w, h = box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    "Face detected. Press SPACE to capture",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
            else:
                cv2.putText(
                    frame,
                    "Center your face in the camera",
                    (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
                if allow_manual_capture:
                    cv2.putText(
                        frame,
                        "Press C to capture anyway",
                        (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 200, 255),
                        2,
                    )

            guide_w = frame.shape[1] // 3
            guide_h = int(frame.shape[0] * 0.55)
            gx = (frame.shape[1] - guide_w) // 2
            gy = (frame.shape[0] - guide_h) // 2
            cv2.rectangle(frame, (gx, gy), (gx + guide_w, gy + guide_h), (255, 255, 255), 1)

            cv2.imshow(window_title, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                raise RuntimeError("Capture cancelled.")
            if key == 32 and box is not None:
                return frame.copy()
            if key == ord("c") and allow_manual_capture:
                return frame.copy()
    finally:
        cap.release()
        cv2.destroyAllWindows()


def run_liveness_check(camera_index: int = 0, timeout_seconds: int = 12, require_active_challenge: bool = True) -> bool:
    result = run_live_verification_session(
        camera_index=camera_index,
        timeout_seconds=timeout_seconds,
        require_active_challenge=require_active_challenge,
    )
    return result.passed


def run_live_verification_session(
    camera_index: int = 0,
    timeout_seconds: int = 12,
    require_active_challenge: bool = True,
) -> LiveSessionResult:
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    engine = OfflineFaceEngine()
    detector = LivenessDetector(engine)
    started = time.time()
    passive_deadline = started + 2.5
    reference_embedding: Optional[np.ndarray] = None
    best_frame: Optional[np.ndarray] = None
    best_quality = -1.0
    last_consistency = 0.0
    min_consistency = 1.0
    challenge_required = False

    try:
        while time.time() - started < timeout_seconds:
            ok, frame = cap.read()
            if not ok:
                continue

            stats = detector.process_frame(frame)
            box = stats.get("box")
            consistency = 0.0
            if box is not None:
                try:
                    current_embedding = engine.extract_embedding(frame)
                    if reference_embedding is None:
                        reference_embedding = current_embedding
                    consistency = engine._compare_embeddings(reference_embedding, current_embedding)
                    last_consistency = consistency
                    min_consistency = min(min_consistency, consistency)
                    if consistency >= 0.55:
                        x, y, w, h = box
                        area_score = min(1.0, (w * h) / 80000.0)
                        quality = (
                            stats.get("live_score", 0.0) * 0.45
                            + consistency * 0.35
                            + area_score * 0.20
                        )
                        if quality > best_quality:
                            best_quality = quality
                            best_frame = frame.copy()
                except Exception:
                    consistency = 0.0

            if box is not None:
                x, y, w, h = box
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            status = (
                f"Move: {stats.get('movement', 0.0):.3f} | "
                f"Motion: {stats.get('motion', 0.0):.3f} | "
                f"Live: {stats.get('live_score', 0.0):.2f} | "
                f"Same: {consistency:.2f}"
            )
            challenge_metrics = (
                f"H:{stats.get('horizontal_range', 0.0):.3f} "
                f"V:{stats.get('vertical_range', 0.0):.3f} "
                f"S:{stats.get('scale_change', 0.0):.2f}"
            )
            instruction = stats.get("challenge_text", "Follow live challenge")
            progress = f"Step {stats.get('challenge_step', 1)}/{stats.get('challenge_total', 2)}"
            cv2.putText(frame, instruction, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, status, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, progress, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 0), 2)
            cv2.putText(frame, challenge_metrics, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 220, 0), 2)
            cv2.imshow("Offline Liveness Check", frame)

            if not challenge_required and time.time() >= passive_deadline:
                if not require_active_challenge and detector.passive_ok() and last_consistency >= 0.25 and best_frame is not None:
                    cv2.waitKey(300)
                    return LiveSessionResult(
                        passed=True,
                        frame=best_frame,
                        risk_level="Low",
                        challenge_required=False,
                        message="Passive liveness passed. Auto-captured same live face.",
                    )
                challenge_required = True
                detector.enable_challenge()

            if challenge_required and detector.is_live() and last_consistency >= 0.25 and best_frame is not None:
                cv2.waitKey(500)
                return LiveSessionResult(
                    passed=True,
                    frame=best_frame,
                    risk_level="Low" if require_active_challenge else "Medium",
                    challenge_required=True,
                    message="Active challenge passed. Auto-captured same live face.",
                )

            if cv2.waitKey(1) & 0xFF == 27:
                break
        risk_level = "High"
        if detector.passive_ok():
            risk_level = "Medium"
        if best_frame is None:
            failure_message = "No stable live face captured during session."
        elif challenge_required:
            failure_message = "Active liveness challenge failed or face changed during session."
        else:
            failure_message = "Passive liveness was uncertain. Challenge would be required."
        return LiveSessionResult(
            passed=False,
            frame=best_frame,
            risk_level=risk_level,
            challenge_required=challenge_required,
            message=failure_message,
        )
    finally:
        cap.release()
        cv2.destroyAllWindows()


def register_from_camera(name: str, camera_index: int = 0) -> FaceRecord:
    frame = capture_face_frame(camera_index=camera_index, window_title="Register Face", allow_manual_capture=True)
    engine = OfflineFaceEngine()
    return engine.register_frame(name, frame)


def verify_from_camera(
    camera_index: int = 0,
    require_liveness: bool = True,
    require_active_challenge: bool = True,
) -> VerificationResult:
    liveness_passed = True
    risk_level = "Low"
    challenge_required = False
    session_message = "Verification completed."
    frame: Optional[np.ndarray] = None
    if require_liveness:
        session = run_live_verification_session(
            camera_index=camera_index,
            require_active_challenge=require_active_challenge,
        )
        liveness_passed = session.passed
        risk_level = session.risk_level
        challenge_required = session.challenge_required
        session_message = session.message
        frame = session.frame

    if frame is None:
        frame = capture_face_frame(camera_index=camera_index, window_title="Verify Face", allow_manual_capture=True)
    engine = OfflineFaceEngine()
    try:
        result = engine.identify_frame(frame, liveness_passed=True)
    except Exception:
        result = engine.identify_frame(frame, liveness_passed=liveness_passed)
    result.risk_level = risk_level
    result.challenge_required = challenge_required
    result.liveness_passed = liveness_passed
    if not liveness_passed:
        result.message = session_message
    sync_manager = SyncManager(store=engine.event_store)
    sync_manager.queue_verification_event(result)
    return result


def benchmark_models(iterations: int = 10) -> Dict[str, float]:
    engine = OfflineFaceEngine()
    detector = LivenessDetector(engine)
    frame = np.full((480, 640, 3), 127, dtype=np.uint8)
    face_crop = np.full((128, 128, 3), 127, dtype=np.uint8)
    fixed_box = (186, 76, 268, 278)

    def avg_ms(fn) -> float:
        started = time.perf_counter()
        for _ in range(iterations):
            fn()
        elapsed = time.perf_counter() - started
        return (elapsed / iterations) * 1000.0

    results = {
        "detector_ms": avg_ms(lambda: engine.detect_face(frame)),
        "embedding_ms": avg_ms(lambda: engine.extract_embedding(frame, fixed_box)),
    }
    if detector.model is not None:
        results["liveness_model_ms"] = avg_ms(lambda: detector._predict_live_score(face_crop))
    results["estimated_pipeline_ms"] = sum(results.values())
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline face recognition and liveness demo.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser("register", help="Register a person from webcam.")
    register_parser.add_argument("--name", required=True)
    register_parser.add_argument("--camera", type=int, default=0)

    verify_parser = subparsers.add_parser("verify", help="Verify a person from webcam.")
    verify_parser.add_argument("--camera", type=int, default=0)
    verify_parser.add_argument("--skip-liveness", action="store_true")
    verify_parser.add_argument(
        "--allow-passive-only",
        action="store_true",
        help="Allow passive liveness to pass without a mandatory active challenge.",
    )

    liveness_parser = subparsers.add_parser("liveness", help="Run standalone offline liveness check.")
    liveness_parser.add_argument("--camera", type=int, default=0)
    liveness_parser.add_argument("--timeout", type=int, default=12)
    liveness_parser.add_argument(
        "--allow-passive-only",
        action="store_true",
        help="Allow passive liveness to pass without a mandatory active challenge.",
    )

    subparsers.add_parser("list-users", help="List stored identities.")
    subparsers.add_parser("queue-status", help="Show local attendance queue status.")
    subparsers.add_parser("list-events", help="List queued attendance events.")
    sync_parser = subparsers.add_parser("sync-events", help="Sync pending offline events to the sync sink.")
    sync_parser.add_argument("--simulate-failure", action="store_true")
    subparsers.add_parser("retry-failed", help="Move failed sync events back to pending state.")
    subparsers.add_parser("purge-events", help="Purge locally synced events from the queue.")
    subparsers.add_parser("profile", help="Show current model footprint and mobile-readiness.")
    benchmark_parser = subparsers.add_parser("benchmark", help="Run rough local model-latency estimates.")
    benchmark_parser.add_argument("--iterations", type=int, default=10)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "register":
        record = register_from_camera(name=args.name, camera_index=args.camera)
        print(f"Registered {record.name} using backend={record.backend} id={record.person_id}")
        return

    if args.command == "verify":
        result = verify_from_camera(
            camera_index=args.camera,
            require_liveness=not args.skip_liveness,
            require_active_challenge=not args.allow_passive_only,
        )
        final_verified = result.matched and result.liveness_passed
        decision = "Verified" if final_verified else "Not Verified"
        print(f"Face Match Score: {result.score:.4f}")
        print(f"Face Match Percentage: {result.percentage:.2f}%")
        print(f"Face Matched: {'Yes' if result.matched else 'No'}")
        print(f"Final Decision: {decision}")
        print(f"Recognized Name: {result.name or 'No match'}")
        print(f"Confidence Band: {result.confidence_band}")
        print(f"Required Threshold: {result.threshold * 100:.2f}%")
        print(f"Liveness Passed: {'Yes' if result.liveness_passed else 'No'}")
        print(f"Risk Level: {result.risk_level}")
        print(f"Challenge Required: {'Yes' if result.challenge_required else 'No'}")
        print(f"Backend: {result.backend}")
        print(f"Message: {result.message}")
        if result.event_id:
            print(f"Queued offline event: {result.event_id}")
        return

    if args.command == "liveness":
        session = run_live_verification_session(
            camera_index=args.camera,
            timeout_seconds=args.timeout,
            require_active_challenge=not args.allow_passive_only,
        )
        print(f"Liveness Passed: {'Yes' if session.passed else 'No'}")
        print(f"Risk Level: {session.risk_level}")
        print(f"Challenge Required: {'Yes' if session.challenge_required else 'No'}")
        print(f"Message: {session.message}")
        return

    if args.command == "list-users":
        engine = OfflineFaceEngine()
        for record in engine.store.list_records():
            print(f"{record.name} | backend={record.backend} | created_at={record.created_at:.0f}")
        return

    if args.command == "queue-status":
        counts = EventStore().counts()
        print(f"Total events: {counts['total']}")
        print(f"Pending sync: {counts['pending_sync']}")
        print(f"Synced: {counts['synced']}")
        print(f"Failed: {counts['failed']}")
        print(f"Sync sink path: {SYNC_SINK_PATH}")
        return

    if args.command == "list-events":
        for event in EventStore().list_events():
            person_name = event.person_name or "No match"
            print(
                f"{event.event_id} | {event.sync_state} | {person_name} | "
                f"matched={event.matched} | liveness={event.liveness_passed} | "
                f"risk={event.risk_level} | created_at={event.created_at:.0f}"
            )
        return

    if args.command == "sync-events":
        summary = SyncManager().sync_pending_events(simulate_failure=args.simulate_failure)
        print(f"Pending before sync: {summary.total_pending}")
        print(f"Synced now: {summary.synced_now}")
        print(f"Failed now: {summary.failed_now}")
        print(f"Remote sink total: {summary.remote_total}")
        print(f"Remote sink path: {SYNC_SINK_PATH}")
        return

    if args.command == "retry-failed":
        reset = SyncManager().retry_failed_events()
        print(f"Failed events moved back to pending: {reset}")
        return

    if args.command == "purge-events":
        removed = SyncManager().purge_synced_events()
        print(f"Purged synced local events: {removed}")
        return

    if args.command == "profile":
        engine = OfflineFaceEngine()
        profile = engine.get_model_profile()
        print(profile)
        print(f"Total model footprint: {profile.total_bytes / (1024 * 1024):.2f} MB")
        print(f"Target <= 20 MB: {profile.meets_target}")
        print(f"React Native ready profile: {profile.react_native_ready}")
        return

    if args.command == "benchmark":
        results = benchmark_models(iterations=args.iterations)
        for key, value in results.items():
            print(f"{key}: {value:.2f} ms")


if __name__ == "__main__":
    main()
