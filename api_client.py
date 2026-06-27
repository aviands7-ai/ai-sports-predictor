"""
api_client.py — גישה ל-Football API v4
דינמי + חסכוני: cache יומי, rate-limit protection, graceful stop.
"""

import os
import time
from datetime import date, timedelta
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("SPORTS_API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {"x-apisports-key": API_KEY}

WC_LEAGUE_ID = 1
WC_SEASON    = 2026

# ── Whitelist ליגות רלוונטיות לשלב 3 ─────────────────────────────────────────
LEAGUE_WHITELIST: set[int] = {
    1, 2, 3, 848, 531,
    39, 40, 41, 48, 45,
    140, 141, 143,
    78, 79, 81,
    135, 136, 137,
    61, 62, 66,
    88, 89,
    94, 95,
    144, 145,
    203, 204,
    197,
    106,
    113, 114,
    103, 104,
    119, 120,
    207, 208,
    218, 219,
    179, 180,
    235,
    333,
    345,
    392,
    210,
    283,
    271,
    253, 254, 262, 263,
    71, 72, 73,
    128, 130,
    239,
    265,
    268,
    281,
    13, 11,
    98, 292, 169, 307,
    29, 20,
}

# ── מצב גלובלי ───────────────────────────────────────────────────────────────
_API_BLOCKED    = False
_BLOCKED_REASON = ""

# ── Cache יומי ────────────────────────────────────────────────────────────────
_DAILY_CACHE: dict          = {}
_CACHE_DATE:  Optional[str] = None


def _get_cache_key(endpoint: str, params: dict) -> str:
    return f"{endpoint}::{sorted(params.items())}"


def _get(endpoint: str, params: dict, retries: int = 3,
         use_cache: bool = False) -> dict:
    global _API_BLOCKED, _BLOCKED_REASON, _DAILY_CACHE, _CACHE_DATE

    if _API_BLOCKED:
        print(f"[API] ⛔ מדולג — API חסום: {_BLOCKED_REASON}", flush=True)
        return {}

    today = date.today().strftime("%Y-%m-%d")
    if _CACHE_DATE != today:
        _DAILY_CACHE = {}
        _CACHE_DATE  = today

    if use_cache:
        key = _get_cache_key(endpoint, params)
        if key in _DAILY_CACHE:
            return _DAILY_CACHE[key]

    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, params=params, timeout=15)

            if res.status_code == 429:
                _API_BLOCKED    = True
                _BLOCKED_REASON = "Rate Limit (429) — חכה עד מחר"
                print("[API] ⛔ RATE LIMIT! הסריקה נעצרת.", flush=True)
                return {}

            if res.status_code in (401, 403):
                _API_BLOCKED    = True
                _BLOCKED_REASON = f"API Key לא תקין ({res.status_code})"
                print("[API] ⛔ API KEY שגוי! הסריקה נעצרת.", flush=True)
                return {}

            res.raise_for_status()
            data = res.json()

            if "errors" in data and data["errors"]:
                err = data["errors"]
                print(f"[API] ⚠️ שגיאת API: {err}", flush=True)
                err_str = str(err).lower()
                if "requests" in err_str or "limit" in err_str or "quota" in err_str:
                    _API_BLOCKED    = True
                    _BLOCKED_REASON = "מכסה יומית נגמרה"
                    print("[API] ⛔ מכסה נגמרה! הסריקה נעצרת.", flush=True)
                    return {}

            if use_cache:
                _DAILY_CACHE[_get_cache_key(endpoint, params)] = data
            return data

        except requests.RequestException as e:
            print(f"[API] Attempt {attempt+1} failed: {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    return {}


def is_api_blocked() -> bool:
    return _API_BLOCKED


def reset_api_block():
    global _API_BLOCKED, _BLOCKED_REASON
    _API_BLOCKED    = False
    _BLOCKED_REASON = ""


def get_all_active_leagues() -> list[dict]:
    data    = _get("leagues", {"current": "true", "type": "League"}, use_cache=True)
    leagues = []

    for item in data.get("response", []):
        league  = item.get("league", {})
        seasons = item.get("seasons", [])

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

    שלב 1 — כל משחקי היום (תאריך נוכחי).
    שלב 2 — מונדיאל 2026 — 7 ימים אחורה + 7 ימים קדימה בלבד (לא כל הטורניר!).
    שלב 3 — ליגות דינמיות — 7 ימים קדימה (מוגבל ל-50 ליגות).

    עוצר אוטומטית אם ה-API חסום.
    """
    if _API_BLOCKED:
        print("[API] ⛔ API חסום — מדלג", flush=True)
        return []

    today     = date.today().strftime("%Y-%m-%d")
    next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    last_week = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    all_fixtures: dict = {}

    # ── שלב 1: כל משחקי היום ────────────────────────────────────────────────
    data = _get("fixtures", {
        "date":   today,
        "status": "NS-1H-HT-2H-ET-BT-P-FT-AET-PEN",
    })
    for f in data.get("response", []):
        fid = f["fixture"]["id"]
        all_fixtures[fid] = f
    print(f"[API] שלב 1 (היום): {len(all_fixtures)} משחקים", flush=True)

    if _API_BLOCKED:
        return _sorted_fixtures(all_fixtures)

    # ── שלב 2: מונדיאל 2026 — 7 ימים אחורה + 7 ימים קדימה בלבד ─────────────
    # לא מושך את כל הטורניר — מונע עדכון Elo מיותר של עשרות משחקים ישנים
    wc_data = _get("fixtures", {
        "league": WC_LEAGUE_ID,
        "season": WC_SEASON,
        "from":   last_week,
        "to":     next_week,
    })
    wc_added = 0
    for f in wc_data.get("response", []):
        fid = f["fixture"]["id"]
        if fid not in all_fixtures:
            all_fixtures[fid] = f
            wc_added += 1
    print(f"[API] שלב 2 (מונדיאל): +{wc_added} משחקים", flush=True)

    if _API_BLOCKED:
        return _sorted_fixtures(all_fixtures)

    # ── שלב 3: ליגות דינמיות — 7 ימים קדימה ────────────────────────────────
    active_leagues  = get_all_active_leagues()
    MAX_LEAGUES     = 50

    leagues_to_scan = [
        l for l in active_leagues
        if l["id"] != WC_LEAGUE_ID
        and l["id"] in LEAGUE_WHITELIST
    ][:MAX_LEAGUES]

    dynamic_added = 0
    skipped_leagues = len([l for l in active_leagues if l["id"] != WC_LEAGUE_ID]) - len(leagues_to_scan)
    if skipped_leagues > 0:
        print(f"[API] שלב 3 — מדלג על {skipped_leagues} ליגות לא-רלוונטיות (Whitelist)", flush=True)

    for league_info in leagues_to_scan:
        if _API_BLOCKED:
            print("[API] ⛔ Rate limit — עוצר שלב 3", flush=True)
            break

        ldata = _get("fixtures", {
            "league": league_info["id"],
            "season": league_info["season"],
            "from":   today,
            "to":     next_week,
        })
        for f in ldata.get("response", []):
            fid = f["fixture"]["id"]
            if fid not in all_fixtures:
                all_fixtures[fid] = f
                dynamic_added += 1

    print(f"[API] שלב 3 ({len(leagues_to_scan)} ליגות): +{dynamic_added} משחקים", flush=True)
    result = _sorted_fixtures(all_fixtures)
    print(f"[API] סה\"כ: {len(result)} משחקים ייחודיים", flush=True)
    return result


def _sorted_fixtures(fixtures_dict: dict) -> list[dict]:
    lst = list(fixtures_dict.values())
    lst.sort(key=lambda x: x["fixture"]["timestamp"])
    return lst


def get_fixtures_by_date(date_str: str) -> list[dict]:
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
    data = _get("odds", {"fixture": fixture_id})
    try:
        response_item = data["response"][0]
        bookmakers    = response_item["bookmakers"]
        updated_at    = response_item.get("update", None)

        target = None
        for bm in bookmakers:
            if bm["id"] == 4:
                target = bm
                break
        if not target:
            target = bookmakers[0]

        for bet in target["bets"]:
            if bet["id"] == 1:
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
