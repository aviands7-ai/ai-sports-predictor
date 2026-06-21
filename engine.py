"""
engine.py — ליבת המודל המתמטי
Elo Rating + Poisson Distribution + Kelly Criterion + Closing Line Value
"""

import math
from scipy.stats import poisson


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
    home_advantage=0 במגרש נייטרלי (מונדיאל), ~50 בליגה רגילה.
    status: 'FT' | 'AET' | 'PEN'
    """
    adj_home = elo_home + home_advantage
    exp_home = expected_score(adj_home, elo_away)
    exp_away = 1.0 - exp_home

    if status == "PEN":
        # פנדלים = תיקו למטרות Elo (שני הצדדים הוכיחו שוויון)
        actual_home, actual_away = 0.5, 0.5
    elif home_goals > away_goals:
        actual_home, actual_away = 1.0, 0.0
    elif home_goals < away_goals:
        actual_home, actual_away = 0.0, 1.0
    else:
        actual_home, actual_away = 0.5, 0.5

    new_home = round(elo_home + k * (actual_home - exp_home), 1)
    new_away = round(elo_away + k * (actual_away - exp_away), 1)
    return new_home, new_away


# ─── Poisson ───────────────────────────────────────────────────────────────────

def expected_goals(elo_home: float, elo_away: float,
                   home_advantage: float = 0.0,
                   league_avg_goals: float = 1.3) -> tuple[float, float]:
    """
    מחשב שערים צפויים לכל קבוצה לפי הפרש Elo.
    league_avg_goals: ממוצע שערים לקבוצה בטורניר (מונדיאל ≈ 1.2–1.4).
    """
    elo_diff = (elo_home + home_advantage) - elo_away
    xg_home = max(0.1, league_avg_goals + (elo_diff / 250))
    xg_away = max(0.1, league_avg_goals - (elo_diff / 250))
    return round(xg_home, 3), round(xg_away, 3)


def match_probabilities(elo_home: float, elo_away: float,
                        home_advantage: float = 0.0,
                        max_goals: int = 6) -> dict:
    """
    מחשב הסתברויות ניצחון/תיקו/הפסד + כל תוצאה אפשרית לפי Poisson.
    מחזיר dict עם 'home', 'draw', 'away' ו-'score_matrix'.
    """
    xg_h, xg_a = expected_goals(elo_home, elo_away, home_advantage)

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
    """מחזיר את התוצאות הסבירות ביותר לפי הסתברות."""
    sorted_scores = sorted(score_matrix.items(), key=lambda x: x[1], reverse=True)
    return [(score, round(prob * 100, 1)) for score, prob in sorted_scores[:top_n]]


# ─── Kelly Criterion ───────────────────────────────────────────────────────────

def implied_probability(odds: float) -> float:
    """המרת יחס עשרוני להסתברות משתמעת (כולל margin של הבית)."""
    if odds <= 1.0:
        return 1.0
    return 1.0 / odds


def overround(odds_home: float, odds_draw: float, odds_away: float) -> float:
    """חישוב ה-margin של אתר ההימורים (Overround / Vig)."""
    total_implied = implied_probability(odds_home) + implied_probability(odds_draw) + implied_probability(odds_away)
    return round((total_implied - 1.0) * 100, 2)


def fair_odds(our_prob: float) -> float:
    """היחס ה'הוגן' ללא margin."""
    if our_prob <= 0:
        return 0.0
    return round(1.0 / our_prob, 3)


def expected_value(our_prob: float, odds: float) -> float:
    """
    EV = (הסתברות_שלנו × יחס) - 1
    EV > 0 = יתרון מתמטי. EV < 0 = נגדנו.
    """
    if odds <= 1.0 or our_prob <= 0:
        return 0.0
    return round((our_prob * odds) - 1.0, 4)


def kelly_fraction(our_prob: float, odds: float,
                   fraction: float = 0.25,
                   max_bet: float = 0.05) -> float:
    """
    קריטריון קלי מחולק (Fractional Kelly).
    fraction=0.25 = Quarter-Kelly — האסטרטגיה המומלצת לרוב המהמרים המקצועיים.
    max_bet = מקסימום % מהתקציב על הימור בודד.
    מחזיר 0 אם EV ≤ 0.
    """
    ev = expected_value(our_prob, odds)
    if ev <= 0:
        return 0.0

    b = odds - 1.0
    q = 1.0 - our_prob
    full_kelly = (our_prob * b - q) / b
    safe = min(full_kelly * fraction, max_bet)
    return round(max(safe, 0.0), 4)


def closing_line_value(our_prob: float, closing_odds: float) -> float:
    """
    Closing Line Value (CLV) — הבדיקה האמיתית של מהמר מקצועי.
    השוואת ההסתברות שלנו לסגירת השוק.
    CLV חיובי = המודל שלנו מנצח את השוק.
    """
    closing_prob = implied_probability(closing_odds)
    return round(our_prob - closing_prob, 4)


# ─── Value Analysis ─────────────────────────────────────────────────────────────

def full_match_analysis(elo_home: float, elo_away: float,
                        odds: dict,
                        home_advantage: float = 0.0) -> dict:
    """
    ניתוח מלא של משחק: הסתברויות + EV + Kelly + יחס הוגן.
    odds = {"home": float, "draw": float, "away": float}
    """
    probs = match_probabilities(elo_home, elo_away, home_advantage)

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

    results["overround"] = overround(odds.get("home", 1), odds.get("draw", 1), odds.get("away", 1))
    results["xg_home"] = probs["xg_home"]
    results["xg_away"] = probs["xg_away"]
    results["top_scores"] = most_likely_scores(probs["score_matrix"])

    return results
