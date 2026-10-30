"""Huấn luyện mô hình YOLOv8 phát hiện vũ khí trên bộ dữ liệu riêng.

Ví dụ:
    python training/train.py --data training/data.yaml --model yolov8s.pt --epochs 100
Sau khi huấn luyện, mô hình tốt nhất được chép vào models/weapon_best.pt.
"""

import argparse
import os
import shutil

from ultralytics import YOLO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="training/data.yaml")
    p.add_argument("--model", default="yolov8s.pt", help="Mô hình khởi tạo (yolov8n/s/m.pt)")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=960, help="Ảnh UAV nên dùng kích thước lớn cho vật thể nhỏ")
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--device", default="")
    p.add_argument("--fraction", type=float, default=1.0, help="Tỉ lệ ảnh train dùng (0-1), giảm để chạy nhanh trên CPU")
    args = p.parse_args()

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device or None,
        project="runs/weapon",
        name="train",
        patience=20,
        fraction=args.fraction,
        # Tăng cường dữ liệu phù hợp góc nhìn từ trên cao
        degrees=15.0,
        flipud=0.5,
        fliplr=0.5,
        scale=0.5,
        mosaic=1.0,
    )
    metrics = model.val()
    print(f"mAP50: {metrics.box.map50:.3f}  mAP50-95: {metrics.box.map:.3f}")

    best = os.path.join(str(model.trainer.save_dir), "weights", "best.pt")
    os.makedirs("models", exist_ok=True)
    shutil.copy(best, "models/weapon_best.pt")
    print("Đã lưu models/weapon_best.pt")


if __name__ == "__main__":
    main()
