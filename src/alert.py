"""Quản lý cảnh báo: xác nhận qua nhiều khung hình, chống lặp, lưu ảnh và CSDL."""

import logging
import os
import time
from datetime import datetime

from .entities import Alert, level_rank

log = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, alert_cfg, db=None, notifiers=None, source=""):
        self.min_level = alert_cfg.get("min_level", "medium")
        self.min_frames = int(alert_cfg.get("min_consecutive_frames", 3))
        self.cooldown = float(alert_cfg.get("cooldown_seconds", 10))
        self.snapshot_dir = alert_cfg.get("snapshot_dir")
        self.db = db
        self.notifiers = notifiers or []
        self.source = source
        self._last_alert = {}   # (class_name, level) -> thời điểm
        self.last_alert_time = 0.0
        self.total = 0

    def process(self, frame, threats, tracks):
        """threats: list[Threat]; tracks: {track_id: Track}. Trả về các Alert mới."""
        now = time.time()
        new_alerts = []
        for th in threats:
            d = th.detection
            track = tracks.get(d.track_id)
            if track is None or track.streak < self.min_frames:
                continue
            if level_rank(th.level) < level_rank(self.min_level):
                continue
            # Mỗi track chỉ cảnh báo lại khi mức độ tăng lên
            if track.alerted_level and level_rank(th.level) <= level_rank(track.alerted_level):
                continue
            track.alerted_level = th.level

            key = (d.class_name, th.level)
            if now - self._last_alert.get(key, 0) < self.cooldown:
                continue
            self._last_alert[key] = now

            alert = Alert(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                class_name=d.class_name,
                label=th.label,
                level=th.level,
                confidence=round(d.confidence, 3),
                track_id=d.track_id,
                near_person=th.near_person,
            )
            alert.snapshot = self._save_snapshot(frame, alert)
            if self.db is not None:
                alert.id = self.db.add_event(alert, self.source)
            for n in self.notifiers:
                n.notify(alert)
            log.warning("CẢNH BÁO [%s] %s %.0f%% (track %s)%s", alert.level.upper(), alert.label,
                        alert.confidence * 100, alert.track_id, " - gần người" if alert.near_person else "")
            new_alerts.append(alert)

        if new_alerts:
            self.last_alert_time = now
            self.total += len(new_alerts)
        return new_alerts

    def _save_snapshot(self, frame, alert):
        if not self.snapshot_dir or frame is None:
            return None
        import cv2

        os.makedirs(self.snapshot_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name = f"{stamp}_{alert.class_name.replace(' ', '_')}_{alert.track_id}.jpg"
        path = os.path.join(self.snapshot_dir, name)
        cv2.imwrite(path, frame)
        return path

    def is_active(self, window=3.0):
        return time.time() - self.last_alert_time < window
