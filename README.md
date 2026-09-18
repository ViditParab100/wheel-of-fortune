# Torn Wheel of Fortune

A one-spin-per-window wheel of fortune for a Torn.com faction/friend group.
Players verify themselves with their **Torn Public API key** (used once,
never stored), then get exactly one spin while an admin-controlled window is
open. No database service — spins are logged to a CSV file and prizes/window
settings live in small JSON files, all on disk.

## Why not just GitHub Pages?

GitHub Pages only serves static files — it can't run Python or remember who
already spun. This app still lives in a GitHub repo, but the *running* app
needs a host that executes Python. **PythonAnywhere's free tier** works well
here: no credit card, a permanent URL (`yourusername.pythonanywhere.com`),
and — importantly — a real persistent filesystem, so the CSV/JSON files
survive restarts (unlike the free tiers of Render/Railway/Fly, whose disks
reset on redeploy).

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then edit .env: set SECRET_KEY and ADMIN_PASSWORD
python app.py
```

Visit `http://127.0.0.1:5000/` for the player page and
`http://127.0.0.1:5000/admin` to log in as admin.

**The spin window is closed by default.** Log into `/admin` and click
"Start brand-new window" with a start/end time to open one.

## Deploying to PythonAnywhere (free)

1. Push this repo to GitHub (see below).
2. Create a free account at pythonanywhere.com.
3. Open a Bash console there and clone your repo:
   ```bash
   git clone https://github.com/<you>/wheel-of-fortune.git
   cd wheel-of-fortune
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Create a `.env` file in that same folder (Bash console: `nano .env`) with
   real `SECRET_KEY` and `ADMIN_PASSWORD` values. Never commit this file.
5. On the **Web** tab, create a new web app → Manual configuration → the
   Python version matching your venv.
6. Set the **virtualenv** path to `/home/<you>/wheel-of-fortune/venv`.
7. Edit the WSGI configuration file it links you to, and replace its
   contents with what's in this repo's `wsgi.py` (update the `PROJECT_DIR`
   path to your actual username).
8. Hit **Reload** on the Web tab. Your live URL is
   `https://<you>.pythonanywhere.com`.
9. Whenever you push changes to GitHub: in the PythonAnywhere Bash console,
   `git pull`, then hit Reload on the Web tab again.

## Admin workflow

- `/admin` — log in with `ADMIN_PASSWORD`.
- **Spin window**: set a start/end time (shown and entered in UTC) and click
  "Start brand-new window" to open a fresh round — this resets everyone's
  ability to spin, even players who spun in a previous window. "Save times
  only" edits the current window without resetting anyone. "Close now" shuts
  it early.
- **Wheel segments**: edit label/prize text/relative weight/color per wedge,
  add or remove wedges, and upload a PNG per wedge for fun custom art. Weight
  is the relative odds (e.g. weight 30 vs weight 10 is 3x as likely) — it's
  never sent to the browser, so players can't infer the odds from page
  source.
- **Spin log**: every recorded spin (time, window, Torn ID, name, prize) —
  this is your CSV data (`data/spins.csv`), viewable right there.

## How "one spin per window" is enforced

The browser session is just a convenience so a player doesn't have to
re-paste their API key between verifying and spinning. The actual rule is
enforced server-side against `data/spins.csv` by **Torn ID**, so clearing
cookies, using a different browser, or a different device doesn't grant a
second spin within the same window.

## Data files (never committed — created automatically)

- `data/spins.csv` — append-only spin log.
- `data/state.json` — current window id/start/end/open-closed.
- `data/segments.json` — wheel prize config (seeded from
  `data/segments.default.json` on first run).
- `static/uploads/` — uploaded wedge PNGs.

Back these up occasionally (they're just files) if you care about history —
git doesn't track them.
