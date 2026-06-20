from __future__ import annotations

import base64
import binascii
import hashlib
import html
import ipaddress
import io
import json
import os
import re
import secrets
import sqlite3
import textwrap
import time
import zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus, urlencode
from urllib.request import Request as UrlRequest, urlopen

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except Exception:  # pragma: no cover - install Pillow from requirements for image exports
    Image = ImageDraw = ImageFont = None

from .analyzer import PROMPT_OPTIONS, astronomy_snapshot, build_report

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_LOGO_PATH = STATIC_DIR / "logo-life-path-decoder.png"

load_dotenv(PROJECT_DIR / ".env")

APP_VERSION = "1.6.6"
APP_NAME = "Life Path Decoder"

# Railway exposes RAILWAY_PUBLIC_DOMAIN after a public domain is generated.
# APP_BASE_URL may still be set manually for custom domains.
RAILWAY_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip().rstrip("/")
_configured_base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
if _configured_base_url:
    APP_BASE_URL = _configured_base_url
elif RAILWAY_PUBLIC_DOMAIN:
    APP_BASE_URL = f"https://{RAILWAY_PUBLIC_DOMAIN}"
else:
    APP_BASE_URL = "http://127.0.0.1:8000"

# Use a Railway Volume automatically when attached. Override with DATA_DIR or DATABASE_PATH if needed.
_volume_mount = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
if os.getenv("DATA_DIR"):
    DATA_DIR = Path(os.getenv("DATA_DIR", "")).expanduser()
elif _volume_mount:
    DATA_DIR = Path(_volume_mount).expanduser() / "lifepath_decoder"
else:
    DATA_DIR = PROJECT_DIR / "data"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "lifepath_users.sqlite3"))).expanduser()
ASSET_DIR = DATA_DIR / "assets"
UPLOADED_LOGO_PATH = ASSET_DIR / "brand_logo.png"

_default_secure_cookie = "true" if APP_BASE_URL.startswith("https://") else "false"
SECURE_COOKIES = os.getenv("SECURE_COOKIES", _default_secure_cookie).strip().lower() in {"1", "true", "yes", "on"}
SESSION_IDLE_SECONDS = int(os.getenv("SESSION_IDLE_SECONDS", "3600"))
SESSION_MAX_SECONDS = int(os.getenv("SESSION_MAX_SECONDS", "28800"))
SHARE_EXPIRY_DAYS = int(os.getenv("SHARE_EXPIRY_DAYS", "30"))
ADMIN_ID = os.getenv("ADMIN_ID", "admin").strip() or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "LifePath@123").strip() or "LifePath@123"

# Geocoding provider settings. Mapbox temporary geocoding is used when
# MAPBOX_ACCESS_TOKEN is available. Results are used only for this lookup/report
# flow unless the user explicitly saves a report.
GEOCODER_PROVIDER = os.getenv("GEOCODER_PROVIDER", "auto").strip().lower() or "auto"
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN", "").strip()
MAPBOX_COUNTRY = os.getenv("MAPBOX_COUNTRY", "in").strip().lower()
MAPBOX_LANGUAGE = os.getenv("MAPBOX_LANGUAGE", "en").strip() or "en"

_session_secret = os.getenv("SESSION_SECRET", "").strip()
if not _session_secret:
    # Local development fallback. Production must set SESSION_SECRET so sessions survive restarts.
    _session_secret = secrets.token_urlsafe(48)


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _host_from_url(url: str) -> str:
    try:
        return url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
    except Exception:
        return ""


def _default_origins() -> str:
    origins = {APP_BASE_URL, "http://127.0.0.1:8000", "http://localhost:8000"}
    if RAILWAY_PUBLIC_DOMAIN:
        origins.add(f"https://{RAILWAY_PUBLIC_DOMAIN}")
    return ",".join(sorted(origin for origin in origins if origin))


def _default_hosts() -> str:
    hosts = {"127.0.0.1", "localhost", "*.up.railway.app"}
    app_host = _host_from_url(APP_BASE_URL)
    if app_host:
        hosts.add(app_host)
    if RAILWAY_PUBLIC_DOMAIN:
        hosts.add(RAILWAY_PUBLIC_DOMAIN)
    return ",".join(sorted(hosts))


ALLOWED_ORIGINS = _csv_env("ALLOWED_ORIGINS", _default_origins())
# Railway health checks may arrive with an internal Host header before the
# public domain is attached. If ALLOWED_HOSTS is explicitly set, we enforce it.
# Otherwise, Railway deployments allow any host so health checks do not get
# blocked by TrustedHostMiddleware. For production custom domains, set
# ALLOWED_HOSTS=your-domain.com,*.up.railway.app to tighten this again.
_EXPLICIT_ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").strip()
_IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID") or RAILWAY_PUBLIC_DOMAIN)
ALLOWED_HOSTS = _csv_env("ALLOWED_HOSTS", _default_hosts()) if _EXPLICIT_ALLOWED_HOSTS else (["*"] if _IS_RAILWAY else _csv_env("ALLOWED_HOSTS", _default_hosts()))

LOCAL_COORDINATES = {
    "bangalore": (12.971599, 77.594566, "Local city database"),
    "bengaluru": (12.971599, 77.594566, "Local city database"),
    "mysuru": (12.295810, 76.639381, "Local city database"),
    "mysore": (12.295810, 76.639381, "Local city database"),
    "mumbai": (19.075984, 72.877656, "Local city database"),
    "delhi": (28.613939, 77.209023, "Local city database"),
    "new delhi": (28.613939, 77.209023, "Local city database"),
    "chennai": (13.082680, 80.270718, "Local city database"),
    "kolkata": (22.572646, 88.363895, "Local city database"),
    "hyderabad": (17.385044, 78.486671, "Local city database"),
    "pune": (18.520430, 73.856744, "Local city database"),
    "ahmedabad": (23.022505, 72.571362, "Local city database"),
    "jaipur": (26.912434, 75.787271, "Local city database"),
    "lucknow": (26.846694, 80.946166, "Local city database"),
    "kochi": (9.931233, 76.267304, "Local city database"),
    "cochin": (9.931233, 76.267304, "Local city database"),
    "coimbatore": (11.016844, 76.955833, "Local city database"),
    "mangalore": (12.914142, 74.855957, "Local city database"),
    "mangaluru": (12.914142, 74.855957, "Local city database"),
    "hubli": (15.364708, 75.123955, "Local city database"),
    "hubballi": (15.364708, 75.123955, "Local city database"),
    "london": (51.507217, -0.127586, "Local city database"),
    "new york": (40.712776, -74.005974, "Local city database"),
    "singapore": (1.352083, 103.819836, "Local city database"),
    "dubai": (25.204849, 55.270783, "Local city database"),
}

# Railway-friendly offline geocoding fallback. This avoids failures when the
# deployed container cannot reach an external geocoding provider or Nominatim
# rate-limits server traffic. Coordinates are approximate city-centre anchors.
LOCAL_COORDINATES.update({
    # Karnataka and common spellings
    "bengaluru urban": (12.971599, 77.594566, "Offline city database"),
    "bangalore urban": (12.971599, 77.594566, "Offline city database"),
    "whitefield": (12.969820, 77.749947, "Offline city database"),
    "electronic city": (12.845215, 77.660169, "Offline city database"),
    "hebbal": (13.035800, 77.597000, "Offline city database"),
    "jayanagar": (12.925000, 77.593800, "Offline city database"),
    "indiranagar": (12.978400, 77.640800, "Offline city database"),
    "malleshwaram": (13.003100, 77.564300, "Offline city database"),
    "basavanagudi": (12.940600, 77.573800, "Offline city database"),
    "tumkur": (13.340881, 77.101181, "Offline city database"),
    "tumakuru": (13.340881, 77.101181, "Offline city database"),
    "belgaum": (15.849695, 74.497674, "Offline city database"),
    "belagavi": (15.849695, 74.497674, "Offline city database"),
    "gulbarga": (17.329731, 76.834296, "Offline city database"),
    "kalaburagi": (17.329731, 76.834296, "Offline city database"),
    "bijapur": (16.830171, 75.710031, "Offline city database"),
    "vijayapura": (16.830171, 75.710031, "Offline city database"),
    "davangere": (14.464408, 75.921758, "Offline city database"),
    "davangeri": (14.464408, 75.921758, "Offline city database"),
    "ballari": (15.139393, 76.921440, "Offline city database"),
    "bellary": (15.139393, 76.921440, "Offline city database"),
    "shivamogga": (13.929930, 75.568101, "Offline city database"),
    "shimoga": (13.929930, 75.568101, "Offline city database"),
    "udupi": (13.340881, 74.742142, "Offline city database"),
    "manipal": (13.352450, 74.792770, "Offline city database"),
    "chikkamagaluru": (13.316144, 75.772043, "Offline city database"),
    "chikmagalur": (13.316144, 75.772043, "Offline city database"),
    "hassan": (13.003323, 76.100389, "Offline city database"),
    "mandya": (12.522156, 76.900919, "Offline city database"),
    "raichur": (16.212003, 77.343928, "Offline city database"),
    "bidar": (17.910394, 77.519907, "Offline city database"),
    "gadag": (15.431874, 75.635956, "Offline city database"),
    "haveri": (14.795132, 75.399536, "Offline city database"),
    "bagalkot": (16.172536, 75.655722, "Offline city database"),
    "kolar": (13.136717, 78.129180, "Offline city database"),
    "chikkaballapur": (13.435455, 77.731476, "Offline city database"),
    "ramanagara": (12.725913, 77.280647, "Offline city database"),
    "kanakapura": (12.546244, 77.421118, "Offline city database"),
    "madikeri": (12.424421, 75.738186, "Offline city database"),
    "kodagu": (12.337494, 75.806908, "Offline city database"),
    "karwar": (14.818482, 74.141613, "Offline city database"),
    "sirsi": (14.619381, 74.835405, "Offline city database"),
    # Major India cities and aliases
    "gurgaon": (28.459497, 77.026638, "Offline city database"),
    "gurugram": (28.459497, 77.026638, "Offline city database"),
    "noida": (28.535517, 77.391029, "Offline city database"),
    "faridabad": (28.408912, 77.317789, "Offline city database"),
    "ghaziabad": (28.669156, 77.453758, "Offline city database"),
    "thiruvananthapuram": (8.524139, 76.936638, "Offline city database"),
    "trivandrum": (8.524139, 76.936638, "Offline city database"),
    "kozhikode": (11.258753, 75.780410, "Offline city database"),
    "calicut": (11.258753, 75.780410, "Offline city database"),
    "thrissur": (10.527642, 76.214435, "Offline city database"),
    "madurai": (9.925201, 78.119775, "Offline city database"),
    "trichy": (10.790483, 78.704672, "Offline city database"),
    "tiruchirappalli": (10.790483, 78.704672, "Offline city database"),
    "salem": (11.664325, 78.146014, "Offline city database"),
    "tirunelveli": (8.713913, 77.756652, "Offline city database"),
    "vellore": (12.916517, 79.132499, "Offline city database"),
    "visakhapatnam": (17.686816, 83.218482, "Offline city database"),
    "vizag": (17.686816, 83.218482, "Offline city database"),
    "vijayawada": (16.506174, 80.648015, "Offline city database"),
    "guntur": (16.306652, 80.436540, "Offline city database"),
    "tirupati": (13.628756, 79.419179, "Offline city database"),
    "warangal": (17.968901, 79.594054, "Offline city database"),
    "nizamabad": (18.672505, 78.094087, "Offline city database"),
    "nagpur": (21.145800, 79.088155, "Offline city database"),
    "nashik": (19.997454, 73.789803, "Offline city database"),
    "thane": (19.218330, 72.978090, "Offline city database"),
    "surat": (21.170240, 72.831061, "Offline city database"),
    "vadodara": (22.307159, 73.181219, "Offline city database"),
    "baroda": (22.307159, 73.181219, "Offline city database"),
    "rajkot": (22.303894, 70.802160, "Offline city database"),
    "indore": (22.719569, 75.857726, "Offline city database"),
    "bhopal": (23.259933, 77.412615, "Offline city database"),
    "gwalior": (26.218287, 78.182831, "Offline city database"),
    "kanpur": (26.449923, 80.331874, "Offline city database"),
    "varanasi": (25.317645, 82.973914, "Offline city database"),
    "prayagraj": (25.435801, 81.846311, "Offline city database"),
    "allahabad": (25.435801, 81.846311, "Offline city database"),
    "agra": (27.176670, 78.008075, "Offline city database"),
    "patna": (25.594095, 85.137566, "Offline city database"),
    "ranchi": (23.344100, 85.309562, "Offline city database"),
    "bhubaneswar": (20.296059, 85.824539, "Offline city database"),
    "cuttack": (20.462521, 85.882989, "Offline city database"),
    "guwahati": (26.144517, 91.736237, "Offline city database"),
    "shillong": (25.578773, 91.893254, "Offline city database"),
    "chandigarh": (30.733315, 76.779418, "Offline city database"),
    "amritsar": (31.634000, 74.872300, "Offline city database"),
    "ludhiana": (30.900965, 75.857276, "Offline city database"),
    "dehradun": (30.316496, 78.032188, "Offline city database"),
    "goa": (15.299326, 74.123996, "Offline city database"),
    "panaji": (15.490930, 73.827850, "Offline city database"),
    "pondicherry": (11.941591, 79.808313, "Offline city database"),
    "puducherry": (11.941591, 79.808313, "Offline city database"),
    "satara": (17.680464, 74.018261, "Offline city database"),
    "kolhapur": (16.705006, 74.243252, "Offline city database"),
    "solapur": (17.659919, 75.906391, "Offline city database"),
    "aurangabad": (19.876165, 75.343314, "Offline city database"),
    "sambhajinagar": (19.876165, 75.343314, "Offline city database"),
    "ahilyanagar": (19.094829, 74.748001, "Offline city database"),
    "ahmednagar": (19.094829, 74.748001, "Offline city database"),
    "jodhpur": (26.238947, 73.024309, "Offline city database"),
    "udaipur": (24.585445, 73.712479, "Offline city database"),
    "ajmer": (26.449896, 74.639916, "Offline city database"),
    "jabalpur": (23.181467, 79.986407, "Offline city database"),
    "raipur": (21.251384, 81.629641, "Offline city database"),
    "bilaspur": (22.079654, 82.139141, "Offline city database"),
    "jamshedpur": (22.804567, 86.202875, "Offline city database"),
    "dhanbad": (23.795653, 86.430385, "Offline city database"),
    "siliguri": (26.727101, 88.395286, "Offline city database"),
})


