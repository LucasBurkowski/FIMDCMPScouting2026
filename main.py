"""
FIM DCMP 2026 Scouting Tool
============================
Lightweight Python / tkinter application that:

1. Fetches every team attending the FIM District Championship via the
   The Blue Alliance API.
2. Finds each team's two highest-scoring matches and retrieves the
   linked YouTube videos for human review.
3. Displays everything in an interactive table with per-team notes
   that are saved automatically to the local ``data/`` directory.

Usage
-----
    python main.py

Set your TBA API key in the "TBA API Key" field and click **Save Key**
once.  Then click **Fetch Data** to populate the table.  Double-click a
YouTube link cell to open the video in your browser.  Select a row,
type notes in the bottom panel, and click **Save Notes**.
"""

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, scrolledtext, ttk

from data_manager import (
    load_api_key,
    load_notes,
    load_teams_data,
    save_api_key,
    save_notes,
    save_teams_data,
)
from tba_api import TBAClient, TBAError

DEFAULT_EVENT_KEY = "2026micmp"

# Column definitions: (internal id, heading text, pixel width)
COLUMNS = [
    ("team_num",   "Team #",   70),
    ("team_name",  "Team Name", 200),
    ("match1",     "Match 1",   130),
    ("score1",     "Score 1",   75),
    ("video1",     "Video 1",   290),
    ("match2",     "Match 2",   130),
    ("score2",     "Score 2",   75),
    ("video2",     "Video 2",   290),
    ("notes",      "Notes",     220),
]


class ScoutingApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("FIM DCMP 2026 — Scouting Tool")
        self.root.geometry("1400x820")
        self.root.minsize(900, 600)

        self.notes: dict = load_notes()
        self.teams_data: dict = load_teams_data()
        self.current_team: str | None = None
        self._m1_url: str | None = None
        self._m2_url: str | None = None

        self._build_ui()

        if self.teams_data:
            self._populate_table()
            self.status_var.set(
                f"Loaded {len(self.teams_data)} teams from cache.  "
                "Click 'Fetch Data' to refresh."
            )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._build_toolbar()
        paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        table_frame = ttk.Frame(paned)
        detail_frame = ttk.LabelFrame(paned, text="Team Details & Notes", padding=6)
        paned.add(table_frame, weight=3)
        paned.add(detail_frame, weight=1)
        self._build_table(table_frame)
        self._build_detail(detail_frame)

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self.root, padding=(6, 6, 6, 4))
        bar.pack(fill=tk.X)

        ttk.Label(bar, text="Event Key:").pack(side=tk.LEFT)
        self.event_key_var = tk.StringVar(value=DEFAULT_EVENT_KEY)
        ttk.Entry(bar, textvariable=self.event_key_var, width=14).pack(
            side=tk.LEFT, padx=(4, 12)
        )

        ttk.Label(bar, text="TBA API Key:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar(value=load_api_key())
        ttk.Entry(bar, textvariable=self.api_key_var, width=44, show="*").pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(bar, text="Save Key", command=self._save_api_key).pack(
            side=tk.LEFT, padx=(4, 12)
        )

        ttk.Button(bar, text="Fetch Data", command=self._start_fetch).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(bar, text="Clear Cache", command=self._clear_cache).pack(
            side=tk.LEFT, padx=4
        )

        self.status_var = tk.StringVar(
            value="Enter your TBA API key, then click 'Fetch Data'."
        )
        ttk.Label(bar, textvariable=self.status_var, foreground="#444").pack(
            side=tk.LEFT, padx=12
        )

    def _build_table(self, parent: ttk.Frame) -> None:
        col_ids = [c[0] for c in COLUMNS]
        self.tree = ttk.Treeview(parent, columns=col_ids, show="headings",
                                 selectmode="browse")

        for col_id, heading, width in COLUMNS:
            self.tree.heading(col_id, text=heading,
                              command=lambda c=col_id: self._sort_column(c, False))
            self.tree.column(col_id, width=width, minwidth=50, stretch=(col_id == "team_name"))

        # Tag for rows that have at least one YouTube link
        self.tree.tag_configure("has_video", foreground="#1a1a8c")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _build_detail(self, parent: ttk.Frame) -> None:
        # Left: match cards
        left = ttk.Frame(parent)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.detail_title = ttk.Label(
            left, text="Select a team to view match details.",
            font=("TkDefaultFont", 11, "bold")
        )
        self.detail_title.pack(anchor=tk.W, pady=(0, 4))

        cards = ttk.Frame(left)
        cards.pack(fill=tk.X)

        self._m1_info_var = tk.StringVar(value="—")
        self._m1_url_var = tk.StringVar(value="—")
        self._m2_info_var = tk.StringVar(value="—")
        self._m2_url_var = tk.StringVar(value="—")

        self._build_match_card(cards, "Top Match 1",
                               self._m1_info_var, self._m1_url_var,
                               lambda _: self._open_video(1))
        self._build_match_card(cards, "Top Match 2",
                               self._m2_info_var, self._m2_url_var,
                               lambda _: self._open_video(2))

        # Right: notes
        right = ttk.Frame(parent)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0))

        ttk.Label(right, text="Scouting Notes:", font=("TkDefaultFont", 10, "bold")).pack(
            anchor=tk.W
        )
        self.notes_text = scrolledtext.ScrolledText(right, height=6, width=42,
                                                     wrap=tk.WORD)
        self.notes_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        btn_row = ttk.Frame(right)
        btn_row.pack(fill=tk.X, pady=4)
        ttk.Button(btn_row, text="Save Notes", command=self._save_current_notes).pack(
            side=tk.RIGHT
        )
        self._notes_saved_label = ttk.Label(btn_row, text="", foreground="green")
        self._notes_saved_label.pack(side=tk.RIGHT, padx=8)

    @staticmethod
    def _build_match_card(
        parent: ttk.Frame,
        title: str,
        info_var: tk.StringVar,
        url_var: tk.StringVar,
        url_click,
    ) -> None:
        card = ttk.LabelFrame(parent, text=title, padding=6)
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        ttk.Label(card, textvariable=info_var).pack(anchor=tk.W)
        link = ttk.Label(card, textvariable=url_var,
                         foreground="#1a1aff", cursor="hand2")
        link.pack(anchor=tk.W)
        link.bind("<Button-1>", url_click)

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _save_api_key(self) -> None:
        save_api_key(self.api_key_var.get().strip())
        self.status_var.set("API key saved to config.json.")

    def _start_fetch(self) -> None:
        api_key = self.api_key_var.get().strip()
        event_key = self.event_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Missing API Key",
                                 "Enter your TBA API key and click 'Save Key'.")
            return
        if not event_key:
            messagebox.showerror("Missing Event Key", "Enter an event key.")
            return
        self.status_var.set("Connecting to The Blue Alliance…")
        threading.Thread(
            target=self._fetch_thread,
            args=(api_key, event_key),
            daemon=True,
        ).start()

    def _fetch_thread(self, api_key: str, event_key: str) -> None:
        def update_status(msg: str) -> None:
            self.root.after(0, self.status_var.set, msg)

        # Derive the season year from the event key (e.g. "2026micmp" → 2026)
        try:
            season_year = int(event_key[:4])
        except ValueError:
            self.root.after(
                0, messagebox.showerror, "Invalid Event Key",
                "Event key must start with a 4-digit year (e.g. 2026micmp)."
            )
            update_status("Fetch failed.")
            return

        try:
            client = TBAClient(api_key)
            update_status("Fetching team list…")
            teams = client.get_event_teams(event_key)
            if not teams:
                self.root.after(
                    0, messagebox.showinfo, "No Teams",
                    f"No teams found for event '{event_key}'.  "
                    "The event may not have teams registered yet."
                )
                update_status("No teams found.")
                return

            teams.sort(key=lambda t: t.get("team_number", 0))
            total = len(teams)
            new_data: dict = {}

            for idx, team in enumerate(teams):
                team_key = team["key"]
                update_status(
                    f"Fetching prior-season matches — {team_key} ({idx + 1}/{total})…"
                )
                try:
                    all_matches = client.get_team_season_matches(team_key, season_year)
                    # Exclude matches played at the DCMP event itself so we
                    # only consider results from earlier district events.
                    prior_matches = [
                        m for m in all_matches
                        if not m.get("event_key", "").startswith(event_key)
                    ]
                    top2 = TBAClient.top_matches(team_key, prior_matches, n=2)
                except TBAError:
                    top2 = []

                new_data[team_key] = {
                    "team_number": team.get("team_number", 0),
                    "team_name": team.get("nickname", "Unknown"),
                    "top_matches": top2,
                }

            self.teams_data = new_data
            save_teams_data(new_data)
            self.root.after(0, self._populate_table)
            update_status(f"Done — {total} teams loaded (prior-event matches).")

        except TBAError as exc:
            self.root.after(0, messagebox.showerror, "TBA API Error", str(exc))
            update_status("Fetch failed.")

    # ------------------------------------------------------------------
    # Table population & interaction
    # ------------------------------------------------------------------

    def _populate_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for team_key, data in sorted(
            self.teams_data.items(),
            key=lambda kv: kv[1].get("team_number", 0),
        ):
            top = data.get("top_matches", [])
            m1 = top[0] if len(top) > 0 else {}
            m2 = top[1] if len(top) > 1 else {}

            note_text = self.notes.get(team_key, "")
            note_display = (note_text[:48] + "…") if len(note_text) > 50 else note_text

            v1 = m1.get("video_url") or ""
            v2 = m2.get("video_url") or ""

            tags = ("has_video",) if (v1 or v2) else ()

            self.tree.insert(
                "", tk.END, iid=team_key,
                values=(
                    data.get("team_number", ""),
                    data.get("team_name", ""),
                    m1.get("match_key", "—"),
                    m1.get("score", "—") if m1 else "—",
                    v1 or "No video",
                    m2.get("match_key", "—"),
                    m2.get("score", "—") if m2 else "—",
                    v2 or "No video",
                    note_display,
                ),
                tags=tags,
            )

    def _sort_column(self, col_id: str, reverse: bool) -> None:
        """Sort the treeview by the clicked column."""
        items = [(self.tree.set(k, col_id), k) for k in self.tree.get_children()]
        try:
            items.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (_, k) in enumerate(items):
            self.tree.move(k, "", index)
        self.tree.heading(col_id,
                          command=lambda: self._sort_column(col_id, not reverse))

    def _on_select(self, _event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        team_key = sel[0]
        self.current_team = team_key
        data = self.teams_data.get(team_key, {})
        top = data.get("top_matches", [])

        self.detail_title.config(
            text=f"Team {data.get('team_number', '?')} — {data.get('team_name', '?')}"
        )

        def fill_card(match: dict, info_var: tk.StringVar,
                      url_var: tk.StringVar, url_attr: str) -> None:
            if match:
                lvl = match.get("comp_level", "").upper()
                num = match.get("match_number", "")
                alliance = match.get("alliance", "").capitalize()
                score = match.get("score", "?")
                opp_colour = "blue" if match.get("alliance") == "red" else "red"
                opp_score = match.get(f"{opp_colour}_score", "?")
                info_var.set(
                    f"{lvl} Match {num}  |  Alliance: {alliance}  "
                    f"|  Score: {score} – {opp_score}"
                )
                url = match.get("video_url")
                url_var.set(url if url else "No video available")
                setattr(self, url_attr, url)
            else:
                info_var.set("No match data")
                url_var.set("—")
                setattr(self, url_attr, None)

        fill_card(top[0] if len(top) > 0 else {}, self._m1_info_var,
                  self._m1_url_var, "_m1_url")
        fill_card(top[1] if len(top) > 1 else {}, self._m2_info_var,
                  self._m2_url_var, "_m2_url")

        # Load notes for selected team
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", self.notes.get(team_key, ""))
        self._notes_saved_label.config(text="")

    def _on_double_click(self, event) -> None:
        """Open YouTube if a video cell was double-clicked."""
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        col = self.tree.identify_column(event.x)
        col_idx = int(col.lstrip("#")) - 1
        col_ids = [c[0] for c in COLUMNS]
        if col_idx >= len(col_ids):
            return
        if col_ids[col_idx] not in ("video1", "video2"):
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        url = self.tree.item(item, "values")[col_idx]
        if url and url.startswith("http"):
            webbrowser.open(url)

    def _open_video(self, match_num: int) -> None:
        url = self._m1_url if match_num == 1 else self._m2_url
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("No Video", "No YouTube video linked for this match.")

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def _save_current_notes(self) -> None:
        if not self.current_team:
            messagebox.showinfo("No Team Selected", "Select a team row first.")
            return
        text = self.notes_text.get("1.0", tk.END).strip()
        self.notes[self.current_team] = text
        save_notes(self.notes)

        # Refresh display in table
        display = (text[:48] + "…") if len(text) > 50 else text
        self.tree.set(self.current_team, "notes", display)
        self._notes_saved_label.config(text="✔ Saved")

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _clear_cache(self) -> None:
        if messagebox.askyesno("Clear Cache",
                               "Delete locally cached team/match data?"):
            self.teams_data = {}
            save_teams_data({})
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.status_var.set("Cache cleared.  Click 'Fetch Data' to reload.")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main() -> None:
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.3)
    except tk.TclError:
        pass
    ScoutingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
