import os
import sys

# Cho phép import các module ở thư mục gốc project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from database import get_db
from models import User


pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


DEMO_ADMIN_EMAIL = os.getenv("DEMO_ADMIN_EMAIL", "admin@petcare.local")
DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD", "")
DEMO_ADMIN_NAME = os.getenv("DEMO_ADMIN_NAME", "Quản trị viên")

DEMO_CUSTOMER_EMAIL = os.getenv(
    "DEMO_CUSTOMER_EMAIL",
    "customer@petcare.local",
)
DEMO_CUSTOMER_PASSWORD = os.getenv("DEMO_CUSTOMER_PASSWORD", "")
DEMO_CUSTOMER_NAME = os.getenv("DEMO_CUSTOMER_NAME", "Khách hàng Demo")


def upsert_user(db, email, password, full_name, role):
    if not password or password.casefold().startswith("change_me_"):
        raise RuntimeError(
            f"Chưa cấu hình mật khẩu cho {email}. "
            "Hãy kiểm tra file .env."
        )

    user = db.query(User).filter_by(email=email.lower()).first()

    if user:
        user.password_hash = pwd.hash(password)
        user.full_name = full_name
        user.role = role
        user.status = "active"
        print(f"Đã cập nhật: {email} ({role})")
    else:
        user = User(
            email=email.lower(),
            password_hash=pwd.hash(password),
            full_name=full_name,
            role=role,
            status="active",
        )
        db.add(user)
        print(f"Đã tạo: {email} ({role})")


def main():
    db = next(get_db())

    try:
        upsert_user(
            db,
            DEMO_ADMIN_EMAIL,
            DEMO_ADMIN_PASSWORD,
            DEMO_ADMIN_NAME,
            "admin",
        )

        upsert_user(
            db,
            DEMO_CUSTOMER_EMAIL,
            DEMO_CUSTOMER_PASSWORD,
            DEMO_CUSTOMER_NAME,
            "user",
        )

        db.commit()

        print()
        print("=== TẠO TÀI KHOẢN THÀNH CÔNG ===")
        print(f"Admin:    {DEMO_ADMIN_EMAIL}")
        print(f"Customer: {DEMO_CUSTOMER_EMAIL}")

    finally:
        db.close()


if __name__ == "__main__":
    main()