# v1.6.1: richer offline geocoding for Railway/local deployments.
# These are approximate city/locality anchors used only to avoid blocking the
# report when an external geocoder is unavailable.
LOCAL_COORDINATES.update({
    # Bengaluru localities and common spellings
    "kaggadasapura": (12.981600, 77.678100, "Offline locality database"),
    "kagadasapura": (12.981600, 77.678100, "Offline locality database"),
    "kagdasapura": (12.981600, 77.678100, "Offline locality database"),
    "new thippasandra": (12.973900, 77.650800, "Offline locality database"),
    "thippasandra": (12.973900, 77.650800, "Offline locality database"),
    "cv raman nagar": (12.978300, 77.664200, "Offline locality database"),
    "c v raman nagar": (12.978300, 77.664200, "Offline locality database"),
    "mahadevapura": (12.991400, 77.692200, "Offline locality database"),
    "marathahalli": (12.956900, 77.701100, "Offline locality database"),
    "koramangala": (12.935200, 77.624500, "Offline locality database"),
    "hsr layout": (12.911600, 77.647400, "Offline locality database"),
    "btm layout": (12.916600, 77.610100, "Offline locality database"),
    "rajajinagar": (12.991500, 77.554600, "Offline locality database"),
    "yelahanka": (13.100700, 77.596300, "Offline locality database"),
    "banashankari": (12.925500, 77.546800, "Offline locality database"),
    "raj rajeshwari nagar": (12.914900, 77.520600, "Offline locality database"),
    "rr nagar": (12.914900, 77.520600, "Offline locality database"),
    "kr puram": (13.007600, 77.695600, "Offline locality database"),
    "k r puram": (13.007600, 77.695600, "Offline locality database"),
    "devanahalli": (13.248700, 77.713700, "Offline locality database"),
    "nelamangala": (13.101900, 77.393600, "Offline locality database"),
    # Karnataka additional districts/towns
    "dharwad": (15.458900, 75.007800, "Offline city database"),
    "chitradurga": (14.225100, 76.398000, "Offline city database"),
    "dakshina kannada": (12.870000, 74.880000, "Offline district database"),
    "uttara kannada": (14.818500, 74.141600, "Offline district database"),
    "yadgir": (16.770000, 77.140000, "Offline city database"),
    "chamarajanagar": (11.923700, 76.939500, "Offline city database"),
    "tiptur": (13.258300, 76.478300, "Offline city database"),
    "bhadravathi": (13.848500, 75.705000, "Offline city database"),
    "sagara": (14.167000, 75.040300, "Offline city database"),
    "sakleshpur": (12.941000, 75.784000, "Offline city database"),
    "gokarna": (14.547900, 74.318800, "Offline city database"),
    # Tamil Nadu
    "erode": (11.341000, 77.717200, "Offline city database"),
    "tiruppur": (11.108500, 77.341100, "Offline city database"),
    "dindigul": (10.367300, 77.980300, "Offline city database"),
    "thanjavur": (10.787000, 79.137800, "Offline city database"),
    "tanjore": (10.787000, 79.137800, "Offline city database"),
    "thoothukudi": (8.764200, 78.134800, "Offline city database"),
    "tuticorin": (8.764200, 78.134800, "Offline city database"),
    "cuddalore": (11.748000, 79.771400, "Offline city database"),
    "kanchipuram": (12.834200, 79.703600, "Offline city database"),
    "kumbakonam": (10.960200, 79.384500, "Offline city database"),
    "sivakasi": (9.453300, 77.802400, "Offline city database"),
    "karur": (10.960100, 78.076600, "Offline city database"),
    "namakkal": (11.219400, 78.167800, "Offline city database"),
    "tiruvannamalai": (12.225300, 79.074700, "Offline city database"),
    "nagercoil": (8.183300, 77.411900, "Offline city database"),
    # Kerala
    "alappuzha": (9.498100, 76.338800, "Offline city database"),
    "alleppey": (9.498100, 76.338800, "Offline city database"),
    "kottayam": (9.591600, 76.522200, "Offline city database"),
    "kannur": (11.874500, 75.370400, "Offline city database"),
    "palakkad": (10.786700, 76.654800, "Offline city database"),
    "malappuram": (11.051000, 76.071100, "Offline city database"),
    "pathanamthitta": (9.264800, 76.787000, "Offline city database"),
    "kollam": (8.893200, 76.614100, "Offline city database"),
    # Andhra / Telangana
    "kakinada": (16.989100, 82.247500, "Offline city database"),
    "nellore": (14.442600, 79.986500, "Offline city database"),
    "kurnool": (15.828100, 78.037300, "Offline city database"),
    "ananthapur": (14.681900, 77.600600, "Offline city database"),
    "anantapur": (14.681900, 77.600600, "Offline city database"),
    "rajahmundry": (17.000500, 81.804000, "Offline city database"),
    "rajamahendravaram": (17.000500, 81.804000, "Offline city database"),
    "karimnagar": (18.438600, 79.128800, "Offline city database"),
    "khammam": (17.247300, 80.151400, "Offline city database"),
    "secunderabad": (17.439900, 78.498300, "Offline city database"),
})

STATE_COORDINATE_FALLBACKS = {
    "karnataka": (12.971599, 77.594566, "Approximate state fallback: Karnataka → Bengaluru"),
    "tamil nadu": (13.082680, 80.270718, "Approximate state fallback: Tamil Nadu → Chennai"),
    "tn": (13.082680, 80.270718, "Approximate state fallback: Tamil Nadu → Chennai"),
    "kerala": (9.931233, 76.267304, "Approximate state fallback: Kerala → Kochi"),
    "telangana": (17.385044, 78.486671, "Approximate state fallback: Telangana → Hyderabad"),
    "andhra pradesh": (16.506174, 80.648015, "Approximate state fallback: Andhra Pradesh → Vijayawada"),
    "maharashtra": (19.075984, 72.877656, "Approximate state fallback: Maharashtra → Mumbai"),
    "goa": (15.490930, 73.827850, "Approximate state fallback: Goa → Panaji"),
    "delhi": (28.613939, 77.209023, "Approximate state fallback: Delhi"),
    "gujarat": (23.022505, 72.571362, "Approximate state fallback: Gujarat → Ahmedabad"),
    "rajasthan": (26.912434, 75.787271, "Approximate state fallback: Rajasthan → Jaipur"),
    "uttar pradesh": (26.846694, 80.946166, "Approximate state fallback: Uttar Pradesh → Lucknow"),
    "madhya pradesh": (23.259933, 77.412615, "Approximate state fallback: Madhya Pradesh → Bhopal"),
    "west bengal": (22.572646, 88.363895, "Approximate state fallback: West Bengal → Kolkata"),
    "odisha": (20.296059, 85.824539, "Approximate state fallback: Odisha → Bhubaneswar"),
    "punjab": (30.733315, 76.779418, "Approximate state fallback: Punjab/Chandigarh region"),
    "haryana": (28.459497, 77.026638, "Approximate state fallback: Haryana → Gurugram"),
    "bihar": (25.594095, 85.137566, "Approximate state fallback: Bihar → Patna"),
}

PINCODE_PREFIX_FALLBACKS = {
    "56": (12.971599, 77.594566, "Approximate PIN fallback: Bengaluru/Karnataka region"),
    "57": (12.295810, 76.639381, "Approximate PIN fallback: Karnataka/Mysuru region"),
    "58": (15.849695, 74.497674, "Approximate PIN fallback: North Karnataka region"),
    "60": (13.082680, 80.270718, "Approximate PIN fallback: Chennai/Tamil Nadu region"),
    "61": (10.787000, 79.137800, "Approximate PIN fallback: Central Tamil Nadu region"),
    "62": (9.925201, 78.119775, "Approximate PIN fallback: South Tamil Nadu region"),
    "63": (11.341000, 77.717200, "Approximate PIN fallback: West Tamil Nadu region"),
    "64": (11.016844, 76.955833, "Approximate PIN fallback: Coimbatore/Tamil Nadu region"),
    "67": (11.874500, 75.370400, "Approximate PIN fallback: North Kerala region"),
    "68": (9.931233, 76.267304, "Approximate PIN fallback: Central Kerala region"),
    "69": (8.524139, 76.936638, "Approximate PIN fallback: South Kerala region"),
    "50": (17.385044, 78.486671, "Approximate PIN fallback: Hyderabad/Telangana region"),
    "51": (14.681900, 77.600600, "Approximate PIN fallback: Andhra Pradesh region"),
    "52": (16.506174, 80.648015, "Approximate PIN fallback: Andhra Pradesh region"),
    "53": (17.686816, 83.218482, "Approximate PIN fallback: Visakhapatnam/Andhra region"),
}

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Life Path Decoder API",
    description="DOB + name + birthplace based reflective report generator with public sharing.",
    version=APP_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    session_cookie="lp_session",
    max_age=SESSION_MAX_SECONDS,
    same_site="lax",
    https_only=SECURE_COOKIES,
)


RATE_LIMITS: dict[str, list[float]] = {}
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SAFE_TEXT = re.compile(r"^[\w\s.,'’\-()&/]+$", re.UNICODE)
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # Public result pages and Open Graph images must be visible to social crawlers.
    response.headers["Cross-Origin-Resource-Policy"] = "cross-origin" if request.url.path.startswith("/s/") else "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' https: data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/") or request.url.path.startswith("/auth/"):
        response.headers["Cache-Control"] = "no-store"
    if SECURE_COOKIES:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


class AnalyzeRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    date_of_birth: str = Field(..., min_length=6, max_length=20, description="YYYY-MM-DD or DD-MM-YYYY")
    birth_time: Optional[str] = Field(default=None, max_length=8, description="HH:MM 24-hour format")
    birth_place: Optional[str] = Field(default=None, max_length=180)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    analysis_type: str = Field(default="life_path", max_length=40)
    report_length: str = Field(default="detailed", max_length=20)
    tone: str = Field(default="balanced", max_length=30)
    output_language: str = Field(default="english", max_length=30)
    brutal_mode: bool = Field(default=False)
    no_storage: bool = Field(default=False)
    prediction_date: Optional[str] = Field(default=None, max_length=20, description="YYYY-MM-DD, DD-MM-YYYY or similar")
    partner_name: Optional[str] = Field(default=None, max_length=120)
    partner_date_of_birth: Optional[str] = Field(default=None, max_length=20)
    partner_birth_time: Optional[str] = Field(default=None, max_length=8)
    partner_birth_place: Optional[str] = Field(default=None, max_length=180)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = _clean_text(value, "Name")
        if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", value):
            raise ValueError("Name must contain letters.")
        return value

    @field_validator("partner_name")
    @classmethod
    def clean_partner_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        value = _clean_text(str(value), "Partner name")
        if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ]", value):
            raise ValueError("Partner name must contain letters.")
        return value

    @field_validator("birth_place", "partner_birth_place")
    @classmethod
    def clean_optional_place(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        return _clean_text(str(value), "Birth place")

    @field_validator("date_of_birth")
    @classmethod
    def clean_dob(cls, value: str) -> str:
        value = _clean_text(value, "Date of birth")
        if not re.match(r"^[0-9./-]+$", value):
            raise ValueError("Date of birth can contain only numbers and date separators.")
        return value

    @field_validator("partner_date_of_birth")
    @classmethod
    def clean_partner_dob(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        value = _clean_text(str(value), "Partner date of birth")
        if not re.match(r"^[0-9./-]+$", value):
            raise ValueError("Partner date of birth can contain only numbers and date separators.")
        return value

    @field_validator("prediction_date")
    @classmethod
    def clean_prediction_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        value = _clean_text(str(value), "Prediction date")
        if not re.match(r"^[0-9./-]+$", value):
            raise ValueError("Prediction date can contain only numbers and date separators.")
        return value

    @field_validator("birth_time", "partner_birth_time")
    @classmethod
    def clean_birth_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not str(value).strip():
            return None
        value = " ".join(str(value).strip().split())
        if CONTROL_CHARS.search(value):
            raise ValueError("Birth time contains invalid control characters.")
        if not re.match(r"^[0-9:]+$", value):
            raise ValueError("Birth time must contain only numbers and colon.")
        return value

    @field_validator("report_length")
    @classmethod
    def validate_report_length(cls, value: str) -> str:
        value = (value or "detailed").strip().lower()
        if value not in {"short", "medium", "detailed"}:
            raise ValueError("Report length must be short, medium or detailed.")
        return value

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: str) -> str:
        value = (value or "balanced").strip().lower()
        if value not in {"balanced", "direct", "positive", "brutally_honest"}:
            raise ValueError("Tone must be balanced, direct, positive or brutally_honest.")
        return value

    @field_validator("output_language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        value = (value or "english").strip().lower()
        if value not in {"english", "kannada", "hindi", "tamil"}:
            raise ValueError("Language must be english, kannada, hindi or tamil.")
        return value

    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, value: str) -> str:
        value = value.strip()
        if value not in PROMPT_OPTIONS:
            raise ValueError("Unknown analysis type selected.")
        return value


class GeocodeRequest(BaseModel):
    birth_place: str = Field(..., min_length=2, max_length=180)

    @field_validator("birth_place")
    @classmethod
    def clean_place(cls, value: str) -> str:
        return _clean_text(value, "Birth place")


class LogoutRequest(BaseModel):
    confirm: bool = True


class AdminLoginRequest(BaseModel):
    admin_id: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=4, max_length=160)


class LogoUploadRequest(BaseModel):
    logo_data_url: str = Field(..., min_length=40, max_length=5_000_000)


class ShareRequest(AnalyzeRequest):
    allow_public_share: bool = True


