"""
odds_api.py — The Odds API v4
דינמי + חסכוני: cache יומי, rate-limit protection.
מגלה ענפי ספורט אוטומטית. תומך ב-3-way (כדורגל) וב-2-way (טניס/בייסבול/כדורסל).
"""

import os
import requests
from datetime import date
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL     = "https://api.the-odds-api.com/v4"

PREFERRED_BOOKMAKERS = [
    "pinnacle", "bet365", "williamhill",
    "unibet", "bwin", "draftkings", "fanduel",
]

# ── מצב גלובלי ───────────────────────────────────────────────────────────────
_ODDS_BLOCKED    = False
_BLOCKED_REASON  = ""

# ── Cache יומי ────────────────────────────────────────────────────────────────
_DAILY_CACHE: dict          = {}
_CACHE_DATE:  Optional[str] = None
_SPORTS_CACHE: list         = []


def _cache_get(key: str):
    today = date.today().strftime("%Y-%m-%d")
    global _CACHE_DATE, _DAILY_CACHE
    if _CACHE_DATE != today:
        _DAILY_CACHE = {}
        _CACHE_DATE  = today
    return _DAILY_CACHE.get(key)


def _cache_set(key: str, value):
    today = date.today().strftime("%Y-%m-%d")
    global _CACHE_DATE, _DAILY_CACHE
    if _CACHE_DATE != today:
        _DAILY_CACHE = {}
        _CACHE_DATE  = today
    _DAILY_CACHE[key] = value


def is_odds_blocked() -> bool:
    return _ODDS_BLOCKED


def _get(endpoint: str, params: dict,
         cache_key: str = "") -> list | dict | None:
    """
    קריאה ל-Odds API עם:
    - cache יומי אם cache_key נמסר
    - עצירה מיידית על 429 / 401 / 403
    """
    global _ODDS_BLOCKED, _BLOCKED_REASON

    if _ODDS_BLOCKED:
        print(f"[OddsAPI] ⛔ חסום: {_BLOCKED_REASON}", flush=True)
        return None

    if not ODDS_API_KEY:
        print("[OddsAPI] ❌ ODDS_API_KEY חסר", flush=True)
        return None

    if cache_key:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    url              = f"{BASE_URL}/{endpoint}"
    params["apiKey"] = ODDS_API_KEY
    try:
        res       = requests.get(url, params=params, timeout=10)
        remaining = res.headers.get("x-requests-remaining", "?")
        used      = res.headers.get("x-requests-used", "?")
        print(f"[OddsAPI] קריאות: used={used} remaining={remaining}", flush=True)

        # עצירה מיידית — Rate Limit
        if res.status_code == 429:
            _ODDS_BLOCKED    = True
            _BLOCKED_REASON  = "Rate Limit (429)"
            print("[OddsAPI] ⛔ RATE LIMIT! הסריקה נעצרת.", flush=True)
            return None

        # עצירה מיידית — Key שגוי
        if res.status_code in (401, 403):
            _ODDS_BLOCKED    = True
            _BLOCKED_REASON  = f"API Key לא תקין ({res.status_code})"
            print("[OddsAPI] ⛔ API KEY שגוי! הסריקה נעצרת.", flush=True)
            return None

        # sport key לא קיים — ממשיך בשקט
        if res.status_code == 422:
            return None

        res.raise_for_status()
        data = res.json()

        if cache_key and data:
            _cache_set(cache_key, data)

        return data if data else None

    except requests.RequestException as e:
        print(f"[OddsAPI] שגיאת רשת: {e}", flush=True)
        return None


def _sport_has_draw(sport_key: str) -> bool:
    """
    כדורגל (soccer_*) = תמיד 3-way.
    כל שאר = 2-way ללא תיקו.
    """
    return sport_key.startswith("soccer_")


def get_all_available_sports() -> list[dict]:
    """
    מגלה דינמית את כל ענפי הספורט הפעילים.
    Cache יומי — קריאה אחת בלבד ביום.
    מחזיר: [{"key", "title", "has_draw", "group"}, ...]
    """
    global _SPORTS_CACHE

    cached = _cache_get("all_sports")
    if cached:
        return cached

    data = _get("sports", {"all": "false"}, cache_key="all_sports")
    if not data or not isinstance(data, list):
        print("[OddsAPI] ⚠️ לא ניתן לטעון רשימת ספורט", flush=True)
        return _SPORTS_CACHE  # fallback לcache קודם

    sports = []
    for s in data:
        if not s.get("active", False):
            continue
        key = s.get("key", "")
        sports.append({
            "key":      key,
            "title":    s.get("title", key),
            "group":    s.get("group", ""),
            "has_draw": _sport_has_draw(key),
        })

    print(f"[OddsAPI] {len(sports)} ענפי ספורט פעילים", flush=True)
    soccer = sum(1 for s in sports if s["has_draw"])
    print(f"[OddsAPI]   כדורגל (3-way): {soccer} | ספורט אחר (2-way): {len(sports)-soccer}", flush=True)

    _SPORTS_CACHE = sports
    return sports


