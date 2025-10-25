# Copilot Instructions for workflow-use

These project-specific instructions help AI coding agents work productively in this repo. Keep responses concise, implement with tools when possible, and follow the repo’s patterns.

## Architecture (big picture)
- Monorepo with three main parts:
  - `extension/` (WXT MV3 Chrome extension): records user actions via rrweb + custom DOM events and streams to a local server.
  - `workflows/` (Python package + CLI + FastAPI backend): converts recorded events into deterministic workflow steps, runs/replays steps (fallback to Browser Use/Playwright).
  - `ui/` (Vite/React frontend): GUI to view and run workflows.
- Data flow:
  1) Content scripts capture events → background aggregates → posts `WORKFLOW_UPDATE` to `http://127.0.0.1:7331/event`.
  2) Backend stores/processes to `workflows/examples/*.json` and executes with Playwright.
  3) UI/CLI visualize/run.
- Key types: `extension/src/lib/types.ts` (Stored* events), `extension/src/lib/workflow-types.ts` (Step union), `workflows` Python `Workflow` model.

## Dev workflows
- Build extension: `cd extension && npm install && npm run build`.
- Python backend setup: `cd workflows && uv sync && playwright install chromium && cp .env.example .env`.
- Record: `cd workflows && python cli.py create-workflow` (starts local server; open Chrome with built extension).
- Run workflow as tool: `python cli.py run-as-tool examples/example.workflow.json --prompt "..."`.
- Run workflow: `python cli.py run-workflow examples/example.workflow.json`.
- Launch GUI: `python cli.py launch-gui` (starts FastAPI + UI dev server).

## Extension patterns
- Use `defineBackground` and `defineContentScript` (WXT). Content script always attaches listeners; background aggregates and emits `WORKFLOW_UPDATE` with a hash to avoid spam.
- Recording:
  - rrweb for scroll/meta; custom `CUSTOM_CLICK_EVENT`, `CUSTOM_INPUT_EVENT`, `CUSTOM_KEY_EVENT`, etc.
  - New-tab intent: content sends `PREPARE_NEW_TAB`; background correlates `tabs.onCreated` and marks `userInitiated`.
  - Activated tab gating: ignore tabs never activated (reduces ad/tracker noise).
  - Dedupe: merge consecutive identical steps, collapse rapid empty input bursts, consolidate navigations per tab.
  - Iframes: content runs with `allFrames: true` and `matchAboutBlank: true`; events carry `frameUrl` and `frameIdPath`. Background only allows rrweb meta navigations from frames the user interacted with and filters ad/analytics hosts.

## Backend patterns
- Python FastAPI endpoint `http://127.0.0.1:7331/event` receives:
  - `RECORDING_STARTED/STOPPED`, `WORKFLOW_UPDATE` with `steps` only (hash-based dedupe).
- CLI: `workflows/cli.py` provides record/run/launch commands; Playwright is used for replay.
- Keep workflow JSON in `workflows/examples/`. Naming is free-form; version stays at `1.0.0` today.

## Conventions
- Step schema (extension `workflow-types.ts`): navigation, click, input, key_press, scroll. Prefer merging updates over emitting new steps.
- Use XPath + enhanced CSS selectors; keep values masked for password inputs.
- Avoid sending events from tabs not in `activatedTabs` unless `userInitiated`.
- When adding new event types, extend Stored* in `types.ts`, enrich in content, and map to `Step` in background.

## Gotchas / Tips
- Avoid noisy iframe navs (recaptcha/ads): rely on `interactedFrameUrls` filtering in background. If adjusting, prefer allow/deny logic over hard-coding hosts in multiple places.
- When changing extension logic, rebuild with `npm run build`; dev opens side panel on install/update.
- Screenshot capture only works for visible tabs; background uses `captureVisibleTab` best-effort.
- If tests are added, ensure they run per package (`extension`, `workflows`, `ui`) rather than at repo root.

## Example tasks for agents
- Add a new step type (e.g., select):
  1) Extend `StoredCustomSelectEvent` in `types.ts` and emit in `content.ts`.
  2) Map to a `SelectStep` in `background.ts` (convertStoredEventsToSteps).
  3) Update backend replay to handle the new step.
- Reduce noise further:
  - Tune debounce windows in content.
  - Post-process duplicates in `broadcastWorkflowDataUpdate`.
  - Add frame interaction checks before accepting rrweb meta navigations.

## Security & secrets
- Do not commit real API keys. `.env.example` exists; load secrets locally. If you see a real key in `workflows/.env`, instruct maintainers to rotate and remove it.
