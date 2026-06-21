"""
odds_api.py — The Odds API
מביא odds חיים מ-40+ אתרי הימורים (Bet365, Pinnacle, William Hill וכו')
https://the-odds-api.com
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"

# מונדיאל 2026 ב-Odds API
SPORT_KEY = "soccer_fifa_world_cup"

# אתרים מועדפים לפי אמינות (margin נמוך)
PREFERRED_BOOKMAKERS = ["pinnacle", "bet365", "williamhill", "draftkings", "fanduel"]


def _to_decimal(odd) -> float:
    """
    ממיר כל פורמט יחס ל-Decimal.
    American: +150 → 2.50 | -200 → 1.50
    Decimal: 1.01–30 → ללא שינוי
    הגבול: מספר שלם >= 100 = American. מספר עשרוני < 30 = Decimal.
    """
    odd = float(odd)
    # אם זה מספר שלם גדול מ-100 — זה American Odds
    if odd == int(odd) and abs(odd) >= 100:
        if odd > 0:
            return round((odd / 100) + 1, 3)
        else:
            return round((100 / abs(odd)) + 1, 3)
    # אחרת — כבר Decimal
    return round(odd, 3)
    """קריאת API עם טיפול בשגיאות."""
    url = f"{BASE_URL}/{endpoint}"
    params["apiKey"] = ODDS_API_KEY
    try:
        res = requests.get(url, params=params, timeout=10)
        remaining = res.headers.get("x-requests-remaining", "?")
        used = res.headers.get("x-requests-used", "?")
        print(f"[OddsAPI] קריאות שנותרו: {remaining} (בשימוש: {used})")
        if res.status_code == 401:
            print("[OddsAPI] ❌ API Key לא תקין")
            return None
        if res.status_code == 429:
            print("[OddsAPI] ❌ חרגת ממכסת הקריאות היומית")
            return None
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"[OddsAPI] שגיאה: {e}")
        return None


def get_live_odds(home_team: str, away_team: str) -> dict | None:
    """
    מביא odds חיים למשחק ספציפי.
    מנסה EU/UK תחילה (Decimal), אחר-כך US עם המרה.
    """
    # ניסיון ראשון: EU + UK (Pinnacle, Bet365, William Hill)
    data = _get(f"sports/{SPORT_KEY}/odds", {
        "regions": "eu,uk",
        "markets": "h2h",
        "oddsFormat": "decimal",
    })

    # אם לא נמצא — נסה US
    if not data:
        data = _get(f"sports/{SPORT_KEY}/odds", {
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        })

    if not data:
        return None

    # חיפוש המשחק לפי שמות קבוצות (partial match)
    home_lower = home_team.lower()
    away_lower = away_team.lower()

    best_match = None
    for event in data:
        event_home = event.get("home_team", "").lower()
        event_away = event.get("away_team", "").lower()

        # בדיקת התאמה גמישה
        home_match = any(w in event_home for w in home_lower.split()) or any(w in home_lower for w in event_home.split())
        away_match = any(w in event_away for w in away_lower.split()) or any(w in away_lower for w in event_away.split())

        if home_match and away_match:
            best_match = event
            break

    if not best_match:
        print(f"[OddsAPI] לא נמצא משחק: {home_team} vs {away_team}")
        return None

    # איסוף odds מכל הבוקמייקרים
    all_books = []
    best_odds = None
    best_priority = 999

    for bm in best_match.get("bookmakers", []):
        bm_name = bm["key"]
        for market in bm.get("markets", []):
            if market["key"] == "h2h":
                outcomes = {o["name"].lower(): o["price"] for o in market["outcomes"]}

                home_key = best_match["home_team"].lower()
                away_key = best_match["away_team"].lower()

                home_odd = outcomes.get(home_key)
                away_odd = outcomes.get(away_key)
                draw_odd = outcomes.get("draw")

                if home_odd and away_odd and draw_odd:
                    # המרה ל-Decimal אם צריך
                    home_d = _to_decimal(home_odd)
                    draw_d = _to_decimal(draw_odd)
                    away_d = _to_decimal(away_odd)

                    # סינון: יחסים לא הגיוניים
                    if home_d < 1.01 or draw_d < 1.01 or away_d < 1.01:
                        continue
                    if home_d > 50 or draw_d > 50 or away_d > 50:
                        continue

                    all_books.append({
                        "name": bm.get("title", bm_name),
                        "home": home_d,
                        "draw": draw_d,
                        "away": away_d,
                        "last_update": market.get("last_update", ""),
                    })

                    priority = PREFERRED_BOOKMAKERS.index(bm_name) if bm_name in PREFERRED_BOOKMAKERS else 999
                    if priority < best_priority:
                        best_priority = priority
                        best_odds = {
                            "home": home_d,
                            "draw": draw_d,
                            "away": away_d,
                            "bookmaker": bm.get("title", bm_name),
                            "last_update": market.get("last_update", ""),
                            "all_books": all_books,
                        }

    return best_odds


def get_best_odds(home_team: str, away_team: str) -> dict | None:
    """
    מחזיר את ה-odds הטובים ביותר לכל תוצאה מכל הבוקמייקרים.
    (Line Shopping — חיפוש היחס הגבוה ביותר בכל אתר)
    """
    result = get_live_odds(home_team, away_team)
    if not result or not result.get("all_books"):
        return result

    all_books = result["all_books"]

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


def get_api_quota() -> dict:
    """בדיקת מכסת קריאות שנותרה."""
    data = _get(f"sports/{SPORT_KEY}/odds", {
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
    })
    # הנתונים מגיעים מה-headers, לא מה-body
    return {"checked": True}