def _clean_text(value: str, label: str) -> str:
    clean = " ".join((value or "").strip().split())
    if CONTROL_CHARS.search(clean):
        raise ValueError(f"{label} contains invalid control characters.")
    if not SAFE_TEXT.match(clean):
        raise ValueError(f"{label} contains unsupported characters.")
    return clean


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shared_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                token_hash TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                share_summary TEXT NOT NULL,
                public_payload TEXT NOT NULL,
                full_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_reports_user_id ON shared_reports(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_reports_token_hash ON shared_reports(token_hash)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS report_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                name TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                input_payload TEXT NOT NULL,
                report_payload TEXT NOT NULL,
                full_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_report_history_user_id ON report_history(user_id)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()


def rate_limit(request: Request, bucket: str, max_calls: int, per_seconds: int) -> None:
    ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{ip}"
    now = time.time()
    calls = [ts for ts in RATE_LIMITS.get(key, []) if now - ts < per_seconds]
    if len(calls) >= max_calls:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again shortly.")
    calls.append(now)
    RATE_LIMITS[key] = calls


def _session_times_valid(request: Request) -> bool:
    created_at = float(request.session.get("created_at", 0) or 0)
    last_seen = float(request.session.get("last_seen", 0) or 0)
    now = time.time()
    if not created_at or now - created_at > SESSION_MAX_SECONDS:
        return False
    if not last_seen or now - last_seen > SESSION_IDLE_SECONDS:
        return False
    request.session["last_seen"] = now
    return True


def ensure_local_session(request: Request) -> dict[str, Any]:
    """Create a local anonymous session for CSRF/session protection."""
    if not request.session.get("csrf_token") or not _session_times_valid(request):
        request.session.clear()
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        request.session["created_at"] = time.time()
        request.session["last_seen"] = time.time()
    return {"id": 0, "name": "Local User", "email": "", "picture": None}


def current_user(request: Request) -> dict[str, Any]:
    return ensure_local_session(request)


def require_csrf(request: Request) -> None:
    header_token = request.headers.get("X-CSRF-Token", "")
    session_token = request.session.get("csrf_token", "")
    if not header_token or not session_token or not secrets.compare_digest(header_token, session_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")


def require_admin(request: Request) -> None:
    ensure_local_session(request)
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin login required.")


def _normalise_place(place: str) -> str:
    text = " ".join((place or "").strip().lower().split())
    # Convert common punctuation into spaces so "Bengaluru Karnataka India"
    # and "Bengaluru, Karnataka, India" both match the offline city table.
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _manual_coordinate_lookup(place: str) -> tuple[float, float, str, str] | None:
    """Allow users to bypass geocoding by entering "lat, lon" directly."""
    coord_match = re.search(r"(-?\d{1,2}(?:\.\d+)?)\s*[,/ ]\s*(-?\d{1,3}(?:\.\d+)?)", place or "")
    if not coord_match:
        return None
    try:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
    except ValueError:
        return None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon, "Manual coordinate input", "coordinates"
    return None


def _mapbox_geocode_lookup(clean: str) -> dict[str, Any]:
    """Forward geocode with Mapbox Temporary Geocoding when configured.

    The endpoint is intentionally called only when MAPBOX_ACCESS_TOKEN is set.
    A failed Mapbox lookup returns a structured unresolved response so offline
    fallbacks can still run without blocking the user.
    """
    if not MAPBOX_ACCESS_TOKEN:
        return {"resolved": False, "error": "MAPBOX_ACCESS_TOKEN is not configured."}

    params: dict[str, str] = {
        "q": clean,
        "access_token": MAPBOX_ACCESS_TOKEN,
        "limit": "1",
        "language": MAPBOX_LANGUAGE,
        "autocomplete": "false",
        "permanent": "false",
    }
    if MAPBOX_COUNTRY:
        params["country"] = MAPBOX_COUNTRY

    url = f"https://api.mapbox.com/search/geocode/v6/forward?{urlencode(params)}"
    req = UrlRequest(
        url,
        headers={
            "User-Agent": f"LifePathDecoder/{APP_VERSION} Mapbox temporary geocoder",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"resolved": False, "error": f"Mapbox temporary geocoder unavailable ({type(exc).__name__})."}

    features = payload.get("features") or []
    if not features:
        return {"resolved": False, "error": "Mapbox returned no matching place."}

    first = features[0]
    props = first.get("properties") or {}
    geometry = first.get("geometry") or {}
    coords = geometry.get("coordinates") or []

    lon: float | None = None
    lat: float | None = None
    if isinstance(coords, list) and len(coords) >= 2:
        lon = float(coords[0])
        lat = float(coords[1])
    else:
        prop_coords = props.get("coordinates") or {}
        if "longitude" in prop_coords and "latitude" in prop_coords:
            lon = float(prop_coords["longitude"])
            lat = float(prop_coords["latitude"])

    if lat is None or lon is None:
        return {"resolved": False, "error": "Mapbox response did not include coordinates."}

    display = (
        props.get("full_address")
        or props.get("place_formatted")
        or props.get("name")
        or clean
    )
    accuracy = props.get("match_code", {}).get("confidence") if isinstance(props.get("match_code"), dict) else None
    source = "Mapbox Temporary Geocoding"
    if accuracy:
        source = f"{source} · confidence {accuracy}"
    if MAPBOX_COUNTRY:
        source = f"{source} · country bias {MAPBOX_COUNTRY.upper()}"

    return {
        "birth_place": clean,
        "display_name": display,
        "latitude": lat,
        "longitude": lon,
        "source": source,
        "resolved": True,
    }


def _local_geocode_lookup(clean: str) -> tuple[float, float, str, str] | None:
    key = _normalise_place(clean)
    if not key:
        return None

    # Allow manual coordinates such as "12.9716, 77.5946" in the place field.
    coord_match = re.search(r"(-?\d{1,2}(?:\.\d+)?)\s*[,/ ]\s*(-?\d{1,3}(?:\.\d+)?)", clean)
    if coord_match:
        try:
            lat = float(coord_match.group(1))
            lon = float(coord_match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, "Manual coordinate fallback", "coordinates"
        except ValueError:
            pass

    # PIN-code fallback for common Indian postal regions. This is deliberately
    # approximate but keeps the report usable when city text is too specific.
    pin_match = re.search(r"\b(\d{6})\b", clean)
    if pin_match:
        prefix = pin_match.group(1)[:2]
        if prefix in PINCODE_PREFIX_FALLBACKS:
            lat, lon, source = PINCODE_PREFIX_FALLBACKS[prefix]
            return lat, lon, source, pin_match.group(1)

    candidates: list[str] = [key]
    # First comma-separated component usually contains the city/locality.
    if "," in clean:
        candidates.append(_normalise_place(clean.split(",", 1)[0]))
    # Also try removing common suffix words.
    stop_words = {
        "india", "bharat", "karnataka", "ka", "maharashtra", "tamil", "nadu", "kerala", "telangana", "andhra", "pradesh",
        "uttar", "madhya", "gujarat", "rajasthan", "punjab", "haryana", "odisha", "assam", "bihar", "jharkhand",
        "west", "bengal", "state", "district", "city", "urban", "rural",
    }
    words = [w for w in key.split() if w not in stop_words]
    if words:
        candidates.append(" ".join(words))
        candidates.extend(words)

    seen = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if candidate in LOCAL_COORDINATES:
            lat, lon, source = LOCAL_COORDINATES[candidate]
            return lat, lon, source, candidate

    # Final fuzzy pass: detect a known city/locality name inside a longer place
    # string. Longest match wins so "new delhi" beats "delhi" and
    # "new thippasandra" beats "thippasandra".
    padded = f" {key} "
    compact_key = key.replace(" ", "")
    for city in sorted(LOCAL_COORDINATES.keys(), key=len, reverse=True):
        city_padded = f" {city} "
        compact_city = city.replace(" ", "")
        if city_padded in padded or compact_city in compact_key:
            lat, lon, source = LOCAL_COORDINATES[city]
            return lat, lon, source, city

    # State-level fallback: when the user enters a very granular locality not in
    # the offline table but includes a state, resolve to a safe state anchor.
    for state in sorted(STATE_COORDINATE_FALLBACKS.keys(), key=len, reverse=True):
        state_padded = f" {state} "
        if state_padded in padded:
            lat, lon, source = STATE_COORDINATE_FALLBACKS[state]
            return lat, lon, source, f"{state} approximate"

    # Country-level fallback. This prevents Railway deployments from showing a
    # hard failure when external geocoding is blocked. The generated report will
    # clearly mark the result as approximate.
    if " india " in padded or " bharat " in padded:
        return 21.145800, 79.088155, "Approximate country fallback: India centre", "india approximate"

    return None


def geocode_place(place: str) -> dict[str, Any]:
    clean = _clean_text(place, "Birth place")
    if len(clean) < 2:
        raise ValueError("Birth place is required for latitude/longitude lookup.")

    manual = _manual_coordinate_lookup(clean)
    if manual:
        lat, lon, source, matched = manual
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": lat,
            "longitude": lon,
            "source": f"{source} · matched {matched.title()}",
            "resolved": True,
        }

    mapbox_error = ""
    use_mapbox = GEOCODER_PROVIDER in {"auto", "mapbox", "mapbox_temporary", "mapbox-temporary"}
    if use_mapbox and MAPBOX_ACCESS_TOKEN:
        mapbox = _mapbox_geocode_lookup(clean)
        if mapbox.get("resolved"):
            return mapbox
        mapbox_error = str(mapbox.get("error") or "Mapbox did not resolve this place.")

    # Offline fallback after Mapbox. This keeps Railway usable even when the
    # Mapbox key is missing, quota is exhausted, or the network is unavailable.
    local = _local_geocode_lookup(clean)
    if local:
        lat, lon, source, matched = local
        suffix = f" · Mapbox fallback after: {mapbox_error}" if mapbox_error else ""
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": lat,
            "longitude": lon,
            "source": f"{source} · matched {matched.title()}{suffix}",
            "resolved": True,
        }

    if use_mapbox and not MAPBOX_ACCESS_TOKEN and GEOCODER_PROVIDER in {"mapbox", "mapbox_temporary", "mapbox-temporary"}:
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": None,
            "longitude": None,
            "source": "Mapbox selected but MAPBOX_ACCESS_TOKEN is not configured. Enter coordinates or configure the token in Railway.",
            "resolved": False,
        }

    if use_mapbox and mapbox_error and GEOCODER_PROVIDER in {"mapbox", "mapbox_temporary", "mapbox-temporary"}:
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": None,
            "longitude": None,
            "source": f"{mapbox_error} Offline database also did not match. Try city, state, country or coordinates like 12.9716, 77.5946.",
            "resolved": False,
        }

    # Optional legacy public geocoder fallback. For production, prefer Mapbox
    # with MAPBOX_ACCESS_TOKEN and keep DISABLE_EXTERNAL_GEOCODING=true if you
    # want to avoid public Nominatim entirely.
    if os.getenv("DISABLE_EXTERNAL_GEOCODING", "false").strip().lower() in {"1", "true", "yes", "on"}:
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": None,
            "longitude": None,
            "source": "Not resolved in Mapbox/offline database. Try city, state, country or coordinates.",
            "resolved": False,
        }

    query = urlencode({"q": clean, "format": "json", "limit": "1", "addressdetails": "0"})
    url = f"https://nominatim.openstreetmap.org/search?{query}"
    req = UrlRequest(url, headers={
        "User-Agent": f"LifePathDecoder/{APP_VERSION} Railway-ready geocoder",
        "Accept": "application/json",
        "Accept-Language": "en",
    })
    try:
        with urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": None,
            "longitude": None,
            "source": f"Mapbox not configured/resolved, offline database did not match, and legacy external geocoder failed ({type(exc).__name__}). Enter coordinates like 12.9716, 77.5946.",
            "resolved": False,
        }

    if not payload:
        return {
            "birth_place": clean,
            "display_name": clean,
            "latitude": None,
            "longitude": None,
            "source": "No matching place found in Mapbox, legacy geocoder, or offline city database.",
            "resolved": False,
        }

    first = payload[0]
    return {
        "birth_place": clean,
        "display_name": first.get("display_name", clean),
        "latitude": float(first["lat"]),
        "longitude": float(first["lon"]),
        "source": "OpenStreetMap Nominatim legacy fallback",
        "resolved": True,
    }


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_public_token() -> str:
    return secrets.token_urlsafe(32)


def _share_url(token: str) -> str:
    return f"{APP_BASE_URL}/s/{token}"


def _facebook_url(share_url: str) -> str:
    return f"https://www.facebook.com/sharer/sharer.php?u={quote_plus(share_url)}"


def _public_payload(report: dict[str, Any]) -> dict[str, Any]:
    calculations = report["calculations"]
    input_data = report["input"]
    title = report["report"]["title"]
    name = input_data["name"]
    summary = (
        f"{name}'s {title}: Life Path {calculations['life_path']} — "
        f"{calculations['life_path_title']}."
    )
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "title": title,
        "name": name,
        "summary": summary,
        "birth_place": input_data.get("birth_place"),
        "analysis_type": input_data.get("analysis_type"),
        "calculations": calculations,
        "sections": report["report"]["sections"],
        "disclaimer": report.get("disclaimer", "Reflective/entertainment use only. Not scientific or deterministic."),
        "created_at": _now_iso(),
    }


def create_shared_report(user_id: int, report: dict[str, Any]) -> dict[str, str]:
    token = make_public_token()
    public_payload = _public_payload(report)
    now = datetime.now(timezone.utc)
    expires_ts = now.timestamp() + SHARE_EXPIRY_DAYS * 86400
    expires = datetime.fromtimestamp(expires_ts, timezone.utc).isoformat()
    url = _share_url(token)
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO shared_reports
            (user_id, token_hash, title, share_summary, public_payload, full_text, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                token_hash(token),
                public_payload["title"][:180],
                public_payload["summary"][:300],
                json.dumps(public_payload, ensure_ascii=False),
                report["report"]["full_text"],
                now.isoformat(),
                expires,
            ),
        )
        conn.commit()
    return {
        "token": token,
        "share_url": url,
        "facebook_share_url": _facebook_url(url),
        "whatsapp_share_url": f"https://wa.me/?text={quote_plus('My Life Path Decoder report: ' + url)}",
        "instagram_cards_url": f"{url}/instagram-cards.zip",
        "instagram_story_url": f"{url}/instagram-story.zip",
        "social_cards_url": f"{url}/social-cards.zip",
        "og_image_url": f"{url}/og.png",
        "expires_at": expires,
    }


def get_share_row(token: str) -> sqlite3.Row:
    if not TOKEN_RE.match(token):
        raise HTTPException(status_code=404, detail="Share not found")
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM shared_reports
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (token_hash(token),),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Share not found")
    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
    except ValueError:
        raise HTTPException(status_code=404, detail="Share not found")
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This share link has expired")
    return row



