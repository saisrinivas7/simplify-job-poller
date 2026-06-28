"""
SimplifyJobs New Grad Positions - Bay Area CA Watcher
Fetches the README, parses job table rows, filters for CA/Bay Area locations,
compares against previously seen jobs, and emails any new ones.
"""

import os
import re
import json
import hashlib
import smtplib
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── Config (all from GitHub Actions secrets/env) ─────────────────────────────
README_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"
SEEN_FILE  = "seen_jobs.json"   # persisted as a GitHub Actions artifact

GMAIL_USER    = os.environ["GMAIL_USER"]      # your Gmail address
GMAIL_PASS    = os.environ["GMAIL_APP_PASS"]  # Gmail App Password (not your real password)
NOTIFY_EMAIL  = os.environ["NOTIFY_EMAIL"]    # where to send alerts (can be same as GMAIL_USER)

# Bay Area cities + any ", CA" match
BAY_AREA_CITIES = {
    "san francisco", "sf", "san jose", "palo alto", "menlo park",
    "mountain view", "sunnyvale", "santa clara", "redwood city",
    "oakland", "berkeley", "fremont", "cupertino", "south san francisco",
    "san mateo", "foster city", "milpitas", "alameda", "hayward",
    "emeryville", "burlingame", "belmont", "campbell", "los altos",
    "los gatos", "saratoga", "morgan hill", "pleasanton", "livermore",
    "walnut creek", "concord", "richmond", "san leandro", "daly city",
    "redwood shores",
}

def fetch_readme() -> str:
    with urllib.request.urlopen(README_URL, timeout=30) as r:
        return r.read().decode("utf-8")

def is_bay_area(location_text: str) -> bool:
    """Return True if location contains a Bay Area city or any ', CA' pattern."""
    loc = location_text.lower()
    # Any ", CA" is worth flagging (catches Irvine CA etc — you can tighten later)
    # For Bay Area specifically:
    if any(city in loc for city in BAY_AREA_CITIES):
        return True
    # Fallback: ", ca" in text (catches "San Francisco, CA" style)
    if re.search(r',\s*ca\b', loc):
        # exclude known non-Bay Area CA cities
        exclude = {"los angeles", "la,", "irvine", "san diego", "sacramento",
                   "fresno", "bakersfield", "anaheim", "riverside", "stockton",
                   "glendale", "san bernardino", "modesto", "santa barbara",
                   "pasadena", "long beach", "torrance", "orange", "pomona"}
        if not any(ex in loc for ex in exclude):
            return True
    return False

def parse_jobs(readme: str) -> list[dict]:
    """
    Parse all <tr> job rows from the README HTML table.
    Returns list of dicts: {company, role, location, apply_url, age}
    """
    jobs = []

    # Each job is a <tr>...</tr> block containing <td> cells
    # Structure: Company | Role | Location | Application | Age
    row_pattern = re.compile(r'<tr>(.*?)</tr>', re.DOTALL)
    td_pattern  = re.compile(r'<td>(.*?)</td>', re.DOTALL)
    # Company name from anchor
    company_pattern = re.compile(r'<strong><a[^>]*>([^<]+)</a></strong>')
    # Apply URL
    apply_pattern   = re.compile(r'href="(https://[^"]+)"[^>]*><img[^>]*alt="Apply"')
    # Age: e.g. "0d", "2d", "1w"
    age_pattern     = re.compile(r'<td>(\d+[dwm])</td>')

    for row_match in row_pattern.finditer(readme):
        row_html = row_match.group(1)
        tds = td_pattern.findall(row_html)
        if len(tds) < 3:
            continue

        company_html  = tds[0] if len(tds) > 0 else ""
        role_html     = tds[1] if len(tds) > 1 else ""
        location_html = tds[2] if len(tds) > 2 else ""
        apply_html    = tds[3] if len(tds) > 3 else ""
        age_html      = tds[4] if len(tds) > 4 else ""

        # Clean location text (strip HTML tags)
        location_text = re.sub(r'<[^>]+>', ' ', location_html)
        location_text = re.sub(r'\s+', ' ', location_text).strip()

        if not location_text or not is_bay_area(location_text):
            continue

        company_m = company_pattern.search(company_html)
        company   = company_m.group(1).strip() if company_m else re.sub(r'<[^>]+>', '', company_html).strip()

        role = re.sub(r'<[^>]+>', '', role_html).strip()

        apply_m   = apply_pattern.search(apply_html)
        apply_url = apply_m.group(1) if apply_m else ""

        age_m = age_pattern.search(f"<td>{age_html}</td>")
        age   = age_m.group(1) if age_m else "?"

        if not company or not role:
            continue

        job_id = hashlib.md5(f"{company}|{role}|{location_text}".encode()).hexdigest()

        jobs.append({
            "id":       job_id,
            "company":  company,
            "role":     role,
            "location": location_text,
            "url":      apply_url,
            "age":      age,
        })

    return jobs

