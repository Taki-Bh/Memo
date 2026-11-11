 from pathlib import Path
from .models import BoundingBox, Detection

class YOLOAdapter:
    def init(self, model=None):
        self.model = model
        self._loaded = None

    @property
    def available(self) -> bool:
        try:
            import ultralytics  # noqa: F401
        except ImportError:
            return False
        return self.model is not None

    def _get_model(self):
        if self._loaded is not None:
            return self._loaded
        if self.model is None:
            return None
        if hasattr(self.model, "predict"):
            self._loaded = self.model
            return self._loaded
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("YOLO support requires the 'ultralytics' package") from exc
        self._loaded = YOLO(str(self.model))
        return self._loaded

    def detect(self, image):
        model = self._get_model()
        if model is None:
            return []
        detections = []
        for result in model.predict(image, verbose=False):
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            names = getattr(result, "names", {})
            for i, xyxy in enumerate(boxes.xyxy.tolist()):
                x1, y1, x2, y2 = map(float, xyxy)
                cls = int(boxes.cls[i].item())
                detections.append(Detection(
                    kind="object",
                    label=names.get(cls, str(cls)),
                    bbox=BoundingBox(x1, y1, x2 - x1, y2 - y1),
                    confidence=float(boxes.conf[i].item()),
                    source="yolo",
                ))
        return detections