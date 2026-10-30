# Đặc tả yêu cầu phần mềm (SRS)

**Tên hệ thống:** Phần mềm phát hiện vũ khí, dao, gậy dùng camera UAV
**Phiên bản:** 1.0

## 1. Giới thiệu

### 1.1 Mục đích
Hỗ trợ lực lượng an ninh, bảo vệ giám sát khu vực rộng (sự kiện đông người, khu công nghiệp, biên giới, khu dân cư)
bằng drone, tự động phát hiện người mang hung khí và cảnh báo kịp thời.

### 1.2 Phạm vi
- Nhận video từ camera UAV qua nhiều giao thức.
- Phát hiện vũ khí (dao, gậy, súng, mã tấu...) và người bằng trí tuệ nhân tạo.
- Đánh giá mức độ đe doạ, cảnh báo đa kênh, lưu bằng chứng.
- Không bao gồm: điều khiển bay drone, nhận dạng danh tính khuôn mặt.

### 1.3 Thuật ngữ
| Thuật ngữ | Giải thích |
|---|---|
| UAV | Unmanned Aerial Vehicle – phương tiện bay không người lái (drone) |
| YOLO | You Only Look Once – mô hình phát hiện đối tượng thời gian thực |
| RTSP/RTMP | Giao thức truyền video trực tiếp |
| Track | Một đối tượng được theo vết qua nhiều khung hình, có ID riêng |
| Tiling | Chia ảnh thành các ô nhỏ để phát hiện vật thể nhỏ |

## 2. Mô tả tổng quan

### 2.1 Tác nhân
| Tác nhân | Vai trò |
|---|---|
| Người vận hành | Khởi động hệ thống, theo dõi video và cảnh báo tại trạm điều khiển |
| Chỉ huy / giám sát viên | Xem dashboard từ xa, nhận cảnh báo Telegram, tra cứu lịch sử |
| Kỹ sư AI | Huấn luyện, cập nhật mô hình |
| Camera UAV | Hệ thống ngoài, cung cấp luồng video |

### 2.2 Môi trường hoạt động
- Windows 10/11 hoặc Linux, Python 3.10+.
- Tối thiểu: CPU 4 nhân, RAM 8 GB. Khuyến nghị: GPU NVIDIA (CUDA) để đạt ≥ 15 FPS.

## 3. Yêu cầu chức năng

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-01 | Nhận video từ webcam/capture card, file, RTSP, RTMP, UDP | Cao |
| FR-02 | Tự động kết nối lại khi mất tín hiệu video | Cao |
| FR-03 | Phát hiện dao, gậy, súng, mã tấu và người trên từng khung hình | Cao |
| FR-04 | Phát hiện vật thể nhỏ bằng chế độ chia ô (tuỳ chọn) | Trung bình |
| FR-05 | Theo vết đối tượng, gán ID qua các khung hình | Cao |
| FR-06 | Phân loại mức đe doạ 4 mức; tăng mức khi vũ khí ở gần người | Cao |
| FR-07 | Chỉ cảnh báo khi đối tượng xuất hiện ≥ N khung liên tiếp | Cao |
| FR-08 | Không lặp cảnh báo cùng loại trong thời gian cooldown | Trung bình |
| FR-09 | Hiển thị khung bao, nhãn, mức độ, FPS lên video; viền đỏ khi có cảnh báo | Cao |
| FR-10 | Phát âm thanh cảnh báo | Trung bình |
| FR-11 | Gửi cảnh báo kèm ảnh qua Telegram | Trung bình |
| FR-12 | Lưu ảnh chụp bằng chứng và sự kiện vào CSDL | Cao |
| FR-13 | Dashboard web: video trực tiếp, thống kê, lịch sử cảnh báo | Cao |
| FR-14 | Ghi lại video kết quả (tuỳ chọn) | Thấp |
| FR-15 | Cấu hình hệ thống qua file YAML và tham số dòng lệnh | Trung bình |
| FR-16 | Huấn luyện mô hình riêng trên dữ liệu vũ khí | Trung bình |

## 4. Yêu cầu phi chức năng

| Mã | Yêu cầu |
|---|---|
| NFR-01 Hiệu năng | ≥ 15 FPS ở 720p với GPU; ≥ 5 FPS với CPU (yolov8n) |
| NFR-02 Độ trễ | Từ lúc vũ khí xuất hiện đến lúc cảnh báo ≤ 2 giây |
| NFR-03 Độ chính xác | mAP50 ≥ 0.6 trên tập kiểm thử của mô hình tự huấn luyện |
| NFR-04 Tin cậy | Lỗi mạng (Telegram, mất sóng) không làm dừng hệ thống |
| NFR-05 Khả dụng | Giao diện tiếng Việt, cài đặt bằng 1 thao tác (setup.bat) |
| NFR-06 Bảo trì | Kiến trúc module, mỗi thành phần thay thế độc lập; có kiểm thử đơn vị |
| NFR-07 Bảo mật | Ảnh bằng chứng lưu cục bộ; token Telegram nằm trong file cấu hình, không đưa lên kho mã |

## 5. Ràng buộc và giả định
- Độ chính xác phụ thuộc độ cao bay, góc camera, ánh sáng; khuyến nghị độ cao 5–30 m.
- Mô hình COCO mặc định không có lớp súng; cần huấn luyện bổ sung.
- Hệ thống là công cụ **hỗ trợ**, quyết định cuối cùng thuộc về con người.
