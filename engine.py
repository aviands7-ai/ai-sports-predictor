"""
engine.py — ליבת המודל המתמטי v2
Elo + FIFA Starting Ratings + Form Factor + Dynamic K + Poisson + Kelly
"""

import math
from scipy.stats import poisson


# ─── FIFA-Based Starting Elo ────────────────────────────────────────────────────
# דירוג התחלתי מבוסס FIFA Ranking (יוני 2026)
# מקור: FIFA World Ranking + המרה ל-Elo scale
# קבוצות שלא ברשימה מקבלות 1400 (ברירת מחדל לקבוצות חלשות)

FIFA_STARTING_ELO = {
    # Top tier (1700-1900)
    "Argentina":       1900,
    "France":          1860,
    "England":         1820,
    "Brazil":          1810,
    "Belgium":         1780,
    "Portugal":        1770,
    "Spain":           1760,
    "Netherlands":     1750,
    "Germany":         1740,
    "Croatia":         1710,
    "Italy":           1700,
    # Strong (1600-1700)
    "Morocco":         1680,
    "Uruguay":         1660,
    "USA":             1650,
    "Colombia":        1640,
    "Mexico":          1630,
    "Senegal":         1620,
    "Denmark":         1615,
    "Switzerland":     1610,
    "Japan":           1600,
    "South Korea":     1590,
    "Ecuador":         1580,
    "Australia":       1570,
    "Poland":          1560,
    "Serbia":          1555,
    "Ukraine":         1550,
    "Austria":         1545,
    "Hungary":         1540,
    "Turkey":          1535,
    "Czech Republic":  1530,
    "Sweden":          1525,
    "Wales":           1520,
    "Chile":           1515,
    "Paraguay":        1510,
    "Peru":            1505,
    "Cameroon":        1500,
    "Nigeria":         1495,
    "Ivory Coast":     1490,
    "Algeria":         1485,
    "Egypt":           1480,
    "Tunisia":         1475,
    "Ghana":           1470,
    "Iran":            1465,
    "Saudi Arabia":    1455,
    "Qatar":           1450,
    "Canada":          1445,
    "Costa Rica":      1440,
    "Panama":          1435,
    "Jamaica":         1430,
    "Honduras":        1425,
    "El Salvador":     1420,
    "Bolivia":         1415,
    "Venezuela":       1410,
    # Weaker (below 1400)
    "New Zealand":     1390,
    "South Africa":    1385,
    "Mali":            1380,
    "Burkina Faso":    1375,
    "Cape Verde":      1370,
}

def get_starting_elo(team_name: str) -> float:
    """
    מחזיר Elo התחלתי לפי FIFA Ranking.
    מנסה match מדויק, אחר-כך partial match, אחר-כך 1400.
    """
    # exact match
    if team_name in FIFA_STARTING_ELO:
        return float(FIFA_STARTING_ELO[team_name])
    # partial match (למקרה של הבדלי שמות קלים)
    for key, val in FIFA_STARTING_ELO.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            return float(val)
    return 1400.0  # ברירת מחדל לקבוצות לא מוכרות


# ─── Dynamic K Factor ───────────────────────────────────────────────────────────

def dynamic_k(round_name: str = "") -> float:
    """
    K דינמי לפי שלב הטורניר.
    שלב מתקדם = המשחק "שווה יותר" ← K גבוה יותר.
    """
    round_lower = round_name.lower()
    if "final" in round_lower and "semi" not in round_lower:
        return 60.0   # גמר
    elif "semi" in round_lower:
        return 55.0   # חצי גמר
    elif "quarter" in round_lower:
        return 50.0   # רבע גמר
    elif "round of 16" in round_lower or "last 16" in round_lower:
        return 45.0   # שמינית גמר
    elif "group" in round_lower:
        return 40.0   # שלב בית
    return 40.0       # ברירת מחדל


# ─── Form Factor ────────────────────────────────────────────────────────────────

