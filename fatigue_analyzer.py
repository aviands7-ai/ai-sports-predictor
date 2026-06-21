"""
fatigue_analyzer.py — פיתוח #5: ניתוח עייפות וסיבוב
מחשב ימי מנוחה בין משחקים ומשפיע על xG
"""

from datetime import datetime, timedelta
from api_client import get_team_last_matches


def days_since_last_match(matches: list[dict]) -> int | None:
    """מחשב כמה ימים עברו מהמשחק האחרון."""
    if not matches:
        return None
    last = sorted(matches, key=lambda x: x["fixture"]["timestamp"], reverse=True)[0]
    last_date_str = last["fixture"]["date"][:10]
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    days = (datetime.now() - last_date).days
    return max(0, days)


def calculate_fatigue_factor(days_rest: int | None) -> dict:
    """
    מחשב מקדם עייפות (0.88 - 1.0):
    0-2 ימים = עייפות גבוהה (0.88)
    3-4 ימים = עייפות בינונית (0.94)
    5+ ימים   = מנוחה מספקת (1.0)
    None      = לא ידוע (1.0)
    """
    if days_rest is None:
        return {"factor": 1.0, "label": "לא ידוע", "days": None, "color": "#6b7280"}
    if days_rest <= 2:
        return {"factor": 0.88, "label": f"עייפות גבוהה ({days_rest} ימים)", "days": days_rest, "color": "#dc2626"}
    elif days_rest <= 4:
        return {"factor": 0.94, "label": f"עייפות בינונית ({days_rest} ימים)", "days": days_rest, "color": "#d97706"}
    else:
        return {"factor": 1.0,  "label": f"מנוחה מספקת ({days_rest} ימים)", "days": days_rest, "color": "#16a34a"}


def get_fatigue_summary(home_id: int, away_id: int) -> dict:
    """מחשב עייפות לשתי הקבוצות."""
    last_h = get_team_last_matches(home_id, last=3)
    last_a = get_team_last_matches(away_id, last=3)

    days_h = days_since_last_match(last_h)
    days_a = days_since_last_match(last_a)

    fatigue_h = calculate_fatigue_factor(days_h)
    fatigue_a = calculate_fatigue_factor(days_a)

    # יתרון יחסי — אם קבוצה A נחה יותר, היא תקבל bonus
    relative_advantage = None
    if days_h is not None and days_a is not None:
        diff = days_h - days_a
        if diff >= 3:
            relative_advantage = "home"
        elif diff <= -3:
            relative_advantage = "away"

    return {
        "home": fatigue_h,
        "away": fatigue_a,
        "relative_advantage": relative_advantage,
    }