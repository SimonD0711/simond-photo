# Susu Cloud Local Handoff

Last updated: 2026-03-28 20:13 HKT

## Workspace

- Main workspace: `C:\Users\ding7\Documents\gpt-susu-cloud`
- Current branch: `codex/susu-cloud`
- Current local HEAD: check `git log --oneline -1` in this workspace
- Local git status when this note was updated: clean

## Authority And Deployment

- Local development authority: this workspace
- Production authority host: `Tokyo`
- Production file paths:
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
- `http://127.0.0.1:9100/health` returns:
  - `primary_model = claude-opus-4-6`
  - `fallback_model = ""`
  - `proactive_enabled = true`

## Current Model Routing

- Susu chat generation is locked to `claude-opus-4-6`
- No runtime fallback path is used for normal replies
- `Gemini`, `Groq`, and other legacy helpers may still exist in code, but the active reply chain is Opus-only
- Claude Opus 4.6 was re-verified on Tokyo on 2026-03-28:
  - `generate_model_text("Reply with ok only.") -> "ok"`

## Recent Changes

### 1. Generic live-search grounding

Latest commit: `005c201` (`Harden generic live search grounding`)

What changed:

- Live search is no longer allowed to jump straight from weak search results into freeform summarization
- The chain is now:
  - router decides whether search is needed
  - results are fetched
  - lightweight reviewer decides `answer` / `refine` / `abstain`
  - if needed, query is refined and searched again once
  - if evidence is still weak, Susu refuses cleanly instead of filling gaps
- Follow-up prompts like `快啲幫我查啦` can inherit the previous search topic from recent inbound history
- Ranking/chart questions are only one example of this hardening, not the whole feature

Observed behavior after deployment:

- `宝宝你帮我看一下现在华语音乐榜前十都是边首歌呀`
  now returns a conservative answer saying the current results are not complete enough to safely list songs
- `快啲帮我查啦`
  now stays on the previous search topic instead of drifting
- `你知唔知今天香港有咩大新聞呀`
  still returns a live-search answer normally
- `而家特朗普係唔係總統`
  still returns a live-search answer normally

### 2. WhatsApp typing indicator pacing

Latest commit: `71b648e` (`Keep WhatsApp typing indicator alive`)

What changed:

- On inbound:
  - Susu marks the latest inbound message as read immediately
  - typing does not show if the reply is ready within `0.5s`
  - if generation exceeds `0.5s`, typing starts
  - typing is refreshed every `4.0s` while the reply is still being generated
  - refresh stops as soon as:
    - a newer inbound message supersedes the old reply job, or
    - the actual outbound reply is about to be sent

Relevant env knobs:

- `WA_TYPING_INDICATOR_DELAY_SECONDS` default `0.5`
- `WA_TYPING_INDICATOR_REFRESH_SECONDS` default `4.0`

### 3. Reply worker architecture

Still active from earlier work:

- fixed inbound 5-second delay was removed
- each contact uses a reply worker
- reply generation runs in a cancellable subprocess
- if a second or third message arrives before send, the old generation job is terminated locally and replaced by a combined reply job

## Search Notes

Current live-search modes:

- `weather`
- `news`
- `music`
- `web`

Current safety posture:

- search summaries must stay grounded in returned results
- when evidence is too weak, Susu should abstain instead of guessing
- ranking/list/count questions are intentionally stricter than normal latest-info questions

## Recent Tokyo Backups

Remote backup retention was cleaned on 2026-03-28 20:13 HKT.

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

Retention rule currently applied:

- keep latest `3` backups for:
  - `wa_agent.py`
  - `api_server.py`
  - `susu-memory-admin.html`
- keep latest `1` backup for:
  - `wa_agent.db`

## Key Files

- Local runtime logic:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\wa_agent.py`
- Local admin API:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\api_server.py`
- Local admin page:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu-memory-admin.html`

## Safe Continue Workflow

If continuing Susu work:

1. Edit in `C:\Users\ding7\Documents\gpt-susu-cloud`
2. Run local `python -m py_compile wa_agent.py` first
3. Backup Tokyo target file before upload
4. Upload changed file(s) to `/var/www/html/`
5. Restart:
   - `wa-agent.service`
   - `cheungchau-api.service`
6. Verify:
   - `systemctl is-active`
   - `curl -s http://127.0.0.1:9100/health`

## Git Notes

- This workspace should not be pushed back into `simond-photo`
- Keep commits local unless an explicitly correct remote is configured for Susu