def load_seen() -> set[str]:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set[str]):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def build_email_html(new_jobs: list[dict]) -> str:
    rows = ""
    for j in new_jobs:
        apply_btn = (
            f'<a href="{j["url"]}" style="background:#0A66C2;color:white;padding:4px 12px;'
            f'border-radius:4px;text-decoration:none;font-size:12px;">Apply ↗</a>'
            if j["url"] else "—"
        )
        rows += f"""
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:10px 8px;font-weight:600;">{j['company']}</td>
          <td style="padding:10px 8px;">{j['role']}</td>
          <td style="padding:10px 8px;color:#555;">{j['location']}</td>
          <td style="padding:10px 8px;color:#888;">{j['age']}</td>
          <td style="padding:10px 8px;">{apply_btn}</td>
        </tr>"""

    return f"""
    <html><body style="font-family:sans-serif;max-width:800px;margin:auto;padding:20px;">
      <h2 style="color:#1a1a1a;">🔔 {len(new_jobs)} new Bay Area job(s) on SimplifyJobs</h2>
      <p style="color:#555;">Detected at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} —
         <a href="https://github.com/SimplifyJobs/New-Grad-Positions">View full list</a></p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f5f5f5;text-align:left;">
            <th style="padding:10px 8px;">Company</th>
            <th style="padding:10px 8px;">Role</th>
            <th style="padding:10px 8px;">Location</th>
            <th style="padding:10px 8px;">Age</th>
            <th style="padding:10px 8px;">Apply</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="margin-top:20px;font-size:12px;color:#aaa;">
        Sent by your SimplifyJobs Bay Area watcher · 
        <a href="https://github.com/SimplifyJobs/New-Grad-Positions">SimplifyJobs repo</a>
      </p>
    </body></html>"""

def send_email(new_jobs: list[dict]):
    subject = f"🔔 {len(new_jobs)} new Bay Area role(s) — SimplifyJobs New Grad"
    html    = build_email_html(new_jobs)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())

    print(f"✅ Email sent: {subject}")

def main():
    print(f"⏱  Fetching README at {datetime.utcnow().isoformat()}Z ...")
    readme   = fetch_readme()
    all_jobs = parse_jobs(readme)
    print(f"📋 Found {len(all_jobs)} Bay Area job(s) in README")

    seen     = load_seen()
    new_jobs = [j for j in all_jobs if j["id"] not in seen]
    print(f"🆕 {len(new_jobs)} new job(s) since last check")

    if new_jobs:
        send_email(new_jobs)
        seen.update(j["id"] for j in new_jobs)
        save_seen(seen)
    else:
        print("😴 No new Bay Area jobs — no email sent")

    # Always save current full set so closed jobs don't re-alert
    seen.update(j["id"] for j in all_jobs)
    save_seen(seen)

if __name__ == "__main__":
    main()
