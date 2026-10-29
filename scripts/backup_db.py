import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups"


def get_database_path():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        env_file = PROJECT_ROOT / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8-sig").splitlines():
                key, separator, value = line.partition("=")
                if separator and key.strip() == "DATABASE_URL":
                    database_url = value.strip().strip("\"'")
                    break
    database_url = database_url or "sqlite:///./pet_care.db"

    scheme, separator, database = database_url.partition(":///")
    if not separator or scheme not in {"sqlite", "sqlite+pysqlite"}:
        raise ValueError("Chỉ hỗ trợ backup database SQLite có đường dẫn file.")

    database = database.split("?", 1)[0]
    if not database:
        raise ValueError("DATABASE_URL không chứa đường dẫn file SQLite.")
    database_path = Path(database).expanduser()
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path
    return database_path.resolve()


def _next_backup_path(backup_dir):
    timestamp = datetime.now().replace(microsecond=0)
    for offset in range(60):
        candidate = backup_dir / f"pet_care-backup-{(timestamp + timedelta(seconds=offset)).strftime('%Y%m%d-%H%M%S')}.db"
        if not candidate.exists():
            return candidate
    raise FileExistsError("Không thể tạo tên backup duy nhất trong thư mục backups.")


def create_backup(database_path, backup_dir=BACKUP_DIR):
    database_path = Path(database_path).resolve()
    backup_dir = Path(backup_dir).resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy database hiện tại: {database_path}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = _next_backup_path(backup_dir)

    try:
        with closing(sqlite3.connect(database_path)) as source:
            with closing(sqlite3.connect(backup_path)) as destination:
                source.backup(destination)
                result = destination.execute("PRAGMA integrity_check").fetchone()
                if not result or result[0] != "ok":
                    raise sqlite3.DatabaseError("Backup không vượt qua kiểm tra toàn vẹn SQLite.")
    except (OSError, sqlite3.Error):
        backup_path.unlink(missing_ok=True)
        raise
    return backup_path


def main():
    try:
        database_path = get_database_path()
        backup_path = create_backup(database_path)
    except (FileNotFoundError, FileExistsError, OSError, sqlite3.Error, ValueError) as error:
        print(f"Không thể backup database: {error}", file=sys.stderr)
        return 1

    print(f"Backup thành công: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
