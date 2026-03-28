# Susu Cloud Local Ops Handoff

Last updated: 2026-03-28 20:18 HKT

## Workspace

- Main workspace:
  - `C:\Users\ding7\Documents\gpt-susu-cloud`
- Active branch:
  - `codex/susu-cloud`
- Current local HEAD:
  - check `git log --oneline -1` in this workspace

## Production Authority

- Local development authority:
  - `C:\Users\ding7\Documents\gpt-susu-cloud`
- Production authority host:
  - `Tokyo`
- Production runtime files:
  - `/var/www/html/wa_agent.py`
  - `/var/www/html/api_server.py`
  - `/var/www/html/susu-memory-admin.html`
- Production services:
  - `wa-agent.service`
  - `cheungchau-api.service`

## Production Status

Checked on 2026-03-28 20:13 HKT:

- `wa-agent.service` = `active`
- `cheungchau-api.service` = `active`
- `http://127.0.0.1:9100/health` currently shows:
  - `primary_model = claude-opus-4-6`
  - `fallback_model = ""`
  - `proactive_enabled = true`
  - `proactive_scan_seconds = 300`
  - `proactive_min_silence_minutes = 45`
  - `proactive_cooldown_minutes = 180`

## Current Runtime Notes

- Susu normal chat is locked to `claude-opus-4-6`
- Tokyo service-environment probe was re-verified on 2026-03-28:
  - `generate_model_text("Reply with ok only.") -> "ok"`
- Reply generation is handled through a reply worker plus cancellable subprocess
- Typing indicator now refreshes periodically while generation is still active

## Recent Local Commits

- `a4b5fc2` `Update handoff backup retention note`
- `e165c70` `Add local Susu handoff note`
- `71b648e` `Keep WhatsApp typing indicator alive`
- `005c201` `Harden generic live search grounding`

## Backup Retention

Retention rule currently applied on Tokyo:

- keep latest `3` backups for:
  - `wa_agent.py`
  - `api_server.py`
  - `susu-memory-admin.html`
- keep latest `1` backup for:
  - `wa_agent.db`

Current kept backups:

- `/var/www/html/wa_agent.py.bak.20260328195958`
- `/var/www/html/wa_agent.py.bak.20260328194113`
- `/var/www/html/wa_agent.py.bak.20260328193731`
- `/var/www/html/api_server.py.bak.20260328182723`
- `/var/www/html/api_server.py.bak.20260328135757`
- `/var/www/html/api_server.py.bak.20260328134352`
- `/var/www/html/susu-memory-admin.html.bak.20260328182723`
- `/var/www/html/susu-memory-admin.html.bak.20260328143617`
- `/var/www/html/susu-memory-admin.html.bak.20260328140309`
- `/var/www/html/wa_agent.db.bak.20260328142143`

## Safe Continue Workflow

If continuing Susu runtime work:

1. Edit in `C:\Users\ding7\Documents\gpt-susu-cloud`
2. Run local `python -m py_compile wa_agent.py`
3. Backup the target file on Tokyo before upload
4. Upload changed file(s) to `/var/www/html/`
5. Restart:
   - `wa-agent.service`
   - `cheungchau-api.service`
6. Verify:
   - `systemctl is-active`
   - `curl -s http://127.0.0.1:9100/health`

## File Ownership

- Runtime logic:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\wa_agent.py`
- Admin API:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\api_server.py`
- Admin UI:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu-memory-admin.html`

## Git Note

- Do not push this workspace back into unrelated remotes such as `simond-photo`
- Keep commits local unless the correct Susu remote is explicitly configured
