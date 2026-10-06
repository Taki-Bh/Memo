from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(frozen=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float

@dataclass
class Detection:
    kind: str
    label: str
    bbox: BoundingBox
    confidence: float | None = None
    text: str | None = None
    source: str = "unknown"
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class DetectionBatch:
    width: int
    height: int
    detections: list[Detection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(schema="memo.vision.v1", width=self.width, height=self.height, detections=[d.to_dict() for d in self.detections], metadata=self.metadata)
