from pathlib import Path
import sqlite3
from config import DATABASE_PATH

def backup(path='backups'):
    Path(path).mkdir(parents=True,exist_ok=True); target=Path(path)/'lucky_backup.db'; src=sqlite3.connect(DATABASE_PATH); dst=sqlite3.connect(target)
    try: src.backup(dst)
    finally: dst.close();src.close()
    return target
