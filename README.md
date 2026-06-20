# Life Path Decoder v1.6.5

A Railway-ready FastAPI web app that generates Life Path / South Indian style reflective reports from name, DOB, time of birth and birth place.

> Important: This software is for reflection and entertainment. It is not scientific, psychological, medical, legal, financial, or deterministic advice.

## v1.6.5 Premium & Commercial Readiness Release

Added in this build:

- Friendlier date of birth selector with separate day, month and year controls
- Date validation for impossible and future dates
- Partner DOB uses the same friendly control
- Premium report options: short, medium, detailed
- Tone options: balanced, positive, direct, brutally honest
- Language preference capture: English, Kannada, Hindi, Tamil
- Brutally Honest Mode
- No Storage Mode
- Partner compatibility inputs and compatibility score section
- Name spelling and lucky name suggestions
- Business name / brand name numerology-style guidance
- PDF download from backend
- TXT download retained
- WhatsApp share link
- Facebook share link
- Instagram carousel cards
- Instagram story cards
- LinkedIn / social cards bundle
- Report history list and delete controls
- Clear report history privacy control
- Admin configuration page at `/admin`
- Admin login dialog before opening settings
- Section 23 / Premium Unlock Preview removed from generated reports
- Analytics endpoint for report counts and report types
- Railway geocode fallback retained

## Run on Windows

Double-click:

```bat
run_windows.bat
```

Then open:

```text
http://127.0.0.1:8000
```

## Run on macOS / Linux

```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

Then open:

```text
http://127.0.0.1:8000
```

## Admin Configuration

Open:

```text
http://127.0.0.1:8000/admin
```

Configurable prototype settings:

- Brand tagline
- Free plan label
- Premium report price label
- Compatibility report price label

## Railway Deployment

Minimum environment variable:

```env
SESSION_SECRET=replace-with-a-long-random-secret
```

Recommended after Railway public domain is generated:

```env
APP_BASE_URL=https://your-service.up.railway.app
SECURE_COOKIES=true
SESSION_IDLE_SECONDS=3600
SESSION_MAX_SECONDS=28800
SHARE_EXPIRY_DAYS=30
```

Railway health check path:

```text
/healthz
```

## GitHub Update

```bat
cd C:\99future
git add .
git commit -m "Life Path Decoder v1.6.5 premium readiness release"
git push -u origin main
```

## API Highlights

- `GET /healthz`
- `POST /api/analyze`
- `POST /api/report.pdf`
- `POST /api/share`
- `GET /api/reports`
- `DELETE /api/reports`
- `GET /api/analytics`
- `GET /api/config`
- `POST /api/config`

## Notes

- PDF export uses Pillow and is suitable for prototype/demo use.
- Payment integration is represented as a premium unlock/price configuration placeholder. Razorpay order creation can be wired in a production build.
- Full native-language report translation is represented by language preference capture; production translation can be connected in the next release.


## v1.6.5 updates
- Added South Indian methodology-inspired Trouble With Law / compliance caution section.
- Added Create Demo Data button. Its visibility is controlled from Admin Settings.
- Added public configuration endpoint for safe UI feature toggles.


## v1.6.5 updates

- Added Today’s Prediction section using approximate visitor IP location.
- The reading uses local date/time, nakshatra, moon rashi, tithi and weekday ruler in a South Indian-style daily interpretation.
- Added fallback handling when visitor IP location cannot be resolved.


## v1.6.5 local reload fix

The local Mac/Linux and Windows run scripts now restrict Uvicorn reload watching to the `app/` folder only. This prevents WatchFiles from repeatedly restarting the server when files inside `.venv/` change.


## v1.6.5 Mac layout stability fix
- Fixed mobile/tablet form layout cascade issue.
- Preserved executable permission guidance for Mac/Linux run script.
- Local reload watches only the app folder.


## v1.6.5 Mac stable UI and service fix

- Main Mac/Windows run scripts now start without `--reload`, so WatchFiles will not watch `.venv` or restart when pip/site-packages changes.
- Dev-mode reload scripts are provided separately: `run_mac_linux_dev.sh` and `run_windows_dev.bat`.
- CSS and JS are loaded with versioned URLs to avoid browser cache mismatch after upgrades.
- A final UI layout guard stabilizes desktop, tablet and mobile rendering.

If an older reload server is still running on Mac, stop it first:

```bash
lsof -ti tcp:8000 | xargs kill -9
```

## v1.6.5 Mapbox Temporary Geocoding

This build adds Mapbox Temporary Geocoding as the preferred geocoder when configured.

Recommended Railway variables:

```env
GEOCODER_PROVIDER=mapbox
MAPBOX_ACCESS_TOKEN=pk.your-mapbox-token
MAPBOX_COUNTRY=in
MAPBOX_LANGUAGE=en
DISABLE_EXTERNAL_GEOCODING=true
```

Geocoding order:

1. Manual coordinates typed by the user, for example `12.9716, 77.5946`
2. Mapbox Temporary Geocoding when `MAPBOX_ACCESS_TOKEN` is available
3. Offline India city/locality/PIN/state fallback
4. Optional legacy public geocoder only when external geocoding is not disabled


## v1.6.5 Selected Date Prediction
- Adds an optional Prediction Date control in Premium Report Options.
- Adds a generated section named “Prediction for Selected Date — South Indian Reading”.
- Uses selected date, Life Path, name vibration, birth place coordinates when available, Nakshatra, Moon Rashi, Tithi and weekday ruler.
- The selected-date prediction is included in report summary, copy/TXT/PDF/share payloads and metrics.

## v1.6.5 Demo Data and Logo Upload Fix
- Demo data creation now self-heals older SQLite/config states and returns partial errors if any sample fails.
- Admin-uploaded logos are automatically processed as smaller transparent PNG brand assets.
- Header/admin preview logo display has been reduced so uploaded logos do not dominate the page.


## v1.6.5 Demo Data Button Reliability Fix

- Demo data button refreshes the local session/CSRF token before creating data.
- Demo creation sends JSON with same-origin credentials and retries once if the session token is stale.
- Demo endpoint rate limit is relaxed for repeated local testing.
