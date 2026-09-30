# Hệ thống quản lý thú cưng và lịch chăm sóc tích hợp AI

## 1. Giới thiệu
Ứng dụng web xây dựng bằng **FastAPI + HTML/CSS/JavaScript + SQLite**, tích hợp **Gemini** (tùy chọn) để quản lý thú cưng, hồ sơ chăm sóc, lịch nhắc, hóa đơn và hỏi đáp chăm sóc cơ bản.

## 2. Chức năng chính
- Đăng ký/đăng nhập và phân quyền `admin`, `reception`, `caregiver`, `user`.
- Quản lý thú cưng: tên, loài, giống, giới tính, ngày sinh, cân nặng, ghi chú y tế.
- Quản lý hồ sơ chăm sóc: tiêm phòng, tẩy giun, grooming, khám sức khỏe, thuốc.
- Quản lý lịch chăm sóc và tự phát hiện lịch bị bỏ sót.
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

## 4. Cấu hình Gemini
Trong `.env`:
```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```
Nếu để `AI_PROVIDER=mock` hoặc không có key, hệ thống vẫn chạy bằng logic hỗ trợ nội bộ.

## 5. Prompt mẫu
**System:** Bạn là trợ lý chăm sóc thú cưng. Dựa trên hồ sơ thú cưng và lịch chăm sóc, hãy trả lời ngắn gọn, dễ hiểu; không chẩn đoán bệnh. Nếu có dấu hiệu nguy hiểm, khuyên người dùng liên hệ bác sĩ thú y.

**User:** “Thú cưng này sắp tới có lịch gì? Nếu có lịch bỏ sót thì nhắc tôi. Tóm tắt hồ sơ chăm sóc và trả lời câu hỏi của tôi.”
