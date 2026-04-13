"""
The Blue Alliance API client.
Docs: https://www.thebluealliance.com/apidocs/v3
"""

import requests

BASE_URL = "https://www.thebluealliance.com/api/v3"


class TBAError(Exception):
    """Raised when a TBA API request fails."""


class TBAClient:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({"X-TBA-Auth-Key": api_key})

    def _get(self, path: str) -> object:
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.get(url, timeout=15)
        except requests.RequestException as exc:
            raise TBAError(f"Network error: {exc}") from exc
        if resp.status_code == 401:
            raise TBAError("Invalid TBA API key (HTTP 401).")
        if resp.status_code == 404:
            raise TBAError(f"Resource not found: {path} (HTTP 404). "
                           "Check that the event key is correct.")
        if not resp.ok:
            raise TBAError(f"TBA API returned HTTP {resp.status_code} for {path}.")
        return resp.json()

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def get_event_teams(self, event_key: str) -> list:
        """Return a list of team objects attending *event_key*."""
        return self._get(f"/event/{event_key}/teams")

    def get_team_event_matches(self, team_key: str, event_key: str) -> list:
        """Return all matches a team played at an event."""
        return self._get(f"/team/{team_key}/event/{event_key}/matches")

    # ------------------------------------------------------------------
    # Match helpers
    # ------------------------------------------------------------------

    @staticmethod
    def team_score_in_match(team_key: str, match: dict) -> int | None:
        """
        Return the score of the alliance *team_key* was on, or *None* if the
        match has not been played yet (score == -1) or the team was not found.
        """
        alliances = match.get("alliances") or {}
        for colour in ("red", "blue"):
            alliance = alliances.get(colour, {})
            if team_key in alliance.get("team_keys", []):
                score = alliance.get("score", -1)
                return score if score >= 0 else None
        return None

    @staticmethod
    def youtube_url(match: dict) -> str | None:
        """Return the first YouTube URL embedded in a match, or *None*."""
        for video in match.get("videos") or []:
            if video.get("type") == "youtube":
                return f"https://www.youtube.com/watch?v={video['key']}"
        return None

    @staticmethod
    def top_matches(team_key: str, matches: list, n: int = 2) -> list:
        """
        Return the *n* highest-scoring played matches for *team_key*.

        Each item in the returned list is a dict::

            {
                "match_key":   str,
                "comp_level":  str,   # e.g. "qm", "sf", "f"
                "match_number": int,
                "score":       int,   # alliance score
                "alliance":    str,   # "red" | "blue"
                "red_score":   int,
                "blue_score":  int,
                "video_url":   str | None,
            }
        """
        scored: list[dict] = []
        for match in matches:
            alliances = match.get("alliances") or {}
            red = alliances.get("red", {})
            blue = alliances.get("blue", {})

            if team_key in red.get("team_keys", []):
                colour = "red"
                score = red.get("score", -1)
            elif team_key in blue.get("team_keys", []):
                colour = "blue"
                score = blue.get("score", -1)
            else:
                continue

            if score < 0:
                continue  # match not yet played

            scored.append({
                "match_key": match.get("key", ""),
                "comp_level": match.get("comp_level", ""),
                "match_number": match.get("match_number", 0),
                "set_number": match.get("set_number", 0),
                "score": score,
                "alliance": colour,
                "red_score": red.get("score", 0),
                "blue_score": blue.get("score", 0),
                "video_url": TBAClient.youtube_url(match),
            })

        scored.sort(key=lambda m: m["score"], reverse=True)
        return scored[:n]
