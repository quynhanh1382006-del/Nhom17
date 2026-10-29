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
```

Trước khi chạy lần đầu, hãy thay `SECRET_KEY` và `ADMIN_PASSWORD` trong `.env` bằng các giá trị mạnh, riêng biệt. Có thể tạo JWT secret bằng:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ứng dụng từ chối khởi động nếu `SECRET_KEY` thiếu hoặc còn là placeholder. `ADMIN_PASSWORD` phải được thay placeholder nếu ứng dụng cần tạo tài khoản admin ban đầu. Không commit `.env` lên GitHub.

```powershell
py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Mở `http://127.0.0.1:8000/login`.

## 4. Chạy bằng Docker Compose

Cài và khởi động Docker Desktop trước. Từ thư mục gốc project, tạo `.env` từ file mẫu nếu chưa có:

```powershell
Copy-Item .env.example .env
```

Giữ nguyên `pet_care.db` hiện có trong thư mục gốc. Compose bind-mount file này vào container tại `/app/pet_care.db`; không tạo database mới và dữ liệu được giữ lại sau khi container restart hoặc được dừng bằng `docker compose down`.

### A. Chạy

```powershell
docker compose up -d --build
```

### B. Kiểm tra trạng thái và log

```powershell
docker compose ps
docker compose logs -f
```

### C. URL

- Web: http://localhost:8000/
- Đăng nhập: http://localhost:8000/login
- API Docs: http://localhost:8000/docs

### D. Dừng container

```powershell
docker compose down
```

Không dùng `docker compose down -v` trong thao tác thông thường. Không xóa `pet_care.db` hoặc thư mục `backups/`.

### E. Khởi động lại sau khi đã dừng

```powershell
docker compose up -d
```

### F. Restart container

```powershell
docker compose restart
```

### G. Backup SQLite

```powershell
py scripts/backup_db.py
```

### H. Restore SQLite

**Dừng container trước khi restore.** Restore sẽ ghi đè database hiện tại, yêu cầu nhập chính xác `RESTORE` để xác nhận và script tự tạo safety backup trước khi thực hiện.

```powershell
py scripts/restore_db.py backups\<ten-file-backup>.db
```

Không xóa `pet_care.db` hoặc thư mục `backups/`.

### I. Cấu hình AI

- `AI_PROVIDER=mock` là chế độ mặc định/an toàn; không yêu cầu Gemini API key.
- Chỉ đặt `GEMINI_API_KEY` trong file `.env` nếu muốn sử dụng Gemini.
- Không commit `.env` lên GitHub.
- Không ghi API key thật vào Dockerfile, `docker-compose.yml` hoặc source code.

### J. Tài khoản demo

File `.env.example` có email admin mẫu và placeholder cho mật khẩu; phải thay placeholder bằng mật khẩu mạnh trước khi chạy. Ứng dụng chỉ tạo tài khoản admin nếu email đó chưa tồn tại. Không có tài khoản user/owner demo hoặc mật khẩu user/owner được ghi rõ trong tài liệu hiện tại; có thể đăng ký user/owner mới từ trang đăng nhập.

## 5. Cấu hình Gemini
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
Chỉ lưu API key thật trong `.env` cục bộ; không commit file này lên GitHub. Nếu để `AI_PROVIDER=mock` hoặc không có key, hệ thống vẫn chạy bằng logic hỗ trợ nội bộ.

## 6. Prompt mẫu
**System:** Bạn là trợ lý chăm sóc thú cưng. Dựa trên hồ sơ thú cưng và lịch chăm sóc, hãy trả lời ngắn gọn, dễ hiểu; không chẩn đoán bệnh. Nếu có dấu hiệu nguy hiểm, khuyên người dùng liên hệ bác sĩ thú y.

**User:** “Thú cưng này sắp tới có lịch gì? Nếu có lịch bỏ sót thì nhắc tôi. Tóm tắt hồ sơ chăm sóc và trả lời câu hỏi của tôi.”

## 7. Backup và Restore SQLite

Các lệnh dưới đây chạy từ thư mục gốc của project. Database được xác định theo `DATABASE_URL` trong `.env` (mặc định là `pet_care.db`).

### Backup

```powershell
py scripts/backup_db.py
```

File backup được tạo trong thư mục `backups/` theo tên `pet_care-backup-YYYYMMDD-HHMMSS.db`. Thư mục này sẽ tự được tạo nếu chưa có. Script dùng API backup của SQLite, phù hợp để tạo bản sao nhất quán khi database đang được sử dụng.

### Restore

**Cảnh báo: Restore sẽ ghi đè toàn bộ database hiện tại. Hãy dừng ứng dụng trước khi chạy.** Script sẽ yêu cầu nhập chính xác `RESTORE` để xác nhận và tự tạo backup an toàn của database hiện tại trong `backups/` trước khi khôi phục.

```powershell
py scripts/restore_db.py backups\<ten-file-backup>.db
```

Nếu không xác nhận, database hiện tại sẽ không bị thay đổi. Không xóa hoặc sửa file backup an toàn được tạo trước khi restore.
