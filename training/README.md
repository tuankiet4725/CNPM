# Huấn luyện mô hình vũ khí

Mô hình mặc định `yolov8n.pt` (COCO) chỉ nhận ra **dao (knife)**, **gậy bóng chày (baseball bat)** và **kéo (scissors)**.
Muốn phát hiện **súng, mã tấu, gậy gộc**, hoặc phát hiện tốt hơn ở góc nhìn từ drone, cần huấn luyện mô hình riêng.

## Cách nhanh: mô hình súng từ dữ liệu có sẵn

Bộ [Subh775/WeaponDetection](https://huggingface.co/datasets/Subh775/WeaponDetection) (CC-BY-4.0, ~9.000 ảnh)
được gộp về 2 lớp `gun` (súng ngắn) và `rifle` (súng dài). Bộ này gần như không có dao, nên mô hình mới
chạy **song song** với `yolov8n.pt` (COCO vẫn lo người, dao, gậy bóng chày, kéo).

```bash
python training/prepare_dataset.py        # tải ~580 MB, tạo datasets/weapons_gun/
python training/train.py --data datasets/weapons_gun/data.yaml --model yolov8n.pt --imgsz 416 --epochs 30
```

Chỉ có CPU thì một epoch trên toàn bộ dữ liệu mất khoảng 50 phút (CPU 4 nhân). Thêm `--fraction 0.3`
để chỉ dùng 30% ảnh (nhanh hơn ~3 lần, kém chính xác hơn). Xong thì sửa `config.yaml`:

```yaml
model:
  weights: [yolov8n.pt, models/weapon_best.pt]
```

## 1. Chuẩn bị dữ liệu

Một số nguồn dữ liệu công khai:
- Roboflow Universe: tìm "weapon detection", "knife detection", "gun detection" rồi xuất ở định dạng **YOLOv8**.
- VisDrone (ảnh từ drone, có lớp người) để mô hình quen góc nhìn từ trên cao.
- Tự quay bằng drone ở độ cao 5–30 m, rồi gán nhãn bằng Roboflow, CVAT hoặc LabelImg.

Gộp các bộ về chung một danh sách lớp như trong [data.yaml](data.yaml), đặt vào:

```
datasets/weapons/
  images/train  images/val  images/test
  labels/train  labels/val  labels/test
```

Gợi ý: tỉ lệ 70/20/10; có ảnh "âm" (người cầm điện thoại, ô, chai nước) để giảm báo động giả.

## 2. Huấn luyện

```bash
python training/train.py --data training/data.yaml --model yolov8s.pt --epochs 100 --imgsz 960
```

Có GPU NVIDIA thì thêm `--device 0`. Kết quả nằm ở `runs/weapon/train`, mô hình tốt nhất được chép vào `models/weapon_best.pt`.

## 3. Sử dụng

Sửa `config.yaml`:

```yaml
model:
  weights: models/weapon_best.pt
```

Kiểm tra các lớp trong `threat_classes` trùng với `names` trong `data.yaml`.
