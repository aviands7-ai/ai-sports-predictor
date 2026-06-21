"""
decision_engine.py — מנוע החלטה מתקדם
ניתוח פונדמנטלי מלא + המלצת השקעה ברורה
"""

import math
from api_client import get_team_last_matches


# ─── קודי מדינות ISO לדגלים ────────────────────────────────────────────────────
COUNTRY_CODE_MAP = {
    "argentina": "ar", "australia": "au", "austria": "at",
    "belgium": "be", "bolivia": "bo", "bosnia": "ba", "brazil": "br",
    "cameroon": "cm", "canada": "ca", "cape verde": "cv", "cape verde islands": "cv",
    "chile": "cl", "colombia": "co", "congo": "cd", "congo dr": "cd",
    "costa rica": "cr", "croatia": "hr",
    "czechia": "cz", "czech republic": "cz", "denmark": "dk",
    "ecuador": "ec", "egypt": "eg", "england": "gb-eng",
    "france": "fr", "germany": "de", "ghana": "gh",
    "haiti": "ht", "honduras": "hn", "hungary": "hu",
    "iran": "ir", "iraq": "iq", "ivory coast": "ci",
    "jamaica": "jm", "japan": "jp", "jordan": "jo",
    "mexico": "mx", "morocco": "ma",
    "netherlands": "nl", "new zealand": "nz", "nigeria": "ng", "norway": "no",
    "panama": "pa", "paraguay": "py", "peru": "pe", "poland": "pl",
    "portugal": "pt", "qatar": "qa",
    "saudi arabia": "sa", "scotland": "gb-sct", "senegal": "sn",
    "serbia": "rs", "south africa": "za", "south korea": "kr",
    "spain": "es", "sweden": "se", "switzerland": "ch",
    "tunisia": "tn", "turkey": "tr", "türkiye": "tr",
    "ukraine": "ua", "uruguay": "uy", "usa": "us",
    "uzbekistan": "uz", "venezuela": "ve", "wales": "gb-wls",
    "curaçao": "cw", "el salvador": "sv", "algeria": "dz",
    "austria": "at", "norway": "no", "bosnia & herzegovina": "ba",
    "korea republic": "kr", "united states": "us",
}

def get_flag_url(team_name: str) -> str:
    """מחזיר URL לתמונת דגל מ-flagcdn.com"""
    name = team_name.lower().strip()
    # חיפוש מדויק
    if name in COUNTRY_CODE_MAP:
        code = COUNTRY_CODE_MAP[name]
        return f"https://flagcdn.com/w80/{code}.png"
    # חיפוש חלקי
    for key, code in COUNTRY_CODE_MAP.items():
        if key in name or name in key:
            return f"https://flagcdn.com/w80/{code}.png"
    return ""

def get_flag(team_name: str) -> str:
    """Fallback — emoji אם אין URL"""
    return ""


# ─── ניתוח 5 משחקים אחרונים ────────────────────────────────────────────────────

