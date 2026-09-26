# Step-by-Step: Free AI Trends Automation on your repo
Repo: https://github.com/pankajigec26/mordenized_card_management

Everything below can be done from a browser (tablet included). No cost:
Gemini free tier + Tavily free tier + your own WordPress + GitHub Actions.

---

## Part A — Get your two free API keys

### A1. Gemini API key (free)
1. Go to **aistudio.google.com**, sign in with your Google account.
2. Click **Get API key** (left sidebar) → **Create API key**.
3. Copy the key somewhere safe — you'll paste it into GitHub in Part C.
4. Note: on the free tier, Google's terms say your prompts/outputs may be
   used to improve their products. Fine for public news content like this —
   just worth knowing.

### A2. Tavily API key (free)
1. Go to **tavily.com** → **Sign Up** (free plan, no card needed at signup).
2. Once logged in, your dashboard shows an **API Key** — copy it.
3. Free plan includes ~1,000 search credits/month. This pipeline uses about
   15 searches per day (~450/month) — comfortably inside that.

---

## Part B — Add the files to your repo

1. Go to **github.com/pankajigec26/mordenized_card_management**.
2. Click **Add file → Create new file** (top right of the file list).
3. In the "Name your file" box, type exactly:
   `ai-trends-automation/pipeline.py`
   (typing the `/` auto-creates the `ai-trends-automation` folder).
4. Paste in the contents of `pipeline.py` (provided below) into the editor.
5. Scroll down → **Commit changes** (commit directly to `main` is fine).
6. Repeat steps 2-5 for:
   - `ai-trends-automation/requirements.txt`
   - `ai-trends-automation/.gitignore`
   - `.github/workflows/daily.yml` ← note this one is **not** inside the
     `ai-trends-automation` folder — GitHub Actions only reads workflow
     files from `.github/workflows/` at the repo root.

---

## Part C — Add your keys as encrypted Secrets

1. In the repo, go to **Settings** tab → **Secrets and variables** (left
   sidebar) → **Actions**.
2. Click **New repository secret** for each row below (name must match
   exactly):

| Secret name | Value |
|---|---|
| `GEMINI_API_KEY` | the key from Part A1 |
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `TAVILY_API_KEY` | the key from Part A2 |
| `WP_URL` | `https://easyaiml.com` |
| `WP_USER` | your WordPress username |
| `WP_APP_PASSWORD` | see Part D below |
| `WP_STATUS` | `draft` |
| `BUFFER_API_KEY` | optional — leave out if you don't have Buffer set up yet |
| `BUFFER_LINKEDIN_CHANNEL_ID` | optional — leave out for now |

---

## Part D — Get your WordPress Application Password

1. Log into your **easyaiml.com** wp-admin.
2. **Users → Profile** (your own profile page).
3. Scroll to **Application Passwords** → type a name like `ai-trends-bot` →
   **Add New Application Password**.
4. WordPress shows the password once, with spaces in it (e.g.
   `abcd 1234 efgh 5678`) — copy it exactly as shown into the
   `WP_APP_PASSWORD` secret in Part C. This is not your login password.

---

## Part E — Run it

1. In the repo, go to the **Actions** tab.
2. Click **Daily AI Trends Pipeline** on the left.
3. Click **Run workflow** (dropdown, top right) → **Run workflow** to confirm.
4. Wait a minute or two, then click into the run to watch it live.
5. Check:
   - **wp-admin → Posts** — a new draft titled "AI Trends Digest — [date]"
     should appear.
   - The run's **Artifacts** section (bottom of the run page) — download the
     zip for `pipeline.log`, and `linkedin_post_pending.txt` if Buffer wasn't
     configured (that file has your ready-to-paste LinkedIn post).

Once a manual run looks right, you're done — `daily.yml` fires automatically
every day at 01:30 UTC (07:00 IST). Change the two cron numbers in that file
whenever you want a different time.

---

## What's different from the paid version
- Report writing uses **Gemini 2.5 Flash (free)** instead of Claude.
- Web search uses **Tavily (free)** with a fixed set of search queries per
  beat (editable at the top of `pipeline.py` under `SEARCH_QUERIES`), instead
  of a model deciding searches dynamically. Quality will be a bit less sharp
  than the paid Claude+web-search version — worth spot-checking the first
  week of drafts and tuning the query lists if a beat feels thin.
- Everything else (WordPress publishing, Buffer/LinkedIn, GitHub Actions
  schedule) works identically.
