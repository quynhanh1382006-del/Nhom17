# Hệ thống quản lý thú cưng và lịch chăm sóc tích hợp AI

## 1. Giới thiệu
Ứng dụng web xây dựng bằng **FastAPI + HTML/CSS/JavaScript + SQLite**, tích hợp **Gemini** (tùy chọn) để quản lý thú cưng, hồ sơ chăm sóc, lịch nhắc, hóa đơn và hỏi đáp chăm sóc cơ bản.

## 2. Chức năng chính
- Đăng ký/đăng nhập và phân quyền `admin`, `reception`, `caregiver`, `user`.
- Quản lý thú cưng: tên, loài, giống, giới tính, ngày sinh, cân nặng, ghi chú y tế.
- Quản lý danh mục dịch vụ: tên, mô tả, giá, thời lượng và trạng thái; chủ nuôi chỉ xem dịch vụ đang hoạt động.
- Quản lý hồ sơ chăm sóc: tiêm phòng, tẩy giun, grooming, khám sức khỏe, thuốc.
- Quản lý lịch chăm sóc, tùy chọn gắn dịch vụ và tự phát hiện lịch bị bỏ sót.
- Nhắc lịch sắp đến theo số ngày cấu hình.
- Hóa đơn và trạng thái thanh toán.
- AI tóm tắt hồ sơ, hỏi đáp cơ bản, cảnh báo lịch bỏ sót và lưu lịch sử tương tác.
- AI fallback cục bộ khi chưa cấu hình API key.

## 3. Chạy dự án
```powershell
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
Copy-Item .env.example .env
py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Mở `http://127.0.0.1:8000/login`.

Trước khi chạy, thay `SECRET_KEY` và `ADMIN_PASSWORD` trong `.env` bằng các giá trị mạnh, riêng biệt. Có thể tạo JWT secret bằng:
```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```
Ứng dụng sẽ báo lỗi cấu hình nếu `SECRET_KEY` chưa được đặt hoặc còn là placeholder. Nếu cần tạo tài khoản admin ban đầu, cũng phải đặt `ADMIN_PASSWORD` khác placeholder. Không commit `.env` hoặc ghi secrets thật vào source code.

## 4. Cấu hình AI
Trong `.env`, chọn một provider:

Chế độ fallback cục bộ (mặc định), không gọi Gemini:
```dotenv
AI_PROVIDER=mock
```

Chế độ Gemini:
```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```
Không lưu API key thật vào source code. Khi chọn Gemini nhưng thiếu key, Gemini lỗi hoặc trả kết quả trống, ứng dụng ghi cảnh báo an toàn ở server và dùng fallback cục bộ. Giá trị `AI_PROVIDER` không hợp lệ cũng dùng fallback. Các trường hợp fallback trả `source: "Fallback"`.

## 5. Chức năng AI và an toàn
- **Hỏi đáp chăm sóc:** `POST /api/ai/chat` dùng thông tin thú cưng, hồ sơ chăm sóc và lịch chăm sóc được phép truy cập; lưu lịch sử tương tác.
- **Tóm tắt hồ sơ:** `POST /api/ai/summary/{pet_id}` tóm tắt hồ sơ và các lịch sắp tới/quá hạn. Fallback tạo bản tóm tắt có cấu trúc trực tiếp từ dữ liệu đã lưu.
- **Soạn tin nhắc lịch:** `POST /api/ai/reminder/{schedule_id}` tạo nội dung nhắc theo lịch, thú cưng và dịch vụ liên kết (nếu có); Gemini không khả dụng thì dùng mẫu cục bộ.
- Các endpoint AI yêu cầu đăng nhập và kiểm tra quyền truy cập thú cưng/lịch theo quyền hiện tại.
- AI chỉ cung cấp hỗ trợ quản lý và thông tin chăm sóc tham khảo; không chẩn đoán, không đưa kết luận y khoa chắc chắn và không thay thế bác sĩ thú y. Với dấu hiệu cấp cứu như khó thở, co giật, chảy máu nhiều, nghi ngộ độc hoặc bất tỉnh, cần liên hệ cơ sở thú y ngay.

Gemini chỉ sử dụng khi cấu hình `AI_PROVIDER=gemini` và có `GEMINI_API_KEY`; `AI_PROVIDER=mock` tuyệt đối không gọi Gemini.
