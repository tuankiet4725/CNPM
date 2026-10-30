"""Phần mềm phát hiện vũ khí, dao, gậy từ camera UAV.

Ví dụ:
    python main.py                               # dùng config.yaml (webcam 0)
    python main.py --source video/drone.mp4
    python main.py --source rtsp://192.168.1.10:8554/live --tiling
    python main.py --weights yolov8n.pt models/weapon_best.pt --no-display
"""

import argparse
import logging
import os
import sys

from src.config import load_config


def parse_args():
    p = argparse.ArgumentParser(description="Phát hiện vũ khí từ camera UAV")
    p.add_argument("--config", default="config.yaml", help="File cấu hình YAML")
    p.add_argument("--source", help="Nguồn video: chỉ số webcam, file, rtsp://, rtmp://, udp://")
    p.add_argument("--weights", nargs="+", help="File trọng số YOLO (.pt), có thể nhiều file")
    p.add_argument("--conf", type=float, help="Ngưỡng tin cậy")
    p.add_argument("--device", help='"cpu" hoặc "0" (GPU)')
    p.add_argument("--tiling", action="store_true", help="Bật suy luận chia ô cho vật thể nhỏ")
    p.add_argument("--no-display", action="store_true", help="Không mở cửa sổ OpenCV")
    p.add_argument("--no-web", action="store_true", help="Tắt bảng điều khiển web")
    p.add_argument("--record", action="store_true", help="Ghi video kết quả")
    return p.parse_args()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    args = parse_args()
    cfg = load_config(args.config)

    if args.source is not None:
        cfg["source"] = args.source
    if args.weights:
        cfg["model"]["weights"] = args.weights
    if args.conf is not None:
        cfg["model"]["conf"] = args.conf
    if args.device is not None:
        cfg["model"]["device"] = args.device
    if args.tiling:
        cfg["tiling"]["enabled"] = True
    if args.no_display:
        cfg["display"] = False
    if args.no_web:
        cfg["web"]["enabled"] = False
    if args.record:
        cfg["record"]["enabled"] = True

    from src.pipeline import DetectionPipeline

    try:
        DetectionPipeline(cfg).run()
    except Exception as e:
        logging.exception("Lỗi: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
