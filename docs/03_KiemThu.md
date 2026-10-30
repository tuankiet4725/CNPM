# Kế hoạch kiểm thử

## 1. Chiến lược
| Mức | Phương pháp | Công cụ |
|---|---|---|
| Kiểm thử đơn vị | Kiểm tra từng module logic không cần mô hình | pytest (`tests/`) |
| Kiểm thử tích hợp | Chạy toàn bộ pipeline với video mẫu | `python main.py --source video/test.mp4` |
| Kiểm thử hệ thống | Bay thực tế với drone, kịch bản có/không vũ khí | Drone + máy tính trạm |
| Đánh giá mô hình | mAP, Precision, Recall trên tập test | `model.val()` của Ultralytics |

Chạy kiểm thử đơn vị:

```bash
python -m pytest -v
```

## 2. Ca kiểm thử đơn vị (tự động)

| Mã | Module | Mô tả | Kết quả mong đợi |
|---|---|---|---|
| UT-01 | utils.iou | Hai hộp trùng nhau / tách rời | 1.0 / 0.0 |
| UT-02 | utils.nms | Hai hộp chồng lấn lớn + một hộp xa | Giữ 2 hộp |
| UT-03 | utils.generate_tiles | Ảnh 1920×1080 | Các ô phủ kín ảnh, ô ≤ 640 |
| UT-04 | utils.generate_tiles | Ảnh nhỏ hơn ô | 1 ô bằng cả ảnh |
| UT-05 | tracker | Cùng vật thể dịch nhẹ | Giữ nguyên ID, hits = 2 |
| UT-06 | tracker | Khác lớp cùng vị trí | ID khác nhau |
| UT-07 | tracker | Mất dấu quá max_missed | Track bị xoá |
| UT-08 | tracker | Mất dấu ngắn | Giữ ID cũ |
| UT-09 | threat | Dao trong tay người | Mức critical, near_person = True |
| UT-10 | threat | Lớp không thuộc danh sách | Bỏ qua |
| UT-11 | alert | Chỉ 2 khung (< 3) | Không cảnh báo |
| UT-12 | alert | 10 khung liên tiếp | Đúng 1 cảnh báo, lưu 1 bản ghi CSDL |
| UT-13 | alert | Lớp mức thấp (kéo) | Không cảnh báo |

## 3. Ca kiểm thử hệ thống (thủ công)

| Mã | Kịch bản | Bước thực hiện | Kết quả mong đợi |
|---|---|---|---|
| ST-01 | Kết nối webcam | `python main.py --source 0` | Hiển thị video, FPS > 0 |
| ST-02 | Kết nối RTSP | Chạy với URL RTSP hợp lệ | Hiển thị video từ UAV |
| ST-03 | Mất sóng | Tắt nguồn phát trong 10 giây rồi bật lại | Log "Mất tín hiệu", tự kết nối lại, không thoát |
| ST-04 | Phát hiện dao | Người cầm dao trong khung hình 3 giây | Khung đỏ, nhãn KNIFE ARMED, viền nhấp nháy, tiếng bíp |
| ST-05 | Cooldown | Dao xuất hiện, biến mất, xuất hiện lại sau 5 giây | Chỉ 1 cảnh báo (cooldown 10 giây) |
| ST-06 | Báo động giả | Người cầm điện thoại, ô | Không cảnh báo |
| ST-07 | Dashboard | Mở `http://localhost:5000` | Video, thống kê, lịch sử cập nhật mỗi 2 giây |
| ST-08 | Telegram | Bật telegram, tạo tình huống có dao | Nhận tin nhắn kèm ảnh |
| ST-09 | Mất mạng Internet | Ngắt mạng khi đang gửi Telegram | Ghi log lỗi, hệ thống vẫn chạy |
| ST-10 | Độ cao bay | Bay ở 5 m, 15 m, 30 m có/không tiling | Ghi nhận tỉ lệ phát hiện để so sánh |
| ST-11 | Ghi video | `--record` | Có file .mp4 trong `output/recordings` |

## 4. Tiêu chí chấp nhận
- 100% ca kiểm thử đơn vị đạt.
- ST-01 đến ST-07 đạt.
- Tỉ lệ phát hiện dao ở độ cao ≤ 15 m ≥ 70%; báo động giả ≤ 1 lần / 10 phút giám sát.
