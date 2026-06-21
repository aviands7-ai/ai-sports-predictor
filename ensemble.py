"""
ensemble.py — פיתוח #6: Ensemble Model
ממוצע משוקלל של שלושה מקורות:
1. Elo + Poisson (המודל הנוכחי) — 50%
2. FIFA World Ranking גרסה אלטרנטיבית — 20%
3. שוק ההימורים כ"דעת הקהל" — 30%
"""

from engine import match_probabilities, implied_probability


# ─── FIFA Rankings → הסתברות ────────────────────────────────────────────────────
# דירוג FIFA מ-2026 (מקום → נקודות)
FIFA_RANKINGS = {
    "Argentina": 1, "France": 2, "England": 3, "Brazil": 4,
    "Belgium": 5, "Portugal": 6, "Spain": 7, "Netherlands": 8,
    "Germany": 9, "Croatia": 10, "Morocco": 11, "Uruguay": 12,
    "Colombia": 13, "USA": 14, "Mexico": 15, "Senegal": 16,
    "Denmark": 17, "Switzerland": 18, "Japan": 19, "South Korea": 20,
    "Ecuador": 21, "Australia": 22, "Poland": 23, "Serbia": 24,
    "Ukraine": 25, "Austria": 26, "Hungary": 27, "Turkey": 28,
    "Türkiye": 28, "Czech Republic": 29, "Sweden": 30, "Czechia": 29,
    "Chile": 31, "Paraguay": 32, "Peru": 33, "Cameroon": 34,
    "Nigeria": 35, "Ivory Coast": 36, "Algeria": 37, "Egypt": 38,
    "Tunisia": 39, "Ghana": 40, "Iran": 41, "Saudi Arabia": 42,
    "Qatar": 43, "Canada": 44, "Costa Rica": 45, "Panama": 46,
    "Jamaica": 47, "Honduras": 48, "El Salvador": 49, "Bolivia": 50,
    "New Zealand": 55, "South Africa": 60, "Iraq": 65,
    "Uzbekistan": 70, "Congo DR": 72, "Haiti": 75, "Scotland": 35,
    "Bosnia & Herzegovina": 50, "Curaçao": 80, "Cape Verde Islands": 65,
    "Jordan": 85, "Norway": 34,
}

MAX_RANK = 90


def fifa_rank_to_strength(team_name: str) -> float:
    """ממיר מקום FIFA לציון עוצמה (0-1)."""
    rank = FIFA_RANKINGS.get(team_name, MAX_RANK // 2)
    return round(1.0 - (rank - 1) / MAX_RANK, 4)


def fifa_probabilities(home_name: str, away_name: str) -> dict:
    """
    מחשב הסתברויות לפי FIFA Ranking בלבד.
    פשוט יותר מ-Elo אבל שיטה אלטרנטיבית טובה לvalidation.
    """
    s_home = fifa_rank_to_strength(home_name)
    s_away = fifa_rank_to_strength(away_name)
    total = s_home + s_away

    if total == 0:
        return {"home": 0.40, "draw": 0.25, "away": 0.35}

    # נרמול + 25% לתיקו
    raw_home = s_home / total
    raw_away = s_away / total

    draw = 0.25
    home = raw_home * 0.75
    away = raw_away * 0.75

    return {
        "home": round(home, 4),
        "draw": round(draw, 4),
        "away": round(away, 4),
    }


def market_probabilities(live_odds: dict | None) -> dict | None:
    """
    ממיר odds של השוק להסתברויות (עם נרמול ל-overround).
    מחזיר None אם אין odds.
    """
    if not live_odds:
        return None

    raw_home = implied_probability(live_odds.get("home", 0))
    raw_draw = implied_probability(live_odds.get("draw", 0))
    raw_away = implied_probability(live_odds.get("away", 0))

    total = raw_home + raw_draw + raw_away
    if total <= 0:
        return None

    return {
        "home": round(raw_home / total, 4),
        "draw": round(raw_draw / total, 4),
        "away": round(raw_away / total, 4),
    }


def ensemble_probabilities(
    elo_home: float, elo_away: float,
    home_name: str, away_name: str,
    form_home: float = 1.0, form_away: float = 1.0,
    lineup_home: float = 1.0, lineup_away: float = 1.0,
    fatigue_home: float = 1.0, fatigue_away: float = 1.0,
    live_odds: dict | None = None,
) -> dict:
    """
    Ensemble של שלושה מודלים:
    - אם יש odds: Elo 50% + FIFA 20% + Market 30%
    - אם אין odds: Elo 70% + FIFA 30%
    """
    # מודל 1 — Elo + Poisson + כל הפקטורים
    elo_probs_raw = match_probabilities(
        elo_home, elo_away,
        form_home=form_home * fatigue_home,
        form_away=form_away * fatigue_away,
        lineup_home=lineup_home,
        lineup_away=lineup_away,
    )
    elo_probs = {k: elo_probs_raw[k] for k in ["home","draw","away"]}

    # מודל 2 — FIFA Rankings
    fifa_probs = fifa_probabilities(home_name, away_name)

    # מודל 3 — שוק ההימורים (אם זמין)
    market_probs = market_probabilities(live_odds)

    if market_probs:
        weights = {"elo": 0.50, "fifa": 0.20, "market": 0.30}
        blended = {}
        for outcome in ["home", "draw", "away"]:
            blended[outcome] = round(
                elo_probs[outcome]   * weights["elo"] +
                fifa_probs[outcome]  * weights["fifa"] +
                market_probs[outcome] * weights["market"],
                4
            )
    else:
        weights = {"elo": 0.70, "fifa": 0.30}
        blended = {}
        for outcome in ["home", "draw", "away"]:
            blended[outcome] = round(
                elo_probs[outcome]  * weights["elo"] +
                fifa_probs[outcome] * weights["fifa"],
                4
            )

    # נרמול
    total = sum(blended.values())
    blended = {k: round(v / total, 4) for k, v in blended.items()}

    return {
        "ensemble": blended,
        "elo": elo_probs,
        "fifa": fifa_probs,
        "market": market_probs,
        "weights": weights,
        "has_market": market_probs is not None,
    }