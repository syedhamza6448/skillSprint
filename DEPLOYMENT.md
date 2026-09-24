# SkillSprint AI — Deployment Guide
> Aptech TechWiz7 · Phase 11: Streamlit Community Cloud

---

## Prerequisites

| Item | Requirement |
|------|-------------|
| Python | 3.10 + |
| GitHub repo | Public **or** private (Streamlit Cloud supports both) |
| Streamlit Community Cloud account | Free at [share.streamlit.io](https://share.streamlit.io) |
| Gemini API Key | From [Google AI Studio](https://aistudio.google.com/app/apikey) |

---

## 1 — Verify the local state before pushing

Run these checks locally (you can skip the `git status` one after confirming):

```bash
# 1a. Confirm skillsprint.db is tracked (NOT gitignored)
git ls-files skillsprint.db
# Expected output:  skillsprint.db
# If blank, the db is still gitignored — fix .gitignore first.

# 1b. Confirm .env is NOT tracked
git ls-files .env
# Expected output:  (nothing)

# 1c. Confirm venv / .venv are NOT tracked
git ls-files venv/ .venv/
# Expected output:  (nothing)

# 1d. Quick sanity: verify requirements.txt is present
cat requirements.txt
```

---

## 2 — Push to GitHub

```bash
# From the repo root (d:\techwiz\SRS_GenerativeAI PowerPlay\skillSprint)

git add .gitignore requirements.txt .streamlit/config.toml DEPLOYMENT.md skillsprint.db
git status          # double-check nothing secret is staged

git commit -m "Phase 11: deployment prep + config"
git push origin main   # or master — whichever your default branch is
```

> [!CAUTION]
> Before running `git add .`, run `git status` first and make sure
> `.env` does **not** appear in the staged files list.
> If it does, the `.gitignore` change was not picked up — run
> `git rm --cached .env` and try again.

---

## 3 — Create the app on Streamlit Community Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in.
2. Click **"New app"**.
3. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **Repository** | `<your-github-username>/skillSprint` |
   | **Branch** | `main` (or `master`) |
   | **Main file path** | `app.py` |
   | **App URL** | Choose a custom slug (e.g. `skillsprint-ai`) |

4. Click **"Deploy"** — Streamlit Cloud will install `requirements.txt` automatically.

---

## 4 — Add the GEMINI_API_KEY secret

> [!IMPORTANT]
> The API key must **never** appear in source code or `requirements.txt`.
> It is injected at runtime through Streamlit's secrets mechanism.

In the Streamlit Cloud dashboard for your app:

1. Click **"⋮" (three dots) → Settings → Secrets**.
2. Paste the following (replace the placeholder):

   ```toml
   GEMINI_API_KEY = "your-real-api-key-here"
   ```

3. Click **Save** — the app restarts automatically.

The app reads the key via `os.environ.get("GEMINI_API_KEY")` (backed by
`python-dotenv` for local dev and Streamlit's secrets injection for cloud).
**Do not add any other file called `secrets.toml` to the repo** —
`.streamlit/secrets.toml` is already in `.gitignore`.

---

## 5 — Gotchas specific to this repo

### 5a — Database: skillsprint.db is committed intentionally

Streamlit Community Cloud gives a **fresh ephemeral container** on every deploy
and on every cold restart. There is no persistent filesystem.

`db.py → setup_db()` creates table schemas and reloads the
`requirement_matrix` from the CSV if the table is missing — **but it does
not re-process the 21 policy documents or re-chunk them**. That chunking
work was done locally and the results are stored in the `documents` and
`chunks` tables.

**Resolution:** `skillsprint.db` (≈ 350 KB, pre-populated) is committed
directly to the repo. The deployed app loads it from disk on startup with
all data already present. Evaluators can use the app immediately without
any manual setup step.

> [!NOTE]
> If you ever need to reset or re-populate the DB after a document change,
> run your existing admin upload flow locally, then commit the updated
> `skillsprint.db` and redeploy.

### 5b — Entrypoint file

The Streamlit Cloud "Main file path" must be set to **`app.py`** (repo root).
The multi-page navigation is handled by the `pages/` directory following
Streamlit's standard naming convention:

```
app.py                  ← entry point (set this in Streamlit Cloud)
pages/
  1_admin_upload.py
  2_employee_plan.py
  3_dashboard.py
```

### 5c — File upload size limit

Streamlit Community Cloud's default `maxUploadSize` is 200 MB.
The current `.streamlit/config.toml` does not override this, which is fine
for the expected policy document sizes. Add this to `config.toml` if needed:

```toml
[server]
maxUploadSize = 50   # MB
```

### 5d — Cold-start time

The first request after a deploy may take 30–60 seconds while the container
installs packages. Subsequent requests are fast. This is expected behaviour
on the free tier.

### 5e — No persistent write-back on cloud

Any comparison results, generation logs, or review decisions written to
`skillsprint.db` during a cloud session **will be lost on the next
deploy/restart** (ephemeral container). This is acceptable for an
evaluation/demo scenario. If you need persistence, migrate to a hosted
database (e.g., Supabase, PlanetScale) in a future phase.

---

## 6 — Verify the deployment

After the app is live, run through this checklist:

- [ ] Home page loads with the hero banner and role selector
- [ ] Employee Plan page: enter any Employee ID, select a role, generate plan
- [ ] Admin Upload page: upload a small PDF — verify it chunks and appears in the DB metrics
- [ ] Dashboard page: KPIs show the correct document / chunk / requirement counts
- [ ] Dashboard → "Role Requirement Matrix" tab shows all 160 rows
- [ ] Comparison results and review queue load without errors

---

## 7 — Local development reminder

To run locally, copy `.env.example` to `.env` and fill in your key:

```bash
copy .env.example .env        # Windows
# then edit .env: GEMINI_API_KEY=your-key-here

streamlit run app.py
```

**Never commit the `.env` file.**
