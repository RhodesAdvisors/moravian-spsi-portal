# How to set up a live Notion-fed portal site

A practical runbook for replicating what we built for SPSI. From a Notion database to a public read-only Vercel site that auto-refreshes every morning.

Time investment: ~2 hours for the initial setup, then it runs unattended.

---

## What you're building

A static HTML page hosted on Vercel that visualizes a Notion database — projects, deliverables, dates, owners, statuses. Each morning at 5 AM, a Cowork scheduled task pulls the latest from Notion, rebuilds the page, commits to GitHub, and Vercel auto-deploys. You don't touch anything day-to-day.

End result for SPSI: https://v0-html-page-hosting-rust.vercel.app/portal.html

---

## What you need before starting

- A **Notion** workspace with the database you want to display
- A **GitHub** account (free tier works) — repo will be private
- A **Vercel** account (free tier works) — sign in with GitHub for the smoothest path
- **Cowork** installed on the Mac that'll run the daily task (the Claude desktop app)
- The Notion connector authenticated in Cowork
- A Mac that stays on overnight (or a Mac mini set up as an always-on agent — Lee did this)

---

## Phase 1 — Build the initial site

### Step 1. Get the HTML template

Two options:

- **Easy:** ask Claude in Cowork to generate the HTML for you. Describe the database you want to visualize (projects, deliverables, dates, statuses) and the views you want (timeline, board, list). Provide a small JSON sample of the data shape. Claude will spit out a single-file `index.html`.
- **Branded:** if you want it to match a specific brand (university colors, your client's palette), tell Claude that upfront. The SPSI portal uses Moravian's blue/accent-blue palette and the Moravian star logo. Claude will accommodate.

Save the generated file as `index.html` in a working folder, e.g. `~/Documents/Claude/<Project Name> Site/`.

### Step 2. Export your initial data from Notion

Two JSON files drive the build:

- `projects_from_notion.json` — the top-level records (projects, in our case)
- `deliverables.json` — the child records (deliverables, keyed by their Notion page ID)
- `user_id_to_name_map.json` — Notion user IDs → display names

Easiest way to get these: ask Claude in Cowork. Point it at the Notion database URL and say "export this database as a JSON file in this shape" with a sample structure. It'll handle the API calls and produce the files.

Verify the data renders correctly by opening `index.html` in your browser directly (double-click). The page should populate with your data and look right.

### Step 3. Write a build script

Create `build_site.py` in the same folder. This script reads the three JSON files and produces `index.html` from a saved `_template.html`. Have Claude write it for you — describe what fields you want where, and any visual conventions (e.g., italic descriptions, status badges, date formats).

Test it: `python3 build_site.py` should produce a fresh `index.html`.

---

## Phase 2 — Auto-deploy infrastructure

### Step 4. Create a private GitHub repo

Go to https://github.com/new. Name it descriptively (e.g., `<client>-project-portal`). Set it to **Private**. Don't initialize with README/.gitignore/license — we'll push from local.

Copy the HTTPS clone URL when GitHub shows you the "Quick setup" page.

### Step 5. Wire up git locally

In Terminal:

```
cd "~/Documents/Claude/<Project Name> Site"
git init -b main
git config user.email "you@example.com"
git config user.name "Your Name"
```

Write a `.gitignore` that excludes secrets and noise:

```
.vercel
.vercel-token
.github-token
git-askpass.sh
archive/
*.previous
__pycache__/
*.pyc
.DS_Store
_*
!_template.html
```

### Step 6. Create a GitHub Personal Access Token

Go to https://github.com/settings/tokens?type=beta. Generate a **fine-grained token**:

- Resource owner: your account or org
- Repository access: only the new repo you just created
- Repository permissions: **Contents: Read and write**, leave the rest as default
- Expiration: 1 year is fine

Copy the token, then save it to a file (don't paste it in Terminal where it'll echo):

```
python3 -c "import getpass,os; p='.github-token'; open(p,'w').write(getpass.getpass('Token: ')); os.chmod(p,0o600)"
```

Paste the token at the prompt. The file is gitignored — it stays local.

### Step 7. Set up auth helper and push

Create `git-askpass.sh` in the folder:

```sh
#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
case "$1" in
  *sername*) echo oauth2 ;;
  *) cat "$SCRIPT_DIR/.github-token" ;;
esac
```

Make it executable and wire it in:

```
chmod +x git-askpass.sh
git config core.askpass "./git-askpass.sh"
```

Now stage, commit, push:

```
git add -A
git commit -m "Initial commit"
git remote add origin "https://github.com/<your-org>/<your-repo>.git"
git push -u origin main
```

If the push fails because of a stale lock, delete it: `rm -f .git/HEAD.lock` and retry.

### Step 8. Connect to Vercel

Go to https://vercel.com — sign in with GitHub. Click **Add New → Project**. Pick the repo you just pushed.

When it asks about framework:

- **Framework Preset: Other** (this is critical — it's a static HTML site, not Next.js)
- **Build Command:** leave empty
- **Output Directory:** leave empty (defaults to root, which is what you want)
- **Install Command:** leave empty

Click **Deploy**. About 30 seconds later you'll have a live URL.

If Vercel auto-detected the wrong framework and the deploy errored, drop a `vercel.json` in your repo with:

```json
{
  "framework": null,
  "buildCommand": null,
  "installCommand": null,
  "outputDirectory": null,
  "rewrites": [
    { "source": "/portal.html", "destination": "/index.html" }
  ]
}
```

Commit and push. The rewrite is optional — only useful if you had an old URL like `/portal.html` and want it to keep working.

---

## Phase 3 — Daily auto-refresh

### Step 9. Make sure Cowork has the Notion connector authenticated

Open Cowork. In settings or the connector panel, authenticate Notion. Grant access to the specific pages/databases you need.

### Step 10. Create a Notion change log page

Optional but recommended. Make a private Notion page somewhere (in your private space) titled e.g. "<Project> Portal — Daily Change Log". Each morning's run will append a dated entry there summarizing what changed in the underlying Notion data (new projects, status flips, date shifts, new deliverables, etc.).

Note the page ID — you'll need it in the scheduled task prompt.

### Step 11. Create the Cowork scheduled task

In Cowork, create a scheduled task with cron `0 5 * * *` (5 AM daily local time). The task prompt should walk Claude through:

1. **Idempotency check** — exit early if today's run already happened (prevents duplicate deploys when the scheduler fires twice after a sleep/wake)
2. **Snapshot** previous JSONs to `.previous` files
3. **Pull from Notion** via `notion-query-database-view` (the database view URL)
4. **Rewrite** `projects_from_notion.json` with the fresh data
5. **Re-fetch each child page** (deliverables, in our case) using `notion-fetch`. Max 3 parallel, validate each response's URL matches the request, retry serially on mismatch, keep prior cached value on hard failure
6. **Run `build_site.py`**
7. **Archive** a dated copy: `archive/index_<YYYY-MM-DD>.html`
8. **Diff** today's data against `.previous` (have a `diff_log.py` script that emits a human-readable Markdown summary)
9. **Commit and push** to GitHub — Vercel auto-deploys on push
10. **Append the diff** to the Notion change log page if anything changed

Lee's full SPSI task prompt is a good starting template — ask Claude to translate it for your use case.

### Step 12. First run + tool approvals

Click **Run now** on the scheduled task once. This surfaces all the permission prompts (Notion access, file system, Bash, GitHub push) so you can approve them. Future scheduled runs won't pause for approval — they'll just execute.

Confirm the live Vercel site updates and the Notion change log gets an entry. You're done.

---

## What happens every morning

5 AM local → Cowork wakes → task runs → pulls Notion → diffs → commits to GitHub → Vercel auto-deploys → you get a notification in Cowork with a one-line summary and the Notion log gets a new entry.

You don't touch anything unless something breaks. If it does break, the morning Cowork notification will tell you what went wrong (auth expired, Notion timeout, etc.) and the site stays on the last good build.

---

## Useful files to keep in your folder

```
<Project> Site/
├── _template.html              # canonical template — build_site.py patches this
├── build_site.py               # the local builder
├── diff_log.py                 # produces the human-readable change log
├── projects_from_notion.json   # current top-level data
├── deliverables.json           # current child data, keyed by page ID
├── user_id_to_name_map.json    # Notion user IDs → display names
├── vercel.json                 # framework/build overrides
├── index.html                  # the deployed page (regenerated each run)
├── .gitignore
├── git-askpass.sh              # gitignored, reads .github-token
├── .github-token               # gitignored, the GitHub PAT
└── archive/                    # gitignored, daily archive copies
```

---

## A few things we learned the hard way

- **`framework: null` in `vercel.json`** is the magic that stops Vercel from trying to treat a static HTML file as a Next.js app
- **`npm install -g`** wants `sudo` on macOS — that's normal. Better long-term path is to reconfigure npm's prefix, but `sudo` once for `vercel` CLI is fine
- **Don't paste tokens in chat** with Claude — even in error messages, the token can echo back. Use `getpass.getpass()` for token entry, then store in a gitignored file
- **The Notion fetch API occasionally returns the wrong page** when you fire many in parallel. We landed on max 3 parallel + per-response URL validation + serial retry as the reliability fix
- **Idempotency at step 0** prevents duplicate Vercel deploys when the Mac wakes from sleep and Cowork fires both a queued run and the regularly-scheduled run
- **Schedule the Mac to wake** with `sudo pmset repeat wakeorpoweron MTWRFSU 04:55:00` — or just leave it on. Cowork has to be running at the scheduled time
- **Cron timing** has small jitter in Cowork (a few minutes by design). Don't be surprised if 5:00 AM fires at 5:05 AM

---

Reach out to Lee if anything's unclear — he ran this end-to-end and can answer Cowork-specific questions faster than the docs.
