 import json
from pathlib import Path
from PIL import Image
from .models import DetectionBatch
from .omni_parser import OmniParserAdapter
from .yolo import YOLOAdapter

class VisionPipeline:
    def init(self, omni_parser=None, yolo=None):
        self.omni_parser = omni_parser or OmniParserAdapter()
        self.yolo = yolo or YOLOAdapter()

    def detect(self, image):
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        detections = self.omni_parser.detect(image) + self.yolo.detect(image)
        detections.sort(key=lambda d: (d.bbox.y, d.bbox.x))
        return DetectionBatch(
            image.width,
            image.height,
            detections,
            {
                "omni_parser_available": self.omni_parser.available