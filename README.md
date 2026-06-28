# SimplifyJobs Bay Area Watcher 🔔

Polls [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions) every hour and emails you whenever a **new Bay Area / CA job** appears.

---

## Setup (5 minutes)

### Step 1 — Create your own GitHub repo
1. Go to [github.com/new](https://github.com/new)
2. Name it `simplify-jobs-watcher` (private is fine)
3. Upload all files from this folder maintaining the structure:
   ```
   .github/workflows/bay_area_watcher.yml
   scripts/check_jobs.py
   README.md
   ```

### Step 2 — Get a Gmail App Password
> This lets the script send email via Gmail without using your real password.

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (required)
3. Search for **"App Passwords"** → Create one → Select app: **Mail**, device: **Other** → name it `github-jobs-watcher`
4. Copy the 16-character password shown (you won't see it again)

### Step 3 — Add GitHub Secrets
In your new repo: **Settings → Secrets and variables → Actions → New repository secret**

Add these 3 secrets:

| Secret name      | Value                                      |
|------------------|--------------------------------------------|
| `GMAIL_USER`     | your Gmail address e.g. `you@gmail.com`    |
| `GMAIL_APP_PASS` | the 16-char App Password from Step 2       |
| `NOTIFY_EMAIL`   | email to notify (can be same as GMAIL_USER)|

### Step 4 — Enable Actions & test it
1. Go to your repo → **Actions** tab → enable workflows if prompted
2. Click **🔔 SimplifyJobs Bay Area Watcher** → **Run workflow** → **Run workflow**
3. Watch the run — if it finds Bay Area jobs you'll get an email within ~30 seconds
4. After that it runs automatically every hour

---

## What triggers an email?

A job triggers an alert when **all** of these are true:
- It appears in the SimplifyJobs README job table
- Its **Location** column contains a Bay Area city OR matches `, CA` (excluding LA, San Diego, etc.)
- It's **new since the last check** (already-seen jobs never re-alert)

### Bay Area cities detected
San Francisco, San Jose, Palo Alto, Menlo Park, Mountain View, Sunnyvale,
Santa Clara, Redwood City, Oakland, Berkeley, Fremont, Cupertino,
South San Francisco, San Mateo, Foster City, Milpitas, Alameda, Hayward,
Emeryville, Burlingame, Belmont, Campbell, Los Altos, Los Gatos, and more.

---

## What the email looks like

You'll get an HTML email like:

> **🔔 3 new Bay Area role(s) — SimplifyJobs New Grad**
>
> | Company   | Role                  | Location            | Age | Apply  |
> |-----------|-----------------------|---------------------|-----|--------|
> | LangChain | AI Engineer           | San Francisco, CA   | 0d  | Apply ↗|
> | Together  | Backend SWE           | San Francisco, CA   | 1d  | Apply ↗|
> | Jobright  | AI Agent Engineer     | Cupertino, CA       | 0d  | Apply ↗|

---

## Customize

**Change schedule** — edit the cron in `bay_area_watcher.yml`:
```yaml
- cron: "0 * * * *"   # every hour
- cron: "0 */6 * * *" # every 6 hours
- cron: "0 9 * * *"   # once daily at 9am UTC
```

**Tighten Bay Area filter** — in `check_jobs.py`, remove the `, CA` fallback
and keep only `BAY_AREA_CITIES` matching for stricter filtering.

**Watch a different repo** — change `README_URL` in `check_jobs.py`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No email received | Check Actions logs for errors; verify secrets are set correctly |
| Gmail auth error | Make sure 2FA is on and you used an App Password, not your real password |
| Getting alerts for non-Bay-Area CA cities | Remove the `, CA` fallback block in `is_bay_area()` |
| Want to reset and re-alert on all current jobs | Delete the `seen-jobs-cache` cache in Actions → Caches |
