# FIM DCMP 2026 Scouting Tool

A lightweight Python desktop application for scouting FRC teams attending the
**FIRST in Michigan District Championship (2026)**.

The tool uses [The Blue Alliance](https://www.thebluealliance.com/) API to:

- Fetch every team qualified for the district championship.
- Find each team's **two highest-scoring matches**.
- Surface linked **YouTube videos** of those matches for human review.
- Present everything in an interactive **table GUI** with match scores,
  alliance information, and a free-text **notes field** that is saved locally.

---

## Requirements

- Python 3.10 or newer (tkinter is bundled with the standard library)
- The `requests` library

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Setup

1. **Get a TBA API key** at <https://www.thebluealliance.com/account>.
   (Free — just create an account and generate a key under "Read API Keys".)

2. **Run the app:**

   ```bash
   python main.py
   ```

3. Paste your TBA API key into the **TBA API Key** field and click **Save Key**.
   The key is stored in `config.json` (excluded from version control).

4. The **Event Key** defaults to `2026micmp`.  Change it if needed
   (e.g., `2025micmp` to preview last year's data).

5. Click **Fetch Data**.  The app will retrieve all teams and their matches and
   cache the results in `data/teams_data.json`.

---

## Using the table

| Action | What it does |
|--------|-------------|
| Click a row | Shows detailed match info and loads notes in the bottom panel |
| Double-click a **Video** cell | Opens the YouTube video in your browser |
| Click a video link in the detail panel | Opens the YouTube video in your browser |
| Type in **Scouting Notes** then click **Save Notes** | Saves notes for the selected team to `data/notes.json` |
| Click a column heading | Sorts the table by that column |
| **Fetch Data** | Re-downloads fresh data from TBA (overwrites cache) |
| **Clear Cache** | Wipes the cached team/match data |
| **Save Key** | Persists your API key to `config.json` |

---

## File layout

```
FIMDCMPScouting2026/
├── main.py            # GUI application (entry point)
├── tba_api.py         # The Blue Alliance API client
├── data_manager.py    # Local JSON read/write helpers
├── requirements.txt   # Python dependencies
├── config.json        # API key (created on first "Save Key" — gitignored)
└── data/
    ├── teams_data.json  # Cached team/match data (gitignored)
    └── notes.json       # Scouting notes (gitignored)
```

> **Note:** `config.json`, `data/teams_data.json`, and `data/notes.json` are
> excluded from version control via `.gitignore` to keep credentials and local
> scouting notes private.