def calculate_form_factor(recent_matches: list[dict], team_id: int) -> float:
    """
    מחשב Form Factor מ-5 משחקים אחרונים.
    מחזיר multiplier בין 0.85 (טופס גרוע) ל-1.15 (טופס מצוין).

    recent_matches: רשימת fixtures מה-API (מסודרת מהישן לחדש).
    team_id: ה-ID של הקבוצה שאנחנו מחשבים עבורה.
    """
    if not recent_matches:
        return 1.0

    points = []
    weights = [0.10, 0.15, 0.20, 0.25, 0.30]  # משחק אחרון שווה יותר

    for i, match in enumerate(recent_matches[-5:]):
        home_id = match["teams"]["home"]["id"]
        away_id = match["teams"]["away"]["id"]
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        status = match["fixture"]["status"]["short"]

        is_home = (home_id == team_id)

        if status == "PEN":
            # פנדלים = חצי נקודה
            points.append(0.5)
        elif is_home:
            if home_goals > away_goals:
                points.append(1.0)   # ניצחון
            elif home_goals == away_goals:
                points.append(0.5)   # תיקו
            else:
                points.append(0.0)   # הפסד
        else:
            if away_goals > home_goals:
                points.append(1.0)
            elif away_goals == home_goals:
                points.append(0.5)
            else:
                points.append(0.0)

    if not points:
        return 1.0

    # weighted average
    active_weights = weights[-len(points):]
    total_weight = sum(active_weights)
    weighted_avg = sum(p * w for p, w in zip(points, active_weights)) / total_weight

    # המרה ל-multiplier: 0.0 → 0.85, 0.5 → 1.0, 1.0 → 1.15
    form_multiplier = 0.85 + (weighted_avg * 0.30)
    return round(form_multiplier, 3)


# ─── Elo ───────────────────────────────────────────────────────────────────────

