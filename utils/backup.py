import os, shutil, sqlite3
from pathlib import Path
from config import DATABASE_PATH

def backup(path='backups'):
    Path(path).mkdir(exist_ok=True); target=Path(path)/'lucky_backup.db'; src=sqlite3.connect(DATABASE_PATH); dst=sqlite3.connect(target)
    try: src.backup(dst)
    finally: dst.close();src.close()
    return target
