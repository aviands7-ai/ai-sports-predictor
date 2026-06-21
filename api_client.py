"""
api_client.py — גישה ל-Football API v2
retry, rate-limit, odds freshness timestamp.
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SPORTS_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

WC_LEAGUE_ID = 1
WC_SEASON    = 2026
WC_FROM      = "2026-06-11"
WC_TO        = "2026-07-19"


def _get(endpoint: str, params: dict, retries: int = 3) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if res.status_code == 429:
                wait = 2 ** attempt
                print(f"[API] Rate limit, waiting {wait}s...")
                time.sleep(wait)
                continue
            res.raise_for_status()
            data = res.json()
            if "errors" in data and data["errors"]:
                print(f"[API] Errors: {data['errors']}")
            return data
        except requests.RequestException as e:
            print(f"[API] Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def get_all_fixtures() -> list[dict]:
    data = _get("fixtures", {
        "league": WC_LEAGUE_ID,
        "season": WC_SEASON,
        "from": WC_FROM,
        "to": WC_TO
    })
    fixtures = data.get("response", [])
    fixtures.sort(key=lambda x: x["fixture"]["timestamp"])
    return fixtures


def get_fixtures_by_date(date_str: str) -> list[dict]:
    data = _get("fixtures", {
        "league": WC_LEAGUE_ID,
        "season": WC_SEASON,
        "date": date_str
    })
    return data.get("response", [])


def get_injuries(fixture_id: int) -> list[dict]:
    data = _get("injuries", {"fixture": fixture_id})
    return data.get("response", [])


def get_odds(fixture_id: int) -> dict | None:
    """
    שואב odds + timestamp עדכון.
    מחזיר {"home": float, "draw": float, "away": float, "updated_at": str} או None.
    """
    data = _get("odds", {"fixture": fixture_id})
    try:
        response_item = data["response"][0]
        bookmakers = response_item["bookmakers"]

        # timestamp עדכון מהתגובה הכללית
        updated_at = response_item.get("update", None)

        # מעדיף Pinnacle (ID 4), אחרת ראשון
        target = None
        for bm in bookmakers:
            if bm["id"] == 4:
                target = bm
                break
        if not target:
            target = bookmakers[0]

        for bet in target["bets"]:
            if bet["id"] == 1:  # Match Winner
                result = {}
                for v in bet["values"]:
                    if v["value"] == "Home":
                        result["home"] = float(v["odd"])
                    elif v["value"] == "Draw":
                        result["draw"] = float(v["odd"])
                    elif v["value"] == "Away":
                        result["away"] = float(v["odd"])
                if len(result) == 3:
                    result["updated_at"] = updated_at
                    result["bookmaker"] = target.get("name", "Unknown")
                    return result
    except (KeyError, IndexError, TypeError):
        pass
    return None


def get_head_to_head(team1_id: int, team2_id: int, last: int = 10) -> list[dict]:
    data = _get("fixtures/headtohead", {
        "h2h": f"{team1_id}-{team2_id}",
        "last": last
    })
    return data.get("response", [])


def get_team_last_matches(team_id: int, last: int = 5) -> list[dict]:
    """שואב 5 משחקים אחרונים שהסתיימו."""
    data = _get("fixtures", {
        "team": team_id,
        "last": last,
        "status": "FT"
    })
    return data.get("response", [])


def get_api_status() -> dict:
    data = _get("status", {})
    return data.get("response", {})
