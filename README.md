# Lucky

Modular Arabic-first Telegram lottery and entertainment bot.

## Run
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Set `BOT_TOKEN` and comma-separated `ADMIN_IDS`. The wallet uses SQLite transactions and a ledger. Keep `TEST_MODE=true` until all flows are manually tested. Never commit `.env` or a production database.
