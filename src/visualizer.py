"""Vẽ khung phát hiện và thông tin trạng thái lên khung hình."""

import time

import cv2

# Màu BGR theo mức độ đe doạ
LEVEL_COLORS = {
    "low": (0, 220, 255),
    "medium": (0, 140, 255),
    "high": (0, 0, 255),
    "critical": (200, 0, 255),
}
PERSON_COLOR = (80, 200, 80)


def _label(img, text, x, y, color):
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    y = max(y, th + base + 2)
    cv2.rectangle(img, (x, y - th - base - 4), (x + tw + 6, y), color, -1)
    cv2.putText(img, text, (x + 3, y - base - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)


def draw(frame, threats, persons, fps=0.0, alert_active=False, total_alerts=0):
    img = frame.copy()
    h, w = img.shape[:2]

    for p in persons:
        x1, y1, x2, y2 = map(int, p.box)
        cv2.rectangle(img, (x1, y1), (x2, y2), PERSON_COLOR, 1)

    for th in threats:
        d = th.detection
        x1, y1, x2, y2 = map(int, d.box)
        color = LEVEL_COLORS.get(th.level, (0, 0, 255))
        thickness = 3 if th.level in ("high", "critical") else 2
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
        tag = f"{th.display} {d.confidence:.0%} #{d.track_id}"
        if th.near_person:
            tag += " ARMED"
        _label(img, tag, x1, y1, color)

    # Thanh trạng thái
    cv2.rectangle(img, (0, 0), (w, 30), (30, 30, 30), -1)
    status = f"UAV WEAPON DETECTION | FPS {fps:4.1f} | Threats {len(threats)} | Alerts {total_alerts}"
    cv2.putText(img, status, (10, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(img, time.strftime("%H:%M:%S"), (w - 90, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                (255, 255, 255), 1, cv2.LINE_AA)

    # Viền đỏ nhấp nháy khi đang có cảnh báo
    if alert_active and int(time.time() * 4) % 2 == 0:
        cv2.rectangle(img, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)
        _label(img, "!!! WEAPON ALERT !!!", w // 2 - 110, 70, (0, 0, 255))
    return img
