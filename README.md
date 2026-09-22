# Mission Control Notifications plugin

Persistent notification inbox for Mission Control.

## Current slice

- external MC plugin with a dedicated `/notifications` route;
- custom Overview card injected through the host plugin surface contract;
- `Attention Needed` contributor for unread items;
- SQLite-backed notifications with idempotent `dedupeKey` publishing;
- read / mark-all-read actions;
- cron routing policy in `notification-policy.json` with `report`, `event`, and `silent` modes;
- report mode imports every historical response, event mode imports only configured failures/recoveries/changes, and silent mode only surfaces failures;
- generic publish endpoint ready for non-cron producers;
- paginated inbox loading with server-side search and read/unread filtering;
- durable cron completion outbox consumer: sanitized events are drained idempotently when available, while the legacy `.md` importer remains as a compatibility path for cron runs that do not emit outbox events;
- plugin-owned live watcher: after the first inbox request it tracks output-file fingerprints and imports changed cron reports in a daemon worker, without modifying Hermes core;
- retention pruning with a 90-day default: archived and old read notifications are removed while unread notifications are preserved (`MISSION_CONTROL_NOTIFICATIONS_RETENTION_DAYS=0` disables it);
- delivery lifecycle with SQLite-backed channel attempts (`pending`, `retrying`, `delivered`, `failed`), atomic claims, exponential backoff, and a configurable maximum attempt count (`MISSION_CONTROL_NOTIFICATIONS_MAX_ATTEMPTS`, default `5`);
- Web Push channel adapter: recent notifications are queued to the host's VAPID subscription registry and delivered by the plugin-owned retry worker; historical backfill is never pushed;
- action-needed filtering: `error`, `warning`, `action`, or payloads with `actionRequired: true` surface in Attention Needed and the Inbox `Action needed` filter;
- deep links are restricted to internal paths and are carried into Web Push click payloads;
- generic Mission Control sidebar indicator: the plugin exposes `/notifications/status`, while MC renders the agnostic dot without knowing notification semantics.

## Installation

```bash
mkdir -p ~/.hermes/mc-plugins
ln -sfn "$PWD" ~/.hermes/mc-plugins/notifications
cd ~/Projects/hermes-mission-control
bash scripts/setup-plugins.sh
```

Restart the telemetry sidecar and Vite after installation.

### Web Push / iPhone

Mission Control already exposes the VAPID subscription toggle and service worker. Enable push from the sidebar on the device, then add the dashboard to the iPhone Home Screen and open it from there; iOS requires a Home Screen web app and a secure HTTPS origin for Web Push. The plugin persists the notification first and only queues a recent event for Web Push, so a historical import cannot suddenly wake up your phone.

## Publish an event

```http
POST /api/local/notifications/publish
Content-Type: application/json

{
  "dedupeKey": "cron:default:daily-ai-digest:run-2026-09-21",
  "type": "cron.completed",
  "severity": "success",
  "title": "AI Digest pronto",
  "body": "Il daily digest è stato generato.",
  "source": {"kind": "cron", "id": "daily-ai-digest"},
  "profile": "default",
  "deepLink": "/cron"
}
```

The store lives at `~/.hermes/mission-control/notifications.db` by default and
can be overridden with `MISSION_CONTROL_NOTIFICATIONS_DB`.
