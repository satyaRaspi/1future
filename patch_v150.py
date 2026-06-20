from pathlib import Path
p=Path('/mnt/data/work150/app/main.py')
s=p.read_text()
s=s.replace('APP_VERSION = "1.4.7"','APP_VERSION = "1.5.0"')
# Add fields to AnalyzeRequest
old='''class AnalyzeRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    date_of_birth: str = Field(..., min_length=6, max_length=20, description="YYYY-MM-DD or DD-MM-YYYY")
    birth_time: Optional[str] = Field(default=None, max_length=8, description="HH:MM 24-hour format")
    birth_place: Optional[str] = Field(default=None, max_length=180)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    analysis_type: str = Field(default="life_path", max_length=40)
'''
new='''class AnalyzeRequest(BaseModel):
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
    partner_name: Optional[str] = Field(default=None, max_length=120)
    partner_date_of_birth: Optional[str] = Field(default=None, max_length=20)
    partner_birth_time: Optional[str] = Field(default=None, max_length=8)
    partner_birth_place: Optional[str] = Field(default=None, max_length=180)
'''
s=s.replace(old,new)
# Add field validators after clean_name maybe
marker='''    @field_validator("birth_place")
    @classmethod
    def clean_optional_place(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        return _clean_text(value, "Birth place")
'''
addition='''    @field_validator("partner_name")
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
'''
s=s.replace(marker, addition)
# Duplicate birth_place validator marker removed, we inserted with same name but okay.
marker='''    @field_validator("date_of_birth")
    @classmethod
    def clean_dob(cls, value: str) -> str:
        value = _clean_text(value, "Date of birth")
        if not re.match(r"^[0-9./-]+$", value):
            raise ValueError("Date of birth can contain only numbers and date separators.")
        return value
'''
addition='''    @field_validator("date_of_birth")
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
'''
s=s.replace(marker, addition)
marker='''    @field_validator("birth_time")
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
'''
addition='''    @field_validator("birth_time", "partner_birth_time")
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
'''
s=s.replace(marker, addition)
# init db add history/config
old='''        conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_reports_user_id ON shared_reports(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_reports_token_hash ON shared_reports(token_hash)")
        conn.commit()
'''
new='''        conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_reports_user_id ON shared_reports(user_id)")
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
'''
s=s.replace(old,new)
# shared report return urls
old='''        "facebook_share_url": _facebook_url(url),
        "instagram_cards_url": f"{url}/instagram-cards.zip",
        "og_image_url": f"{url}/og.png",
        "expires_at": expires,
'''
new='''        "facebook_share_url": _facebook_url(url),
        "whatsapp_share_url": f"https://wa.me/?text={quote_plus('My Life Path Decoder report: ' + url)}",
        "instagram_cards_url": f"{url}/instagram-cards.zip",
        "instagram_story_url": f"{url}/instagram-story.zip",
        "social_cards_url": f"{url}/social-cards.zip",
        "og_image_url": f"{url}/og.png",
        "expires_at": expires,
'''
s=s.replace(old,new)
# insert helper functions before report_from_request
insert_before='''def report_from_request(req: AnalyzeRequest) -> dict[str, Any]:
'''
helper=r'''
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


def enhance_report(report: dict[str, Any], req: AnalyzeRequest) -> dict[str, Any]:
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

    if req.output_language != "english":
        sections.insert(1, _section(
            f"{req.output_language.title()} Output Note",
            "This build stores the selected language preference and labels the report for that language. Full native-language rendering can be connected to a translation layer in the next production release.",
            bullets=["The current report remains in English for accuracy and consistency.", "Language preference is carried in the report payload for future translation/export."],
        ))

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

    sections.append(_section(
        "Name Spelling & Lucky Name Suggestions",
        "Small spelling changes can be explored for branding, public identity or numerology-style preference, but legal names and established personal identity should not be changed casually.",
        bullets=_name_spelling_suggestions(str(input_data.get("name", ""))) + [
            "For business names, prefer clarity, recall and trust before numerology.",
            f"Current Name Expression: {calc.get('name_expression')}.",
        ],
    ))
    sections.append(_section(
        "Premium Unlock Preview",
        "This report is structured for a freemium/premium model.",
        bullets=[
            "Free: summary, core numbers and one-page share card.",
            "Premium: full destiny report, PDF, compatibility, timing windows, and social card bundle.",
            "Payment gateway placeholder: Razorpay can be connected using RAZORPAY_KEY_ID and backend order creation in production.",
        ],
    ))

    # Trim optional sections for shorter report lengths while keeping critical items.
    if req.report_length == "short":
        sections = sections[:8]
    elif req.report_length == "medium":
        sections = sections[:14]

    report["report"]["sections"] = sections
    report["input"].update({
        "report_length": req.report_length,
        "tone": req.tone,
        "output_language": req.output_language,
        "brutal_mode": req.brutal_mode,
        "no_storage": req.no_storage,
        "partner_name": req.partner_name,
        "partner_date_of_birth": req.partner_date_of_birth,
    })
    # Rebuild full text from sections so copy, TXT, PDF and share all include the upgrades.
    lines = [report["report"].get("title", APP_NAME), "", f"Name: {input_data.get('name')}", f"Date of Birth: {input_data.get('dob')}", ""]
    for sec in sections:
        lines.append(str(sec.get("title", "")))
        if sec.get("body"):
            lines.append(str(sec.get("body")))
        for b in sec.get("bullets", []) or []:
            lines.append(f"- {b}")
        for row in sec.get("table", []) or []:
            lines.append("- " + " | ".join(str(v) for v in row.values()))
        lines.append("")
    lines.append("Disclaimer: Reflective/entertainment use only. Not scientific, medical, psychological, legal or financial advice.")
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
        "pricing": {"free": "Summary", "premium": "₹99 Full Report", "compatibility": "₹149 Couple Report"},
        "features": {"pdf": True, "whatsapp": True, "history": True, "compatibility": True, "story_cards": True},
        "privacy": {"share_expiry_days": SHARE_EXPIRY_DAYS, "no_storage_available": True},
    }


def load_app_config() -> dict[str, Any]:
    config = _default_config()
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM app_config").fetchall()
    for row in rows:
        try:
            config[row["key"]] = json.loads(row["value"])
        except Exception:
            config[row["key"]] = row["value"]
    return config


def save_app_config(payload: dict[str, Any]) -> dict[str, Any]:
    with get_db() as conn:
        for key, value in payload.items():
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value, updated_at) VALUES (?, ?, ?)",
                (str(key), json.dumps(value, ensure_ascii=False), _now_iso()),
            )
        conn.commit()
    return load_app_config()


def report_pdf_bytes(report: dict[str, Any]) -> bytes:
    if Image is None or ImageDraw is None:
        raise HTTPException(status_code=500, detail="Pillow is required for PDF export.")
    full_text = report.get("report", {}).get("full_text", "") or "Life Path Decoder Report"
    title = f"{report.get('input', {}).get('name', 'Life Path')} Report"
    W, H = 1240, 1754
    margin = 90
    pages = []
    font_title = _load_font(46, True)
    font_body = _load_font(26, False)
    font_footer = _load_font(20, False)
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
                draw.text((margin, y), line, font=_load_font(30, True), fill=(70, 48, 130))
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

'''
s=s.replace(insert_before, helper+insert_before)
# modify report_from_request to call enhance
old='''    # Preserve only tile title/short; never send or store prompt wording in output.
    if "prompt" in report:
        report["prompt"] = {"title": report["prompt"]["title"], "short": report["prompt"].get("short", "")}
    return report
'''
new='''    report = enhance_report(report, req)
    # Preserve only tile title/short; never send or store prompt wording in output.
    if "prompt" in report:
        report["prompt"] = {"title": report["prompt"]["title"], "short": report["prompt"].get("short", "")}
    return report
'''
s=s.replace(old,new)
# analyze route save history
old='''    try:
        return report_from_request(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
'''
# only replace first occurrence after api/analyze maybe multiple; use count 1 after marker
marker='''@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "analyze", max_calls=15, per_seconds=60)
    try:
        return report_from_request(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
'''
new_marker='''@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "analyze", max_calls=15, per_seconds=60)
    try:
        report = report_from_request(req)
        report_id = save_report_history(int(user.get("id", 0)), req, report)
        report["report_id"] = report_id
        return report
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
'''
s=s.replace(marker,new_marker)
# Add endpoints before auth/logout
insert_before='''@app.post("/auth/logout")
'''
endpoints=r'''
@app.post("/api/report.pdf")
def report_pdf(req: AnalyzeRequest, request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    rate_limit(request, "report_pdf", max_calls=8, per_seconds=60)
    try:
        report = report_from_request(req)
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


@app.get("/api/analytics")
def analytics(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    with get_db() as conn:
        total_reports = conn.execute("SELECT COUNT(*) c FROM report_history WHERE user_id = ?", (int(user.get("id", 0)),)).fetchone()["c"]
        total_shares = conn.execute("SELECT COUNT(*) c FROM shared_reports WHERE user_id = ? AND revoked_at IS NULL", (int(user.get("id", 0)),)).fetchone()["c"]
        by_type = conn.execute("SELECT analysis_type, COUNT(*) c FROM report_history WHERE user_id = ? GROUP BY analysis_type ORDER BY c DESC", (int(user.get("id", 0)),)).fetchall()
    return {"total_reports": total_reports, "total_shares": total_shares, "by_type": [dict(row) for row in by_type]}


@app.get("/api/config")
def get_config(request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    return load_app_config()


@app.post("/api/config")
def update_config(payload: dict[str, Any], request: Request, user: dict[str, Any] = Depends(current_user)):
    require_csrf(request)
    return save_app_config(payload)

'''
s=s.replace(insert_before, endpoints+insert_before)
# Add public social endpoints after instagram endpoint
insert_after='''@app.get("/s/{token}/instagram-cards.zip")
def public_instagram_cards(token: str, request: Request):
    rate_limit(request, "instagram", max_calls=20, per_seconds=60)
    row = get_share_row(token)
    payload = json.loads(row["public_payload"])
    zip_bytes = _instagram_zip(payload)
    safe_name = re.sub(r"[^a-z0-9]+", "-", payload.get("name", "life-path").lower()).strip("-") or "life-path"
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={safe_name}-instagram-carousel.zip"},
    )


'''
additional=r'''@app.get("/s/{token}/instagram-story.zip")
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


'''
s=s.replace(insert_after, insert_after+additional)
# Add /admin before root
insert_before='''@app.get("/")
def index():
'''
admin='''@app.get("/admin")
def admin_page():
    return FileResponse(STATIC_DIR / "admin.html")


'''
s=s.replace(insert_before, admin+insert_before)
p.write_text(s)
print('main patched')
