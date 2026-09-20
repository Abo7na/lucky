import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "lucky.db"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
if not BOT_TOKEN: raise RuntimeError("BOT_TOKEN is required")
if not ADMIN_IDS: raise RuntimeError("ADMIN_IDS is required")
