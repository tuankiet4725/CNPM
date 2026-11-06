"""Tải và gộp các dataset vũ khí trên Roboflow Universe (góc nhìn drone) thành một bộ YOLO.

Mỗi nguồn là "workspace/project" (tải bằng API key, bản mới nhất) hoặc "workspace/project/phiên_bản",
hoặc đường dẫn tới thư mục đã giải nén từ bản export "YOLOv8" tải tay trên web.

Hai cách gộp lớp (--scheme):
    gop     (mặc định) mọi loại vũ khí -> 1 lớp "weapon". Hợp với góc nhìn từ trên cao, nơi khó phân biệt
            súng/dao, và dùng được cả các dataset chỉ gán nhãn chung "weapon".
    chitiet gun / rifle / knife. Ảnh chỉ có nhãn chung "weapon" bị bỏ vì không biết là loại nào.
Lớp không phải vũ khí (person, Unlabeled, ...) bị bỏ; ảnh không còn nhãn nào giữ lại làm ảnh "âm".
Ảnh lớn (drone 4K) được cắt thành ô 1280 px để vũ khí không bị thu nhỏ còn vài pixel khi train ở 640.

Ví dụ:
    set ROBOFLOW_API_KEY=xxxxxxxx
    python training/prepare_roboflow.py
    python training/train.py --data datasets/weapons_uav/data.yaml --model yolov8n.pt --imgsz 640 --epochs 30
"""

import argparse
import glob
import os
import random
import shutil
import zlib

import yaml
from PIL import Image

# drone-detection-96cia/anamoly-detection-hnzvs không dùng: tên lớp bị hỏng ("=====...", "weapon detect - v1 ...")
# nên không biết 557 khung là vật gì; gộp vào sẽ biến ảnh có vũ khí thành ảnh "âm".
# dulooj/air-rjoqk không dùng: là dataset phân loại ảnh (multilabel-classification), không có khung bao.
DEFAULT_SOURCES = [
    "visiontechdroneproject/drone-weapon-our-drone",
    "teamdrone/weapon.detect",
]

GUN = {"gun", "guns", "pistol", "pistols", "handgun", "revolver", "glock"}
RIFLE = {"rifle", "rifles", "shotgun", "machine gun", "machinegun", "smg", "sniper", "sniper rifle", "assault rifle",
         "ak47", "ak-47", "long gun", "long guns", "heavy gun", "heavyweapon", "rocket launcher"}
KNIFE = {"knife", "knives", "machete", "sword", "dagger", "blade", "katana", "cleaver", "cutlass", "sickle"}
GENERIC = {"weapon", "weapons", "arma", "armas"}
# Vũ khí khác: lớp "weapon" ở cách gộp; ở cách chi tiết thì bỏ cả ảnh (không thuộc gun/rifle/knife)
OTHER = {"axe", "mace", "bow", "crossbow", "grenade", "hammer", "war hammer", "morningstar", "spear", "bomb"}

SCHEMES = {"gop": ["weapon"], "chitiet": ["gun", "rifle", "knife"]}
SPLITS = {"train": "train", "valid": "val", "val": "val", "test": "test"}


def target_class(name, scheme):
    """Trả về chỉ số lớp đích, None nếu bỏ nhãn, "skip" nếu phải bỏ cả ảnh."""
    n = name.strip().lower()
    if scheme == "gop":
        return 0 if n in GUN | RIFLE | KNIFE | GENERIC | OTHER else None
    if n in GUN:
        return 0
    if n in RIFLE:
        return 1
    if n in KNIFE:
        return 2
    return "skip" if n in GENERIC | OTHER else None


def download(source, raw_dir, api_key):
    if os.path.isdir(source):
        return source
    from roboflow import Roboflow

    parts = source.strip("/").split("/")
    ws, name = parts[0], parts[1]
    rf = Roboflow(api_key=api_key)
    project = rf.workspace(ws).project(name)
    if len(parts) > 2:
        ver = int(parts[2])
    else:
        ver = max(int(str(v.version).split("/")[-1]) for v in project.versions())
    location = os.path.join(raw_dir, f"{ws}__{name}__v{ver}")
    if not os.path.isdir(location):
        project.version(ver).download("yolov8", location=location)
    return location


