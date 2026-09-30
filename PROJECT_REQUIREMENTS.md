# Đối chiếu yêu cầu đề tài

| Yêu cầu | Đã triển khai |
|---|---|
| Quản lý thú cưng | `pets`, CRUD + giao diện |
| Lịch chăm sóc | `care_schedules`, trạng thái pending/done/missed |
| Hồ sơ chăm sóc | `care_records` |
| Hóa đơn, thanh toán | `invoices`, unpaid/paid |
| Phân quyền quản lý/lễ tân/nhân viên/chủ nuôi | JWT + role `admin/reception/caregiver/user` |
| AI nhắc lịch | Notification tự động từ lịch + AI nêu cảnh báo |
| AI tóm tắt hồ sơ | `POST /api/ai/summary/{pet_id}` |
| AI hỏi đáp cơ bản | `POST /api/ai/chat` |
| Cảnh báo bỏ sót lịch | Lịch quá hạn tự chuyển `missed` và tạo notification |
| Lịch sử chat AI | bảng `ai_chats` + `/api/ai/history` |
| Dữ liệu AI | pet profile + care history + schedule |
| Prompt mẫu | README + báo cáo + phụ lục |
| AI trong SDLC | Báo cáo Chương 4 và Chương 6 |
| Công nghệ | FastAPI + HTML/CSS/JS + SQLite; Gemini tùy chọn |
| Fallback khi AI lỗi | `services/ai_service.py` |
| Cảnh báo thú y | AI prompt/fallback yêu cầu khuyên liên hệ bác sĩ khi có dấu hiệu nguy hiểm |
