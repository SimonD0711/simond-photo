# Susu Cloud Local Ops Handoff

Last updated: 2026-03-31 03:05 HKT

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
  - `/var/www/html/susu_admin_core.py`
  - `/var/www/html/susu_admin_server.py`
  - `/var/www/html/susu-memory-admin.html`
- Production services:
  - `wa-agent.service`
  - `cheungchau-api.service`
  - `susu-admin-api.service`
  - `sillytavern-bridge.service`
  - `susu-brain-backend.service`

## Production Status

Checked on 2026-03-31 03:05 HKT:

- `wa-agent.service` = `active`
- `cheungchau-api.service` = `active`
- `susu-admin-api.service` = `active`
- `sillytavern-bridge.service` = `active`
- `susu-brain-backend.service` = `active`
- `http://127.0.0.1:9100/health` currently shows:
  - `brain_provider = sillytavern`
  - `bridge_brain_enabled = true`
- `http://127.0.0.1:9102/health` currently shows:
  - `service = susu_brain_bridge`
  - `upstream_mode = agnai`
- `http://127.0.0.1:9103/health` currently shows:
  - `service = susu_brain_backend`

## Current Runtime Notes

- Susu production chat now runs through:
  - `wa_agent.py -> sillytavern_bridge_server.py -> susu_brain_backend.py -> relay`
- The backend model is still `claude-opus-4-6`, but the shell now uses the bridge-backed provider
- Reply generation is still handled through a reply worker plus cancellable subprocess
- Typing indicator still refreshes periodically while generation is active
- Susu admin API is now fully split from the photo API:
  - Susu admin: `127.0.0.1:9001`, `susu-admin-api.service`
  - Photo admin/site API: `127.0.0.1:9000`, `cheungchau-api.service`

## Recent Local Commits

- `dff992c` `Extract Susu admin core from photo API`
- `d810083` `Tighten clue handling and backend retries`
- `1a30dcc` `Add local Susu brain backend service`
- `9c0dcfd` `Add Agnai-style backend bridge adapter`

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
5. Restart only the affected services:
   - runtime / chat: `wa-agent.service`
   - photo admin/site API: `cheungchau-api.service`
   - Susu admin API: `susu-admin-api.service`
   - bridge: `sillytavern-bridge.service`
   - brain backend: `susu-brain-backend.service`
6. Verify:
   - `systemctl is-active`
   - `curl -s http://127.0.0.1:9100/health`

## File Ownership

- Runtime logic:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\wa_agent.py`
- Photo/admin API:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\api_server.py`
- Susu admin core:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu_admin_core.py`
- Susu admin API:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu_admin_server.py`
- Admin UI:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu-memory-admin.html`
- Brain bridge:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\sillytavern_bridge_server.py`
- Brain backend:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu_brain_backend.py`

## Git Note

- Do not push this workspace back into unrelated remotes such as `simond-photo`
- Keep commits local unless the correct Susu remote is explicitly configured