def class_names(ds_dir):
    with open(os.path.join(ds_dir, "data.yaml"), encoding="utf-8") as f:
        names = yaml.safe_load(f)["names"]
    return names if isinstance(names, list) else [names[k] for k in sorted(names)]


def merge(ds_dir, out_dir, scheme, tag, stats, tile=0, neg_per_image=1):
    rng = random.Random(0)
    names = class_names(ds_dir)
    has_val = any(os.path.isdir(os.path.join(ds_dir, s, "images")) for s in ("valid", "val"))
    for src_split, split0 in SPLITS.items():
        img_dir = os.path.join(ds_dir, src_split, "images")
        if not os.path.isdir(img_dir):
            continue
        for s in ("train", "val", "test"):
            os.makedirs(os.path.join(out_dir, "images", s), exist_ok=True)
            os.makedirs(os.path.join(out_dir, "labels", s), exist_ok=True)
        for img in glob.glob(os.path.join(img_dir, "*")):
            split = split0
            # Không có tập valid: tách 15% theo ẢNH GỐC trước khi cắt ô, để các ô của cùng một ảnh
            # không rơi vào cả train lẫn val (điểm đánh giá sẽ cao giả)
            if split0 == "train" and not has_val and zlib.crc32(os.path.basename(img).encode()) % 100 < 15:
                split = "val"
            stem = os.path.splitext(os.path.basename(img))[0]
            lbl = os.path.join(ds_dir, src_split, "labels", stem + ".txt")
            lines, skip = [], False
            if os.path.exists(lbl):
                for row in open(lbl, encoding="utf-8").read().split("\n"):
                    parts = row.split()
                    if len(parts) != 5:
                        continue  # bỏ nhãn đa giác / dòng lỗi
                    cls = target_class(names[int(parts[0])], scheme)
                    if cls == "skip":
                        skip = True
                        break
                    if cls is not None:
                        lines.append(" ".join([str(cls)] + parts[1:]))
            if skip:
                stats["skipped"] += 1
                continue
            new = f"{tag}_{stem}"
            with Image.open(img) as im:
                w, h = im.size
                if tile and max(w, h) > tile * 1.25:
                    pieces = slice_image(im.convert("RGB"), lines, tile, neg_per_image, rng)
                else:
                    pieces = None
            if pieces is None:
                shutil.copy(img, os.path.join(out_dir, "images", split, new + os.path.splitext(img)[1]))
                pieces_out = [(new, lines)]
                with open(os.path.join(out_dir, "labels", split, new + ".txt"), "w") as f:
                    f.write("\n".join(lines))
            else:
                pieces_out = []
                for k, (crop, crop_lines) in enumerate(pieces):
                    name = f"{new}_t{k}"
                    crop.save(os.path.join(out_dir, "images", split, name + ".jpg"), quality=92)
                    with open(os.path.join(out_dir, "labels", split, name + ".txt"), "w") as f:
                        f.write("\n".join(crop_lines))
                    pieces_out.append((name, crop_lines))
            for _, pl in pieces_out:
                stats[split] += 1
                stats["boxes"] += len(pl)
                stats["negative"] += not pl


def slice_image(im, lines, tile, neg_per_image, rng, overlap=0.2, min_keep=0.6, neg_keep=0.35):
    """Cắt ảnh lớn (drone 4K) thành các ô tile x tile chồng lấn.

    Giữ mọi ô có vũ khí (khung bị cắt còn >= min_keep diện tích) và tối đa neg_per_image ô không có gì
    làm ảnh âm. Ô cắt ngang một khung (còn < min_keep) bị bỏ, vì không phải ảnh âm cũng không gán nhãn đủ.
    """
    w, h = im.size
    # Ảnh âm nên ~10-20% tập train; giữ ô âm của mỗi ảnh lớn với xác suất neg_keep
    if rng.random() >= neg_keep:
        neg_per_image = 0
    boxes = []
    for ln in lines:
        c, cx, cy, bw, bh = ln.split()
        cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
        boxes.append((c, cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2))
    step = int(tile * (1 - overlap))
    xs = list(range(0, max(w - tile, 0) + 1, step)) or [0]
    ys = list(range(0, max(h - tile, 0) + 1, step)) or [0]
    if xs[-1] + tile < w:
        xs.append(w - tile)
    if ys[-1] + tile < h:
        ys.append(h - tile)
    pos, neg = [], []
    for y in ys:
        for x in xs:
            x2, y2 = min(x + tile, w), min(y + tile, h)
            out, partial = [], False
            for c, b1, b2, b3, b4 in boxes:
                ix1, iy1, ix2, iy2 = max(b1, x), max(b2, y), min(b3, x2), min(b4, y2)
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                if inter <= 0:
                    continue
                if inter < min_keep * (b3 - b1) * (b4 - b2):
                    partial = True
                    continue
                tw, th = x2 - x, y2 - y
                out.append(f"{c} {((ix1 + ix2) / 2 - x) / tw:.6f} {((iy1 + iy2) / 2 - y) / th:.6f} "
                           f"{(ix2 - ix1) / tw:.6f} {(iy2 - iy1) / th:.6f}")
            if out:
                pos.append(((x, y, x2, y2), out))
            elif not partial:
                neg.append(((x, y, x2, y2), []))
    rng.shuffle(neg)
    return [(im.crop(r), ls) for r, ls in pos + neg[:neg_per_image]]