def expected_score(elo_a: float, elo_b: float) -> float:
    """הסתברות שקבוצה A תנצח לפי מודל Elo."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(elo_home: float, elo_away: float,
               home_goals: int, away_goals: int,
               status: str, k: float = 40,
               home_advantage: float = 0.0) -> tuple[float, float]:
    """
    מעדכן דירוגי Elo אחרי משחק שהסתיים.
    home_advantage=0 במגרש נייטרלי (מונדיאל).
    """
    adj_home = elo_home + home_advantage
    exp_home = expected_score(adj_home, elo_away)

    if status == "PEN":
        actual_home, actual_away = 0.5, 0.5
    elif home_goals > away_goals:
        actual_home, actual_away = 1.0, 0.0
    elif home_goals < away_goals:
        actual_home, actual_away = 0.0, 1.0
    else:
        actual_home, actual_away = 0.5, 0.5

    new_home = round(elo_home + k * (actual_home - exp_home), 1)
    new_away = round(elo_away + k * (1.0 - actual_home - (1.0 - exp_home)), 1)
    return new_home, new_away


# ─── Poisson ───────────────────────────────────────────────────────────────────

def expected_goals(elo_home: float, elo_away: float,
                   home_advantage: float = 0.0,
                   league_avg_goals: float = 1.3,
                   form_home: float = 1.0,
                   form_away: float = 1.0) -> tuple[float, float]:
    """
    מחשב שערים צפויים לכל קבוצה.
    כולל Form Factor: קבוצה בטופס טוב מצפה לייצר יותר שערים.
    """
    elo_diff = (elo_home + home_advantage) - elo_away
    base_xg_home = max(0.1, league_avg_goals + (elo_diff / 250))
    base_xg_away = max(0.1, league_avg_goals - (elo_diff / 250))

    # Form Factor משפיע על ה-xG
    xg_home = round(max(0.1, base_xg_home * form_home), 3)
    xg_away = round(max(0.1, base_xg_away * form_away), 3)
    return xg_home, xg_away


def match_probabilities(elo_home: float, elo_away: float,
                        home_advantage: float = 0.0,
                        form_home: float = 1.0,
                        form_away: float = 1.0,
                        max_goals: int = 6) -> dict:
    """
    מחשב הסתברויות + score matrix לפי Poisson.
    כולל Form Factor.
    """
    xg_h, xg_a = expected_goals(
        elo_home, elo_away, home_advantage,
        form_home=form_home, form_away=form_away
    )

    home_pmf = [poisson.pmf(i, xg_h) for i in range(max_goals + 1)]
    away_pmf = [poisson.pmf(i, xg_a) for i in range(max_goals + 1)]

    home_win = draw = away_win = 0.0
    score_matrix = {}

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = home_pmf[i] * away_pmf[j]
            score_matrix[f"{i}-{j}"] = p
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p

    total = home_win + draw + away_win
    return {
        "home": round(home_win / total, 4),
        "draw": round(draw / total, 4),
        "away": round(away_win / total, 4),
        "xg_home": xg_h,
        "xg_away": xg_a,
        "score_matrix": score_matrix,
    }


def most_likely_scores(score_matrix: dict, top_n: int = 5) -> list[tuple[str, float]]:
    """מחזיר את התוצאות הסבירות ביותר."""
    sorted_scores = sorted(score_matrix.items(), key=lambda x: x[1], reverse=True)
    return [(score, round(prob * 100, 1)) for score, prob in sorted_scores[:top_n]]


# ─── Kelly Criterion ───────────────────────────────────────────────────────────

def implied_probability(odds: float) -> float:
    if odds <= 1.0:
        return 1.0
    return 1.0 / odds


def overround(odds_home: float, odds_draw: float, odds_away: float) -> float:
    total = implied_probability(odds_home) + implied_probability(odds_draw) + implied_probability(odds_away)
    return round((total - 1.0) * 100, 2)


def fair_odds(our_prob: float) -> float:
    if our_prob <= 0:
        return 0.0
    return round(1.0 / our_prob, 3)


def expected_value(our_prob: float, odds: float) -> float:
    if odds <= 1.0 or our_prob <= 0:
        return 0.0
    return round((our_prob * odds) - 1.0, 4)


def kelly_fraction(our_prob: float, odds: float,
                   fraction: float = 0.25,
                   max_bet: float = 0.05) -> float:
    ev = expected_value(our_prob, odds)
    if ev <= 0:
        return 0.0
    b = odds - 1.0
    q = 1.0 - our_prob
    full_kelly = (our_prob * b - q) / b
    safe = min(full_kelly * fraction, max_bet)
    return round(max(safe, 0.0), 4)


def closing_line_value(our_prob: float, closing_odds: float) -> float:
    closing_prob = implied_probability(closing_odds)
    return round(our_prob - closing_prob, 4)


# ─── Odds Freshness ────────────────────────────────────────────────────────────

def odds_freshness(odds_updated_at: str | None) -> dict:
    """
    בודק כמה ישנים יחסי ההימורים.
    מחזיר: status ('live'|'fresh'|'stale'|'missing'), hours_ago, label.
    """
    if not odds_updated_at:
        return {"status": "missing", "hours_ago": None, "label": "⚪ אין odds", "color": "#6b7a99"}

    from datetime import datetime, timezone
    try:
        # parse ISO format
        updated = datetime.fromisoformat(odds_updated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours_ago = (now - updated).total_seconds() / 3600

        if hours_ago < 1:
            return {"status": "live", "hours_ago": round(hours_ago, 1), "label": f"🟢 חי ({int(hours_ago*60)} דקות)", "color": "#10b981"}
        elif hours_ago < 24:
            return {"status": "fresh", "hours_ago": round(hours_ago, 1), "label": f"🟡 {round(hours_ago, 1)} שעות", "color": "#f59e0b"}
        elif hours_ago < 72:
            return {"status": "stale", "hours_ago": round(hours_ago, 1), "label": f"🟠 {int(hours_ago/24)} ימים", "color": "#ef4444"}
        else:
            return {"status": "old", "hours_ago": round(hours_ago, 1), "label": f"🔴 ישן ({int(hours_ago/24)} ימים)", "color": "#dc2626"}
    except Exception:
        return {"status": "missing", "hours_ago": None, "label": "⚪ תאריך לא ידוע", "color": "#6b7a99"}


# ─── Full Analysis ──────────────────────────────────────────────────────────────

def full_match_analysis(elo_home: float, elo_away: float,
                        odds: dict,
                        home_advantage: float = 0.0,
                        form_home: float = 1.0,
                        form_away: float = 1.0,
                        odds_updated_at: str | None = None) -> dict:
    """
    ניתוח מלא: הסתברויות + Form + EV + Kelly + Odds Freshness.
    """
    probs = match_probabilities(
        elo_home, elo_away, home_advantage,
        form_home=form_home, form_away=form_away
    )

    results = {}
    for outcome in ["home", "draw", "away"]:
        p = probs[outcome]
        o = odds.get(outcome, 0)
        ev = expected_value(p, o)
        k = kelly_fraction(p, o)
        results[outcome] = {
            "our_prob": round(p * 100, 1),
            "our_prob_raw": p,
            "odds": o,
            "implied_prob": round(implied_probability(o) * 100, 1),
            "fair_odds": fair_odds(p),
            "ev": ev,
            "kelly_pct": round(k * 100, 2),
            "is_value": ev > 0,
        }

    results["overround"] = overround(
        odds.get("home", 1), odds.get("draw", 1), odds.get("away", 1)
    )
    results["xg_home"] = probs["xg_home"]
    results["xg_away"] = probs["xg_away"]
    results["top_scores"] = most_likely_scores(probs["score_matrix"])
    results["form_home"] = round(form_home, 3)
    results["form_away"] = round(form_away, 3)
    results["odds_freshness"] = odds_freshness(odds_updated_at)

    return results