def _get_events() -> list:
    """
    מגלה דינמית ואוסף משחקים מכל ענפי הספורט הפעילים.
    Cache יומי לכל sport_key.
    כל event מתויג _sport_key ו-_has_draw.
    עוצר אם ה-API חסום.
    """
    sports     = get_all_available_sports()
    all_events = {}

    # fallback אם get_all_available_sports החזיר ריק
    if not sports:
        print("[OddsAPI] ⚠️ רשימת ספורט ריקה — משתמש ב-fallback", flush=True)
        sports = [
            {"key": "soccer_fifa_world_cup",    "has_draw": True},
            {"key": "soccer_international",      "has_draw": True},
            {"key": "soccer_usa_mls",            "has_draw": True},
            {"key": "soccer_epl",                "has_draw": True},
            {"key": "tennis_atp",                "has_draw": False},
            {"key": "baseball_mlb",              "has_draw": False},
            {"key": "basketball_nba",            "has_draw": False},
        ]

    for sport_info in sports:
        if _ODDS_BLOCKED:
            print("[OddsAPI] ⛔ חסום — עוצר איסוף events", flush=True)
            break

        sport_key = sport_info.get("key", "")
        has_draw  = sport_info.get("has_draw", True)
        if not sport_key:
            continue

        ck = f"events_{sport_key}"

        # EU/UK — Decimal (כדורגל + ספורט בינלאומי)
        # לא שומרים cache אם אין bookmakers — כדי לאפשר fallback ל-US
        data = _get(f"sports/{sport_key}/odds", {
            "regions":    "eu,uk",
            "markets":    "h2h",
            "oddsFormat": "decimal",
        }, cache_key="")  # ללא cache — מונע שמירת נתונים ריקים

        has_eu_books = bool(data and any(e.get("bookmakers") for e in data))
        if has_eu_books:
            _cache_set(ck, data)  # שמור cache רק אם יש bookmakers

        # אם אין bookmakers אירופאיים — נסה US (NFL/MLB/NBA/MMA)
        if not has_eu_books:
            data_us = _get(f"sports/{sport_key}/odds", {
                "regions":    "us",
                "markets":    "h2h",
                "oddsFormat": "decimal",
            }, cache_key=f"{ck}_us")
            if data_us and any(e.get("bookmakers") for e in data_us):
                data = data_us

        if data and isinstance(data, list) and len(data) > 0:
            print(f"[OddsAPI] ✅ {sport_key}: {len(data)} משחקים", flush=True)
            for event in data:
                eid = event.get("id")
                if eid and eid not in all_events:
                    event["_sport_key"] = sport_key
                    event["_has_draw"]  = has_draw
                    all_events[eid] = event

    result = list(all_events.values())
    if result:
        print(f"[OddsAPI] סה\"כ: {len(result)} משחקים ייחודיים", flush=True)
    return result


def _find_event(data: list, home_team: str, away_team: str) -> dict | None:
    home_words = set(home_team.lower().split())
    away_words = set(away_team.lower().split())
    for event in data:
        eh = event.get("home_team", "").lower()
        ea = event.get("away_team", "").lower()
        home_match = bool(home_words & set(eh.split())) or home_team.lower() in eh or eh in home_team.lower()
        away_match = bool(away_words & set(ea.split())) or away_team.lower() in ea or ea in away_team.lower()
        if home_match and away_match:
            return event
    return None


def _to_decimal(odd) -> float:
    odd = float(odd)
    if odd == int(odd) and abs(odd) >= 100:
        if odd > 0: return round((odd / 100) + 1, 3)
        else:       return round((100 / abs(odd)) + 1, 3)
    return round(odd, 3)


def _extract_odds(event: dict) -> list[dict]:
    """
    מחלץ odds מכל הבוקמייקרים.
    תומך אוטומטית ב-3-way (draw קיים) וב-2-way (draw לא קיים).
    """
    all_books      = []
    home_team_name = event.get("home_team", "").lower()
    away_team_name = event.get("away_team", "").lower()
    has_draw       = event.get("_has_draw", True)

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

            if has_draw:
                if not (raw_home and raw_away and raw_draw):
                    continue
            else:
                if not (raw_home and raw_away):
                    continue

            home_d = _to_decimal(raw_home)
            away_d = _to_decimal(raw_away)
            draw_d = _to_decimal(raw_draw) if raw_draw else 0.0

            check = [home_d, away_d] + ([draw_d] if has_draw and draw_d > 0 else [])
            if any(x < 1.01 or x > 50 for x in check):
                continue

            all_books.append({
                "name":        bm_title,
                "key":         bm_key,
                "home":        home_d,
                "draw":        draw_d,
                "away":        away_d,
                "last_update": market.get("last_update", ""),
                "has_draw":    has_draw,
            })

    return all_books


