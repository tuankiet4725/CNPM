"""Bộ theo vết đơn giản dựa trên IoU.

Gán ID ổn định cho mỗi đối tượng qua các khung hình để:
  - chỉ cảnh báo khi đối tượng xuất hiện liên tiếp nhiều khung (giảm báo động giả)
  - không cảnh báo lặp lại cho cùng một đối tượng.
"""

import time
from dataclasses import dataclass, field

from .utils import iou


@dataclass
class Track:
    track_id: int
    class_name: str
    box: tuple
    confidence: float
    hits: int = 1
    streak: int = 1  # số khung liên tiếp gần nhất thấy đối tượng
    missed: int = 0
    alerted_level: str = ""
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class IoUTracker:
    def __init__(self, iou_threshold=0.2, max_missed=15):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.tracks = {}
        self._next_id = 1

    def update(self, detections):
        """Cập nhật với danh sách Detection của khung hiện tại.

        Gán `track_id` cho từng detection, trả về các track đang hiển thị.
        """
        now = time.time()
        pairs = []
        for tid, t in self.tracks.items():
            for di, d in enumerate(detections):
                if d.class_name != t.class_name:
                    continue
                score = iou(t.box, d.box)
                if score >= self.iou_threshold:
                    pairs.append((score, tid, di))
        pairs.sort(reverse=True)

        matched_tracks, matched_dets = set(), set()
        for _, tid, di in pairs:
            if tid in matched_tracks or di in matched_dets:
                continue
            matched_tracks.add(tid)
            matched_dets.add(di)
            t, d = self.tracks[tid], detections[di]
            t.box, t.confidence = d.box, d.confidence
            t.hits += 1
            t.streak = t.streak + 1 if t.missed == 0 else 1
            t.missed = 0
            t.last_seen = now
            d.track_id = tid

        for tid in list(self.tracks):
            if tid in matched_tracks:
                continue
            self.tracks[tid].missed += 1
            if self.tracks[tid].missed > self.max_missed:
                del self.tracks[tid]

        for di, d in enumerate(detections):
            if di in matched_dets:
                continue
            tid = self._next_id
            self._next_id += 1
            self.tracks[tid] = Track(tid, d.class_name, d.box, d.confidence)
            d.track_id = tid

        return [t for t in self.tracks.values() if t.missed == 0]
