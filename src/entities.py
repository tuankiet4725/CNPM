"""Các đối tượng dữ liệu dùng chung giữa các module."""

from dataclasses import dataclass, field
from typing import Optional, Tuple

Box = Tuple[float, float, float, float]  # x1, y1, x2, y2 (pixel)

LEVELS = ["low", "medium", "high", "critical"]


def level_rank(level: str) -> int:
    return LEVELS.index(level) if level in LEVELS else 0


@dataclass
class Detection:
    class_name: str
    confidence: float
    box: Box
    track_id: Optional[int] = None

    @property
    def center(self):
        x1, y1, x2, y2 = self.box
        return (x1 + x2) / 2, (y1 + y2) / 2


@dataclass
class Threat:
    detection: Detection
    label: str          # tên tiếng Việt
    display: str        # nhãn ASCII vẽ lên video
    level: str
    near_person: bool = False


@dataclass
class Alert:
    timestamp: str
    class_name: str
    label: str
    level: str
    confidence: float
    track_id: Optional[int]
    near_person: bool
    snapshot: Optional[str] = None
    id: Optional[int] = None
    extra: dict = field(default_factory=dict)
