import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from backup_db import BACKUP_DIR, create_backup, get_database_path


def _validate_backup(backup_path):
    try:
        with closing(sqlite3.connect(backup_path)) as backup:
            result = backup.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as error:
        raise ValueError(f"Không đọc được file backup SQLite: {error}") from error
    if not result or result[0] != "ok":
        raise ValueError("File backup không vượt qua kiểm tra toàn vẹn SQLite.")


def restore_database(backup_path, database_path):
    backup_path = Path(backup_path).resolve()
    database_path = Path(database_path).resolve()
    if not backup_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file backup: {backup_path}")
    if backup_path == database_path:
        raise ValueError("File backup không được trùng với database hiện tại.")
    if not database_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy database hiện tại để backup an toàn: {database_path}")

    _validate_backup(backup_path)
    safety_backup = create_backup(database_path, BACKUP_DIR)
    try:
        with closing(sqlite3.connect(backup_path)) as source:
            with closing(sqlite3.connect(database_path)) as destination:
                source.backup(destination)
                result = destination.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise sqlite3.DatabaseError("Database sau restore không vượt qua kiểm tra toàn vẹn.")
    except (OSError, sqlite3.Error) as error:
        raise RuntimeError(
            f"Restore gặp lỗi. Backup an toàn của database trước khi restore: {safety_backup}"
        ) from error
    return safety_backup


def main():
    parser = argparse.ArgumentParser(
        description="Khôi phục pet_care.db từ một file backup SQLite."
    )
    parser.add_argument("backup_file", help="Đường dẫn file backup cần khôi phục")
    args = parser.parse_args()

    try:
        database_path = get_database_path()
        backup_path = Path(args.backup_file).expanduser()
        if not backup_path.is_absolute():
            backup_path = Path(__file__).resolve().parent.parent / backup_path
        backup_path = backup_path.resolve()
        if not backup_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file backup: {backup_path}")
        if backup_path == database_path:
            raise ValueError("File backup không được trùng với database hiện tại.")
        _validate_backup(backup_path)
    except (FileNotFoundError, OSError, sqlite3.Error, ValueError) as error:
        print(f"Không thể bắt đầu restore: {error}", file=sys.stderr)
        return 1

    print("CẢNH BÁO: Restore sẽ ghi đè toàn bộ database hiện tại.")
    print("Hãy dừng ứng dụng PetCare AI trước khi tiếp tục.")
    print(f"Database đích: {database_path}")
    print(f"File backup:   {backup_path}")
    try:
        confirmation = input("Nhập RESTORE để xác nhận: ")
    except (EOFError, KeyboardInterrupt):
        print("\nĐã hủy restore; database không thay đổi.")
        return 1
    if confirmation != "RESTORE":
        print("Đã hủy restore; database không thay đổi.")
        return 1

    try:
        safety_backup = restore_database(backup_path, database_path)
    except (FileNotFoundError, OSError, sqlite3.Error, ValueError, RuntimeError) as error:
        print(f"Restore thất bại: {error}", file=sys.stderr)
        return 1

    print(f"Restore thành công từ: {backup_path}")
    print(f"Backup an toàn trước restore: {safety_backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
