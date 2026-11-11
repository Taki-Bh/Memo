from typing import Any
from .models import BoundingBox, Detection

class OmniParserAdapter:
    def init(self, backend=None):
        self.backend = backend

    @property
    def available(self) -> bool:
        return self.backend is not None

    def detect(self, image: Any) -> list[Detection]:
        if self.backend is None:
            return []
        return [self._normalize(item) for item in (self.backend(image) or [])]

    @staticmethod
    def _normalize(item: dict[str, Any]) -> Detection:
        box = item.get("bbox") or item.get("box") or [0, 0, 0, 0]
        if len(box) != 4:
            raise ValueError("Omni Parser bbox must contain four values")
        x, y, a, b = map(float, box)
        if item.get("bbox_format", "xywh") == "xyxy":
            a, b = a - x, b - y
        return Detection(
            kind=item.get("kind", "ui_element"),
            label=item.get("label", item.get("type", "unknown")),
            bbox=BoundingBox(x, y, a, b),
            confidence=item.get("confidence"),
            text=item.get("text"),
            source="omni_parser",
            attributes=item.get("attributes", {}),
        )