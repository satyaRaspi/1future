# Railway Deployment Guide — Life Path Decoder v1.6.7

This build is Railway-ready.

## Included

- `railway.toml`
- `railway_start.py`
- `/healthz` health check
- Auto `$PORT` binding
- Auto Railway domain support through `RAILWAY_PUBLIC_DOMAIN`
- SQLite local storage with Railway Volume support
- PDF export
- Report history
- Public share pages
- Facebook, WhatsApp, Instagram Carousel, Instagram Story and social card links

## 1. Push to GitHub

```bat
cd C:\99future
git add .
git commit -m "Deploy Life Path Decoder v1.6.7"
git push -u origin main
```

## 2. Railway settings

Start command is already configured:

```text
python railway_start.py
```

Healthcheck path:

```text
/healthz
```

## 3. Environment variables

Minimum:

```env
SESSION_SECRET=replace-with-a-long-random-secret
```

Recommended:

```env
APP_BASE_URL=https://your-service.up.railway.app
SECURE_COOKIES=true
SHARE_EXPIRY_DAYS=30
```

Avoid setting strict `ALLOWED_HOSTS` until the first health check passes.

## 4. Persistent storage

For demo, built-in SQLite works. For persistent share/history data, attach a Railway Volume. The app automatically uses:

```text
$RAILWAY_VOLUME_MOUNT_PATH/lifepath_decoder/lifepath_users.sqlite3
```

## 5. Verify

Open:

```text
https://your-service.up.railway.app/healthz
```

Expected version:

```json
{"status":"ok","app":"Life Path Decoder","version":"1.5.0"}
```


## v1.6.7 note

Today’s Prediction uses Railway proxy headers such as X-Forwarded-For to locate the visitor approximately. If strict proxy settings are changed, the section will fall back to a generic UTC reading.


## Mapbox Temporary Geocoding

Set these Railway Variables to use Mapbox as the primary geocoder:

```env
GEOCODER_PROVIDER=mapbox
MAPBOX_ACCESS_TOKEN=pk.your-mapbox-token
MAPBOX_COUNTRY=in
MAPBOX_LANGUAGE=en
DISABLE_EXTERNAL_GEOCODING=true
```

Keep `DISABLE_EXTERNAL_GEOCODING=true` if you want to avoid the legacy public geocoder and rely on Mapbox + offline fallback only.


## v1.6.7 Selected Date Prediction
No new Railway variable is required. Deploy normally after pushing the updated code.

## v1.6.7 Demo Data and Logo Upload Fix
- Demo data creation is more reliable on Railway with old persistent volumes/config rows.
- Uploaded logos are saved into the Railway volume as smaller transparent PNGs under the configured data directory.


## v1.6.7 Demo Data Button Reliability Fix

- Demo data button refreshes the local session/CSRF token before creating data.
- Demo creation sends JSON with same-origin credentials and retries once if the session token is stale.
- Demo endpoint rate limit is relaxed for repeated local testing.

## v1.6.7 Language Output Fix
- No new Railway variable is required.
- Language selection is handled locally in the app for Kannada, Hindi and Tamil.
