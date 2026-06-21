"""
lineup_analyzer.py — ניתוח הרכב שחקנים
פיתוח #1: השפעת שחקנים חסרים על התחזית
"""

from api_client import _get


# ─── דירוג חשיבות שחקנים לפי עמדה ────────────────────────────────────────────
# מייצג כמה % מה-xG של הקבוצה תלוי בעמדה זו
POSITION_WEIGHT = {
    "G":  0.08,   # שוער — משפיע על הגנה
    "D":  0.06,   # בלם
    "M":  0.08,   # קשר
    "F":  0.12,   # חלוץ — השפעה הכי גדולה
}

# שחקני כוכב ידועים ומשקלם היחסי (0-1)
# 1.0 = הקבוצה תלויה בו לחלוטין
STAR_PLAYERS = {
    # France
    "K. Mbappé":       0.35,
    "A. Griezmann":    0.20,
    "O. Dembélé":      0.15,
    # Brazil
    "Vinicius Junior": 0.30,
    "Rodrygo":         0.18,
    "Raphinha":        0.15,
    # Argentina
    "L. Messi":        0.40,
    "J. Álvarez":      0.18,
    "Enzo Fernández":  0.12,
    # England
    "J. Bellingham":   0.25,
    "H. Kane":         0.28,
    "P. Foden":        0.18,
    # Portugal
    "C. Ronaldo":      0.30,
    "B. Fernandes":    0.20,
    "R. Leão":         0.15,
    # Netherlands
    "V. van Dijk":     0.15,
    "X. Simons":       0.20,
    "C. Gakpo":        0.18,
    # Germany
    "F. Wirtz":        0.25,
    "K. Havertz":      0.18,
    "J. Musiala":      0.22,
    # Spain
    "P. Pedri":        0.20,
    "A. Yamal":        0.25,
    "M. Morata":       0.18,
    # Morocco
    "A. Hakimi":       0.20,
    "H. Ziyech":       0.18,
    # Japan
    "Takefusa Kubo":   0.22,
    "Ritsu Doan":      0.18,
}


def get_lineup(fixture_id: int) -> dict | None:
    """
    שואב הרכב מאושר או הרכב צפוי מה-API.
    מחזיר {"home": [...players], "away": [...players]} או None.
    """
    data = _get("fixtures/lineups", {"fixture": fixture_id})
    response = data.get("response", [])
    if not response:
        return None

    result = {}
    for team_data in response:
        team_id = team_data["team"]["id"]
        side = "home" if team_data.get("team", {}).get("id") == team_data["team"]["id"] else "away"
        players = []
        for p in team_data.get("startXI", []):
            players.append({
                "name": p["player"]["name"],
                "position": p["player"]["pos"],
                "number": p["player"]["number"],
            })
        result[side] = players

    # API מחזיר לפי סדר — ראשון=home, שני=away
    if len(response) >= 2:
        result["home"] = []
        result["away"] = []
        for p in response[0].get("startXI", []):
            result["home"].append({
                "name": p["player"]["name"],
                "position": p["player"]["pos"],
            })
        for p in response[1].get("startXI", []):
            result["away"].append({
                "name": p["player"]["name"],
                "position": p["player"]["pos"],
            })

    return result if result else None


def get_missing_players(fixture_id: int, home_id: int, away_id: int) -> dict:
    """
    מחשב שחקנים חסרים מהרכב רגיל לעומת פציעות.
    מחזיר רשימת שחקנים חסרים לכל קבוצה.
    """
    from api_client import get_injuries
    injuries = get_injuries(fixture_id)

    missing_home = []
    missing_away = []

    for inj in injuries:
        player_name = inj["player"]["name"]
        team_id = inj["team"]["id"]
        reason = inj["player"].get("reason", "פציעה")

        player_info = {
            "name": player_name,
            "reason": reason,
            "impact": STAR_PLAYERS.get(player_name, 0),
        }

        if team_id == home_id:
            missing_home.append(player_info)
        elif team_id == away_id:
            missing_away.append(player_info)

    return {"home": missing_home, "away": missing_away}


def calculate_lineup_factor(missing_players: list[dict]) -> float:
    """
    מחשב מקדם הרכב (0.7 - 1.0):
    1.0 = הרכב מלא
    0.7 = כל הכוכבים חסרים

    missing_players: רשימת שחקנים חסרים עם impact score
    """
    if not missing_players:
        return 1.0

    total_impact = sum(p.get("impact", 0.05) for p in missing_players)
    # מוגבל ל-30% ירידה מקסימלית
    factor = max(0.70, 1.0 - min(total_impact, 0.30))
    return round(factor, 3)


def get_lineup_summary(fixture_id: int, home_id: int, away_id: int) -> dict:
    """
    סיכום מלא של ניתוח הרכב.
    מחזיר: missing, factors, has_lineup
    """
    missing = get_missing_players(fixture_id, home_id, away_id)
    lineup = get_lineup(fixture_id)

    factor_home = calculate_lineup_factor(missing["home"])
    factor_away = calculate_lineup_factor(missing["away"])

    return {
        "missing_home": missing["home"],
        "missing_away": missing["away"],
        "factor_home": factor_home,
        "factor_away": factor_away,
        "has_confirmed_lineup": lineup is not None,
        "lineup_home": lineup["home"] if lineup else [],
        "lineup_away": lineup["away"] if lineup else [],
        "total_impact_home": round(1.0 - factor_home, 3),
        "total_impact_away": round(1.0 - factor_away, 3),
    }