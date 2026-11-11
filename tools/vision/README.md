# Vision

Screen/UI perception layer for Memo. It normalizes Omni Parser-style UI detections and YOLO object detections into the memo.vision.v1 schema for downstream LLM consumption.

## Components

- models.py — canonical bounding boxes and detection structures.
- omni_parser.py — backend-injected Omni Parser adapter.
- yolo.py — lazy Ultralytics YOLO adapter.
- pipeline.py — combines both detectors and serializes the result.

The current environment does not have ultralytics, torch, onnxruntime, or transformers installed, so the adapters remain optional and do not break imports.

Example:

python
from tools.vision import VisionPipeline

pipeline = VisionPipeline()
batch = pipeline.detect("screenshot.png")
payload = pipeline.to_llm_payload(batch)


The payload contains image dimensions, normalized detections, source, confidence, text when available, and detector availability metadata.
