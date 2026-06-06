Place offline ONNX models in this folder. The app now supports both a prototype profile and a mobile-target profile.

Prototype profile:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec.onnx`
- `face_recognition_sface_2021dec_int8bq.onnx`

Recommended mobile-target profile:

- `face_detection_yunet_2023mar.onnx`
- `face_recognition_sface_2021dec_int8bq.onnx`
- or `face_recognition_mobilefacenet_int8.onnx`
- `liveness_minifasnet_v2.onnx`

Behavior:

- If these files are missing, the project falls back to a fully offline LBP-histogram recognizer.
- If `face_recognition_mobilefacenet_int8.onnx` is present, the project prefers the mobile-target recognizer backend.
- Otherwise, if `face_recognition_sface_2021dec_int8bq.onnx` is present, the project prefers the compact official SFace backend.
- Otherwise, if `face_recognition_sface_2021dec.onnx` is present, the project uses the stronger prototype `YuNet + SFace` backend.

Recommended flow:

1. Keep the selected ONNX files inside `models/`.
2. Run `python app.py profile` to verify footprint and backend.
3. Register users again after switching backends so all stored embeddings use the same model.
