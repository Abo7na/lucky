# Lucky

Admin commands: `/stats`, `/pending`, `/approve_deposit ID`, `/reject_deposit ID`, `/approve_withdraw ID`, `/reject_withdraw ID`, `/draw`, `/ledger`, `/backup`.

Before deployment:
```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```
Keep `TEST_MODE=true` until all financial flows are manually tested. Never commit `.env` or a production database.
