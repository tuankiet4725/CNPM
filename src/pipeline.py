"""Luồng xử lý chính: đọc video -> phát hiện -> theo vết -> đánh giá -> cảnh báo -> hiển thị."""

import logging
import os
import threading
import time

import cv2

from .alert import AlertManager
from .database import EventDatabase
from .detector import WeaponDetector
from .notifier import build_notifiers
from .threat import ThreatAssessor
from .tracker import IoUTracker
from .utils import FPSMeter
from .video_source import VideoSource
from .visualizer import draw

log = logging.getLogger(__name__)

WINDOW = "UAV Weapon Detection (Q: thoat)"


class DetectionPipeline:
    def __init__(self, cfg):
        self.cfg = cfg
        threat_classes = cfg["threat_classes"]
        wanted = list(threat_classes) + [cfg["person_class"]]

        class_conf = {name: float(c["min_conf"]) for name, c in threat_classes.items() if "min_conf" in c}
        self.detector = WeaponDetector(cfg["model"], cfg["tiling"], wanted, class_conf)
        self.tracker = IoUTracker(**cfg["tracker"])
        self.assessor = ThreatAssessor(threat_classes, cfg["person_class"], cfg["person_proximity"])
        self.db = EventDatabase(cfg["database"])
        self.alerts = AlertManager(cfg["alert"], self.db, build_notifiers(cfg["alert"]), str(cfg["source"]))

        self.state = None
        if cfg["web"]["enabled"]:
            from .web import SharedState, create_app, run_in_background

            self.state = SharedState()
            self.state.status["source"] = str(cfg["source"])
            app = create_app(self.state, self.db, cfg["alert"]["snapshot_dir"])
            run_in_background(app, cfg["web"]["host"], int(cfg["web"]["port"]))

    def process_frame(self, frame, fps=0.0):
        """Phát hiện + theo vết + cảnh báo. Trả về (annotated, threats, persons, new_alerts).

        `threats` chỉ gồm vũ khí đã thấy liên tiếp đủ display_min_frames khung,
        để khung nhận nhầm thoáng qua không nhấp nháy trên màn hình.
        """
        detections = self.detector.detect(frame)
        tracks = {t.track_id: t for t in self.tracker.update(detections)}
        threats, persons = self.assessor.assess(detections)
        # Ảnh bằng chứng có vẽ toàn bộ khung phát hiện; chỉ vẽ khi có vũ khí
        snapshot = draw(frame, threats, persons) if threats else frame
        new_alerts = self.alerts.process(snapshot, threats, tracks)
        min_frames = int(self.cfg.get("display_min_frames", 1))
        shown = [th for th in threats if th.detection.track_id in tracks
                 and tracks[th.detection.track_id].streak >= min_frames]
        annotated = draw(frame, shown, persons, fps, self.alerts.is_active(), self.alerts.total)
        return annotated, shown, persons, new_alerts

    def _open_writer(self, frame, fps):
        out_dir = self.cfg["record"]["dir"]
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, time.strftime("uav_%Y%m%d_%H%M%S.mp4"))
        h, w = frame.shape[:2]
        log.info("Ghi video ra %s", path)
        return cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps or 20.0, (w, h))

    def _output(self, annotated, fps, n_threats, source, writer):
        """Đưa khung đã vẽ ra web / file ghi / cửa sổ. Trả về (writer, có_yêu_cầu_thoát)."""
        if self.state:
            self.state.set_frame(annotated)
            self.state.status.update(fps=round(fps, 1), threats_now=n_threats)
        if self.cfg["record"]["enabled"]:
            if writer is None:
                writer = self._open_writer(annotated, source.fps)
            writer.write(annotated)
        quit_ = False
        if self.cfg["display"]:
            cv2.imshow(WINDOW, annotated)
            quit_ = cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27)
        return writer, quit_

    def _run_sync(self, source, writer):
        """File video: xử lý lần lượt từng khung."""
        meter = FPSMeter()
        while True:
            ok, frame = source.read()
            if not ok:
                if source.is_live:
                    continue
                log.info("Hết video.")
                return writer
            fps = meter.tick()
            annotated, threats, _, _ = self.process_frame(frame, fps)
            writer, quit_ = self._output(annotated, fps, len(threats), source, writer)
            if quit_:
                return writer

    def _run_async(self, source, writer):
        """Camera trực tiếp: luồng nền phát hiện trên khung mới nhất, luồng chính hiển thị theo
        tốc độ camera và vẽ kết quả phát hiện gần nhất, nên hình không bị giật khi suy luận chậm."""
        stop = threading.Event()
        meter = FPSMeter()
        result = ([], [])  # (threats, persons) gần nhất; gán cả tuple nên an toàn giữa 2 luồng

        def worker():
            nonlocal result
            while not stop.is_set():
                ok, frame = source.read()
                if not ok:
                    continue
                fps = meter.tick()
                try:
                    _, threats, persons, _ = self.process_frame(frame, fps)
                except Exception:
                    log.exception("Lỗi khi phát hiện")
                    continue
                result = (threats, persons)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        last_id = 0
        try:
            while thread.is_alive():
                frame_id, frame = source.latest()
                if frame is None or frame_id == last_id:
                    if self.cfg["display"]:
                        if cv2.waitKey(5) & 0xFF in (ord("q"), ord("Q"), 27):
                            break
                    else:
                        time.sleep(0.005)
                    continue
                last_id = frame_id
                threats, persons = result
                annotated = draw(frame, threats, persons, meter.fps, self.alerts.is_active(), self.alerts.total)
                writer, quit_ = self._output(annotated, meter.fps, len(threats), source, writer)
                if quit_:
                    break
        finally:
            stop.set()
            thread.join(timeout=5)
        return writer

    def run(self):
        source = VideoSource(self.cfg["source"]).start()
        writer = None
        if self.state:
            self.state.status["running"] = True
        log.info("Bắt đầu xử lý nguồn %s", self.cfg["source"])
        try:
            if source.is_live:
                writer = self._run_async(source, writer)
            else:
                writer = self._run_sync(source, writer)
        except KeyboardInterrupt:
            log.info("Dừng theo yêu cầu người dùng.")
        finally:
            if self.state:
                self.state.status["running"] = False
            source.stop()
            if writer is not None:
                writer.release()
            if self.cfg["display"]:
                cv2.destroyAllWindows()
            log.info("Tổng số cảnh báo: %d", self.alerts.total)
