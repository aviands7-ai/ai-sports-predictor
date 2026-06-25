"""
odds_api.py — The Odds API v4
odds חיים מ-40+ אתרי הימורים בזמן אמת
מורחב לכל ליגות הכדורגל הפעילות בעולם.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL     = "https://api.the-odds-api.com/v4"

# ── ליגות כדורגל — מונדיאל + ליגות קיץ פעילות ───────────────────────────────
SPORT_KEYS = [
    # טורנירים בינלאומיים
    "soccer_fifa_world_cup",
    "soccer_international",
    "soccer_fifa_world_cup_qualifier_conmebol",

    # ליגות קיץ פעילות
    "soccer_usa_mls",
    "soccer_japan_j_league",
    "soccer_brazil_campeonato",
    "soccer_sweden_allsvenskan",
    "soccer_norway_eliteserien",
    "soccer_finland_veikkausliiga",

    # ליגות אירופה (עונה 2024-25)
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_france_ligue_one",
    "soccer_uefa_champs_league",
    "soccer_uefa_europa_league",
]

PREFERRED_BOOKMAKERS = [
    "pinnacle", "bet365", "williamhill",
    "unibet", "bwin", "draftkings", "fanduel",
]


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
    if not ODDS_API_KEY:
        print("[OddsAPI] ❌ ODDS_API_KEY חסר", flush=True)
        return None
    url = f"{BASE_URL}/{endpoint}"
    params["apiKey"] = ODDS_API_KEY
    try:
        res = requests.get(url, params=params, timeout=10)
        remaining = res.headers.get("x-requests-remaining", "?")
        print(f"[OddsAPI] קריאות שנותרו: {remaining}", flush=True)
        if res.status_code in (401, 403):
            print("[OddsAPI] ❌ API Key לא תקין", flush=True)
            return None
        if res.status_code == 422:
            return None  # sport key לא קיים — ממשיך לבא
        if res.status_code == 429:
            print("[OddsAPI] ❌ חרגת ממכסה", flush=True)
            return None
        res.raise_for_status()
        data = res.json()
        return data if data else None
    except requests.RequestException as e:
        print(f"[OddsAPI] שגיאה: {e}", flush=True)
        return None


def _get_events() -> list:
    """
    מנסה כל sport key ואוסף את כל המשחקים.
    מחזיר רשימה מאוחדת מכל הליגות.
    """
    all_events = {}

    for sport_key in SPORT_KEYS:
        # EU/UK — Decimal
        data = _get(f"sports/{sport_key}/odds", {
            "regions":    "eu,uk",
            "markets":    "h2h",
            "oddsFormat": "decimal",
        })
        if data and len(data) > 0:
            print(f"[OddsAPI] ✅ {sport_key} (EU): {len(data)} משחקים", flush=True)
            for event in data:
                eid = event.get("id")
                if eid and eid not in all_events:
                    all_events[eid] = event
            continue  # אם EU עבד — לא צריך US

        # US — American (עם המרה)
        data = _get(f"sports/{sport_key}/odds", {
            "regions":    "us",
            "markets":    "h2h",
            "oddsFormat": "american",
        })
        if data and len(data) > 0:
            print(f"[OddsAPI] ✅ {sport_key} (US): {len(data)} משחקים", flush=True)
            for event in data:
                eid = event.get("id")
                if eid and eid not in all_events:
                    all_events[eid] = event

    result = list(all_events.values())
    if not result:
        print("[OddsAPI] ⚠️ לא נמצאו משחקים בשום sport key", flush=True)
    else:
        print(f"[OddsAPI] סה\"כ: {len(result)} משחקים ייחודיים מכל הליגות", flush=True)
    return result


# ─── חיפוש משחק ───────────────────────────────────────────────────────────────

def _find_event(data: list, home_team: str, away_team: str) -> dict | None:
    """חיפוש גמיש לפי שמות קבוצות."""
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


def list_available_matches() -> list[str]:
    """מחזיר רשימת כל המשחקים הזמינים — לצורך דיבוג."""
    data = _get_events()
    return [
        f"{e.get('home_team')} vs {e.get('away_team')} ({e.get('commence_time','')[:10]})"
        for e in data
    ]


# ─── שליפת Odds ────────────────────────────────────────────────────────────────

def _extract_odds(event: dict) -> list[dict]:
    """מחלץ odds מכל הבוקמייקרים של event."""
    all_books = []
    home_team_name = event.get("home_team", "").lower()
    away_team_name = event.get("away_team", "").lower()

    for bm in event.get("bookmakers", []):
        bm_key   = bm["key"]
        bm_title = bm.get("title", bm_key)

        for market in bm.get("markets", []):
            if market["key"] != "h2h":
                continue

            outcomes = {o["name"].lower(): o["price"] for o in market["outcomes"]}
            raw_home = outcomes.get(home_team_name)
            raw_away = outcomes.get(away_team_name)
            raw_draw = outcomes.get("draw")

            if not (raw_home and raw_away and raw_draw):
                continue

            home_d = _to_decimal(raw_home)
            draw_d = _to_decimal(raw_draw)
            away_d = _to_decimal(raw_away)

            if any(x < 1.01 or x > 50 for x in [home_d, draw_d, away_d]):
                continue

            all_books.append({
                "name":        bm_title,
                "key":         bm_key,
                "home":        home_d,
                "draw":        draw_d,
                "away":        away_d,
                "last_update": market.get("last_update", ""),
            })

    return all_books


def get_live_odds(home_team: str, away_team: str) -> dict | None:
    """מביא odds חיים למשחק."""
    data = _get_events()
    if not data:
        return None

    event = _find_event(data, home_team, away_team)
    if not event:
        available = [f"{e.get('home_team')} vs {e.get('away_team')}" for e in data[:10]]
        print(f"[OddsAPI] לא נמצא: '{home_team}' vs '{away_team}'", flush=True)
        print(f"[OddsAPI] זמינים: {available}", flush=True)
        return None

    all_books = _extract_odds(event)
    if not all_books:
        return None

    best_odds    = None
    best_priority = 999
    for book in all_books:
        priority = PREFERRED_BOOKMAKERS.index(book["key"]) if book["key"] in PREFERRED_BOOKMAKERS else 999
        if priority < best_priority:
            best_priority = priority
            best_odds = {
                "home":        book["home"],
                "draw":        book["draw"],
                "away":        book["away"],
                "bookmaker":   book["name"],
                "last_update": book["last_update"],
                "all_books":   all_books,
            }
    return best_odds


def get_best_odds(home_team: str, away_team: str) -> dict | None:
    """Best Line — היחס הטוב ביותר לכל תוצאה מכל הבוקמייקרים."""
    result = get_live_odds(home_team, away_team)
    if not result or not result.get("all_books"):
        return result

    all_books = result["all_books"]
    best_home = max(all_books, key=lambda b: b["home"])
    best_draw = max(all_books, key=lambda b: b["draw"])
    best_away = max(all_books, key=lambda b: b["away"])

    return {
        "home":         best_home["home"],
        "home_book":    best_home["name"],
        "draw":         best_draw["draw"],
        "draw_book":    best_draw["name"],
        "away":         best_away["away"],
        "away_book":    best_away["name"],
        "last_update":  best_home["last_update"],
        "all_books":    all_books,
        "is_best_line": True,
    }


def get_all_odds_batch() -> dict:
    """
    קריאת Odds אחת לכל המשחקים מכל הליגות.
    מחזיר מילון {(home_team, away_team): odds_dict}
    חוסך עשרות קריאות API.
    """
    data = _get_events()
    if not data:
        return {}

    batch = {}
    for event in data:
        h = event.get("home_team", "")
        a = event.get("away_team", "")
        books = _extract_odds(event)
        if not books:
            continue

        valid = [b for b in books if 1.01 <= b["home"] <= 25 and 1.01 <= b["draw"] <= 25 and 1.01 <= b["away"] <= 25]
        if not valid:
            continue

        best_home = max(valid, key=lambda b: b["home"])
        best_draw = max(valid, key=lambda b: b["draw"])
        best_away = max(valid, key=lambda b: b["away"])

        odds_result = {
            "home":         best_home["home"],
            "home_book":    best_home["name"],
            "draw":         best_draw["draw"],
            "draw_book":    best_draw["name"],
            "away":         best_away["away"],
            "away_book":    best_away["name"],
            "last_update":  best_home.get("last_update", ""),
            "is_best_line": True,
        }

        batch[(h, a)]                     = odds_result
        batch[(h.lower(), a.lower())]     = odds_result

    print(f"[OddsAPI] Batch: {len(data)} משחקים → {len(batch)//2} עם odds", flush=True)
    return batch


def lookup_odds_from_batch(batch: dict, home_team: str, away_team: str) -> dict | None:
    """
    שולף odds ממילון ה-batch מבלי לקרוא ל-API.
    מחפש לפי שמות מקוריים ואחר כך לפי מילים.
    """
    key = (home_team.lower(), away_team.lower())
    if key in batch:
        return batch[key]

    home_words = set(home_team.lower().split())
    away_words = set(away_team.lower().split())

    for (bh, ba), odds in batch.items():
        bh_words = set(bh.split())
        ba_words = set(ba.split())
        if bool(home_words & bh_words) and bool(away_words & ba_words):
            return odds

    return None
