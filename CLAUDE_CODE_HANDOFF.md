# Susu WhatsApp Agent Handoff For Claude Code

Last updated: 2026-03-31 HKT

## 1. Project Background

This project is an actively used WhatsApp-based AI companion called "Susu".

Primary product goal:

- make Susu feel like a believable WhatsApp girlfriend / companion
- preserve strong WhatsApp-native behavior
- keep memory, reminders, proactive messaging, search, and admin tooling under operator control

This is not just a chat demo. It already has:

- real WhatsApp runtime behavior
- message persistence
- memory layers
- reminders
- proactive messages
- admin UI
- grounded live search
- reply worker recovery

Current core weakness:

- the runtime / product shell is relatively mature
- the "conversation brain" is still too prompt-driven
- Susu is often weak at implicit intent tracking and multi-turn task state

Because of that, the current recommended direction is:

- keep the WhatsApp runtime shell
- gradually swap or augment the chat brain
- current production target is now a bridge-backed pure backend brain, not a browser-bound SillyTavern frontend

## 2. Main Workspace

- Main workspace:
  - `C:\Users\ding7\Documents\gpt-susu-cloud`
- Current branch:
  - `codex/susu-cloud`
- Current local commit:
  - check `git log --oneline -1`
- Main runtime file:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\wa_agent.py`
- Photo/admin API:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\api_server.py`
- Susu admin core:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu_admin_core.py`
- Susu admin API:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu_admin_server.py`
- Admin UI:
  - `C:\Users\ding7\Documents\gpt-susu-cloud\susu-memory-admin.html`

Public open-source mirror:

