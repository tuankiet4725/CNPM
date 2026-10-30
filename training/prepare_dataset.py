"""Tải và chuyển bộ dữ liệu súng Subh775/WeaponDetection (Hugging Face, CC-BY-4.0) sang định dạng YOLO.

Bộ gốc có 29 nhãn lộn xộn (Guns/guns, pistol/pistols...), được gộp về 2 lớp:
    0: gun    (súng ngắn)
    1: rifle  (súng dài: súng trường, shotgun, súng hạng nặng)
Ảnh chứa nhãn mơ hồ ("weapon", "weapons", "al") bị bỏ để không dạy sai mô hình.
Người, dao... không nằm trong mô hình này: mô hình COCO yolov8n.pt vẫn đảm nhận.

Ví dụ:
    python training/prepare_dataset.py
    python training/train.py --data datasets/weapons_gun/data.yaml --model yolov8n.pt --imgsz 416
"""

import argparse
import io
import os

import pyarrow.parquet as pq
import yaml
from huggingface_hub import hf_hub_download
from PIL import Image

REPO = "Subh775/WeaponDetection"
NAMES = ["gun", "rifle"]

GUN = {"Guns", "Guns perspective", "Pistol", "guns", "handgun", "pistol", "pistols"}
RIFLE = {"Heavy Gun", "Long guns", "Rifle", "Shotgun", "heavyweapon", "larga", "rifle", "shotgun"}
AMBIGUOUS = {"weapon", "weapons", "al"}

SPLITS = {"train": "train", "validation": "val", "test": "test"}


def category_names(pf):
    import json

    info = json.loads(pf.schema_arrow.metadata[b"huggingface"])
    return info["info"]["features"]["objects"]["feature"]["category"]["names"]


def convert_split(parquet_path, out_dir, split):
    pf = pq.ParquetFile(parquet_path)
    names = category_names(pf)
    img_dir = os.path.join(out_dir, "images", split)
    lbl_dir = os.path.join(out_dir, "labels", split)
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)

    kept = skipped = 0
    for batch in pf.iter_batches(batch_size=256):
        for row in batch.to_pylist():
            cats = [names[c] for c in row["objects"]["category"]]
            if AMBIGUOUS & set(cats):
                skipped += 1
                continue

            w, h = row["width"], row["height"]
            lines = []
            for (x, y, bw, bh), name in zip(row["objects"]["bbox"], cats):
                cls = 0 if name in GUN else 1 if name in RIFLE else None
                if cls is None or bw <= 0 or bh <= 0:
                    continue
                cx = min(max((x + bw / 2) / w, 0.0), 1.0)
                cy = min(max((y + bh / 2) / h, 0.0), 1.0)
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {min(bw / w, 1.0):.6f} {min(bh / h, 1.0):.6f}")

            # Ảnh không có súng (chỉ người, dao...) vẫn giữ làm ảnh "âm" (nhãn rỗng)
            stem = f"{split}_{row['image_id']}"
            img = Image.open(io.BytesIO(row["image"]["bytes"])).convert("RGB")
            img.save(os.path.join(img_dir, stem + ".jpg"), quality=95)
            with open(os.path.join(lbl_dir, stem + ".txt"), "w") as f:
                f.write("\n".join(lines))
            kept += 1
    print(f"{split}: {kept} ảnh, bỏ {skipped} ảnh nhãn mơ hồ")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", default="datasets/raw/WeaponDetection", help="Thư mục chứa file parquet tải về")
    p.add_argument("--out", default="datasets/weapons_gun")
    args = p.parse_args()

    for hf_split, split in SPLITS.items():
        path = hf_hub_download(REPO, f"data/{hf_split}-00000-of-00001.parquet",
                               repo_type="dataset", local_dir=args.raw)
        convert_split(path, args.out, split)

    # Đường dẫn tuyệt đối để Ultralytics không tìm nhầm thư mục datasets mặc định
    data = {
        "path": os.path.abspath(args.out),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": dict(enumerate(NAMES)),
    }
    yaml_path = os.path.join(args.out, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    print(f"Đã tạo {yaml_path}")


if __name__ == "__main__":
    main()
