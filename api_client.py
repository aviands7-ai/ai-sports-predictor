"""
api_client.py — גישה ל-Football API v4
דינמי לחלוטין: מגלה ליגות פעילות אוטומטית מה-API.
"""

import os
import time
from datetime import date, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("SPORTS_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

# ── מונדיאל 2026 — תמיד נכלל (גם בין עונות) ─────────────────────────────────
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
                print(f"[API] Rate limit, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            res.raise_for_status()
            data = res.json()
            if "errors" in data and data["errors"]:
                print(f"[API] Errors: {data['errors']}", flush=True)
            return data
        except requests.RequestException as e:
            print(f"[API] Attempt {attempt+1} failed: {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(1)
    return {}


def get_all_active_leagues() -> list[dict]:
    """
    מגלה דינמית את כל ליגות הכדורגל הפעילות כרגע.
    פונה ל-/leagues?current=true ומחזיר רשימת:
      [{"id": int, "season": int, "name": str, "country": str}, ...]

    מוגבל ל-100 ליגות עם מספר משחקים גדול מ-0 כדי לחסוך קריאות API.
    """
    data = _get("leagues", {"current": "true", "type": "League"})
    leagues = []

    for item in data.get("response", []):
        league  = item.get("league", {})
        seasons = item.get("seasons", [])

        # מצא את העונה הנוכחית
        current_season = None
        for s in seasons:
            if s.get("current"):
                current_season = s.get("year")
                break

        if not current_season:
            continue

        leagues.append({
            "id":      league.get("id"),
            "name":    league.get("name", ""),
            "country": item.get("country", {}).get("name", ""),
            "season":  current_season,
        })

    print(f"[API] נמצאו {len(leagues)} ליגות פעילות", flush=True)
    return leagues


def get_all_fixtures() -> list[dict]:
    """
    מושך את כל משחקי הכדורגל הפעילים בעולם.

    שלב 1: כל משחקי היום (כולל כל ליגה שמשחקת היום).
    שלב 2: מונדיאל 2026 — כל הטורניר.
    שלב 3: ליגות פעילות דינמיות — 7 ימים קדימה.
    מסנן כפילויות לפי fixture_id.
    """
    today     = date.today().strftime("%Y-%m-%d")
    next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    all_fixtures = {}

    # ── שלב 1: כל משחקי היום ────────────────────────────────────────────────
    data = _get("fixtures", {
        "date":   today,
        "status": "NS-1H-HT-2H-ET-BT-P-FT-AET-PEN",
    })
    for f in data.get("response", []):
        fid = f["fixture"]["id"]
        all_fixtures[fid] = f
    print(f"[API] שלב 1 (היום): {len(all_fixtures)} משחקים", flush=True)

    # ── שלב 2: מונדיאל 2026 — כל הטורניר ───────────────────────────────────
    wc_data = _get("fixtures", {
        "league": WC_LEAGUE_ID,
        "season": WC_SEASON,
        "from":   WC_FROM,
        "to":     WC_TO,
    })
    wc_added = 0
    for f in wc_data.get("response", []):
        fid = f["fixture"]["id"]
        if fid not in all_fixtures:
            all_fixtures[fid] = f
            wc_added += 1
    print(f"[API] שלב 2 (מונדיאל): +{wc_added} משחקים", flush=True)

    # ── שלב 3: ליגות פעילות דינמיות — 7 ימים קדימה ─────────────────────────
    active_leagues = get_all_active_leagues()
    dynamic_added  = 0

    for league_info in active_leagues:
        lid    = league_info["id"]
        season = league_info["season"]

        if lid == WC_LEAGUE_ID:
            continue  # כבר נמשך בשלב 2

        ldata = _get("fixtures", {
            "league": lid,
            "season": season,
            "from":   today,
            "to":     next_week,
        })
        for f in ldata.get("response", []):
            fid = f["fixture"]["id"]
            if fid not in all_fixtures:
                all_fixtures[fid] = f
                dynamic_added += 1

    print(f"[API] שלב 3 (דינמי, {len(active_leagues)} ליגות): +{dynamic_added} משחקים", flush=True)

    fixtures = list(all_fixtures.values())
    fixtures.sort(key=lambda x: x["fixture"]["timestamp"])
    print(f"[API] סה\"כ: {len(fixtures)} משחקים ייחודיים", flush=True)
    return fixtures


def get_fixtures_by_date(date_str: str) -> list[dict]:
    """מושך כל משחקי הכדורגל לתאריך נתון."""
    data = _get("fixtures", {
        "date":   date_str,
        "status": "NS-1H-HT-2H-ET-BT-P-FT-AET-PEN",
    })
    fixtures = data.get("response", [])
    fixtures.sort(key=lambda x: x["fixture"]["timestamp"])
    return fixtures


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
        bookmakers    = response_item["bookmakers"]
        updated_at    = response_item.get("update", None)

        target = None
        for bm in bookmakers:
            if bm["id"] == 4:  # Pinnacle
                target = bm
                break
        if not target:
            target = bookmakers[0]

        for bet in target["bets"]:
            if bet["id"] == 1:  # Match Winner
                result = {}
                for v in bet["values"]:
                    if v["value"] == "Home":   result["home"] = float(v["odd"])
                    elif v["value"] == "Draw": result["draw"] = float(v["odd"])
                    elif v["value"] == "Away": result["away"] = float(v["odd"])
                if len(result) == 3:
                    result["updated_at"] = updated_at
                    result["bookmaker"]  = target.get("name", "Unknown")
                    return result
    except (KeyError, IndexError, TypeError):
        pass
    return None


def get_head_to_head(team1_id: int, team2_id: int, last: int = 10) -> list[dict]:
    data = _get("fixtures/headtohead", {
        "h2h":  f"{team1_id}-{team2_id}",
        "last": last,
    })
    return data.get("response", [])


def get_team_last_matches(team_id: int, last: int = 5) -> list[dict]:
    data = _get("fixtures", {
        "team":   team_id,
        "last":   last,
        "status": "FT",
    })
    return data.get("response", [])


def get_api_status() -> dict:
    data = _get("status", {})
    return data.get("response", {})
