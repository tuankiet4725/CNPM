"""Đọc video từ camera UAV: webcam/capture card, file, RTSP/RTMP/UDP.

Với luồng trực tiếp, một luồng nền liên tục đọc và chỉ giữ khung hình mới nhất
để tránh trễ tích luỹ, đồng thời tự kết nối lại khi mất sóng.
"""

import logging
import os
import threading
import time

import cv2

log = logging.getLogger(__name__)

STREAM_PREFIXES = ("rtsp://", "rtmp://", "http://", "https://", "udp://", "tcp://", "srt://")


class VideoSource:
    def __init__(self, source, reconnect_delay=2.0):
        src = str(source).strip()
        self.source = int(src) if src.isdigit() else src
        self.is_stream = isinstance(self.source, str) and self.source.lower().startswith(STREAM_PREFIXES)
        self.is_live = isinstance(self.source, int) or self.is_stream
        self.reconnect_delay = reconnect_delay

        self._cap = None
        self._frame = None
        self._frame_id = 0
        self._read_id = 0
        self._lock = threading.Lock()
        self._new_frame = threading.Condition(self._lock)
        self._running = False
        self._thread = None

    # ---------------------------------------------------------------
    def _open(self):
        if self.is_stream:
            # RTSP qua TCP ổn định hơn khi sóng yếu
            os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
            cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def start(self):
        self._cap = self._open()
        if self._cap is None and not self.is_live:
            raise RuntimeError(f"Không mở được nguồn video: {self.source}")
        if self._cap is None:
            log.warning("Chưa kết nối được %s, sẽ thử lại...", self.source)
        if self.is_live:
            self._running = True
            self._thread = threading.Thread(target=self._reader, daemon=True)
            self._thread.start()
        return self

    def _reader(self):
        while self._running:
            if self._cap is None:
                time.sleep(self.reconnect_delay)
                self._cap = self._open()
                if self._cap is not None:
                    log.info("Đã kết nối lại nguồn video %s", self.source)
                continue
            ok, frame = self._cap.read()
            if not ok:
                log.warning("Mất tín hiệu video, đang kết nối lại...")
                self._cap.release()
                self._cap = None
                continue
            with self._new_frame:
                self._frame = frame
                self._frame_id += 1
                self._new_frame.notify_all()

    def read(self, timeout=1.0):
        """Trả về (ok, frame). Với luồng trực tiếp: chờ khung hình mới tối đa `timeout` giây."""
        if not self.is_live:
            return self._cap.read()
        with self._new_frame:
            if self._frame_id == self._read_id:
                self._new_frame.wait(timeout)
            if self._frame is None or self._frame_id == self._read_id:
                return False, None
            self._read_id = self._frame_id
            return True, self._frame.copy()

    def latest(self):
        """Trả về (frame_id, frame) mới nhất, không chờ và không đánh dấu đã đọc (dùng để hiển thị)."""
        with self._lock:
            if self._frame is None:
                return 0, None
            return self._frame_id, self._frame.copy()

    @property
    def fps(self):
        if self._cap is None:
            return 0.0
        return self._cap.get(cv2.CAP_PROP_FPS) or 0.0

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
