"""Bộ phát hiện đối tượng dựa trên YOLOv8 (Ultralytics).

Hỗ trợ suy luận theo ô (tiling) để phát hiện vật thể nhỏ trong ảnh chụp từ trên cao.
"""

import logging
import os

from .entities import Detection
from .utils import drop_contained, generate_tiles, nms

log = logging.getLogger(__name__)


class WeaponDetector:
    def __init__(self, model_cfg, tiling_cfg, wanted_classes, class_conf=None):
        from ultralytics import YOLO  # import trễ để test không cần ultralytics

        self.conf = float(model_cfg["conf"])
        self.iou = float(model_cfg["iou"])
        self.imgsz = int(model_cfg["imgsz"])
        self.device = model_cfg.get("device") or None
        self.tiling = tiling_cfg
        self.class_conf = class_conf or {}  # ngưỡng tin cậy riêng theo lớp (cao hơn conf chung)
        self.backend = (model_cfg.get("backend") or "pytorch").lower()

        # weights có thể là một file hoặc danh sách nhiều file (chạy song song rồi gộp kết quả),
        # ví dụ mô hình COCO (dao, gậy, người) + mô hình tự huấn luyện (súng).
        # Mỗi phần tử là đường dẫn, hoặc {path: ..., classes: [...]} để chỉ lấy một số lớp từ mô hình đó.
        weights = model_cfg["weights"]
        if isinstance(weights, str):
            weights = [weights]

        wanted = set(wanted_classes)
        found = set()
        self.models = []  # [(model, names, class_ids)]
        for w in weights:
            only = None
            if isinstance(w, dict):
                w, only = w["path"], set(w.get("classes") or wanted)
            log.info("Đang nạp mô hình %s ...", w)
            model = self._load(YOLO, w)
            ids = [i for i, n in model.names.items() if n in wanted and (only is None or n in only)]
            if not ids:
                log.warning("Mô hình %s không chứa lớp nào cần theo dõi (bỏ qua)", w)
                continue
            self.models.append((model, model.names, ids))
            found.update(model.names[i] for i in ids)

        missing = sorted(wanted - found)
        if missing:
            log.warning("Mô hình không có các lớp: %s (bỏ qua)", ", ".join(missing))
        if not self.models:
            raise ValueError("Mô hình không chứa lớp nào trong threat_classes/person_class.")
        log.info("Theo dõi các lớp: %s", ", ".join(sorted(found)))

    def _load(self, YOLO, weights):
        """Nạp mô hình; với backend openvino thì chuyển .pt sang OpenVINO (lần đầu) để chạy nhanh hơn trên CPU Intel."""
        if self.backend != "openvino" or not weights.endswith(".pt"):
            return YOLO(weights)
        ov_dir = weights[:-3] + "_openvino_model"
        if not os.path.isdir(ov_dir):
            log.info("Chuyển %s sang OpenVINO (chỉ làm lần đầu, mất khoảng 1 phút)...", weights)
            YOLO(weights).export(format="openvino", imgsz=self.imgsz, half=True)
        return YOLO(ov_dir, task="detect")

    def _predict(self, model, class_ids, images):
        return model.predict(
            images,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            device=self.device,
            classes=class_ids,
            verbose=False,
        )

    @staticmethod
    def _parse(result, names, ox=0, oy=0):
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)
        return [
            Detection(
                class_name=names[c],
                confidence=float(s),
                box=(float(b[0] + ox), float(b[1] + oy), float(b[2] + ox), float(b[3] + oy)),
            )
            for b, s, c in zip(xyxy, confs, clss)
        ]

    def detect(self, frame):
        tiled = self.tiling.get("enabled")
        detections = []
        for model, names, ids in self.models:
            if tiled:
                detections.extend(self._detect_tiled(model, names, ids, frame))
            else:
                detections.extend(self._parse(self._predict(model, ids, frame)[0], names))
        if self.class_conf:
            detections = [d for d in detections if d.confidence >= self.class_conf.get(d.class_name, 0)]
        if tiled or len(self.models) > 1:
            return self._merge(detections)
        return detections

    def _detect_tiled(self, model, names, ids, frame):
        h, w = frame.shape[:2]
        tiles = generate_tiles(w, h, int(self.tiling["tile_size"]), float(self.tiling["overlap"]))

        # Ảnh toàn cảnh cho vật thể lớn + các ô cho vật thể nhỏ
        detections = self._parse(self._predict(model, ids, frame)[0], names)
        if len(tiles) <= 1:
            return detections  # ảnh nhỏ hơn 1 ô (ví dụ webcam 640x480): chia ô chỉ chạy trùng lần nữa
        for x1, y1, x2, y2 in tiles:
            res = self._predict(model, ids, frame[y1:y2, x1:x2])[0]
            detections.extend(self._parse(res, names, x1, y1))
        return detections

    def _merge(self, detections):
        """Gộp kết quả trùng (giữa các ô / các mô hình) theo từng lớp."""
        merged = []
        for name in {d.class_name for d in detections}:
            group = [d for d in detections if d.class_name == name]
            boxes = [d.box for d in group]
            keep = drop_contained(boxes, nms(boxes, [d.confidence for d in group], self.iou))
            merged.extend(group[i] for i in keep)
        return merged
