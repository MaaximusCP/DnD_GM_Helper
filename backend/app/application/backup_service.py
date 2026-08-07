import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from app.infrastructure.database import Database


class BackupService:
    def __init__(self, database: Database, backup_dir: Path):
        self.database = database
        self.backup_dir = backup_dir

    def create(self) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = self.backup_dir / f"campaign_backup_{stamp}.db"
        with self.database.connect() as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
        return destination

    def list(self) -> list[dict[str, int | str]]:
        if not self.backup_dir.exists():
            return []
        return [
            {"name": path.name, "size": path.stat().st_size, "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat()}
            for path in sorted(self.backup_dir.glob("campaign_backup_*.db"), reverse=True)
            if path.is_file()
        ]

    def restore(self, name: str) -> Path:
        if Path(name).name != name or not name.startswith("campaign_backup_") or not name.endswith(".db"):
            raise ValueError("Nom de backup no vàlid")
        source_path = (self.backup_dir / name).resolve()
        if source_path.parent != self.backup_dir.resolve() or not source_path.is_file():
            raise FileNotFoundError(name)
        safety_backup = self.create()
        with closing(sqlite3.connect(source_path)) as source:
            with closing(sqlite3.connect(self.database.path)) as target:
                source.backup(target)
        return safety_backup
