"""Hàm tiện ích hình học: IoU, NMS, chia ô ảnh."""

import time

import numpy as np


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def nms(boxes, scores, iou_threshold):
    """Non-Maximum Suppression, trả về chỉ số các box được giữ lại."""
    boxes = np.asarray(boxes, dtype=float)
    scores = np.asarray(scores, dtype=float)
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes.T
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        rest = order[1:]
        xx1 = np.maximum(x1[i], x1[rest])
        yy1 = np.maximum(y1[i], y1[rest])
        xx2 = np.minimum(x2[i], x2[rest])
        yy2 = np.minimum(y2[i], y2[rest])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        overlap = inter / (areas[i] + areas[rest] - inter + 1e-9)
        order = rest[overlap <= iou_threshold]
    return keep


def drop_contained(boxes, keep, ratio=0.8):
    """Bỏ box nằm gần trọn (>= ratio diện tích) trong một box lớn hơn.

    Khi chia ô, vật thể bị đường cắt ô đi qua sinh ra box "một nửa" nằm trong box đầy đủ;
    IoU giữa chúng thấp nên NMS không loại được.
    """
    boxes = np.asarray(boxes, dtype=float)
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1]) if len(boxes) else []
    result = []
    for i in sorted(keep, key=lambda k: areas[k], reverse=True):
        b = boxes[i]
        inside = False
        for j in result:
            o = boxes[j]
            inter = max(0.0, min(b[2], o[2]) - max(b[0], o[0])) * max(0.0, min(b[3], o[3]) - max(b[1], o[1]))
            if inter >= ratio * areas[i]:
                inside = True
                break
        if not inside:
            result.append(i)
    return result


def generate_tiles(width, height, tile_size, overlap):
    """Sinh toạ độ các ô (x1, y1, x2, y2) phủ kín ảnh, có chồng lấn."""
    step = max(1, int(tile_size * (1 - overlap)))

    def starts(length):
        pos = list(range(0, max(length - tile_size, 0) + 1, step))
        if pos[-1] + tile_size < length:
            pos.append(length - tile_size)
        return pos

    return [
        (x, y, min(x + tile_size, width), min(y + tile_size, height))
        for y in starts(height)
        for x in starts(width)
    ]


class FPSMeter:
    def __init__(self, smoothing=0.9):
        self.smoothing = smoothing
        self.fps = 0.0
        self._last = None

    def tick(self):
        now = time.perf_counter()
        if self._last is not None:
            dt = now - self._last
            if dt > 0:
                inst = 1.0 / dt
                self.fps = inst if self.fps == 0 else self.smoothing * self.fps + (1 - self.smoothing) * inst
        self._last = now
        return self.fps