def ensure_val(out_dir, ratio=0.15):
    """Dataset không có tập valid: tách ngẫu nhiên (cố định seed) một phần ảnh train làm val."""
    import random

    val_dir = os.path.join(out_dir, "images", "val")
    if os.path.isdir(val_dir) and os.listdir(val_dir):
        return
    imgs = sorted(glob.glob(os.path.join(out_dir, "images", "train", "*")))
    random.Random(0).shuffle(imgs)
    os.makedirs(val_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "labels", "val"), exist_ok=True)
    n_val = max(1, int(len(imgs) * ratio)) if len(imgs) > 1 else 0
    for img in imgs[:n_val]:
        stem = os.path.splitext(os.path.basename(img))[0]
        shutil.move(img, val_dir)
        shutil.move(os.path.join(out_dir, "labels", "train", stem + ".txt"), os.path.join(out_dir, "labels", "val"))
    print(f"Không có tập val: đã tách {n_val} ảnh từ train")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sources", nargs="*", default=DEFAULT_SOURCES,
                   help="workspace/project[/version] hoặc thư mục export YOLOv8 đã giải nén")
    p.add_argument("--scheme", choices=SCHEMES, default="gop")
    p.add_argument("--raw", default="datasets/raw/roboflow")
    p.add_argument("--out", default="datasets/weapons_uav")
    p.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY"))
    p.add_argument("--tile", type=int, default=1280,
                   help="Cắt ảnh lớn hơn 1,25 lần giá trị này thành ô vuông (0 = không cắt). Ảnh drone 4K -> ô 1280")
    p.add_argument("--neg-per-image", type=int, default=1, help="Số ô không có vũ khí giữ lại mỗi ảnh lớn")
    args = p.parse_args()

    if any(not os.path.isdir(s) for s in args.sources) and not args.api_key:
        p.error("Cần API key Roboflow: đặt biến ROBOFLOW_API_KEY hoặc --api-key "
                "(lấy tại https://app.roboflow.com/settings/api)")

    os.makedirs(args.raw, exist_ok=True)
    for source in args.sources:
        ds_dir = download(source, args.raw, args.api_key)
        tag = os.path.basename(os.path.normpath(ds_dir)).replace(".", "_")
        stats = {"train": 0, "val": 0, "test": 0, "boxes": 0, "negative": 0, "skipped": 0}
        merge(ds_dir, args.out, args.scheme, tag, stats, args.tile, args.neg_per_image)
        print(f"{source}: lớp gốc {class_names(ds_dir)}")
        print(f"   train {stats['train']} · val {stats['val']} · test {stats['test']} ảnh, "
              f"{stats['boxes']} khung, {stats['negative']} ảnh âm, bỏ {stats['skipped']} ảnh")

    ensure_val(args.out)
    data = {"path": os.path.abspath(args.out), "train": "images/train", "val": "images/val",
            "names": dict(enumerate(SCHEMES[args.scheme]))}
    if os.path.isdir(os.path.join(args.out, "images", "test")):
        data["test"] = "images/test"
    yaml_path = os.path.join(args.out, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    print(f"Đã tạo {yaml_path}")


if __name__ == "__main__":
    main()