def get_all_odds_batch() -> dict:
    """
    קריאה דינמית אחת לכל ענפי הספורט הפעילים.
    מחזיר מילון {(home_team, away_team): odds_dict}.
    כל ערך כולל has_draw לזיהוי 2-way/3-way.
    Cache יומי לכל sport_key.
    """
    data = _get_events()
    if not data:
        return {}

    batch = {}
    for event in data:
        h        = event.get("home_team", "")
        a        = event.get("away_team", "")
        has_draw = event.get("_has_draw", True)
        books    = _extract_odds(event)
        if not books:
            continue

        valid = [
            b for b in books
            if 1.01 <= b["home"] <= 100 and 1.01 <= b["away"] <= 100
            and (not has_draw or 1.01 <= b["draw"] <= 25)
        ]
        if not valid:
            continue

        best_home = max(valid, key=lambda b: b["home"])
        best_draw = max(valid, key=lambda b: b["draw"]) if has_draw else None
        best_away = max(valid, key=lambda b: b["away"])

        odds_result = {
            "home":         best_home["home"],
            "home_book":    best_home["name"],
            "draw":         best_draw["draw"] if best_draw else 0.0,
            "draw_book":    best_draw["name"] if best_draw else "",
            "away":         best_away["away"],
            "away_book":    best_away["name"],
            "last_update":  best_home.get("last_update", ""),
            "has_draw":     has_draw,
            "sport_key":    event.get("_sport_key", ""),
            "is_best_line": True,
        }

        batch[(h, a)]                 = odds_result
        batch[(h.lower(), a.lower())] = odds_result

    # DEBUG — show NFL events bookmakers
    nfl_events = [e for e in data if e.get("_sport_key","").startswith("americanfootball_nfl")]
    if nfl_events:
        e = nfl_events[0]
        books = e.get("bookmakers", [])
        print(f"[OddsAPI DEBUG] NFL event: {e.get('home_team')} vs {e.get('away_team')}", flush=True)
        print(f"[OddsAPI DEBUG] bookmakers count: {len(books)}", flush=True)
        if books:
            b = books[0]
            print(f"[OddsAPI DEBUG] first book: {b.get('key')} markets: {[m['key'] for m in b.get('markets',[])]}",flush=True)
            for m in b.get('markets',[]):
                if m['key']=='h2h':
                    print(f"[OddsAPI DEBUG] h2h outcomes: {[(o['name'],o['price']) for o in m.get('outcomes',[])]}", flush=True)
    else:
        print("[OddsAPI DEBUG] ❌ אין NFL events בכלל אחרי _get_events!", flush=True)

    print(f"[OddsAPI] Batch: {len(data)} משחקים → {len(batch)//2} עם odds", flush=True)
    return batch


def lookup_odds_from_batch(batch: dict, home_team: str, away_team: str) -> dict | None:
    """
    שולף odds ממילון ה-batch.
    חיפוש מדויק → חיפוש גמיש לפי מילים.
    """
    key = (home_team.lower(), away_team.lower())
    if key in batch:
        return batch[key]

    home_words = set(home_team.lower().split())
    away_words = set(away_team.lower().split())
    for (bh, ba), odds in batch.items():
        if bool(home_words & set(bh.split())) and bool(away_words & set(ba.split())):
            return odds
    return None


def get_live_odds(home_team: str, away_team: str) -> dict | None:
    data = _get_events()
    if not data:
        return None
    event = _find_event(data, home_team, away_team)
    if not event:
        return None
    all_books = _extract_odds(event)
    if not all_books:
        return None
    best_odds     = None
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
                "has_draw":    book["has_draw"],
                "all_books":   all_books,
            }
    return best_odds


def get_best_odds(home_team: str, away_team: str) -> dict | None:
    result = get_live_odds(home_team, away_team)
    if not result or not result.get("all_books"):
        return result
    all_books = result["all_books"]
    best_home = max(all_books, key=lambda b: b["home"])
    best_draw = max(all_books, key=lambda b: b["draw"]) if result.get("has_draw") else None
    best_away = max(all_books, key=lambda b: b["away"])
    return {
        "home":         best_home["home"],
        "home_book":    best_home["name"],
        "draw":         best_draw["draw"] if best_draw else 0.0,
        "draw_book":    best_draw["name"] if best_draw else "",
        "away":         best_away["away"],
        "away_book":    best_away["name"],
        "last_update":  best_home["last_update"],
        "has_draw":     result.get("has_draw", True),
        "all_books":    all_books,
        "is_best_line": True,
    }


def list_available_matches() -> list[str]:
    data = _get_events()
    return [
        f"{e.get('home_team')} vs {e.get('away_team')} "
        f"({e.get('_sport_key','?')}) {e.get('commence_time','')[:10]}"
        for e in data
    ]