def _section(title: str, body: str = "", bullets: list[str] | None = None, table: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {"title": title, "body": body or "", "bullets": bullets or [], "table": table or []}


def _safe_payload_from_req(req: AnalyzeRequest) -> dict[str, Any]:
    return {
        "name": req.name,
        "date_of_birth": req.date_of_birth,
        "birth_time": req.birth_time,
        "birth_place": req.birth_place,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "analysis_type": req.analysis_type,
        "report_length": req.report_length,
        "tone": req.tone,
        "output_language": req.output_language,
        "brutal_mode": req.brutal_mode,
        "no_storage": req.no_storage,
        "prediction_date": req.prediction_date,
        "partner_name": req.partner_name,
        "partner_date_of_birth": req.partner_date_of_birth,
        "partner_birth_time": req.partner_birth_time,
        "partner_birth_place": req.partner_birth_place,
    }


def _compatibility_score(a: dict[str, Any], b: dict[str, Any]) -> tuple[int, list[str]]:
    ac = a.get("calculations", {})
    bc = b.get("calculations", {})
    score = 58
    notes: list[str] = []
    if ac.get("life_path") == bc.get("life_path"):
        score += 14
        notes.append("Both profiles share the same Life Path, so rhythm and instinct may feel familiar.")
    elif abs(int(ac.get("life_path", 0) or 0) - int(bc.get("life_path", 0) or 0)) <= 2:
        score += 8
        notes.append("Life Path numbers are close enough to create practical understanding with effort.")
    else:
        notes.append("Life Path numbers differ, so the relationship needs conscious translation rather than assumptions.")
    if ac.get("moon_rashi") == bc.get("moon_rashi"):
        score += 10
        notes.append("Moon Rashi matches, suggesting emotional familiarity.")
    if ac.get("nakshatra") == bc.get("nakshatra"):
        score += 8
        notes.append("Nakshatra matches, which can create a strong shared instinctive tone.")
    if ac.get("personal_year") == bc.get("personal_year"):
        score += 5
        notes.append("Both are in a similar personal-year rhythm right now.")
    score = max(35, min(96, score))
    return score, notes


def _name_spelling_suggestions(name: str) -> list[str]:
    base = " ".join(name.split())
    compact = re.sub(r"[^A-Za-z]", "", base)
    suggestions = []
    if compact:
        suggestions.append(f"{base} — keep current spelling if public recognition already exists.")
        suggestions.append(f"{base}a — adds a softer, more relationship-oriented ending.")
        suggestions.append(f"{base}h — adds a more traditional/anchored sound in Indian naming contexts.")
    return suggestions[:3]


def _law_caution_section(report: dict[str, Any]) -> dict[str, Any]:
    """Create an entertainment-only South Indian style compliance/caution reading.

    This deliberately avoids deterministic claims. It uses the same approximate
    South Indian/nakshatra-inspired profile already used by the app and converts
    it into practical risk-management advice.
    """
    calc = report.get("calculations", {}) or {}
    astro = report.get("report", {}).get("astronomy", {}) or {}
    life_path = int(calc.get("life_path", 0) or 0)
    name_expression = int(calc.get("name_expression", 0) or 0)
    personal_year = int(calc.get("personal_year", 0) or 0)
    nakshatra = str(calc.get("nakshatra") or "").split()[0]
    moon_rashi = str(calc.get("moon_rashi") or "")
    weekday_ruler = str(astro.get("weekday_ruler") or "")
    tithi = str(calc.get("tithi") or astro.get("tithi") or "")

    caution_points = 0
    signals: list[str] = []

    if weekday_ruler in {"Mars", "Saturn"}:
        caution_points += 2
        signals.append(f"Birth-day ruler {weekday_ruler} calls for discipline around anger, speed, paperwork and authority.")
    elif weekday_ruler in {"Sun"}:
        caution_points += 1
        signals.append("Sun influence can create pride and status sensitivity; avoid ego clashes with authority.")

    rahu_like = {"Ardra", "Swati", "Shatabhisha"}
    ketu_like = {"Ashwini", "Magha", "Mula"}
    mars_like = {"Mrigashira", "Chitra", "Dhanishta"}
    saturn_like = {"Pushya", "Anuradha", "Uttara", "Uttara Ashadha", "Uttara Bhadrapada"}
    if nakshatra in rahu_like:
        caution_points += 2
        signals.append(f"{nakshatra} nakshatra has a Rahu-style restless/intense tone; avoid shortcuts, hidden arrangements and impulsive online commitments.")
    elif nakshatra in ketu_like:
        caution_points += 1
        signals.append(f"{nakshatra} nakshatra can act suddenly; verify consequences before making abrupt decisions.")
    elif nakshatra in mars_like:
        caution_points += 2
        signals.append(f"{nakshatra} nakshatra carries a sharper Mars-like signature; manage conflict, driving speed and competitive reactions.")
    elif any(part in nakshatra for part in saturn_like):
        caution_points += 1
        signals.append(f"{nakshatra} nakshatra benefits from strict compliance, timing and documentation discipline.")

    if life_path in {4, 8}:
        caution_points += 2
        signals.append(f"Life Path {life_path} links strongly with systems, money, contracts and responsibility; legal risk reduces when records are clean.")
    elif life_path in {1, 5, 9}:
        caution_points += 1
        signals.append(f"Life Path {life_path} can be bold or restless; pause before confrontational decisions.")

    if name_expression in {4, 8}:
        caution_points += 1
        signals.append(f"Name Expression {name_expression} increases the need for structure, receipts, written agreements and audit trails.")

    if personal_year in {4, 8, 9}:
        caution_points += 1
        signals.append(f"Personal Year {personal_year} is better handled with closure, compliance and careful commitments.")

    if "Tithi 8" in tithi or "Tithi 14" in tithi or "Tithi 15" in tithi:
        caution_points += 1
        signals.append(f"{tithi} indicates a more intense lunar phase; choose calm responses over escalation.")

    if caution_points >= 6:
        level = "High caution — not a prediction of legal trouble, but a strong instruction to stay extremely compliant."
    elif caution_points >= 3:
        level = "Moderate caution — risk is mainly through haste, poor documentation or conflict escalation."
    else:
        level = "Low to moderate caution — legal trouble is not indicated strongly; still keep clean records and avoid casual commitments."

    practical = [
        "Do not sign, lend, borrow, invest or guarantee anything without written proof and review.",
        "Avoid arguments in public, road-rage situations, aggressive messages and impulsive social-media posts.",
        "Keep tax, property, employment, business and vehicle documents updated.",
        "When there is a dispute, use mediation, written communication and professional legal advice rather than emotional reaction.",
    ]
    if "Mesha" in moon_rashi or "Vrischika" in moon_rashi:
        practical.append("Moon Rashi shows a stronger Mars tone; be especially careful with anger, driving and physical confrontation.")
    if "Makara" in moon_rashi or "Kumbha" in moon_rashi:
        practical.append("Moon Rashi shows a Saturn tone; compliance, deadlines and documentary proof are especially important.")

    return _section(
        "Trouble With Law — South Indian Caution Reading",
        "This is an astrology-inspired compliance reading, not a legal prediction. The aim is to identify where avoidable legal friction may arise and how to stay protected.",
        bullets=[f"Overall caution level: {level}"] + signals[:7] + practical,
    )



def _digital_root(value: int) -> int:
    value = abs(int(value or 0))
    while value > 9:
        value = sum(int(ch) for ch in str(value))
    return value or 9


def _public_client_ip(request: Request | None) -> tuple[str | None, str]:
    """Return the best public client IP detected behind Railway/proxies.

    Raw IP is used only to derive an approximate location and is not written
    into the report payload. The location itself remains approximate.
    """
    if request is None:
        return None, "not available"
    candidates: list[tuple[str, str]] = []
    for header in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for", "forwarded"):
        raw = request.headers.get(header)
        if not raw:
            continue
        if header == "x-forwarded-for":
            parts = [part.strip() for part in raw.split(",") if part.strip()]
        elif header == "forwarded":
            parts = []
            for token in raw.split(";"):
                token = token.strip()
                if token.lower().startswith("for="):
                    parts.append(token.split("=", 1)[1].strip('"[]'))
        else:
            parts = [raw.strip()]
        candidates.extend((part, header) for part in parts if part)
    if request.client and request.client.host:
        candidates.append((request.client.host, "request.client"))

    for ip_text, source in candidates:
        ip_text = ip_text.split(":", 1)[0] if ip_text.count(":") == 1 and "." in ip_text else ip_text
        try:
            ip_obj = ipaddress.ip_address(ip_text)
        except ValueError:
            continue
        if ip_obj.is_global:
            return str(ip_obj), source
    return None, "private/local or unavailable"


def _lookup_ip_location(ip: str | None) -> dict[str, Any]:
    """Lookup approximate location. Uses HTTPS services and degrades safely."""
    if not ip:
        return {"ok": False, "provider": "none", "label": "Public visitor IP was not visible", "timezone": "UTC", "latitude": None, "longitude": None}

    safe_ip = quote_plus(ip)
    urls: list[tuple[str, str]] = [
        ("ipapi.co", f"https://ipapi.co/{safe_ip}/json/"),
        ("ipwho.is", f"https://ipwho.is/{safe_ip}"),
    ]

    for provider, url in urls:
        try:
            req = UrlRequest(url, headers={"User-Agent": f"LifePathDecoder/{APP_VERSION} ip-location", "Accept": "application/json"})
            with urlopen(req, timeout=2.8) as resp:
                payload = json.loads(resp.read().decode("utf-8", "ignore"))
            if provider.startswith("ipapi"):
                if payload.get("error"):
                    continue
                city = payload.get("city") or ""
                region = payload.get("region") or payload.get("region_code") or ""
                country = payload.get("country_name") or payload.get("country") or ""
                lat = payload.get("latitude")
                lon = payload.get("longitude")
                tz = payload.get("timezone") or "UTC"
            else:
                if payload.get("success") is False:
                    continue
                city = payload.get("city") or ""
                region = payload.get("region") or ""
                country = payload.get("country") or ""
                lat = payload.get("latitude")
                lon = payload.get("longitude")
                tz_payload = payload.get("timezone") or {}
                tz = tz_payload.get("id") if isinstance(tz_payload, dict) else tz_payload
            try:
                lat_f = float(lat) if lat is not None else None
                lon_f = float(lon) if lon is not None else None
            except (TypeError, ValueError):
                lat_f = lon_f = None
            if city or region or country or (lat_f is not None and lon_f is not None):
                parts = [str(x).strip() for x in [city, region, country] if str(x or "").strip()]
                return {
                    "ok": True,
                    "provider": provider,
                    "city": city,
                    "region": region,
                    "country": country,
                    "latitude": lat_f,
                    "longitude": lon_f,
                    "timezone": tz or "UTC",
                    "label": ", ".join(parts) if parts else "Approximate IP location",
                }
        except Exception:
            continue
    return {"ok": False, "provider": "none", "label": "IP location could not be resolved", "timezone": "UTC", "latitude": None, "longitude": None}


def _weekday_focus(ruler: str) -> tuple[str, str]:
    ruler = str(ruler or "")
    if ruler == "Sun":
        return "leadership, visibility and respectful dealings with authority", "ego clashes and forcing outcomes"
    if ruler == "Moon":
        return "family, emotional clarity and gentle decisions", "mood-led promises"
    if ruler == "Mars":
        return "action, courage and disciplined execution", "anger, speed and unnecessary conflict"
    if ruler == "Mercury":
        return "communication, negotiation, accounts and learning", "careless messages or misunderstood commitments"
    if ruler == "Jupiter":
        return "guidance, expansion, learning and blessings through elders/mentors", "over-promising or assuming luck will replace preparation"
    if ruler == "Venus":
        return "relationships, comfort, aesthetics, money choices and harmony", "indulgence or people-pleasing"
    if ruler == "Saturn":
        return "discipline, patience, duty, structure and documentation", "shortcuts, delays and avoidable rule-breaking"
    return "steady work and clean decisions", "rushed judgement"


def _today_prediction_section(report: dict[str, Any], request: Request | None = None) -> dict[str, Any]:
    calc = report.get("calculations", {}) or {}
    ip, ip_source = _public_client_ip(request)
    location = _lookup_ip_location(ip)
    tz_name = str(location.get("timezone") or "UTC")
    try:
        now_local = datetime.now(ZoneInfo(tz_name))
    except Exception:
        tz_name = "UTC"
        now_local = datetime.now(timezone.utc)

    lat = location.get("latitude") if location.get("ok") else None
    lon = location.get("longitude") if location.get("ok") else None
    place_label = location.get("label") or "IP location could not be resolved"
    today_astro = astronomy_snapshot(now_local.date(), now_local.time().replace(microsecond=0), lat, lon, place_label if location.get("ok") else None)

    weekday_ruler = str(today_astro.get("weekday_ruler") or "")
    focus, avoid = _weekday_focus(weekday_ruler)
    tithi = str(today_astro.get("tithi") or "")
    nakshatra = str(today_astro.get("nakshatra") or "")
    moon_rashi = str(today_astro.get("moon_rashi") or "")
    life_path = int(calc.get("life_path", 0) or 0)
    personal_year = int(calc.get("personal_year", 0) or 0)
    today_number = _digital_root(now_local.year + now_local.month + now_local.day + life_path)

    intensity = "balanced"
    if re.search(r"Tithi\s+(8|14|15)", tithi):
        intensity = "intense"
    elif re.search(r"Tithi\s+(2|3|5|10|11|12)", tithi):
        intensity = "supportive"

    if intensity == "intense":
        tone = "Today is better used for restraint, completion, careful communication and avoiding escalation."
    elif intensity == "supportive":
        tone = "Today supports constructive movement, practical decisions and conversations that need goodwill."
    else:
        tone = "Today is neutral-to-steady: results improve when you choose consistency over drama."

    personal_advice = {
        1: "take one clear initiative, but avoid dominating the room",
        2: "listen first and use diplomacy",
        3: "communicate, present and create, but avoid scattered effort",
        4: "organise documents, duties and routines",
        5: "move, sell, travel or adapt, but avoid impulsive risks",
        6: "handle family, relationship and responsibility matters",
        7: "study, reflect and verify before deciding",
        8: "focus on money, contracts, authority and execution discipline",
        9: "close loops, forgive what is finished and avoid emotional overreach",
    }.get(today_number, "keep the day simple and grounded")

    location_note = "Detected from visitor IP headers and external IP-location lookup."
    if not location.get("ok"):
        location_note = "Visitor IP location could not be resolved; this uses UTC and a generic location-neutral reading."

    today_payload = {
        "location_label": place_label,
        "timezone": tz_name,
        "local_datetime": now_local.strftime("%d %B %Y, %I:%M %p"),
        "nakshatra": nakshatra,
        "moon_rashi": moon_rashi,
        "tithi": tithi,
        "weekday_ruler": weekday_ruler,
        "today_number": today_number,
        "focus": focus,
        "avoid": avoid,
        "provider": location.get("provider"),
    }
    report.setdefault("report", {})["today_prediction"] = today_payload

    bullets = [
        f"Approximate access location: {place_label}.",
        f"Local date/time used: {today_payload['local_datetime']} ({tz_name}).",
        f"Today's South Indian layer: Nakshatra {nakshatra}, Moon Rashi {moon_rashi}, {tithi}, weekday ruler {weekday_ruler}.",
        f"Best focus today: {focus}.",
        f"Avoid today: {avoid}.",
        f"Personal day number from your Life Path and today's date: {today_number}; practical advice is to {personal_advice}.",
        tone,
        location_note,
        "This is a reflective daily reading, not a factual prediction, legal/financial advice, or guaranteed outcome.",
    ]
    return _section(
        "Today’s Prediction — IP Location South Indian Reading",
        "This section uses the visitor's approximate IP-based location and today's local sky markers to create a practical South Indian-style daily reading.",
        bullets=bullets,
    )


def _parse_prediction_date(raw: str | None) -> datetime.date:
    if not raw or not str(raw).strip():
        raise ValueError("Prediction date is required.")
    s = str(raw).strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError("Please enter the prediction date as YYYY-MM-DD or DD-MM-YYYY.")


def _given_date_prediction_section(report: dict[str, Any], req: AnalyzeRequest) -> dict[str, Any] | None:
    """Create a South Indian-style reading for a user-selected date."""
    if not req.prediction_date:
        return None

    target_date = _parse_prediction_date(req.prediction_date)
    calc = report.get("calculations", {}) or {}
    input_data = report.get("input", {}) or {}
    name = str(input_data.get("name") or req.name or "This profile")
    lat = input_data.get("latitude")
    lon = input_data.get("longitude")
    place_label = input_data.get("birth_place") or req.birth_place or "location-neutral reading"

    # Use midday for the chosen date so a date-only prediction is stable and easy to understand.
    midday = datetime.strptime("12:00", "%H:%M").time()
    astro = astronomy_snapshot(target_date, midday, lat, lon, place_label)

    weekday_ruler = str(astro.get("weekday_ruler") or "")
    focus, avoid = _weekday_focus(weekday_ruler)
    tithi = str(astro.get("tithi") or "")
    nakshatra = str(astro.get("nakshatra") or "")
    moon_rashi = str(astro.get("moon_rashi") or "")
    life_path = int(calc.get("life_path", 0) or 0)
    name_expression = int(calc.get("name_expression", 0) or 0)
    date_number = _digital_root(target_date.year + target_date.month + target_date.day + life_path)
    expression_blend = _digital_root(target_date.day + name_expression)

    days_delta = (target_date - datetime.now().date()).days
    if days_delta == 0:
        timing_label = "today"
    elif days_delta == 1:
        timing_label = "tomorrow"
    elif days_delta > 1:
        timing_label = f"{days_delta} days from today"
    elif days_delta == -1:
        timing_label = "yesterday"
    else:
        timing_label = f"{abs(days_delta)} days ago"

    intensity = "steady"
    if re.search(r"Tithi\s+(8|14|15)", tithi):
        intensity = "high-caution"
    elif re.search(r"Tithi\s+(2|3|5|10|11|12)", tithi):
        intensity = "supportive"

    date_advice = {
        1: "start, decide, lead and keep the agenda simple",
        2: "cooperate, negotiate, listen and avoid emotional overreaction",
        3: "speak, present, create and keep promises realistic",
        4: "organise documents, complete tasks and respect rules/process",
        5: "move, travel, sell or adapt, but avoid impulsive commitments",
        6: "handle relationship, home, duty and service matters",
        7: "research, review, pray/reflect and postpone noisy decisions",
        8: "focus on money, authority, contracts, execution and accountability",
        9: "complete, forgive, release and avoid dragging old emotion into new action",
    }.get(date_number, "keep the day grounded and uncluttered")

    if intensity == "high-caution":
        caution = "This date carries a sharper caution tone: avoid arguments, shortcuts, careless driving, unclear commitments and unnecessary confrontation."
    elif intensity == "supportive":
        caution = "This date is comparatively supportive for practical movement, goodwill conversations and constructive progress."
    else:
        caution = "This date is steady: outcomes improve when preparation is stronger than emotion."

    payload = {
        "date": target_date.isoformat(),
        "date_label": target_date.strftime("%d %B %Y"),
        "timing_label": timing_label,
        "place_label": place_label,
        "nakshatra": nakshatra,
        "moon_rashi": moon_rashi,
        "tithi": tithi,
        "weekday_ruler": weekday_ruler,
        "date_number": date_number,
        "expression_blend": expression_blend,
        "focus": focus,
        "avoid": avoid,
        "intensity": intensity,
    }
    report.setdefault("report", {})["given_date_prediction"] = payload

    return _section(
        "Prediction for Selected Date — South Indian Reading",
        f"This reading is generated for {name} for {payload['date_label']} ({timing_label}), using the selected date, Life Path {life_path}, name vibration and South Indian-style sky markers.",
        bullets=[
            f"Date selected: {payload['date_label']} — {timing_label}.",
            f"Location basis: {place_label}; coordinates are used when available, otherwise the reading remains location-neutral.",
            f"South Indian date layer: Nakshatra {nakshatra}, Moon Rashi {moon_rashi}, {tithi}, weekday ruler {weekday_ruler}.",
            f"Best focus for this date: {focus}.",
            f"Avoid on this date: {avoid}.",
            f"Personal date number: {date_number}; practical instruction is to {date_advice}.",
            f"Name-date blend number: {expression_blend}; use this to tune communication, visibility and timing for the day.",
            caution,
            "This is a reflective timing guide, not a guaranteed prediction or substitute for legal, medical, financial or professional advice.",
        ],
    )


def _quick_report_summary(report: dict[str, Any], req: AnalyzeRequest) -> dict[str, Any]:
    """Build a compact at-a-glance summary shown before section tiles."""
    calc = report.get("calculations", {}) or {}
    input_data = report.get("input", {}) or {}
    report_data = report.get("report", {}) or {}
    astro = report_data.get("astronomy", {}) or {}
    name = str(input_data.get("name") or req.name or "This profile").strip() or "This profile"
    title = str(report_data.get("title") or "Life Path Report")
    life_path = calc.get("life_path", "-")
    life_title = calc.get("life_path_title") or "core pattern"
    personal_year = calc.get("personal_year", "-")
    personal_theme = calc.get("personal_year_theme") or "current-year theme"
    nakshatra = calc.get("nakshatra") or "not available"
    moon_rashi = calc.get("moon_rashi") or "not available"
    name_meaning = calc.get("name_meaning") or "not available"
    commonness = calc.get("name_commonness") or "not available"
    lucky_color = calc.get("lucky_color") or "-"
    lucky_fruit = calc.get("lucky_fruit") or "-"
    lucky_day = calc.get("lucky_day") or "-"
    lucky_number = calc.get("lucky_number") or "-"
    birth_place = input_data.get("birth_place") or "birth place not supplied"
    birth_time = input_data.get("birth_time") or "time not supplied"
    language_note = ""
    if req.output_language and req.output_language != "english":
        language_note = f" The selected output language is {req.output_language.title()}, with full native rendering reserved for production translation integration."
    tone_label = (req.tone or "balanced").replace("_", " ").title()
    length_label = (req.report_length or "detailed").title()
    body = (
        f"{name}'s {title} is anchored by Life Path {life_path} — {life_title}. "
        f"The report combines name meaning, numerology-style calculations, South Indian-style nakshatra/rashi signals, "
        f"and current personal-year timing into a practical reading. It was generated for {birth_place} with {birth_time}, "
        f"using a {length_label.lower()} report length and {tone_label.lower()} tone.{language_note}"
    )
    today_prediction = report_data.get("today_prediction") if isinstance(report_data.get("today_prediction"), dict) else None
    bullets = [
        f"Core signature: Life Path {life_path}, Name Expression {calc.get('name_expression', '-')}, Soul Urge {calc.get('soul_urge', '-')}, Birth Day {calc.get('birth_day', '-')}",
        f"South Indian layer: Nakshatra {nakshatra}, Moon Rashi {moon_rashi}, Tithi {calc.get('tithi', '-')}, Sun Sign {calc.get('sun_sign', '-')}",
        f"Name insight: {name_meaning}; commonness estimate: {commonness}",
        f"Current cycle: Personal Year {personal_year} — {personal_theme}",
        f"Lucky signals: {lucky_color} color, {lucky_fruit} fruit, {lucky_day} day, number {lucky_number}",
    ]
    if today_prediction:
        bullets.append(
            f"Today’s IP-location reading: {today_prediction.get('location_label', 'location unavailable')} — focus on {today_prediction.get('focus', 'steady action')} and avoid {today_prediction.get('avoid', 'rushed judgement')}."
        )
    given_prediction = report_data.get("given_date_prediction") if isinstance(report_data.get("given_date_prediction"), dict) else None
    if given_prediction:
        bullets.append(
            f"Selected-date prediction: {given_prediction.get('date_label', 'selected date')} — focus on {given_prediction.get('focus', 'steady action')} and avoid {given_prediction.get('avoid', 'rushed judgement')}."
        )
    bullets.append("The tiles below open the detailed sections; each tile expands into the full interpretation, cautions and practical guidance.")
    if req.partner_name and req.partner_date_of_birth:
        bullets.append(f"Compatibility inputs included for partner: {req.partner_name}.")
    if req.no_storage:
        bullets.append("Privacy: No-storage mode was selected, so this report is not kept in local history.")
    else:
        bullets.append("Privacy: This report is saved in local history and can be deleted from the History area.")
    return {"title": "Report Summary", "body": body, "bullets": bullets}




LOCALIZED_REPORT_TEXT: dict[str, dict[str, str]] = {
    "kannada": {
        "report_title": "ಜೀವನ ಪಥ ವರದಿ",
        "summary_title": "ವರದಿ ಸಾರಾಂಶ",
        "summary_body": "{name} ಅವರ ವರದಿ ಜೀವನ ಪಥ {life_path} — {life_title} ಅನ್ನು ಆಧಾರವಾಗಿ ತೆಗೆದುಕೊಂಡಿದೆ. ಹೆಸರು, ಜನ್ಮ ದಿನಾಂಕ, ಜನ್ಮ ಸಮಯ, ಜನ್ಮ ಸ್ಥಳ, ನಕ್ಷತ್ರ, ಚಂದ್ರ ರಾಶಿ, ತಿಥಿ ಮತ್ತು ಪ್ರಸ್ತುತ ವೈಯಕ್ತಿಕ ವರ್ಷದ ಸೂಚನೆಗಳನ್ನು ಸೇರಿಸಿ ಈ ಓದನ್ನು ರೂಪಿಸಲಾಗಿದೆ.",
        "section_body": "{name} ಅವರ ಈ ವಿಭಾಗವು ಜೀವನ ಪಥ {life_path}, ಹೆಸರು ಸಂಖ್ಯೆ {name_expression}, ಆತ್ಮ ಸಂಖ್ಯೆ {soul_urge}, ನಕ್ಷತ್ರ {nakshatra}, ಚಂದ್ರ ರಾಶಿ {moon_rashi} ಮತ್ತು ವೈಯಕ್ತಿಕ ವರ್ಷ {personal_year} ಆಧಾರವಾಗಿ ಓದಬೇಕು.",
        "bullet_core": "ಮೂಲ ಸೂಚನೆ: ಜೀವನ ಪಥ {life_path}, ಹೆಸರು ಸಂಖ್ಯೆ {name_expression}, ಆತ್ಮ ಸಂಖ್ಯೆ {soul_urge}, ಜನ್ಮ ದಿನ {birth_day}.",
        "bullet_south": "ದಕ್ಷಿಣ ಭಾರತೀಯ ಪದರ: ನಕ್ಷತ್ರ {nakshatra}, ಚಂದ್ರ ರಾಶಿ {moon_rashi}, ತಿಥಿ {tithi}, ಸೂರ್ಯ ರಾಶಿ {sun_sign}.",
        "bullet_name": "ಹೆಸರಿನ ಅರ್ಥ: {name_meaning}; ಸಾಮಾನ್ಯತೆ: {name_commonness}.",
        "bullet_cycle": "ಪ್ರಸ್ತುತ ಚಕ್ರ: ವೈಯಕ್ತಿಕ ವರ್ಷ {personal_year} — {personal_year_theme}.",
        "bullet_lucky": "ಶುಭ ಸೂಚನೆಗಳು: ಬಣ್ಣ {lucky_color}, ಹಣ್ಣು {lucky_fruit}, ದಿನ {lucky_day}, ಸಂಖ್ಯೆ {lucky_number}.",
        "bullet_action": "ಪ್ರಾಯೋಗಿಕ ಕ್ರಮ: {action}",
        "privacy_saved": "ಗೌಪ್ಯತೆ: ಈ ವರದಿ ಸ್ಥಳೀಯ ಇತಿಹಾಸದಲ್ಲಿ ಉಳಿಯುತ್ತದೆ; History ವಿಭಾಗದಿಂದ ಅಳಿಸಬಹುದು.",
        "privacy_nostore": "ಗೌಪ್ಯತೆ: No-storage ಆಯ್ಕೆ ಮಾಡಿರುವುದರಿಂದ ಈ ವರದಿ ಸ್ಥಳೀಯ ಇತಿಹಾಸದಲ್ಲಿ ಉಳಿಯುವುದಿಲ್ಲ.",
        "tiles_note": "ಕೆಳಗಿನ ಟೈಲ್‌ಗಳನ್ನು ತೆರೆಯುವುದರಿಂದ ಪ್ರತಿ ವಿಭಾಗದ ವಿವರವಾದ ಓದು ಕಾಣುತ್ತದೆ.",
        "today_title": "ಇಂದಿನ ಭವಿಷ್ಯ — ಸ್ಥಳ ಆಧಾರಿತ ಓದು",
        "date_title": "ಆಯ್ಕೆ ಮಾಡಿದ ದಿನಾಂಕದ ಭವಿಷ್ಯ",
        "law_title": "ಕಾನೂನು ಸಂಬಂಧಿತ ಎಚ್ಚರಿಕೆ — ದಕ್ಷಿಣ ಭಾರತೀಯ ಓದು",
        "compat_title": "ಜೋಡಿ ಹೊಂದಾಣಿಕೆ ಅಂಕ",
        "name_title": "ಹೆಸರು spelling ಮತ್ತು ಶುಭ ಹೆಸರು ಸೂಚನೆಗಳು",
        "mode_title": "ವರದಿ ವಿಧಾನ ಮತ್ತು ಗೌಪ್ಯತೆ",
        "disclaimer": "ಹಕ್ಕು ನಿರಾಕರಣೆ: ಇದು ಮನನ/ಮನರಂಜನೆಗಾಗಿ ಮಾತ್ರ. ಇದು ವೈಜ್ಞಾನಿಕ, ವೈದ್ಯಕೀಯ, ಮಾನಸಿಕ, ಕಾನೂನು ಅಥವಾ ಹಣಕಾಸು ಸಲಹೆಯಲ್ಲ.",
        "themes_default": "ಶಾಂತವಾಗಿ ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳಿ, ದಾಖಲಾತಿ ಇಟ್ಟುಕೊಳ್ಳಿ ಮತ್ತು ಅತಿವೇಗದ ಪ್ರತಿಕ್ರಿಯೆಗಳನ್ನು ತಪ್ಪಿಸಿ.",
        "themes_career": "ಕೆಲಸದಲ್ಲಿ ಶಿಸ್ತು, ಸಂವಹನ ಮತ್ತು ಸಮಯಪಾಲನೆಯನ್ನು ಬಲಪಡಿಸಿ.",
        "themes_relationship": "ಸಂಬಂಧಗಳಲ್ಲಿ ಸ್ಪಷ್ಟ ಮಾತು, ಸಹನೆ ಮತ್ತು ಗೌರವಪೂರ್ಣ ಮಿತಿಗಳನ್ನು ಪಾಲಿಸಿ.",
        "themes_wealth": "ಹಣಕಾಸಿನಲ್ಲಿ ದಾಖಲೆ, ಬಜೆಟ್ ಮತ್ತು ದೀರ್ಘಕಾಲದ ದೃಷ್ಟಿಕೋನವನ್ನು ಅನುಸರಿಸಿ.",
        "themes_law": "ಒಪ್ಪಂದ, ಸಾಲ, ಗ್ಯಾರಂಟಿ, ಸಾಮಾಜಿಕ ಮಾಧ್ಯಮ ಮತ್ತು ಸಾರ್ವಜನಿಕ ವಾದಗಳಲ್ಲಿ ಹೆಚ್ಚು ಎಚ್ಚರಿಕೆ ವಹಿಸಿ.",
        "themes_date": "ಆ ದಿನದ ಶಕ್ತಿಯನ್ನು ಶಾಂತ ಯೋಜನೆ ಮತ್ತು ಸಮತೋಲನದ ಕ್ರಮಕ್ಕೆ ಬಳಸಿ.",
    },
    "hindi": {
        "report_title": "जीवन पथ रिपोर्ट",
        "summary_title": "रिपोर्ट सारांश",
        "summary_body": "{name} की रिपोर्ट जीवन पथ {life_path} — {life_title} पर आधारित है। नाम, जन्म तिथि, जन्म समय, जन्म स्थान, नक्षत्र, चंद्र राशि, तिथि और वर्तमान व्यक्तिगत वर्ष को मिलाकर यह पठन तैयार किया गया है.",
        "section_body": "{name} के लिए यह भाग जीवन पथ {life_path}, नाम संख्या {name_expression}, आत्म संख्या {soul_urge}, नक्षत्र {nakshatra}, चंद्र राशि {moon_rashi} और व्यक्तिगत वर्ष {personal_year} के आधार पर पढ़ा जाना चाहिए.",
        "bullet_core": "मुख्य संकेत: जीवन पथ {life_path}, नाम संख्या {name_expression}, आत्म संख्या {soul_urge}, जन्म दिन {birth_day}.",
        "bullet_south": "दक्षिण भारतीय परत: नक्षत्र {nakshatra}, चंद्र राशि {moon_rashi}, तिथि {tithi}, सूर्य राशि {sun_sign}.",
        "bullet_name": "नाम का अर्थ: {name_meaning}; सामान्यता: {name_commonness}.",
        "bullet_cycle": "वर्तमान चक्र: व्यक्तिगत वर्ष {personal_year} — {personal_year_theme}.",
        "bullet_lucky": "शुभ संकेत: रंग {lucky_color}, फल {lucky_fruit}, दिन {lucky_day}, संख्या {lucky_number}.",
        "bullet_action": "व्यावहारिक कदम: {action}",
        "privacy_saved": "गोपनीयता: यह रिपोर्ट स्थानीय इतिहास में सहेजी जाएगी और History से हटाई जा सकती है.",
        "privacy_nostore": "गोपनीयता: No-storage चुना गया है, इसलिए यह रिपोर्ट स्थानीय इतिहास में सहेजी नहीं जाएगी.",
        "tiles_note": "नीचे के टाइल खोलने पर हर भाग का विस्तृत पठन दिखेगा.",
        "today_title": "आज का पूर्वानुमान — स्थान आधारित पठन",
        "date_title": "चुनी हुई तारीख का पूर्वानुमान",
        "law_title": "कानूनी सावधानी — दक्षिण भारतीय पठन",
        "compat_title": "साथी अनुकूलता अंक",
        "name_title": "नाम spelling और शुभ नाम सुझाव",
        "mode_title": "रिपोर्ट मोड और गोपनीयता",
        "disclaimer": "अस्वीकरण: यह केवल चिंतन/मनोरंजन के लिए है। यह वैज्ञानिक, चिकित्सा, मनोवैज्ञानिक, कानूनी या वित्तीय सलाह नहीं है.",
        "themes_default": "शांत निर्णय लें, रिकॉर्ड रखें और जल्दबाज़ी वाली प्रतिक्रिया से बचें.",
        "themes_career": "काम में अनुशासन, संवाद और समयपालन को मजबूत करें.",
        "themes_relationship": "रिश्तों में स्पष्ट बात, धैर्य और सम्मानजनक सीमाएँ रखें.",
        "themes_wealth": "धन के मामलों में दस्तावेज़, बजट और लंबी सोच अपनाएँ.",
        "themes_law": "अनुबंध, ऋण, गारंटी, सोशल मीडिया और सार्वजनिक बहस में अधिक सावधानी रखें.",
        "themes_date": "उस दिन की ऊर्जा को शांत योजना और संतुलित कार्रवाई में लगाएँ.",
    },
    "tamil": {
        "report_title": "வாழ்க்கைப் பாதை அறிக்கை",
        "summary_title": "அறிக்கை சுருக்கம்",
        "summary_body": "{name} அவர்களின் அறிக்கை வாழ்க்கைப் பாதை {life_path} — {life_title} என்பதை அடிப்படையாகக் கொண்டது. பெயர், பிறந்த தேதி, பிறந்த நேரம், பிறந்த இடம், நட்சத்திரம், சந்திர ராசி, திதி மற்றும் நடப்பு தனிப்பட்ட ஆண்டை இணைத்து இந்த வாசிப்பு உருவாக்கப்பட்டுள்ளது.",
        "section_body": "{name} அவர்களுக்கு இந்த பகுதி வாழ்க்கைப் பாதை {life_path}, பெயர் எண் {name_expression}, ஆன்ம எண் {soul_urge}, நட்சத்திரம் {nakshatra}, சந்திர ராசி {moon_rashi} மற்றும் தனிப்பட்ட ஆண்டு {personal_year} அடிப்படையில் வாசிக்கப்பட வேண்டும்.",
        "bullet_core": "முக்கிய குறிப்பு: வாழ்க்கைப் பாதை {life_path}, பெயர் எண் {name_expression}, ஆன்ம எண் {soul_urge}, பிறந்த நாள் {birth_day}.",
        "bullet_south": "தென்னிந்திய அடுக்கு: நட்சத்திரம் {nakshatra}, சந்திர ராசி {moon_rashi}, திதி {tithi}, சூரிய ராசி {sun_sign}.",
        "bullet_name": "பெயரின் பொருள்: {name_meaning}; பொதுவான தன்மை: {name_commonness}.",
        "bullet_cycle": "தற்போதைய சுழற்சி: தனிப்பட்ட ஆண்டு {personal_year} — {personal_year_theme}.",
        "bullet_lucky": "அதிர்ஷ்ட குறிகள்: நிறம் {lucky_color}, பழம் {lucky_fruit}, நாள் {lucky_day}, எண் {lucky_number}.",
        "bullet_action": "நடைமுறை செயல்: {action}",
        "privacy_saved": "தனியுரிமை: இந்த அறிக்கை உள்ளூர் வரலாற்றில் சேமிக்கப்படும்; History பகுதியில் இருந்து நீக்கலாம்.",
        "privacy_nostore": "தனியுரிமை: No-storage தேர்வு செய்யப்பட்டதால் இந்த அறிக்கை உள்ளூர் வரலாற்றில் சேமிக்கப்படாது.",
        "tiles_note": "கீழே உள்ள டைல்களைத் திறந்தால் ஒவ்வொரு பகுதியின் விரிவான வாசிப்பு தெரியும்.",
        "today_title": "இன்றைய கணிப்பு — இடம் அடிப்படையிலான வாசிப்பு",
        "date_title": "தேர்ந்தெடுத்த தேதிக்கான கணிப்பு",
        "law_title": "சட்ட சம்பந்தமான எச்சரிக்கை — தென்னிந்திய வாசிப்பு",
        "compat_title": "இணை பொருத்த மதிப்பெண்",
        "name_title": "பெயர் spelling மற்றும் அதிர்ஷ்ட பெயர் பரிந்துரைகள்",
        "mode_title": "அறிக்கை முறை மற்றும் தனியுரிமை",
        "disclaimer": "மறுப்பு: இது சிந்தனை/வேடிக்கை பயன்பாட்டிற்காக மட்டுமே. இது அறிவியல், மருத்துவ, உளவியல், சட்ட அல்லது நிதி ஆலோசனை அல்ல.",
        "themes_default": "அமைதியாக முடிவு எடுக்கவும், பதிவுகளை வைத்திருக்கவும், அவசரமான பதில்களைத் தவிர்க்கவும்.",
        "themes_career": "வேலையில் ஒழுக்கம், தொடர்பு மற்றும் நேரப்படுத்தலை வலுப்படுத்தவும்.",
        "themes_relationship": "உறவுகளில் தெளிவான பேச்சு, பொறுமை மற்றும் மரியாதையான எல்லைகளை கடைபிடிக்கவும்.",
        "themes_wealth": "பண விஷயங்களில் ஆவணம், பட்ஜெட் மற்றும் நீண்டகால பார்வையைப் பின்பற்றவும்.",
        "themes_law": "ஒப்பந்தம், கடன், உத்தரவாதம், சமூக ஊடகம் மற்றும் பொது விவாதங்களில் அதிக கவனம் தேவை.",
        "themes_date": "அந்த நாளின் சக்தியை அமைதியான திட்டமிடல் மற்றும் சமநிலையான செயலுக்கு பயன்படுத்தவும்.",
    },
}


def _localized_terms(req: AnalyzeRequest) -> dict[str, str] | None:
    lang = (req.output_language or "english").lower().strip()
    return LOCALIZED_REPORT_TEXT.get(lang)


def _section_theme_key(title: str) -> str:
    t = (title or "").lower()
    if any(word in t for word in ("career", "professional", "work", "business")):
        return "themes_career"
    if any(word in t for word in ("relationship", "partner", "marriage", "love", "compatibility", "children", "family")):
        return "themes_relationship"
    if any(word in t for word in ("wealth", "money", "abundance", "finance")):
        return "themes_wealth"
    if any(word in t for word in ("law", "caution", "compliance")):
        return "themes_law"
    if any(word in t for word in ("today", "date", "prediction", "timeline", "future")):
        return "themes_date"
    return "themes_default"


def _localized_title(title: str, terms: dict[str, str]) -> str:
    t = (title or "").lower()
    if "report mode" in t or "privacy" in t:
        return terms["mode_title"]
    if "today" in t:
        return terms["today_title"]
    if "selected date" in t or "prediction for" in t:
        return terms["date_title"]
    if "law" in t:
        return terms["law_title"]
    if "compatibility" in t or "partner" in t:
        return terms["compat_title"]
    if "name spelling" in t or "lucky name" in t:
        return terms["name_title"]
    # Add a readable target-language prefix so even uncommon generated section names appear localized.
    lang_title_prefix = {
        "kannada": "ವಿಭಾಗ",
        "hindi": "भाग",
        "tamil": "பகுதி",
    }
    for lang, meta in LOCALIZED_REPORT_TEXT.items():
        if terms is meta:
            return f"{lang_title_prefix.get(lang, '')}: {title}".strip()
    return title


def _localized_context(report: dict[str, Any], req: AnalyzeRequest) -> dict[str, Any]:
    calc = report.get("calculations", {}) or {}
    input_data = report.get("input", {}) or {}
    return {
        "name": str(input_data.get("name") or req.name or "Profile"),
        "dob": str(input_data.get("dob") or req.date_of_birth or "-"),
        "birth_place": str(input_data.get("birth_place") or req.birth_place or "-"),
        "birth_time": str(input_data.get("birth_time") or req.birth_time or "-"),
        "life_path": calc.get("life_path", "-"),
        "life_title": calc.get("life_path_title") or "core pattern",
        "name_expression": calc.get("name_expression", "-"),
        "soul_urge": calc.get("soul_urge", "-"),
        "birth_day": calc.get("birth_day", "-"),
        "nakshatra": calc.get("nakshatra") or "-",
        "moon_rashi": calc.get("moon_rashi") or "-",
        "tithi": calc.get("tithi") or "-",
        "sun_sign": calc.get("sun_sign") or "-",
        "personal_year": calc.get("personal_year", "-"),
        "personal_year_theme": calc.get("personal_year_theme") or "-",
        "name_meaning": calc.get("name_meaning") or "-",
        "name_commonness": calc.get("name_commonness") or "-",
        "lucky_color": calc.get("lucky_color") or "-",
        "lucky_fruit": calc.get("lucky_fruit") or "-",
        "lucky_day": calc.get("lucky_day") or "-",
        "lucky_number": calc.get("lucky_number") or "-",
    }


def _localized_summary(report: dict[str, Any], req: AnalyzeRequest) -> dict[str, Any]:
    terms = _localized_terms(req)
    if not terms:
        return _quick_report_summary(report, req)
    ctx = _localized_context(report, req)
    bullets = [
        terms["bullet_core"].format(**ctx),
        terms["bullet_south"].format(**ctx),
        terms["bullet_name"].format(**ctx),
        terms["bullet_cycle"].format(**ctx),
        terms["bullet_lucky"].format(**ctx),
        terms["tiles_note"],
        terms["privacy_nostore"] if req.no_storage else terms["privacy_saved"],
    ]
    today_prediction = report.get("report", {}).get("today_prediction") if isinstance(report.get("report", {}).get("today_prediction"), dict) else None
    if today_prediction:
        bullets.insert(5, terms["bullet_action"].format(action=f"{today_prediction.get('focus', 'steady action')} / avoid {today_prediction.get('avoid', 'rushed judgement')}"))
    given_prediction = report.get("report", {}).get("given_date_prediction") if isinstance(report.get("report", {}).get("given_date_prediction"), dict) else None
    if given_prediction:
        bullets.insert(5, terms["bullet_action"].format(action=f"{given_prediction.get('date_label', 'selected date')}: {given_prediction.get('focus', 'steady action')}"))
    return {
        "title": terms["summary_title"],
        "body": terms["summary_body"].format(**ctx),
        "bullets": bullets,
    }


def _localize_report_sections(report: dict[str, Any], req: AnalyzeRequest, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = _localized_terms(req)
    if not terms:
        return sections
    ctx = _localized_context(report, req)
    localized: list[dict[str, Any]] = []
    for sec in sections:
        title = str(sec.get("title") or "")
        theme_action = terms[_section_theme_key(title)]
        body = terms["section_body"].format(**ctx)
        bullets = [
            terms["bullet_core"].format(**ctx),
            terms["bullet_south"].format(**ctx),
            terms["bullet_action"].format(action=theme_action),
            terms["bullet_lucky"].format(**ctx),
        ]
        # Preserve important numeric/data points from specialized sections while keeping the surrounding text native.
        if "compatibility" in title.lower() or "partner" in title.lower():
            bullets.append(terms["bullet_action"].format(action=f"{req.partner_name or 'Partner'} — compatibility details are based on both dates and names."))
        if "today" in title.lower():
            tp = report.get("report", {}).get("today_prediction") or {}
            if isinstance(tp, dict):
                bullets.append(terms["bullet_action"].format(action=f"{tp.get('location_label', '-')}: focus {tp.get('focus', '-')}; avoid {tp.get('avoid', '-')}"))
        if "selected date" in title.lower() or "prediction for" in title.lower():
            gp = report.get("report", {}).get("given_date_prediction") or {}
            if isinstance(gp, dict):
                bullets.append(terms["bullet_action"].format(action=f"{gp.get('date_label', '-')}: {gp.get('focus', '-')}"))
        localized.append({
            "title": _localized_title(title, terms),
            "body": body,
            "bullets": bullets,
            "table": sec.get("table", []),
        })
    report["report"]["title"] = terms["report_title"]
    return localized

def enhance_report(report: dict[str, Any], req: AnalyzeRequest, request: Request | None = None) -> dict[str, Any]:
    calc = report.get("calculations", {})
    input_data = report.get("input", {})
    sections = list(report.get("report", {}).get("sections", []))

    settings_bullets = [
        f"Report length selected: {req.report_length.title()}.",
        f"Tone selected: {req.tone.replace('_', ' ').title()}.",
        f"Language selected: {req.output_language.title()}.",
        "Brutally Honest Mode is ON." if req.brutal_mode or req.tone == "brutally_honest" else "Balanced interpretation mode is ON.",
        "No-storage mode requested: this report will not be kept in local history." if req.no_storage else "Report history is enabled for convenience and can be deleted.",
    ]
    sections.insert(0, _section("Report Mode & Privacy", bullets=settings_bullets))
    sections.insert(1, _today_prediction_section(report, request))
    given_date_section = _given_date_prediction_section(report, req)
    if given_date_section:
        sections.insert(2, given_date_section)


    if req.brutal_mode or req.tone == "brutally_honest":
        sections.insert(2, _section(
            "Brutally Honest Upgrade",
            "This section deliberately sharpens the advice: the biggest risk is not lack of potential, but repeating the same comfort pattern while expecting a different result.",
            bullets=[
                "Stop treating insight as progress unless it changes behaviour.",
                "Choose one measurable action this week that proves the report is being used, not merely admired.",
                f"Your Life Path {calc.get('life_path')} pattern becomes powerful only when it is disciplined.",
            ],
        ))
    elif req.tone == "positive":
        sections.insert(2, _section(
            "Positive Strength Lens",
            "This version emphasises encouragement, self-belief and practical optimism.",
            bullets=["Your report should be read as a map of usable strengths, not a verdict.", "The best next step is the one that makes you more consistent and more alive."],
        ))

    if req.partner_name and req.partner_date_of_birth:
        try:
            partner = build_report(req.partner_name, req.partner_date_of_birth, analysis_type="relationships", birth_place=req.partner_birth_place, birth_time=req.partner_birth_time)
            score, notes = _compatibility_score(report, partner)
            sections.insert(3, _section(
                "Partner Compatibility Score",
                f"Compatibility estimate for {input_data.get('name')} and {partner.get('input', {}).get('name')}: {score}/100.",
                bullets=notes + [
                    f"Partner Life Path: {partner.get('calculations', {}).get('life_path')} — {partner.get('calculations', {}).get('life_path_title')}",
                    f"Partner Nakshatra / Moon Rashi: {partner.get('calculations', {}).get('nakshatra')} / {partner.get('calculations', {}).get('moon_rashi')}",
                    "Use this as a conversation map, not a fixed relationship verdict.",
                ],
            ))
        except Exception:
            sections.insert(3, _section("Partner Compatibility", "Partner details were provided, but the compatibility layer could not calculate because the partner DOB/time format needs correction."))

    sections.append(_law_caution_section(report))

    sections.append(_section(
        "Name Spelling & Lucky Name Suggestions",
        "Small spelling changes can be explored for branding, public identity or numerology-style preference, but legal names and established personal identity should not be changed casually.",
        bullets=_name_spelling_suggestions(str(input_data.get("name", ""))) + [
            "For business names, prefer clarity, recall and trust before numerology.",
            f"Current Name Expression: {calc.get('name_expression')}.",
        ],
    ))
    # Trim optional sections for shorter report lengths while keeping critical items.
    if req.report_length == "short":
        sections = sections[:8]
    elif req.report_length == "medium":
        sections = sections[:14]

    if not any(str(sec.get("title", "")).startswith("Trouble With Law") for sec in sections):
        sections.append(_law_caution_section(report))

    sections = _localize_report_sections(report, req, sections)
    report["report"]["sections"] = sections
    quick_summary = _localized_summary(report, req)
    report["report"]["quick_summary"] = quick_summary
    report["input"].update({
        "report_length": req.report_length,
        "tone": req.tone,
        "output_language": req.output_language,
        "brutal_mode": req.brutal_mode,
        "no_storage": req.no_storage,
        "prediction_date": req.prediction_date,
        "partner_name": req.partner_name,
        "partner_date_of_birth": req.partner_date_of_birth,
    })
    # Rebuild full text from sections so copy, TXT, PDF and share all include the upgrades.
    lines = [report["report"].get("title", APP_NAME), "", f"Name: {input_data.get('name')}", f"Date of Birth: {input_data.get('dob')}", ""]
    lines.append(quick_summary.get("title", "Report Summary"))
    if quick_summary.get("body"):
        lines.append(str(quick_summary.get("body")))
    for b in quick_summary.get("bullets", []) or []:
        lines.append(f"- {b}")
    lines.append("")
    for sec in sections:
        lines.append(str(sec.get("title", "")))
        if sec.get("body"):
            lines.append(str(sec.get("body")))
        for b in sec.get("bullets", []) or []:
            lines.append(f"- {b}")
        for row in sec.get("table", []) or []:
            lines.append("- " + " | ".join(str(v) for v in row.values()))
        lines.append("")
    terms_for_text = _localized_terms(req)
    lines.append(terms_for_text["disclaimer"] if terms_for_text else "Disclaimer: Reflective/entertainment use only. Not scientific, medical, psychological, legal or financial advice.")
    report["report"]["full_text"] = "\n".join(lines).strip()
    return report


def save_report_history(user_id: int, req: AnalyzeRequest, report: dict[str, Any]) -> int | None:
    if req.no_storage:
        return None
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO report_history
            (user_id, name, analysis_type, input_payload, report_payload, full_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                report.get("input", {}).get("name", req.name),
                req.analysis_type,
                json.dumps(_safe_payload_from_req(req), ensure_ascii=False),
                json.dumps(report, ensure_ascii=False),
                report.get("report", {}).get("full_text", ""),
                _now_iso(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def _default_config() -> dict[str, Any]:
    return {
        "brand_tagline": "Shockingly Accurate",
        "brand_logo": {"url": "/brand/logo", "source": "default"},
        "pricing": {"free": "Summary", "premium": "₹99 Full Report", "compatibility": "₹149 Couple Report"},
        "features": {"pdf": True, "whatsapp": True, "history": True, "compatibility": True, "story_cards": True, "demo_data_button": True},
        "privacy": {"share_expiry_days": SHARE_EXPIRY_DAYS, "no_storage_available": True},
    }


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge stored config over defaults without dropping newly added nested feature keys."""
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_app_config() -> dict[str, Any]:
    # Some local/Railway installs may carry an older SQLite file that predates app_config.
    # Keep config and demo-data endpoints self-healing instead of failing with "no such table".
    init_db()
    config = _default_config()
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM app_config").fetchall()
    stored: dict[str, Any] = {}
    for row in rows:
        try:
            stored[row["key"]] = json.loads(row["value"])
        except Exception:
            stored[row["key"]] = row["value"]
    return _deep_merge_dict(config, stored)


def save_app_config(payload: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with get_db() as conn:
        for key, value in payload.items():
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value, updated_at) VALUES (?, ?, ?)",
                (str(key), json.dumps(value, ensure_ascii=False), _now_iso()),
            )
        conn.commit()
    return load_app_config()


def active_logo_path() -> Path:
    if UPLOADED_LOGO_PATH.exists():
        return UPLOADED_LOGO_PATH
    return DEFAULT_LOGO_PATH


def _make_border_background_transparent(image: "Image.Image") -> "Image.Image":
    """Remove only near-white background connected to the image border.

    This keeps white details inside a logo, but removes common white JPEG/PNG canvases.
    """
    image = image.convert("RGBA")
    w, h = image.size
    if not w or not h:
        return image
    px = image.load()

    def is_background(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        if a < 12:
            return True
        # Near-white / pale matte backgrounds. Conservative enough to preserve most logo art.
        return a > 220 and r >= 238 and g >= 238 and b >= 238 and (max(r, g, b) - min(r, g, b) <= 18)

    from collections import deque
    q = deque()
    seen: set[tuple[int, int]] = set()
    for x in range(w):
        for y in (0, h - 1):
            if (x, y) not in seen and is_background(x, y):
                seen.add((x, y)); q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in seen and is_background(x, y):
                seen.add((x, y)); q.append((x, y))

    while q:
        x, y = q.popleft()
        r, g, b, a = px[x, y]
        px[x, y] = (r, g, b, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and is_background(nx, ny):
                seen.add((nx, ny)); q.append((nx, ny))
    return image


def _prepare_uploaded_logo(image: "Image.Image") -> "Image.Image":
    image = ImageOps.exif_transpose(image).convert("RGBA")
    # Work at a bounded size first so transparency cleanup is fast on large uploads.
    image.thumbnail((1200, 1200), Image.LANCZOS)
    image = _make_border_background_transparent(image)
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    # Keep the stored brand asset small and transparent. The UI also constrains it further.
    image.thumbnail((520, 180), Image.LANCZOS)
    canvas = Image.new("RGBA", (560, 200), (255, 255, 255, 0))
    x = (canvas.width - image.width) // 2
    y = (canvas.height - image.height) // 2
    canvas.alpha_composite(image, (x, y))
    return canvas


def save_uploaded_logo(data_url: str) -> dict[str, Any]:
    if Image is None:
        raise HTTPException(status_code=500, detail="Pillow is required to validate and save uploaded logos.")
    raw = (data_url or "").strip()
    if "," in raw and raw.lower().startswith("data:image/"):
        header, encoded = raw.split(",", 1)
        if not any(kind in header.lower() for kind in ("image/png", "image/jpeg", "image/jpg", "image/webp")):
            raise HTTPException(status_code=400, detail="Logo must be a PNG, JPG, JPEG or WEBP image.")
    else:
        encoded = raw
    try:
        blob = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Logo upload was not valid base64 image data.") from exc
    if len(blob) > 3_500_000:
        raise HTTPException(status_code=400, detail="Logo is too large. Please upload an image under 3.5 MB.")
    try:
        image = Image.open(io.BytesIO(blob))
        image.verify()
        image = Image.open(io.BytesIO(blob))
        image = _prepare_uploaded_logo(image)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded logo file could not be read as an image.") from exc
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image.save(UPLOADED_LOGO_PATH, format="PNG", optimize=True)
    saved_at = _now_iso()
    return save_app_config({
        "brand_logo": {
            "url": f"/brand/logo?ts={quote_plus(saved_at)}",
            "source": "admin_upload_transparent_small",
            "updated_at": saved_at,
            "max_display_width": 280,
            "background": "transparent",
        }
    })


def reset_uploaded_logo() -> dict[str, Any]:
    if UPLOADED_LOGO_PATH.exists():
        UPLOADED_LOGO_PATH.unlink()
    return save_app_config({"brand_logo": {"url": "/brand/logo", "source": "default", "updated_at": _now_iso()}})


def report_pdf_bytes(report: dict[str, Any]) -> bytes:
    if Image is None or ImageDraw is None:
        raise HTTPException(status_code=500, detail="Pillow is required for PDF export.")
    full_text = report.get("report", {}).get("full_text", "") or "Life Path Decoder Report"
    title = f"{report.get('input', {}).get('name', 'Life Path')} Report"
    W, H = 1240, 1754
    margin = 90
    pages = []
    font_title = _load_font(46, True, full_text)
    font_body = _load_font(26, False, full_text)
    font_footer = _load_font(20, False, full_text)
    line_h = 36
    max_chars = 82
    lines = []
    for para in full_text.splitlines():
        if not para.strip():
            lines.append("")
        else:
            lines.extend(textwrap.wrap(para, width=max_chars) or [para])
    idx = 0
    page_no = 1
    while idx < len(lines) or not pages:
        img = Image.new("RGB", (W, H), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, W, 34), fill=(26, 17, 72))
        draw.text((margin, 70), title[:60], font=font_title, fill=(26, 17, 72))
        draw.text((margin, 128), "Life Path Decoder · Shockingly Accurate", font=font_footer, fill=(100, 80, 150))
        y = 190
        while idx < len(lines) and y < H - 120:
            line = lines[idx]
            if line and not line.startswith("- ") and len(line) < 72 and idx + 1 < len(lines) and lines[idx + 1] != "":
                draw.text((margin, y), line, font=_load_font(30, True, full_text), fill=(70, 48, 130))
                y += 44
            else:
                draw.text((margin, y), line, font=font_body, fill=(30, 30, 45))
                y += line_h if line else 24
            idx += 1
        draw.text((margin, H - 70), f"Page {page_no} · Reflective/entertainment use only", font=font_footer, fill=(120, 120, 130))
        pages.append(img)
        page_no += 1
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()

def report_from_request(req: AnalyzeRequest, request: Request | None = None) -> dict[str, Any]:
    lat = req.latitude
    lon = req.longitude
    place = req.birth_place.strip() if req.birth_place else None
    if place and (lat is None or lon is None):
        resolved = geocode_place(place)
        lat = resolved.get("latitude")
        lon = resolved.get("longitude")
    report = build_report(
        req.name,
        req.date_of_birth,
        analysis_type=req.analysis_type,
        birth_place=place,
        latitude=lat,
        longitude=lon,
        birth_time=req.birth_time,
    )
    report = enhance_report(report, req, request)
    # Preserve only tile title/short; never send or store prompt wording in output.
    if "prompt" in report:
        report["prompt"] = {"title": report["prompt"]["title"], "short": report["prompt"].get("short", "")}
    return report


def public_share_html(token: str, row: sqlite3.Row) -> str:
    payload = json.loads(row["public_payload"])
    title = payload.get("title", APP_NAME)
    name = payload.get("name", "Shared Report")
    summary = payload.get("summary", "A shared reflective report from Life Path Decoder.")
    share_url = _share_url(token)
    og_image = f"{share_url}/og.png"
    sections_html = []
    for section in payload.get("sections", [])[:10]:
        sec_title = html.escape(str(section.get("title", "")))
        body = html.escape(str(section.get("body", "")))
        bullets = section.get("bullets", []) or []
        table = section.get("table", []) or []
        b_html = f"<p>{body}</p>" if body else ""
        if bullets:
            b_html += "<ul>" + "".join(f"<li>{html.escape(str(item))}</li>" for item in bullets[:8]) + "</ul>"
        if table:
            rows = []
            for row_data in table[:8]:
                rows.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row_data.values()) + "</tr>")
            b_html += "<table>" + "".join(rows) + "</table>"
        sections_html.append(f"<article><h2>{sec_title}</h2>{b_html}</article>")

    calc = payload.get("calculations", {})
    metrics = [
        ("Life Path", calc.get("life_path", "")),
        ("Archetype", calc.get("life_path_title", "")),
        ("Personal Year", calc.get("personal_year", "")),
        ("Name Expression", calc.get("name_expression", "")),
    ]
    metric_html = "".join(
        f"<div class='metric'><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>"
        for label, value in metrics
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(name)} — {html.escape(title)}</title>
  <meta name="description" content="{html.escape(summary)}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{html.escape(name)} — {html.escape(title)}" />
  <meta property="og:description" content="{html.escape(summary)}" />
  <meta property="og:url" content="{html.escape(share_url)}" />
  <meta property="og:image" content="{html.escape(og_image)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <style>
    :root {{ --bg:#08061f; --panel:rgba(255,255,255,.09); --text:#f7f5ff; --muted:#c5bddf; --accent:#d6b66c; --line:rgba(255,255,255,.16); }}
    * {{ box-sizing:border-box; }} body {{ margin:0; font-family:Inter,Arial,sans-serif; color:var(--text); background:radial-gradient(circle at top left, rgba(141,215,255,.18), transparent 34%),linear-gradient(145deg,#07051d,#10113e 52%,#08061f); }}
    main {{ width:min(980px, calc(100vw - 32px)); margin:0 auto; padding:36px 0; }}
    .hero, article {{ border:1px solid var(--line); border-radius:26px; background:var(--panel); padding:24px; box-shadow:0 20px 54px rgba(0,0,0,.28); }}
    .public-logo {{ display:block; width:min(420px,100%); height:auto; margin:0 0 22px; border-radius:22px; background:#fff; padding:10px 14px; box-shadow:0 18px 46px rgba(0,0,0,.28); }}
    h1 {{ font-size:clamp(2rem,5vw,4rem); line-height:.98; letter-spacing:-.05em; margin:.2rem 0 1rem; }}
    h2 {{ margin:0 0 12px; color:#fff; }} p, li, td {{ color:var(--muted); line-height:1.65; }} .eyebrow {{ color:var(--accent); text-transform:uppercase; font-weight:800; letter-spacing:.13em; font-size:.75rem; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:18px 0; }} .metric {{ border:1px solid var(--line); border-radius:18px; padding:14px; background:rgba(255,255,255,.06); }} .metric span {{ display:block; color:var(--muted); font-size:.8rem; }} .metric strong {{ display:block; margin-top:6px; color:var(--accent); }}
    article {{ margin-top:16px; }} a.button {{ display:inline-flex; margin-top:16px; padding:12px 14px; border-radius:999px; background:linear-gradient(135deg,var(--accent),#fff0b7); color:#17102d; text-decoration:none; font-weight:800; }} table {{ width:100%; border-collapse:collapse; }} td {{ border-top:1px solid var(--line); padding:10px; }} footer {{ color:var(--muted); margin-top:18px; font-size:.9rem; }}
    @media(max-width:760px) {{ .metrics {{ grid-template-columns:1fr 1fr; }} }}
  </style>
</head>
<body>
<main>
  <section class="hero">
    <img class="public-logo" src="/brand/logo" alt="Life Path Decoder logo" />
    <div class="eyebrow">Shared Life Path Decoder Result</div>
    <h1>{html.escape(name)} — {html.escape(title)}</h1>
    <p>{html.escape(summary)}</p>
    <div class="metrics">{metric_html}</div>
    <a class="button" href="{html.escape(_facebook_url(share_url))}" target="_blank" rel="noopener noreferrer">Share on Facebook</a>
  </section>
  {''.join(sections_html)}
  <footer>{html.escape(str(payload.get('disclaimer', 'Reflective/entertainment use only.')))}</footer>
</main>
</body>
</html>"""


def _load_font(size: int, bold: bool = False, sample_text: str = ""):
    if ImageFont is None:
        return None

    sample = sample_text or ""
    has_kannada = any("\u0C80" <= ch <= "\u0CFF" for ch in sample)
    has_devanagari = any("\u0900" <= ch <= "\u097F" for ch in sample)
    has_tamil = any("\u0B80" <= ch <= "\u0BFF" for ch in sample)

    script_candidates: list[str] = []
    if has_kannada:
        script_candidates.append("/usr/share/fonts/truetype/noto/NotoSansKannada-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansKannada-Regular.ttf")
    if has_devanagari:
        script_candidates.append("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf")
    if has_tamil:
        script_candidates.append("/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf")

    candidates = script_candidates + [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _text_size(draw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _line_height(draw, font) -> int:
    _, h = _text_size(draw, "Ag", font)
    return max(1, h)


def _wrap_lines(draw, text: str, font, max_width: int) -> list[str]:
    words = str(text or "").replace("\n", " ").split()
    if not words:
        return []
    lines: list[str] = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        width, _ = _text_size(draw, test, font)
        if width <= max_width:
            line = test
            continue
        if line:
            lines.append(line)
            line = word
        else:
            # Very long single word: keep it rather than crashing the layout.
            lines.append(word)
            line = ""
    if line:
        lines.append(line)
    return lines


def _truncate_lines(draw, lines: list[str], font, max_lines: int) -> list[str]:
    if max_lines <= 0 or len(lines) <= max_lines:
        return lines
    out = lines[:max_lines]
    if out:
        last = out[-1].rstrip(".,;: ")
        while last and _text_size(draw, last + "…", font)[0] > _text_size(draw, out[-1], font)[0]:
            last = last[:-1].rstrip()
        out[-1] = (last or out[-1][: max(1, len(out[-1]) - 1)]).rstrip(".,;: ") + "…"
    return out


def _fit_text_block(
    draw,
    text: str,
    box: tuple[int, int, int, int],
    start_size: int,
    min_size: int,
    bold: bool = False,
    max_lines: int | None = None,
) -> tuple[Any, list[str], int]:
    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    for size in range(start_size, min_size - 1, -2):
        font = _load_font(size, bold)
        line_spacing = max(10, int(size * 0.28))
        lines = _wrap_lines(draw, text, font, width)
        if max_lines and len(lines) > max_lines:
            continue
        line_h = _line_height(draw, font)
        required = len(lines) * line_h + max(0, len(lines) - 1) * line_spacing
        if required <= height:
            return font, lines, line_spacing

    font = _load_font(min_size, bold)
    line_spacing = max(9, int(min_size * 0.25))
    lines = _wrap_lines(draw, text, font, width)
    line_h = _line_height(draw, font)
    allowed_lines_by_height = max(1, (height + line_spacing) // (line_h + line_spacing))
    allowed = min(max_lines or allowed_lines_by_height, allowed_lines_by_height)
    return font, _truncate_lines(draw, lines, font, allowed), line_spacing


def _draw_lines(
    draw,
    lines: list[str],
    box: tuple[int, int, int, int],
    font,
    fill,
    line_spacing: int,
    align: str = "left",
    valign: str = "top",
) -> int:
    x1, y1, x2, y2 = box
    line_h = _line_height(draw, font)
    total_h = len(lines) * line_h + max(0, len(lines) - 1) * line_spacing
    if valign == "center":
        y = y1 + max(0, (y2 - y1 - total_h) // 2)
    elif valign == "bottom":
        y = y2 - total_h
    else:
        y = y1
    for line in lines:
        width, _ = _text_size(draw, line, font)
        if align == "center":
            x = x1 + max(0, (x2 - x1 - width) // 2)
        elif align == "right":
            x = x2 - width
        else:
            x = x1
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h + line_spacing
    return y


def _draw_fit_text(
    draw,
    text: str,
    box: tuple[int, int, int, int],
    start_size: int,
    min_size: int,
    fill,
    bold: bool = False,
    align: str = "left",
    valign: str = "top",
    max_lines: int | None = None,
) -> int:
    font, lines, spacing = _fit_text_block(draw, text, box, start_size, min_size, bold=bold, max_lines=max_lines)
    return _draw_lines(draw, lines, box, font, fill, spacing, align=align, valign=valign)


def _gradient_image(width: int, height: int) -> "Image.Image":
    image = Image.new("RGB", (width, height), (28, 12, 78))
    px = image.load()
    for y in range(height):
        for x in range(width):
            xf = x / max(1, width - 1)
            yf = y / max(1, height - 1)
            r = int(28 + 80 * xf + 36 * (1 - yf))
            g = int(12 + 34 * yf + 18 * (1 - xf))
            b = int(78 + 120 * yf + 35 * xf)
            px[x, y] = (min(255, r), min(255, g), min(255, b))
    return image


def _draw_card_frame(draw, w: int, h: int) -> tuple[int, int, int, int]:
    panel = (26, 17, 72)
    margin = 48 if h >= 1000 else 34
    draw.rounded_rectangle(
        (margin, margin, w - margin, h - margin),
        radius=54 if h >= 1000 else 34,
        fill=panel,
        outline=(255, 199, 74),
        width=4,
    )
    accent = (255, 199, 74)
    draw.rounded_rectangle((margin + 1, margin + 1, margin + 14, h - margin - 1), radius=7, fill=accent)
    draw.rounded_rectangle((w - margin - 14, margin + 1, w - margin - 1, h - margin - 1), radius=7, fill=(105, 233, 255))
    return (margin, margin, w - margin, h - margin)


def _card_png(payload: dict[str, Any], index: int, title: str, body: str, footer: str, size=(1080, 1350)) -> bytes:
    if Image is None or ImageDraw is None:
        raise HTTPException(status_code=500, detail="Pillow is required to generate image cards. Run pip install -r requirements.txt.")
    w, h = size
    img = _gradient_image(w, h)
    draw = ImageDraw.Draw(img)
    accent = (255, 199, 74)
    text = (255, 252, 255)
    muted = (236, 240, 255)
    soft = (169, 233, 255)
    line = (153, 114, 255)
    x0, y0, x3, y3 = _draw_card_frame(draw, w, h)

    if h < 900:
        # Landscape Open Graph image layout.
        pad = 56
        x1, x2 = x0 + pad, x3 - pad
        draw.text((x1, y0 + 38), "LIFE PATH DECODER", font=_load_font(28, True), fill=accent)
        card_label = f"CARD {index}"
        label_w, _ = _text_size(draw, card_label, _load_font(24, True))
        draw.text((x2 - label_w, y0 + 40), card_label, font=_load_font(24, True), fill=soft)
        _draw_fit_text(draw, str(payload.get("name", "Shared Report"))[:46], (x1, y0 + 86, x2, y0 + 128), 36, 30, text, bold=True, max_lines=1)
        _draw_fit_text(draw, title, (x1, y0 + 145, x2, y0 + 260), 58, 42, text, bold=True, align="left", max_lines=2)
        draw.line((x1, y0 + 285, x2, y0 + 285), fill=line, width=2)
        _draw_fit_text(draw, body, (x1, y0 + 315, x2, y3 - 88), 34, 27, muted, max_lines=5)
        _draw_fit_text(draw, footer, (x1, y3 - 66, x2, y3 - 28), 24, 21, accent, align="center", valign="center", max_lines=1)
    else:
        # Instagram 4:5 layout with large, readable safe zones.
        pad = 74
        x1, x2 = x0 + pad, x3 - pad
        y = y0 + 58
        draw.text((x1, y), "LIFE PATH DECODER", font=_load_font(36, True), fill=accent)
        card_label = f"CARD {index}/6"
        label_font = _load_font(30, True)
        label_w, _ = _text_size(draw, card_label, label_font)
        draw.text((x2 - label_w, y + 3), card_label, font=label_font, fill=soft)

        y += 68
        _draw_fit_text(draw, str(payload.get("name", "Shared Report"))[:46], (x1, y, x2, y + 70), 58, 46, text, bold=True, align="center", valign="center", max_lines=1)

        title_box = (x1, y0 + 245, x2, y0 + 505)
        _draw_fit_text(draw, title, title_box, 82, 60, text, bold=True, align="center", valign="center", max_lines=3)

        draw.line((x1, y0 + 548, x2, y0 + 548), fill=line, width=3)

        body_box = (x1, y0 + 590, x2, y3 - 190)
        # Body starts large and auto-fits down only when the section is lengthy.
        _draw_fit_text(draw, body, body_box, 56, 42, muted, bold=True, align="left", valign="top", max_lines=9)

        draw.line((x1, y3 - 155, x2, y3 - 155), fill=line, width=2)
        footer_box = (x1, y3 - 128, x2, y3 - 62)
        _draw_fit_text(draw, footer, footer_box, 40, 32, accent, bold=True, align="center", valign="center", max_lines=2)

        # Small bottom page indicator dots, centered and aligned.
        dots = 6
        dot_gap = 20
        dot_r = 5
        total_w = dots * dot_r * 2 + (dots - 1) * dot_gap
        start_x = (w - total_w) // 2
        dot_y = y3 - 30
        for i in range(dots):
            fill = accent if i + 1 == index else (93, 87, 135)
            cx = start_x + i * (dot_r * 2 + dot_gap)
            draw.ellipse((cx, dot_y, cx + dot_r * 2, dot_y + dot_r * 2), fill=fill)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

def _og_png(payload: dict[str, Any]) -> bytes:
    calc = payload.get("calculations", {})
    body = f"Life Path {calc.get('life_path', '')} — {calc.get('life_path_title', '')}. {payload.get('summary', '')}"
    return _card_png(payload, 1, str(payload.get("title", APP_NAME)), body, "Shared result · Life Path Decoder", size=(1200, 630))


def _instagram_zip(payload: dict[str, Any]) -> bytes:
    calc = payload.get("calculations", {})
    sections = payload.get("sections", []) or []
    strengths = next((s for s in sections if "Strength" in s.get("title", "") or "Talent" in s.get("title", "")), {})
    weaknesses = next((s for s in sections if "Weak" in s.get("title", "") or "Warning" in s.get("title", "") or "Blocking" in s.get("title", "")), {})
    purpose = next((s for s in sections if "Purpose" in s.get("title", "") or "Mission" in s.get("title", "")), {})
    roadmap = next((s for s in sections if "Roadmap" in s.get("title", "") or "Timeline" in s.get("title", "") or "Destiny" in s.get("title", "")), {})

    def bullet_text(section: dict[str, Any], fallback: str) -> str:
        if section.get("body"):
            return str(section["body"])
        bullets = section.get("bullets") or []
        if bullets:
            return " • ".join(str(b) for b in bullets[:4])
        table = section.get("table") or []
        if table:
            return " • ".join(" | ".join(str(v) for v in row.values()) for row in table[:3])
        return fallback

    cards = [
        (
            "Your Life Path Snapshot",
            f"Life Path {calc.get('life_path', '')}: {calc.get('life_path_title', '')}. Personal Year {calc.get('personal_year', '')}: {calc.get('personal_year_theme', '')}.",
            "Swipe for strengths, watchouts and purpose.",
        ),
        (
            "Core Numbers",
            f"Birth Day {calc.get('birth_day', '')}. Name Expression {calc.get('name_expression', '')}. Soul Urge {calc.get('soul_urge', '')}. Personality {calc.get('personality', '')}.",
            "Numbers are reflective cues, not fixed destiny.",
        ),
        (
            str(strengths.get("title", "Hidden Strengths")),
            bullet_text(strengths, "Your strengths are best seen when discipline turns personality into value."),
            "Use strengths deliberately, not accidentally.",
        ),
        (
            str(weaknesses.get("title", "Watchouts")),
            bullet_text(weaknesses, "The main risk is overusing your strongest trait until it becomes a blind spot."),
            "The shadow becomes power when it is named.",
        ),
        (
            str(purpose.get("title", "Purpose Direction")),
            bullet_text(purpose, "Your purpose is to turn your core pattern into useful contribution."),
            "Purpose becomes real when it becomes weekly action.",
        ),
        (
            str(roadmap.get("title", "Next Step")),
            bullet_text(roadmap, "Choose one practical next step that converts insight into action."),
            "Generated by Life Path Decoder.",
        ),
    ]

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, (title, body, footer) in enumerate(cards, start=1):
            zf.writestr(f"instagram-carousel-card-{idx:02d}.png", _card_png(payload, idx, title, body, footer))
        zf.writestr("caption.txt", _instagram_caption(payload))
    return zip_buf.getvalue()


def _instagram_caption(payload: dict[str, Any]) -> str:
    calc = payload.get("calculations", {})
    return textwrap.dedent(
        f"""
        {payload.get('name', 'My')} Life Path Decoder snapshot

        Life Path {calc.get('life_path', '')} — {calc.get('life_path_title', '')}
        Personal Year {calc.get('personal_year', '')} — {calc.get('personal_year_theme', '')}

        Reflective/entertainment use only. Not scientific, medical, psychological, legal or financial advice.

        #LifePath #Reflection #PersonalGrowth #Numerology #SelfDiscovery
        """
    ).strip()


@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "auth": "local_session",
        "secure_cookies": SECURE_COOKIES,
        "public_share_enabled": True,
        "app_base_url": APP_BASE_URL,
        "data_dir": str(DATA_DIR),
        "database_path": str(DB_PATH),
        "railway_public_domain": RAILWAY_PUBLIC_DOMAIN or None,
    }


@app.get("/brand/logo")
def brand_logo():
    logo_path = active_logo_path()
    if not logo_path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(logo_path, media_type="image/png", headers={"Cache-Control": "no-cache, max-age=0"})


@app.get("/api/me")
def me(request: Request):
    user = ensure_local_session(request)
    return {
        "authenticated": True,
        "auth_mode": "local_session",
        "csrf_token": request.session.get("csrf_token"),
        "version": APP_VERSION,
        "app_base_url": APP_BASE_URL,
        "secure_cookies": SECURE_COOKIES,
        "session_idle_seconds": SESSION_IDLE_SECONDS,
        "user": user,
    }


@app.get("/api/prompts")
def prompts(user: dict[str, Any] = Depends(current_user)):
    public_prompts = {
        key: {"title": value["title"], "short": value["short"]}
        for key, value in PROMPT_OPTIONS.items()
    }
    return {"version": APP_VERSION, "prompts": public_prompts}




@app.get("/api/public-config")
def public_config(user: dict[str, Any] = Depends(current_user)):
    config = load_app_config()
    features = config.get("features", {}) if isinstance(config.get("features"), dict) else {}
    return {
        "version": APP_VERSION,
        "brand_tagline": config.get("brand_tagline", "Shockingly Accurate"),
        "brand_logo": config.get("brand_logo", {"url": "/brand/logo", "source": "default"}),
        "features": {
            "demo_data_button": bool(features.get("demo_data_button", False)),
        },
    }


@app.post("/api/geocode")
def geocode(req: GeocodeRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "geocode", max_calls=60, per_seconds=60)
    try:
        return geocode_place(req.birth_place)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "analyze", max_calls=15, per_seconds=60)
    try:
        report = report_from_request(req, request)
        report_id = save_report_history(int(user.get("id", 0)), req, report)
        report["report_id"] = report_id
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/share")
def share(req: ShareRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "share", max_calls=8, per_seconds=60)
    if not req.allow_public_share:
        raise HTTPException(status_code=400, detail="Public share permission was not provided.")
    try:
        report = report_from_request(req, request)
        share_data = create_shared_report(int(user.get("id", 0)), report)
        return {
            "ok": True,
            **share_data,
            "note": "Anyone with this link can view the shared report until it expires or is revoked.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/my-shares")
def my_shares(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, share_summary, created_at, expires_at, revoked_at
            FROM shared_reports WHERE user_id = ? ORDER BY id DESC LIMIT 25
            """,
            (int(user.get("id", 0)),),
        ).fetchall()
    return {"shares": [dict(row) for row in rows]}



@app.post("/api/report.pdf")
def report_pdf(req: AnalyzeRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "report_pdf", max_calls=8, per_seconds=60)
    try:
        report = report_from_request(req, request)
        pdf = report_pdf_bytes(report)
        safe_name = re.sub(r"[^a-z0-9]+", "-", report.get("input", {}).get("name", "life-path").lower()).strip("-") or "life-path"
        return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={safe_name}-life-path-report.pdf"})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/reports")
def report_history(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, analysis_type, created_at FROM report_history WHERE user_id = ? ORDER BY id DESC LIMIT 50",
            (int(user.get("id", 0)),),
        ).fetchall()
    return {"reports": [dict(row) for row in rows]}


@app.get("/api/reports/{report_id}")
def read_report(report_id: int, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    with get_db() as conn:
        row = conn.execute("SELECT report_payload FROM report_history WHERE id = ? AND user_id = ?", (report_id, int(user.get("id", 0)))).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return json.loads(row["report_payload"])


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: int, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM report_history WHERE id = ? AND user_id = ?", (report_id, int(user.get("id", 0))))
        conn.commit()
    return {"ok": True, "deleted": cur.rowcount}


@app.delete("/api/reports")
def clear_reports(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    with get_db() as conn:
        cur = conn.execute("DELETE FROM report_history WHERE user_id = ?", (int(user.get("id", 0)),))
        conn.commit()
    return {"ok": True, "deleted": cur.rowcount}




DEMO_REPORT_REQUESTS: list[dict[str, Any]] = [
    {"name": "Aarav Sharma", "date_of_birth": "1988-07-13", "birth_time": "09:30", "birth_place": "Bengaluru, Karnataka, India", "latitude": 12.971599, "longitude": 77.594566, "analysis_type": "life_path", "report_length": "detailed", "tone": "balanced", "output_language": "english"},
    {"name": "Ananya Rao", "date_of_birth": "1990-02-21", "birth_time": "18:15", "birth_place": "Mysuru, Karnataka, India", "latitude": 12.295810, "longitude": 76.639381, "analysis_type": "relationships", "report_length": "medium", "tone": "positive", "output_language": "english"},
    {"name": "Raghavendra Iyer", "date_of_birth": "1975-07-13", "birth_time": "06:45", "birth_place": "Chennai, Tamil Nadu, India", "latitude": 13.082680, "longitude": 80.270718, "analysis_type": "professional_destiny", "report_length": "detailed", "tone": "direct", "output_language": "english"},
    {"name": "Meera Krishnan", "date_of_birth": "1984-11-04", "birth_time": "21:05", "birth_place": "Kochi, Kerala, India", "latitude": 9.931233, "longitude": 76.267304, "analysis_type": "wealth_abundance", "report_length": "medium", "tone": "balanced", "output_language": "english"},
    {"name": "Vikram Gowda", "date_of_birth": "1995-05-17", "birth_time": "13:20", "birth_place": "Hubballi, Karnataka, India", "latitude": 15.364708, "longitude": 75.123955, "analysis_type": "future_timeline", "report_length": "short", "tone": "brutally_honest", "output_language": "english"},
    {"name": "Kavya Nair", "date_of_birth": "1992-09-29", "birth_time": "04:10", "birth_place": "Coimbatore, Tamil Nadu, India", "latitude": 11.016844, "longitude": 76.955833, "analysis_type": "name_suggestion", "report_length": "medium", "tone": "positive", "output_language": "english"},
]


@app.post("/api/demo-data")
def create_demo_data(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "demo_data", max_calls=20, per_seconds=300)
    init_db()
    config = load_app_config()
    features = config.get("features", {}) if isinstance(config.get("features"), dict) else {}
    if not bool(features.get("demo_data_button", False)):
        raise HTTPException(status_code=403, detail="Demo data creation is disabled by admin configuration.")
    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for sample in DEMO_REPORT_REQUESTS:
        try:
            sample_payload = dict(sample)
            sample_payload["no_storage"] = False
            req = AnalyzeRequest(**sample_payload)
            report = report_from_request(req, request)
            report_id = save_report_history(int(user.get("id", 0)), req, report)
            created.append({"id": report_id, "name": sample["name"], "analysis_type": sample["analysis_type"]})
        except Exception as exc:
            errors.append(f"{sample.get('name', 'Sample')}: {exc}")
    if errors and not created:
        raise HTTPException(status_code=500, detail="Demo data could not be created. " + "; ".join(errors[:3]))
    return {"ok": True, "message": f"Created {len(created)} demo report(s).", "created_count": len(created), "reports": created, "errors": errors}


@app.post("/api/admin/login")
def admin_login(payload: AdminLoginRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "admin_login", max_calls=8, per_seconds=300)
    supplied_id = " ".join(payload.admin_id.strip().split())
    supplied_password = payload.password.strip()
    if not (secrets.compare_digest(supplied_id, ADMIN_ID) and secrets.compare_digest(supplied_password, ADMIN_PASSWORD)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin ID or password.")
    request.session["admin_authenticated"] = True
    request.session["admin_id"] = ADMIN_ID
    return {"ok": True, "admin": ADMIN_ID}


@app.post("/api/admin/logout")
def admin_logout(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    request.session.pop("admin_authenticated", None)
    request.session.pop("admin_id", None)
    return {"ok": True}


@app.get("/api/admin/status")
def admin_status(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    return {"authenticated": bool(request.session.get("admin_authenticated")), "admin": request.session.get("admin_id") if request.session.get("admin_authenticated") else None}


@app.get("/api/analytics")
def analytics(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    require_admin(request)
    with get_db() as conn:
        total_reports = conn.execute("SELECT COUNT(*) c FROM report_history WHERE user_id = ?", (int(user.get("id", 0)),)).fetchone()["c"]
        total_shares = conn.execute("SELECT COUNT(*) c FROM shared_reports WHERE user_id = ? AND revoked_at IS NULL", (int(user.get("id", 0)),)).fetchone()["c"]
        by_type = conn.execute("SELECT analysis_type, COUNT(*) c FROM report_history WHERE user_id = ? GROUP BY analysis_type ORDER BY c DESC", (int(user.get("id", 0)),)).fetchall()
    return {"total_reports": total_reports, "total_shares": total_shares, "by_type": [dict(row) for row in by_type]}


@app.get("/api/config")
def get_config(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    require_admin(request)
    return load_app_config()


@app.post("/api/config")
def update_config(payload: dict[str, Any], request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    require_admin(request)
    return save_app_config(payload)


@app.post("/api/admin/logo")
def upload_admin_logo(payload: LogoUploadRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    require_admin(request)
    return save_uploaded_logo(payload.logo_data_url)


@app.delete("/api/admin/logo")
def delete_admin_logo(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    require_admin(request)
    return reset_uploaded_logo()


@app.post("/auth/logout")
def logout(request: Request, payload: LogoutRequest):
    require_csrf(request)
    request.session.clear()
    ensure_local_session(request)
    return {"ok": True}


@app.get("/s/{token}/instagram-story.zip")
def public_instagram_story_cards(token: str, request: Request):
    rate_limit(request, "instagram_story", max_calls=20, per_seconds=60)
    row = get_share_row(token)
    payload = json.loads(row["public_payload"])
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        calc = payload.get("calculations", {})
        cards = [
            ("Shockingly Accurate Snapshot", f"Life Path {calc.get('life_path')} · {calc.get('life_path_title')}\nNakshatra {calc.get('nakshatra', '-')}", "Life Path Decoder"),
            ("Love & Destiny Cue", f"Moon Rashi {calc.get('moon_rashi', '-')}\nPersonal Year {calc.get('personal_year', '-')}: {calc.get('personal_year_theme', '-')}", "Share your report"),
            ("Lucky Signals", f"Lucky Color {calc.get('lucky_color', '-')}\nLucky Fruit {calc.get('lucky_fruit', '-')}\nLucky Number {calc.get('lucky_number', '-')}", "Shockingly Accurate"),
        ]
        for idx, (title, body, footer) in enumerate(cards, start=1):
            zf.writestr(f"instagram-story-{idx:02d}.png", _card_png(payload, idx, title, body, footer, size=(1080, 1920)))
    return StreamingResponse(io.BytesIO(zip_buf.getvalue()), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=instagram-story-cards.zip"})


@app.get("/s/{token}/social-cards.zip")
def public_social_cards(token: str, request: Request):
    rate_limit(request, "social_cards", max_calls=20, per_seconds=60)
    row = get_share_row(token)
    payload = json.loads(row["public_payload"])
    calc = payload.get("calculations", {})
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("linkedin-professional-destiny.png", _card_png(payload, 1, "Professional Destiny", f"Life Path {calc.get('life_path')} · {calc.get('life_path_title')}\nName Expression {calc.get('name_expression')} · Personal Year {calc.get('personal_year')}", "LinkedIn-ready card", size=(1200, 627)))
        zf.writestr("shockingly-accurate-highlight.png", _card_png(payload, 2, "Shockingly Accurate Highlight", payload.get("summary", "Life Path Decoder report"), "Life Path Decoder", size=(1080, 1080)))
    return StreamingResponse(io.BytesIO(zip_buf.getvalue()), media_type="application/zip", headers={"Content-Disposition": "attachment; filename=social-card-bundle.zip"})


@app.get("/s/{token}", response_class=HTMLResponse)
def public_share_page(token: str, request: Request):
    rate_limit(request, "public_share_view", max_calls=120, per_seconds=60)
    row = get_share_row(token)
    return HTMLResponse(public_share_html(token, row))


@app.get("/s/{token}/og.png")
def public_share_og_image(token: str, request: Request):
    rate_limit(request, "public_og", max_calls=120, per_seconds=60)
    row = get_share_row(token)
    payload = json.loads(row["public_payload"])
    png = _og_png(payload)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/s/{token}/instagram-cards.zip")
def public_instagram_cards(token: str, request: Request):
    rate_limit(request, "instagram_zip", max_calls=30, per_seconds=60)
    row = get_share_row(token)
    payload = json.loads(row["public_payload"])
    data = _instagram_zip(payload)
    safe_name = re.sub(r"[^a-z0-9]+", "-", str(payload.get("name", "life-path")).lower()).strip("-") or "life-path"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={safe_name}-instagram-carousel.zip"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/s/") and not request.url.path.endswith((".png", ".zip")):
        return HTMLResponse(
            f"<h1>{html.escape(str(exc.detail))}</h1><p>The share link may have expired or been revoked.</p>",
            status_code=exc.status_code,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/admin")
def admin_page(request: Request):
    ensure_local_session(request)
    if not request.session.get("admin_authenticated"):
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{path:path}")
def spa_fallback(path: str):
    if path.startswith("api/") or path.startswith("auth/") or path.startswith("s/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(STATIC_DIR / "index.html")
