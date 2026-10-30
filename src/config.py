"""Đọc và chuẩn hoá file cấu hình YAML."""

import copy

import yaml

DEFAULT_THREAT_CLASSES = {
    "knife": {"label": "Dao", "display": "KNIFE", "level": "high"},
    "baseball bat": {"label": "Gậy bóng chày", "display": "BAT", "level": "medium"},
    "scissors": {"label": "Kéo", "display": "SCISSORS", "level": "low"},
}

DEFAULTS = {
    "source": 0,
    "model": {"weights": "yolov8n.pt", "conf": 0.35, "iou": 0.45, "imgsz": 640, "device": ""},
    "tiling": {"enabled": False, "tile_size": 640, "overlap": 0.2},
    "tracker": {"iou_threshold": 0.2, "max_missed": 15},
    "person_class": "person",
    "person_proximity": 0.3,
    "alert": {
        "min_level": "medium",
        "min_consecutive_frames": 3,
        "cooldown_seconds": 10,
        "snapshot_dir": "output/snapshots",
        "sound": True,
        "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
    },
    "database": "output/events.db",
    "display": True,
    "display_min_frames": 1,
    "record": {"enabled": False, "dir": "output/recordings"},
    "web": {"enabled": True, "host": "0.0.0.0", "port": 5000},
}


def deep_merge(base, override):
    """Gộp override vào base (đệ quy với dict con)."""
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # threat_classes được thay thế toàn bộ, không gộp với mặc định
    threats = data.pop("threat_classes", None)
    cfg = deep_merge(DEFAULTS, data)
    cfg["threat_classes"] = threats or copy.deepcopy(DEFAULT_THREAT_CLASSES)
    return cfg
