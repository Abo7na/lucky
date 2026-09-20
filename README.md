# Lucky

Modular Arabic-first Telegram lottery and entertainment bot.

Admin commands:
- `/stats` dashboard counts.
- `/pending` list deposit/withdrawal requests.
- `/approve_deposit ID` and `/reject_deposit ID`.
- `/approve_withdraw ID` and `/reject_withdraw ID`.
- `/draw` close the active lottery and choose winners from individual ticket rows.
- `/ledger` inspect recent balance transactions.
- `/backup` create a WAL-safe database backup.

Run tests before deployment:
```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```
Keep `TEST_MODE=true` until every financial flow is manually tested with a test account.