def analyze_recent_form(matches: list[dict], team_id: int) -> dict:
    """
    ניתוח מעמיק של 5 משחקים אחרונים.
    מחזיר: form_string, goals_scored, goals_conceded, win_streak, trend
    """
    if not matches:
        return {
            "form_string": "N/A",
            "results": [],
            "goals_scored": 0,
            "goals_conceded": 0,
            "avg_scored": 0,
            "avg_conceded": 0,
            "win_streak": 0,
            "clean_sheets": 0,
            "trend": "unknown",
            "efficiency": 0,
        }

    results = []
    goals_scored = []
    goals_conceded = []

    for match in matches[-5:]:
        home_id    = match["teams"]["home"]["id"]
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        is_home    = (home_id == team_id)

        gf = home_goals if is_home else away_goals
        ga = away_goals if is_home else home_goals
        goals_scored.append(gf)
        goals_conceded.append(ga)

        status = match["fixture"]["status"]["short"]
        if status == "PEN":
            results.append("D")
        elif gf > ga:
            results.append("W")
        elif gf == ga:
            results.append("D")
        else:
            results.append("L")

    # Win streak (מהמשחק האחרון אחורה)
    streak = 0
    for r in reversed(results):
        if r == "W":
            streak += 1
        else:
            break

    # מגמה — השווה 2 ראשונים ל-2 אחרונים
    points = {"W": 3, "D": 1, "L": 0}
    early = sum(points[r] for r in results[:2]) if len(results) >= 2 else 0
    late  = sum(points[r] for r in results[-2:]) if len(results) >= 2 else 0
    if late > early:
        trend = "rising"
    elif late < early:
        trend = "falling"
    else:
        trend = "stable"

    avg_scored    = round(sum(goals_scored) / len(goals_scored), 2) if goals_scored else 0
    avg_conceded  = round(sum(goals_conceded) / len(goals_conceded), 2) if goals_conceded else 0
    clean_sheets  = sum(1 for g in goals_conceded if g == 0)

    # יעילות = שערים שקלע / (שערים שקלע + שקיבל)
    total = sum(goals_scored) + sum(goals_conceded)
    efficiency = round(sum(goals_scored) / total * 100) if total > 0 else 50

    return {
        "form_string": " ".join(results),
        "results":     results,
        "goals_scored": sum(goals_scored),
        "goals_conceded": sum(goals_conceded),
        "avg_scored":   avg_scored,
        "avg_conceded": avg_conceded,
        "win_streak":   streak,
        "clean_sheets": clean_sheets,
        "trend":        trend,
        "efficiency":   efficiency,
        "games":        len(results),
    }


# ─── ציון כולל לכל קבוצה ────────────────────────────────────────────────────────

def calculate_team_score(elo: float, form: dict, form_factor: float) -> dict:
    """
    מחשב ציון כולל (0-100) מ-4 קטגוריות:
    - עוצמה (Elo) 35%
    - טופס אחרון 25%
    - התקפה 20%
    - הגנה 20%
    """
    # עוצמה — Elo מנורמל (1400-1900 → 0-100)
    elo_score = max(0, min(100, (elo - 1400) / 5))

    # טופס — points מ-5 משחקים (מקס 15)
    points = {"W": 3, "D": 1, "L": 0}
    form_points = sum(points.get(r, 0) for r in form.get("results", []))
    form_score  = (form_points / 15) * 100 if form.get("results") else 50

    # התקפה — ממוצע שערים (0-3+ → 0-100)
    attack_score = min(100, form.get("avg_scored", 0) * 33)

    # הגנה — הפוך (פחות שערים = ציון גבוה)
    defense_score = max(0, 100 - form.get("avg_conceded", 1.5) * 40)

    total = (
        elo_score    * 0.35 +
        form_score   * 0.25 +
        attack_score * 0.20 +
        defense_score * 0.20
    )

    return {
        "total":   round(total, 1),
        "elo":     round(elo_score, 1),
        "form":    round(form_score, 1),
        "attack":  round(attack_score, 1),
        "defense": round(defense_score, 1),
    }


# ─── המלצת השקעה ─────────────────────────────────────────────────────────────────