- `C:\Users\ding7\Documents\susu-cloud`
- GitHub:
  - [SimonD0711/susu-cloud-ai-companion-on-whatsapp](https://github.com/SimonD0711/susu-cloud-ai-companion-on-whatsapp)

## 3. Authority / Deployment Model

Important:

- the authority production runtime is on Tokyo, not in another local worktree
- local development should continue in:
  - `C:\Users\ding7\Documents\gpt-susu-cloud`
- then deploy to Tokyo

Authoritative production files:

- `/var/www/html/wa_agent.py`
- `/var/www/html/api_server.py`
- `/var/www/html/susu_admin_core.py`
- `/var/www/html/susu_admin_server.py`
- `/var/www/html/susu-memory-admin.html`

Operational expectations for code changes:

1. edit locally in `C:\Users\ding7\Documents\gpt-susu-cloud`
2. run local `py_compile`
3. backup Tokyo target files before overwrite
4. upload
5. restart:
   - `wa-agent.service`
   - `cheungchau-api.service`
   - `susu-admin-api.service`
   - `sillytavern-bridge.service`
   - `susu-brain-backend.service`

Do not assume any other worktree is the authority runtime.

## 4. Product Capabilities That Must Be Preserved

These are considered core and should not be broken during refactors.

### WhatsApp runtime behavior

- webhook-based inbound processing
- SQLite-backed message ledger
- quote / reply-context handling
- read receipt pacing
- fake typing pacing
- multi-bubble reply splitting
- cancellable reply generation
- stale worker recovery

### Memory and operator controls

- long-term memories
- layered short-term memories:
  - `within_24h`
  - `within_3d`
  - `within_7d`
- archive tier for older short-term memories
- reminders
- admin management UI
- editable Susu settings / runtime settings

### Search and grounding

- live search routing
- grounded answer behavior
- answer / refine / abstain review step
- avoid making up unsupported facts from weak search results

### Companion features

- proactive messages
- girlfriend-style tone
- quote-aware replies
- emoji frequency control

Future migration work must preserve all of the above.

## 5. Current Runtime Architecture

### 5.1 `wa_agent.py` responsibilities

This file currently does too much, but it is the real runtime shell.

It handles:

- inbound webhook parsing
- message persistence
- quote context parsing
- media fetch for images
- memory extraction
- search routing and grounding
- reminder parsing / scheduling
- proactive loop
- reply worker state
- subprocess-based cancellable generation
- WhatsApp send / mark-as-read / typing / reactions

### 5.2 Reply worker model

Current behavior:

- one reply worker per contact
- if a new message arrives before send:
  - old local reply generation job is terminated
  - pending inbound messages are recombined
  - a fresh reply is generated

This is already better than most simple WhatsApp bot examples online.

### 5.3 Read / typing behavior

Current design:

- first inbound message in a cycle gets a short read delay
- follow-up messages inside that initial delay share the same read deadline
- later messages in the same cycle are immediate
- typing appears only if generation is not ready quickly
- typing is periodically refreshed while generation is still running

### 5.4 Quote context

Inbound quoted replies are parsed from WhatsApp `context.id`.

The runtime can:

- detect which earlier message was quoted
- expose quote context to prompt/history
- send a real quoted outbound reply when the generated text starts with:
  - `QUOTE:<message_id>`

## 6. Current Model / Brain State

### Active default brain

Normal chat currently runs through a bridge-backed pure backend path:

- `wa_agent.py -> sillytavern_bridge_server.py -> susu_brain_backend.py -> relay`

The backend model is still `claude-opus-4-6`, but production no longer depends on a browser/frontend bridge.

### Current weakness

Susu is often weak at:

- implicit intent tracking
- understanding clue-based turns
- maintaining explicit multi-turn task state

Example pattern:

- user gives a clue like a course code
- human would infer "this is probably the answer"
- Susu often keeps chatting at surface level instead of solving the immediate task

### Current strategy direction

Do not replace the WhatsApp runtime.

Instead:

- keep `wa_agent.py` as the WhatsApp shell
- make the "brain" switchable
- first target brain integration: SillyTavern

## 7. New Bridge-Backed Brain Scaffold

This work has already started locally.

Relevant files:

- `C:\Users\ding7\Documents\gpt-susu-cloud\wa_agent.py`
- `C:\Users\ding7\Documents\gpt-susu-cloud\sillytavern_adapter.py`
- `C:\Users\ding7\Documents\gpt-susu-cloud\sillytavern_bridge_server.py`
- `C:\Users\ding7\Documents\gpt-susu-cloud\agnai_backend_adapter.py`
- `C:\Users\ding7\Documents\gpt-susu-cloud\susu_brain_backend.py`
- `C:\Users\ding7\Documents\gpt-susu-cloud\susu-brain-backend.service`
- `C:\Users\ding7\Documents\gpt-susu-cloud\sillytavern-bridge.service`
- `C:\Users\ding7\Documents\gpt-susu-cloud\SILLYTAVERN_BRIDGE.md`
- `C:\Users\ding7\Documents\gpt-susu-cloud\susu_admin_core.py`
- `C:\Users\ding7\Documents\gpt-susu-cloud\susu_admin_server.py`

Recent commits in this area:

- `dff992c` `Extract Susu admin core from photo API`
- `d810083` `Tighten clue handling and backend retries`
- `1a30dcc` `Add local Susu brain backend service`
- `9c0dcfd` `Add Agnai-style backend bridge adapter`

What was added:

- a new switchable `brain provider` concept
- a minimal HTTP adapter for a bridge-backed brain endpoint
- a guarded path so only ordinary text chat is eligible for the bridge-backed provider
- fallback to the legacy Opus path if SillyTavern fails
- a structured multi-turn context payload builder for the bridge path
- a local bridge server that exposes an OpenAI-style `/v1/chat/completions` endpoint
- a bridge service file so Tokyo can run the bridge as a separate process
- a local pure backend service that accepts Agnai-style structured payloads and calls the relay model
- a fully separate Susu admin service so photo API and Susu admin no longer share one codepath

New env vars already supported in code:

- `WA_BRAIN_PROVIDER`
- `WA_BRAIN_FALLBACK_ON_ERROR`
- `WA_SILLYTAVERN_API_URL`
- `WA_SILLYTAVERN_API_KEY`
- `WA_SILLYTAVERN_MODEL`
- `WA_SILLYTAVERN_TIMEOUT_SECONDS`
- `WA_ST_BRIDGE_HOST`
- `WA_ST_BRIDGE_PORT`
- `WA_ST_BRIDGE_API_KEY`
- `WA_ST_BRIDGE_UPSTREAM_MODE`
- `WA_ST_BRIDGE_UPSTREAM_URL`
- `WA_ST_BRIDGE_UPSTREAM_API_KEY`
- `WA_ST_BRIDGE_UPSTREAM_MODEL`
- `WA_ST_BRIDGE_TIMEOUT_SECONDS`
- `WA_ST_BRIDGE_UPSTREAM_AUTH_HEADER`
- `WA_SUSU_BRAIN_HOST`
- `WA_SUSU_BRAIN_PORT`
- `WA_SUSU_BRAIN_API_KEY`
- `WA_SUSU_BRAIN_TIMEOUT_SECONDS`
- `WA_SUSU_BRAIN_MODEL`

Current production behavior:

- Tokyo currently runs `brain_provider = sillytavern`
- operationally this means “bridge-backed backend provider”, not a browser-bound SillyTavern frontend
- the bridge upstream mode is `agnai`
- the backend service is local and pure-server-side

Current gating logic for SillyTavern path:

- only ordinary text chat
- not image replies
- not live-search-triggered requests
- not Claude Code special-route traffic

This is intentionally conservative for phase 1.

### 7.1 Current bridge contract

The current Phase 2 bridge contract is:

- `wa_agent.py` sends OpenAI-style chat payloads to `WA_SILLYTAVERN_API_URL`
- the bridge accepts:
  - `POST /v1/chat/completions`
  - `POST /chat/completions`
- the bridge returns an OpenAI-style response with:
  - `choices[0].message.content`

The bridge is intentionally generic.

It can sit in front of:

- an Agnai-style backend
- another OpenAI-compatible backend
- a future custom structured-chat service

SQLite remains the single runtime source of truth. The backend is expected to consume structured context only, and must not take ownership of `wa_messages`, `wa_reminders`, or other business tables.

### 7.2 Current admin split

The photo/admin API and Susu admin API are now split:

- Photo/admin API:
  - service: `cheungchau-api.service`
  - file: `api_server.py`
  - bind: `127.0.0.1:9000`
  - nginx path: generic `/api/*`
- Susu admin API:
  - service: `susu-admin-api.service`
  - files: `susu_admin_core.py`, `susu_admin_server.py`
  - bind: `127.0.0.1:9001`
  - nginx path: `/api/susu-admin/*`

Do not re-mix these layers unless there is a very strong reason.

## 8. Why Not Replace The Whole Runtime

The bridge-backed backend should not replace the entire system.

Reasons:

- the SQLite message ledger is not just "memory"; it is runtime state
- reminders are product/business state, not just LLM memory
- reply workers, quote sending, read pacing, typing, and recovery loops are runtime behaviors
- the admin UI depends on the current database model

Recommended split:

- keep WhatsApp shell + DB + scheduling in this project
- move only the chat-brain / context-generation layer to SillyTavern

## 9. Database Guidance

### Tables / data that should remain the truth source here

- `wa_messages`
- `wa_reminders`
- contact state / runtime state
- operator-managed Susu settings

### Data that can be mirrored or partly consumed by SillyTavern

- long-term memory
- short-term memory summaries
- profile / persona material
- world/lore style knowledge

Recommended rule:

- SQLite remains the operational truth source
- SillyTavern consumes structured context, not raw operational ownership

## 10. Important Recent Fixes Already Landed

These are worth knowing before making larger changes.

### Quote handling

- inbound quote context is parsed and surfaced
- outbound `QUOTE:<message_id>` directive is handled before send

### Emoji frequency

- replies no longer keep emojis on nearly every sentence
- inline emoji count is trimmed

### Reply worker recovery

- stale workers can be recovered
- recovery loop exists so pending replies do not silently stall forever

### Read receipt pacing

- first read in a burst is delayed slightly
- subsequent messages after that first read become immediate in the same cycle

### Live search short-term memory insertion removed

- the runtime no longer stores:
  - `對方啱啱問過：...`
  as explicit short-term memory entries

### Public repo sync

The public repository has already been updated to release `v0.1.2` for share-safe runtime improvements.

## 11. Current Search State

Current search behavior is grounded, but not yet "mature assistant" level.

Search currently includes:

- weather
- news
- music
- web

The shell already added multi-source groundwork, but not all external providers are always configured.

Important principle:

- do not let weak evidence become a confident answer
- preserve abstain / refine behavior

If integrating SillyTavern more deeply, keep the search/tool layer outside the brain where possible, then pass structured evidence into the brain for tone shaping.

## 12. Current Voice State

Do not assume voice STT is already implemented in this runtime.

The current runtime has discussed "voice mode" and message style behavior, but does not yet have a full inbound audio-to-text pipeline wired in as a finished product feature.

Future desired direction:

- inbound `audio` / `ptt`
  - download media
  - STT
  - store transcript
  - feed transcript into normal reply flow
- optional outbound TTS

## 13. Recommended Next Steps

Priority order:

### Phase 1

Continue improving task-state and memory relevance in the production pure backend path.

### Phase 2

Keep tightening structured runtime context so both `legacy` and bridge-backed provider consume the same middle layer.

### Phase 3

Improve state tracking for implicit tasks and quoted short answers.

Examples:

- clue-following
- guessing tasks
- "you asked me what course I am in"
- carrying explicit unresolved user prompts across multiple turns

### Phase 4

Add STT / TTS without disturbing the runtime shell.

### Phase 4

Optionally make proactive and reminder content generation use the new brain after ordinary chat is stable.

## 14. Do / Do Not

### Do

- continue editing in `C:\Users\ding7\Documents\gpt-susu-cloud`
- preserve the WhatsApp-native behavior shell
- keep fallbacks during migration
- prefer additive migration over destructive replacement
- use local `py_compile` before deployment

### Do not

- do not replace the whole runtime with a generic chat frontend
- do not move reminders or runtime truth entirely into SillyTavern
- do not remove SQLite message history
- do not assume public GitHub code is the full production authority
- do not leak secrets into docs or commits

## 15. Suggested First Task For Claude Code

Recommended immediate handoff task:

- continue improving the bridge-backed pure backend path in a safe way
- keep current WhatsApp runtime behavior stable
- improve task-state handling and memory selection before adding any new UI entrypoints
- keep structured runtime context shared across providers
- preserve automatic fallback behavior

If more specificity is needed, the first implementation target should be:

1. design `build_sillytavern_context_payload(...)`
2. keep search/image/Claude-route out of the SillyTavern path
3. add local-only integration test probes
4. do not deploy until the bridge protocol is confirmed
