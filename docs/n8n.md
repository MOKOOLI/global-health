# n8n: get early-warning signals

1. **Schedule Trigger** (e.g. daily).
2. **HTTP Request**: GET `https://YOUR-HOST/api/feeds/signals.json?min_level=regional_outbreak&alerts=false`.
3. **Split Out** the `entries` field, then **IF** `{{$json.stale}}` is false.
4. Send to Slack/email/Telegram with `{{$json.title}}` and `{{$json.summary}}`.

Use `id` as the de-duplication key. These are statistical signals from reported counts, not official declarations; say so in your message. For feed readers use `/api/feeds/signals.atom`.
