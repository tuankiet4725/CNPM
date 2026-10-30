# Phần mềm phát hiện vũ khí, dao, gậy từ camera UAV

Hệ thống nhận luồng video từ camera gắn trên drone (UAV), dùng mô hình học sâu **YOLOv8** để phát hiện
dao, gậy, súng... theo thời gian thực. Khi phát hiện, hệ thống đánh giá mức độ đe doạ, phát cảnh báo,
lưu ảnh bằng chứng và hiển thị trên bảng điều khiển web.

## Tính năng

| Tính năng | Mô tả |
|---|---|
| Đa nguồn video | Webcam / bộ thu sóng (capture card), file video, RTSP, RTMP, UDP (DJI Tello) |
| Tự kết nối lại | Mất sóng UAV thì tự kết nối lại, luôn xử lý khung hình mới nhất (độ trễ thấp) |
| Phát hiện vũ khí | YOLOv8: dao, gậy, kéo (COCO), súng, mã tấu (mô hình tự huấn luyện) |
| Vật thể nhỏ | Chế độ chia ô (tiling) khi drone bay cao |
| Theo vết đối tượng | Gán ID, chỉ cảnh báo khi thấy liên tiếp N khung → giảm báo động giả |
| Đánh giá đe doạ | 4 mức: thấp / trung bình / cao / nghiêm trọng. Vũ khí trong tay người → tăng 1 mức |
| Cảnh báo | Viền đỏ nhấp nháy, âm thanh, Telegram (kèm ảnh), chống lặp (cooldown) |
| Lưu trữ | Ảnh chụp bằng chứng + lịch sử sự kiện trong SQLite, ghi video tuỳ chọn |
| Web dashboard | `http://localhost:5000`: video trực tiếp, thống kê, lịch sử cảnh báo |

## Cài đặt (Windows)

1. Cài **Python 3.10 – 3.12** từ https://www.python.org/downloads/ (tick *Add python.exe to PATH*).
2. Nháy đúp `setup.bat` (tạo môi trường ảo và cài thư viện).
   Có GPU NVIDIA: cài thêm PyTorch CUDA theo hướng dẫn tại https://pytorch.org.
3. Nháy đúp `run.bat`. Lần chạy đầu sẽ tự tải mô hình `yolov8n.pt`.

Cài thủ công:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Sử dụng

```bash
python main.py                                       # theo config.yaml (mặc định webcam 0)
python main.py --source video/drone.mp4              # file video quay từ drone
python main.py --source rtsp://192.168.1.10:8554/live
python main.py --source udp://@0.0.0.0:11111         # DJI Tello
python main.py --source 1 --tiling --record          # capture card + chia ô + ghi video
python main.py --weights yolov8n.pt models/weapon_best.pt  # COCO + mô hình súng tự huấn luyện
python main.py --no-display                          # chạy trên server, xem qua web
```

Nhấn **Q** hoặc **Esc** trong cửa sổ video để thoát. Mọi tham số nằm trong [config.yaml](config.yaml).

### Kết nối camera UAV

- **Drone có bộ phát video analog/HDMI** (FPV): cắm bộ thu vào máy tính qua capture card USB → `--source 1`.
- **DJI (Mini/Air/Mavic)**: bật *Live Streaming → RTMP* trong DJI Fly tới một máy chủ RTMP (ví dụ MediaMTX
  chạy trên máy tính), rồi đọc lại `--source rtsp://localhost:8554/live`.
- **DJI Tello**: kết nối Wi-Fi Tello, gửi lệnh `command` và `streamon` (qua app/SDK), rồi `--source udp://@0.0.0.0:11111`.
- **Camera IP gắn trên UAV**: dùng URL RTSP của camera.

### Cảnh báo Telegram

Tạo bot với @BotFather, lấy `bot_token` và `chat_id`, rồi điền vào `config.yaml` → `alert.telegram`, đặt `enabled: true`.

## Mô hình

Mô hình mặc định `yolov8n.pt` (COCO) chỉ có **knife**, **baseball bat**, **scissors** (tự tải khi chạy lần đầu).

Súng được nhận bằng mô hình thứ hai chạy song song, khai báo trong `config.yaml` → `model.weights`.
File `.pt` không nằm trong kho mã, cần tải về trước khi chạy:

```bash
mkdir models\hf_gun_knife
curl -L -o models/hf_gun_knife/best.pt https://huggingface.co/cosgun99/gun-knife-yolo11n/resolve/main/best.pt
```

(Mô hình [cosgun99/gun-knife-yolo11n](https://huggingface.co/cosgun99/gun-knife-yolo11n), giấy phép MIT.)
Không muốn dùng mô hình súng thì xoá dòng `models/hf_gun_knife/best.pt` khỏi `model.weights`.

Trên máy Intel, `model.backend: openvino` với `device: "intel:gpu"` chạy nhanh hơn PyTorch khoảng 4–5 lần;
máy không có GPU Intel thì đổi `device` thành `"intel:cpu"`, hoặc `backend: pytorch`.

Để phát hiện **mã tấu, gậy** và chính xác hơn ở góc nhìn từ trên cao, xem [training/README.md](training/README.md).

## Cấu trúc dự án

```
UAV_Weapon_Detection/
├── main.py               Điểm khởi chạy, đọc tham số dòng lệnh
├── config.yaml           Cấu hình hệ thống
├── src/
│   ├── config.py         Đọc cấu hình
│   ├── video_source.py   Đọc video UAV (đa nguồn, tự kết nối lại)
│   ├── detector.py       Phát hiện bằng YOLOv8, hỗ trợ tiling
│   ├── tracker.py        Theo vết đối tượng bằng IoU
│   ├── threat.py         Đánh giá mức độ đe doạ
│   ├── alert.py          Quản lý cảnh báo
│   ├── notifier.py       Âm thanh, Telegram
│   ├── database.py       Lưu sự kiện SQLite
│   ├── visualizer.py     Vẽ kết quả lên khung hình
│   ├── web.py            Máy chủ web Flask
│   └── pipeline.py       Ghép toàn bộ luồng xử lý
├── templates/index.html  Giao diện dashboard
├── training/             Huấn luyện mô hình riêng
├── tests/                Kiểm thử đơn vị (pytest)
├── docs/                 Tài liệu CNPM: đặc tả, thiết kế, kiểm thử
└── output/               Ảnh chụp, CSDL, video (tự tạo khi chạy)
```

## Kiểm thử

```bash
python -m pytest -v
```

## Tài liệu

- [docs/01_DacTaYeuCau.md](docs/01_DacTaYeuCau.md) – Đặc tả yêu cầu phần mềm
- [docs/02_ThietKe.md](docs/02_ThietKe.md) – Thiết kế kiến trúc, use case, sơ đồ tuần tự
- [docs/03_KiemThu.md](docs/03_KiemThu.md) – Kế hoạch và ca kiểm thử
