"""
odds_api.py — The Odds API v2
odds חיים מ-40+ אתרי הימורים בזמן אמת
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT_KEY = "soccer_fifa_world_cup"
PREFERRED_BOOKMAKERS = ["pinnacle", "bet365", "williamhill", "unibet", "draftkings", "fanduel"]


# ─── המרת פורמט ────────────────────────────────────────────────────────────────

def _to_decimal(odd) -> float:
    """ממיר American Odds ל-Decimal אם צריך."""
    odd = float(odd)
    if odd == int(odd) and abs(odd) >= 100:
        if odd > 0:
            return round((odd / 100) + 1, 3)
        else:
            return round((100 / abs(odd)) + 1, 3)
    return round(odd, 3)


# ─── קריאת API ─────────────────────────────────────────────────────────────────

def _get(endpoint: str, params: dict) -> list | dict | None:
    """קריאת The Odds API עם טיפול בשגיאות."""
    if not ODDS_API_KEY:
        print("[OddsAPI] ❌ ODDS_API_KEY חסר ב-.env / Streamlit Secrets")
        return None

    url = f"{BASE_URL}/{endpoint}"
    params["apiKey"] = ODDS_API_KEY
    try:
        res = requests.get(url, params=params, timeout=10)
        remaining = res.headers.get("x-requests-remaining", "?")
        print(f"[OddsAPI] קריאות שנותרו היום: {remaining}")
        if res.status_code == 401:
            print("[OddsAPI] ❌ API Key לא תקין")
            return None
        if res.status_code == 422:
            print(f"[OddsAPI] ❌ Sport key לא קיים: {SPORT_KEY}")
            return None
        if res.status_code == 429:
            print("[OddsAPI] ❌ חרגת ממכסת הקריאות")
            return None
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"[OddsAPI] שגיאה: {e}")
        return None


# ─── חיפוש משחק ───────────────────────────────────────────────────────────────

def _find_event(data: list, home_team: str, away_team: str) -> dict | None:
    """מחפש משחק ברשימה לפי שמות קבוצות (partial match גמיש)."""
    home_words = set(home_team.lower().split())
    away_words = set(away_team.lower().split())

    for event in data:
        eh = event.get("home_team", "").lower()
        ea = event.get("away_team", "").lower()
        eh_words = set(eh.split())
        ea_words = set(ea.split())

        home_match = bool(home_words & eh_words) or home_team.lower() in eh or eh in home_team.lower()
        away_match = bool(away_words & ea_words) or away_team.lower() in ea or ea in away_team.lower()

        if home_match and away_match:
            return event

    return None


# ─── שליפת Odds ────────────────────────────────────────────────────────────────

def get_live_odds(home_team: str, away_team: str) -> dict | None:
    """
    מביא odds חיים למשחק.
    מנסה EU/UK (Decimal) תחילה, אחר-כך US (American → המרה).
    """
    # ניסיון 1: EU + UK
    data = _get(f"sports/{SPORT_KEY}/odds", {
        "regions": "eu,uk",
        "markets": "h2h",
        "oddsFormat": "decimal",
    })

    # ניסיון 2: US אם EU ריק
    if not data:
        data = _get(f"sports/{SPORT_KEY}/odds", {
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        })

    if not data:
        return None

    event = _find_event(data, home_team, away_team)
    if not event:
        print(f"[OddsAPI] לא נמצא: {home_team} vs {away_team}")
        # הדפס רשימה לצורך דיבוג
        for e in data[:5]:
            print(f"  → {e.get('home_team')} vs {e.get('away_team')}")
        return None

    all_books = []
    best_odds = None
    best_priority = 999

    for bm in event.get("bookmakers", []):
        bm_key = bm["key"]
        bm_title = bm.get("title", bm_key)

        for market in bm.get("markets", []):
            if market["key"] != "h2h":
                continue

            outcomes = {o["name"].lower(): o["price"] for o in market["outcomes"]}
            home_key = event["home_team"].lower()
            away_key = event["away_team"].lower()

            raw_home = outcomes.get(home_key)
            raw_away = outcomes.get(away_key)
            raw_draw = outcomes.get("draw")

            if not (raw_home and raw_away and raw_draw):
                continue

            home_d = _to_decimal(raw_home)
            draw_d = _to_decimal(raw_draw)
            away_d = _to_decimal(raw_away)

            # סינון ערכים לא הגיוניים
            if any(x < 1.01 or x > 50 for x in [home_d, draw_d, away_d]):
                continue

            all_books.append({
                "name": bm_title,
                "home": home_d,
                "draw": draw_d,
                "away": away_d,
                "last_update": market.get("last_update", ""),
            })

            priority = PREFERRED_BOOKMAKERS.index(bm_key) if bm_key in PREFERRED_BOOKMAKERS else 999
            if priority < best_priority:
                best_priority = priority
                best_odds = {
                    "home": home_d,
                    "draw": draw_d,
                    "away": away_d,
                    "bookmaker": bm_title,
                    "last_update": market.get("last_update", ""),
                    "all_books": all_books,
                }

    if best_odds:
        best_odds["all_books"] = all_books

    return best_odds


def get_best_odds(home_team: str, away_team: str) -> dict | None:
    """
    Best Line — היחס הטוב ביותר לכל תוצאה מכל הבוקמייקרים.
    """
    result = get_live_odds(home_team, away_team)
    if not result or not result.get("all_books"):
        return result

    all_books = result["all_books"]
    if not all_books:
        return result

    best_home = max(all_books, key=lambda b: b["home"])
    best_draw = max(all_books, key=lambda b: b["draw"])
    best_away = max(all_books, key=lambda b: b["away"])

    return {
        "home": best_home["home"],
        "home_book": best_home["name"],
        "draw": best_draw["draw"],
        "draw_book": best_draw["name"],
        "away": best_away["away"],
        "away_book": best_away["name"],
        "last_update": best_home["last_update"],
        "all_books": all_books,
        "is_best_line": True,
    }