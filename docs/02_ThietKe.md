# Thiết kế hệ thống

## 1. Sơ đồ use case

```mermaid
flowchart LR
    OP([Người vận hành])
    CMD([Chỉ huy])
    AI([Kỹ sư AI])
    UAV([Camera UAV])

    subgraph Hệ thống phát hiện vũ khí
        UC1(Kết nối nguồn video)
        UC2(Giám sát video trực tiếp)
        UC3(Phát hiện & đánh giá đe doạ)
        UC4(Nhận cảnh báo)
        UC5(Xem lịch sử & ảnh bằng chứng)
        UC6(Cấu hình hệ thống)
        UC7(Huấn luyện mô hình)
    end

    UAV --> UC1
    OP --> UC1
    OP --> UC2
    OP --> UC6
    UC2 -. include .-> UC3
    UC3 -. extend .-> UC4
    OP --> UC4
    CMD --> UC4
    CMD --> UC5
    AI --> UC7
```

## 2. Kiến trúc

Kiến trúc dạng **pipeline** (ống dẫn – bộ lọc), mỗi bước là một module độc lập:

```mermaid
flowchart LR
    A[VideoSource] --> B[WeaponDetector<br/>YOLOv8 + tiling]
    B --> C[IoUTracker]
    C --> D[ThreatAssessor]
    D --> E[Visualizer]
    E --> F[AlertManager]
    F --> G[(EventDatabase<br/>SQLite)]
    F --> H[Notifiers<br/>Âm thanh / Telegram]
    F --> I[Snapshot .jpg]
    E --> J[Cửa sổ OpenCV]
    E --> K[Web Flask<br/>MJPEG + REST API]
    G --> K
```

| Module | Trách nhiệm |
|---|---|
| `video_source.py` | Mở nguồn video, luồng nền đọc khung mới nhất, tự kết nối lại |
| `detector.py` | Nạp YOLOv8, suy luận thường hoặc chia ô, gộp kết quả bằng NMS |
| `tracker.py` | Ghép detection với track cũ theo IoU, đếm số khung liên tiếp |
| `threat.py` | Ánh xạ lớp → mức đe doạ, tăng mức khi vũ khí gần người |
| `alert.py` | Lọc theo mức tối thiểu, số khung, cooldown; lưu ảnh, CSDL, gọi notifier |
| `notifier.py` | Phát âm thanh, gửi Telegram (chạy luồng riêng, không chặn) |
| `database.py` | Lưu/truy vấn sự kiện, thống kê |
| `visualizer.py` | Vẽ khung, nhãn, thanh trạng thái, viền cảnh báo |
| `web.py` | Dashboard, luồng MJPEG, API `/api/events`, `/api/stats` |
| `pipeline.py` | Điều phối toàn bộ các module |

### Mẫu thiết kế áp dụng
- **Pipeline / Pipes and Filters**: luồng xử lý tuần tự qua các bước.
- **Observer**: `AlertManager` thông báo tới danh sách `notifiers`.
- **Strategy**: `WeaponDetector` chọn chiến lược suy luận thường hoặc chia ô.
- **Producer–Consumer**: luồng đọc video và luồng xử lý trao đổi qua khung hình dùng chung có khoá.

## 3. Sơ đồ lớp

```mermaid
classDiagram
    class Detection { class_name; confidence; box; track_id }
    class Threat { detection; label; display; level; near_person }
    class Alert { id; timestamp; class_name; label; level; confidence; track_id; snapshot }
    class Track { track_id; class_name; box; hits; missed; alerted_level }
    class VideoSource { start(); read(); stop() }
    class WeaponDetector { detect(frame) List~Detection~ }
    class IoUTracker { update(detections) List~Track~ }
    class ThreatAssessor { assess(detections) }
    class AlertManager { process(frame, threats, tracks) List~Alert~ }
    class EventDatabase { add_event(); recent(); stats() }
    class Notifier { <<interface>> notify(alert) }
    class DetectionPipeline { run(); process_frame() }

    DetectionPipeline --> VideoSource
    DetectionPipeline --> WeaponDetector
    DetectionPipeline --> IoUTracker
    DetectionPipeline --> ThreatAssessor
    DetectionPipeline --> AlertManager
    AlertManager --> EventDatabase
    AlertManager --> Notifier
    Notifier <|.. SoundNotifier
    Notifier <|.. TelegramNotifier
    Threat *-- Detection
    IoUTracker o-- Track
```

## 4. Sơ đồ tuần tự – xử lý một khung hình

```mermaid
sequenceDiagram
    participant P as Pipeline
    participant V as VideoSource
    participant D as Detector
    participant T as Tracker
    participant TA as ThreatAssessor
    participant A as AlertManager
    participant DB as Database
    participant N as Notifier

    P->>V: read()
    V-->>P: frame
    P->>D: detect(frame)
    D-->>P: detections
    P->>T: update(detections)
    T-->>P: tracks
    P->>TA: assess(detections)
    TA-->>P: threats, persons
    P->>A: process(frame, threats, tracks)
    alt đủ N khung, mức ≥ min_level, hết cooldown
        A->>A: lưu ảnh chụp
        A->>DB: add_event()
        A->>N: notify(alert)
    end
    A-->>P: alerts mới
```

## 5. Thiết kế dữ liệu

Bảng `events` (SQLite):

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| id | INTEGER PK | Mã sự kiện |
| timestamp | TEXT | Thời gian `YYYY-MM-DD HH:MM:SS` |
| class_name | TEXT | Lớp mô hình (knife, gun...) |
| label | TEXT | Tên tiếng Việt |
| level | TEXT | low / medium / high / critical |
| confidence | REAL | Độ tin cậy 0–1 |
| track_id | INTEGER | ID đối tượng |
| near_person | INTEGER | 1 nếu ở gần người |
| snapshot | TEXT | Đường dẫn ảnh |
| source | TEXT | Nguồn video |

## 6. Thuật toán chính

**Đánh giá đe doạ:** mức cơ sở lấy theo lớp trong `config.yaml`. Nếu khung vũ khí giao với khung người
được mở rộng thêm 30% → coi là "trong tay người", tăng 1 mức (ví dụ dao: cao → nghiêm trọng).

**Chống báo động giả:** một track chỉ được cảnh báo khi `hits ≥ min_consecutive_frames`; mỗi track chỉ
cảnh báo lại khi mức độ tăng; mỗi cặp (lớp, mức) có thời gian cooldown.

**Tiling:** ảnh được chia thành các ô 640×640 chồng lấn 20%, suy luận theo lô cùng ảnh toàn cảnh,
toạ độ được dịch về ảnh gốc rồi gộp bằng NMS theo từng lớp.
