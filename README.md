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
- retention pruning with a 90-day default: archived and old read notifications are removed while unread notifications are preserved (`MISSION_CONTROL_NOTIFICATIONS_RETENTION_DAYS=0` disables it).

## Installation

```bash
mkdir -p ~/.hermes/mc-plugins
ln -sfn "$PWD" ~/.hermes/mc-plugins/notifications
cd ~/Projects/hermes-mission-control
bash scripts/setup-plugins.sh
```

Restart the telemetry sidecar and Vite after installation.

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