def generate_decision(
    home_name: str, away_name: str,
    home_score: dict, away_score: dict,
    home_form: dict, away_form: dict,
    probs: dict, fair_odds: dict,
    live_odds: dict | None,
    elo_home: float, elo_away: float,
) -> dict:
    """
    מייצר המלצת השקעה מנומקת.
    """
    # קבע מועדף
    score_diff = home_score["total"] - away_score["total"]
    prob_home  = probs.get("home", 0)
    prob_away  = probs.get("away", 0)
    prob_draw  = probs.get("draw", 0)

    # מנצח צפוי
    if prob_home > prob_away + 10:
        winner = "home"
        winner_name = home_name
        winner_prob = prob_home
    elif prob_away > prob_home + 10:
        winner = "away"
        winner_name = away_name
        winner_prob = prob_away
    else:
        winner = "draw"
        winner_name = "תיקו"
        winner_prob = prob_draw

    # רמת ביטחון
    score_gap = abs(score_diff)
    if score_gap >= 20 and winner_prob >= 60:
        confidence = "גבוה"
        confidence_color = "#16a34a"
        confidence_emoji = "🟢"
    elif score_gap >= 10 and winner_prob >= 50:
        confidence = "בינוני"
        confidence_color = "#d97706"
        confidence_emoji = "🟡"
    else:
        confidence = "נמוך"
        confidence_color = "#dc2626"
        confidence_emoji = "🔴"

    # נימוקים
    reasons = []

    # Elo
    elo_diff = abs(elo_home - elo_away)
    if elo_diff >= 50:
        stronger = home_name if elo_home > elo_away else away_name
        reasons.append(f"פער עוצמה של {elo_diff:.0f} נקודות Elo לטובת {stronger}")

    # טופס
    home_pts = sum({"W":3,"D":1,"L":0}.get(r,0) for r in home_form.get("results",[]))
    away_pts = sum({"W":3,"D":1,"L":0}.get(r,0) for r in away_form.get("results",[]))
    if home_pts > away_pts + 3:
        reasons.append(f"{home_name} בטופס עדיף ({home_pts}/15 נקודות)")
    elif away_pts > home_pts + 3:
        reasons.append(f"{away_name} בטופס עדיף ({away_pts}/15 נקודות)")

    # מגמה
    if home_form.get("trend") == "rising" and winner == "home":
        reasons.append(f"{home_name} במגמת עלייה")
    if away_form.get("trend") == "rising" and winner == "away":
        reasons.append(f"{away_name} במגמת עלייה")

    # ניצחונות ברצף
    if home_form.get("win_streak", 0) >= 3 and winner == "home":
        reasons.append(f"{home_form['win_streak']} ניצחונות ברצף ל-{home_name}")
    if away_form.get("win_streak", 0) >= 3 and winner == "away":
        reasons.append(f"{away_form['win_streak']} ניצחונות ברצף ל-{away_name}")

    # הגנה
    if home_form.get("clean_sheets", 0) >= 2 and winner == "home":
        reasons.append(f"{home_name} שמרה על שער נקי {home_form['clean_sheets']} פעמים")
    if away_form.get("clean_sheets", 0) >= 2 and winner == "away":
        reasons.append(f"{away_name} שמרה על שער נקי {away_form['clean_sheets']} פעמים")

    # Value Bet
    bet_recommendation = None
    if live_odds:
        for outcome in ["home", "draw", "away"]:
            odd = live_odds.get(outcome, 0)
            fair = fair_odds.get(outcome, 0)
            if odd > 0 and fair > 0 and odd > fair * 1.05:
                ev = (probs.get(outcome, 0) / 100 * odd) - 1
                if ev > 0.03:
                    outcome_name = {"home": f"{home_name} מנצחת", "draw": "תיקו", "away": f"{away_name} מנצחת"}[outcome]
                    kelly = min(ev / (odd - 1) * 0.25, 0.05) * 100
                    bet_recommendation = {
                        "outcome": outcome_name,
                        "odds": odd,
                        "ev": round(ev * 100, 1),
                        "kelly": round(kelly, 1),
                        "edge": round((odd / fair - 1) * 100, 1),
                    }
                    break

    # סיכונים
    risks = []
    if confidence == "נמוך":
        risks.append("משחק מאוזן — תוצאה פתוחה")
    if home_form.get("trend") == "falling" and winner == "home":
        risks.append(f"{home_name} במגמת ירידה")
    if away_form.get("trend") == "falling" and winner == "away":
        risks.append(f"{away_name} במגמת ירידה")
    if not live_odds:
        risks.append("אין odds זמינים — לא ניתן לאמת Value")
    if abs(prob_home - prob_away) < 15:
        risks.append("הפרש הסתברויות קטן — אל תסכן יותר מ-2%")

    return {
        "winner":           winner,
        "winner_name":      winner_name,
        "winner_prob":      winner_prob,
        "confidence":       confidence,
        "confidence_color": confidence_color,
        "confidence_emoji": confidence_emoji,
        "reasons":          reasons[:4],  # מקס 4 נימוקים
        "risks":            risks[:3],
        "bet_recommendation": bet_recommendation,
        "score_diff":       score_diff,
    }