"""
engine.py — ליבת המודל המתמטי v3
Elo + Dixon-Coles + Logistic (2-way) + Kelly + Form Factor
תומך בכדורגל (3-way + Poisson) ובספורט ללא תיקו (2-way + Logistic).
"""

import math
from scipy.stats import poisson


# ─── זיהוי ענף ספורט ────────────────────────────────────────────────────────────

# ענפי ספורט ללא תיקו (2-way markets)
NO_DRAW_SPORTS = {
    "tennis", "baseball", "basketball", "american_football",
    "hockey", "volleyball", "handball",
}

# מיפוי league_id לסוג ספורט
LEAGUE_SPORT_MAP = {
    # כדורגל (3-way)
    1:   "soccer",   # World Cup
    253: "soccer",   # MLS
    98:  "soccer",   # J-League
    71:  "soccer",   # Brasileirão
    113: "soccer",   # Allsvenskan
    103: "soccer",   # Eliteserien
    244: "soccer",   # Veikkausliiga
    2:   "soccer",   # Champions League
    3:   "soccer",   # Europa League
    39:  "soccer",   # Premier League
    140: "soccer",   # La Liga
    78:  "soccer",   # Bundesliga
    135: "soccer",   # Serie A
    61:  "soccer",   # Ligue 1
}

# מיפוי sport_key של Odds API לסוג ספורט
SPORT_KEY_MAP = {
    "soccer_fifa_world_cup":                  "soccer",
    "soccer_international":                   "soccer",
    "soccer_fifa_world_cup_qualifier_conmebol": "soccer",
    "soccer_usa_mls":                         "soccer",
    "soccer_japan_j_league":                  "soccer",
    "soccer_brazil_campeonato":               "soccer",
    "soccer_sweden_allsvenskan":              "soccer",
    "soccer_norway_eliteserien":              "soccer",
    "soccer_finland_veikkausliiga":           "soccer",
    "soccer_epl":                             "soccer",
    "soccer_spain_la_liga":                   "soccer",
    "soccer_germany_bundesliga":              "soccer",
    "soccer_italy_serie_a":                   "soccer",
    "soccer_france_ligue_one":                "soccer",
    "soccer_uefa_champs_league":              "soccer",
    "soccer_uefa_europa_league":              "soccer",
    "tennis_atp":                             "tennis",
    "tennis_wta":                             "tennis",
    "baseball_mlb":                           "baseball",
    "basketball_nba":                         "basketball",
    "basketball_euroleague":                  "basketball",
}


def sport_has_draw(sport: str) -> bool:
    """מחזיר True אם הספורט כולל תיקו (3-way)."""
    return sport.lower() == "soccer"


def detect_sport_from_league(league_id: int) -> str:
    """מזהה ענף ספורט לפי league_id."""
    return LEAGUE_SPORT_MAP.get(league_id, "soccer")


def detect_sport_from_key(sport_key: str) -> str:
    """מזהה ענף ספורט לפי Odds API sport_key."""
    return SPORT_KEY_MAP.get(sport_key, "soccer")


# ─── FIFA-Based Starting Elo ────────────────────────────────────────────────────

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
    "New Zealand":     1390,
    "South Africa":    1385,
    "Mali":            1380,
    "Burkina Faso":    1375,
    "Cape Verde":      1370,
}


def get_starting_elo(team_name: str) -> float:
    """מחזיר Elo התחלתי לפי FIFA Ranking."""
    if team_name in FIFA_STARTING_ELO:
        return float(FIFA_STARTING_ELO[team_name])
    for key, val in FIFA_STARTING_ELO.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            return float(val)
    return 1400.0


# ─── Elo Confidence Discount ────────────────────────────────────────────────────

# Elo שברירת מחדל — קבוצות שטרם שיחקו ואין להן דירוג ידוע
ELO_DEFAULT     = 1400.0
ELO_CONVERGENCE_GAMES = 10   # לאחר כמה משחקים Elo נחשב מכוייל

def elo_confidence_weight(elo: float, games_played: int = 0) -> float:
    """
    מחשב משקל ביטחון ל-Elo של קבוצה.

    קבוצה שטרם שיחקה (games_played=0) עם Elo ברירת מחדל (1400):
      → weight = 0.0  (אין ביטחון — shrink מלא לכיוון prior)
    קבוצה עם 10+ משחקים:
      → weight = 1.0  (ביטחון מלא — ללא shrinkage)
    בין לבין — ליניארי.

    אם games_played לא ידוע (−1) → משתמש ב-Elo distance מ-1400 כ-proxy:
      ±50 נקודות מ-1400 = ~5 משחקים בהערכה גסה.
    """
    if games_played >= ELO_CONVERGENCE_GAMES:
        return 1.0
    if games_played > 0:
        return min(1.0, games_played / ELO_CONVERGENCE_GAMES)
    # proxy לפי מרחק מ-default — קבוצה ב-1400 = 0 ביטחון
    elo_delta = abs(elo - ELO_DEFAULT)
    # כל 20 נקודות מרחק = ~1 משחק בהערכה
    proxy_games = min(ELO_CONVERGENCE_GAMES, elo_delta / 20.0)
    return min(1.0, proxy_games / ELO_CONVERGENCE_GAMES)


def shrink_probability(p: float, prior_p: float, confidence: float) -> float:
    """
    Market-Based Shrinkage: כיווץ הסתברות לכיוון יעד ספציפי (prior_p).

    confidence=1.0 → p ללא שינוי (Elo מכויל — EV נשמר)
    confidence=0.0 → prior_p בלבד (הסכמה מלאה עם השוק — EV=0)

    שיפור על Prior אחיד:
    - Prior אחיד (33%/50%) מנפח אנדרדוגים: ניו זילנד 5% → 19% → EV מזויף.
    - Market Prior שומר על פרופורציות: ניו זילנד 5% → 5% כש-confidence=0 → EV=0.
    """
    return confidence * p + (1.0 - confidence) * prior_p


def apply_elo_confidence(probs: dict, elo_home: float, elo_away: float,
                          games_home: int = -1, games_away: int = -1,
                          odds: dict | None = None) -> dict:
    """
    מחיל Elo Confidence Discount על מילון הסתברויות — Market-Based Shrinkage.

    לוגיקת prior:
    1. אם יש odds תקינים → prior = Implied Market Probability (מנורמל, ללא overround).
       confidence=0 → EV=0 (מסכים עם השוק בדיוק) — אין False Value Bets.
    2. אם אין odds / לא תקינים → Fallback ל-Prior אחיד (1/n_outcomes).
       מתאים למשחקים ללא שוק (אימונים, כוס קטנה וכד').

    מחזיר מילון הסתברויות מעוכבות (מנורמלות) + _elo_confidence.
    """
    conf_h   = elo_confidence_weight(elo_home, games_home)
    conf_a   = elo_confidence_weight(elo_away, games_away)
    combined = (conf_h + conf_a) / 2.0

    has_draw   = "draw" in probs and probs.get("draw", 0) > 0
    n_outcomes = 3 if has_draw else 2
    outcomes   = ["home", "draw", "away"] if has_draw else ["home", "away"]

    # ── בנה Market Prior ──────────────────────────────────────────────────────
    market_prior: dict[str, float] = {}
    if odds:
        raw: dict[str, float] = {}
        valid = True
        for k in outcomes:
            o = odds.get(k, 0)
            if o and o > 1.01:
                raw[k] = implied_probability(o)
            else:
                valid = False
                break
        if valid and raw:
            total_imp = sum(raw.values())
            if total_imp > 0:
                # נרמול — מסיר את ה-overround של הבוקמייקר
                market_prior = {k: v / total_imp for k, v in raw.items()}

    # Fallback: Prior אחיד אם אין odds תקינים
    uniform_prior = 1.0 / n_outcomes
    if not market_prior:
        market_prior = {k: uniform_prior for k in outcomes}

    # ── החל Shrinkage ─────────────────────────────────────────────────────────
    result = dict(probs)  # שמור מפתחות נוספים (xg_home וכד')
    for k in outcomes:
        p     = probs.get(k, uniform_prior)
        prior = market_prior.get(k, uniform_prior)
        result[k] = shrink_probability(p, prior, combined)

    # נרמול סופי (מתקן drift קטן מהכיווץ)
    total = sum(result.get(k, 0) for k in outcomes)
    if total > 0:
        for k in outcomes:
            result[k] = round(result[k] / total, 4)

    result["_elo_confidence"] = round(combined, 3)
    return result


# ─── Dynamic K Factor ───────────────────────────────────────────────────────────

def dynamic_k(round_name: str = "") -> float:
    round_lower = round_name.lower()
    if "final" in round_lower and "semi" not in round_lower:
        return 60.0
    elif "semi" in round_lower:
        return 55.0
    elif "quarter" in round_lower:
        return 50.0
    elif "round of 16" in round_lower or "last 16" in round_lower:
        return 45.0
    elif "group" in round_lower:
        return 40.0
    return 40.0


# ─── Form Factor ────────────────────────────────────────────────────────────────

def calculate_form_factor(recent_matches: list[dict], team_id: int) -> float:
    """
    מחשב Form Factor מ-5 משחקים אחרונים.
    מחזיר multiplier בין 0.85 (טופס גרוע) ל-1.15 (טופס מצוין).
    """
    if not recent_matches:
        return 1.0

    points  = []
    weights = [0.10, 0.15, 0.20, 0.25, 0.30]

    for match in recent_matches[-5:]:
        home_id    = match["teams"]["home"]["id"]
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        status     = match["fixture"]["status"]["short"]
        is_home    = (home_id == team_id)

        if status == "PEN":
            points.append(0.5)
        elif is_home:
            points.append(1.0 if home_goals > away_goals else (0.5 if home_goals == away_goals else 0.0))
        else:
            points.append(1.0 if away_goals > home_goals else (0.5 if away_goals == home_goals else 0.0))

    if not points:
        return 1.0

    active_weights = weights[-len(points):]
    total_weight   = sum(active_weights)
    weighted_avg   = sum(p * w for p, w in zip(points, active_weights)) / total_weight
    return round(0.85 + (weighted_avg * 0.30), 3)


# ─── Elo ───────────────────────────────────────────────────────────────────────

def expected_score(elo_a: float, elo_b: float) -> float:
    """הסתברות שקבוצה A תנצח לפי מודל Elo."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def update_elo(elo_home: float, elo_away: float,
               home_goals: int, away_goals: int,
               status: str, k: float = 40,
               home_advantage: float = 0.0) -> tuple[float, float]:
    """מעדכן דירוגי Elo אחרי משחק שהסתיים."""
    adj_home = elo_home + home_advantage
    exp_home = expected_score(adj_home, elo_away)

    if status == "PEN":
        actual_home, goal_diff_factor = 0.5, 1.0
    elif home_goals > away_goals:
        actual_home = 1.0
        goal_diff_factor = _goal_diff_multiplier(home_goals - away_goals)
    elif home_goals < away_goals:
        actual_home = 0.0
        goal_diff_factor = _goal_diff_multiplier(away_goals - home_goals)
    else:
        actual_home, goal_diff_factor = 0.5, 1.0

    k_adjusted = k * goal_diff_factor
    new_home = round(elo_home + k_adjusted * (actual_home - exp_home), 1)
    new_away = round(elo_away + k_adjusted * (1.0 - actual_home - (1.0 - exp_home)), 1)
    return new_home, new_away


def update_elo_2way(elo_home: float, elo_away: float,
                    home_won: bool, k: float = 40) -> tuple[float, float]:
    """
    עדכון Elo לספורט דו-כיווני (ללא תיקו).
    home_won: True אם הביתי ניצח, False אם האורח ניצח.
    """
    exp_home = expected_score(elo_home, elo_away)
    actual_home = 1.0 if home_won else 0.0
    new_home = round(elo_home + k * (actual_home - exp_home), 1)
    new_away = round(elo_away + k * (1.0 - actual_home - (1.0 - exp_home)), 1)
    return new_home, new_away


def _goal_diff_multiplier(diff: int) -> float:
    if diff == 1:   return 1.0
    elif diff == 2: return 1.5
    else:           return 1.75


def apply_lineup_factor(xg_home: float, xg_away: float,
                        lineup_factor_home: float = 1.0,
                        lineup_factor_away: float = 1.0) -> tuple[float, float]:
    return (
        round(max(0.1, xg_home * lineup_factor_home), 3),
        round(max(0.1, xg_away * lineup_factor_away), 3),
    )


# ─── 2-Way Logistic Model (ללא תיקו) ───────────────────────────────────────────

def match_probabilities_2way(elo_home: float, elo_away: float,
                              form_home: float = 1.0,
                              form_away: float = 1.0) -> dict:
    """
    מחשב הסתברויות לספורט ללא תיקו (טניס, בייסבול, כדורסל).
    משתמש בנוסחה הלוגיסטית הסטנדרטית של Elo:
      P(home wins) = 1 / (1 + 10^((EloAway - EloHome) / 400))

    Form Factor מוסף כ-bonus Elo זמני.
    """
    # Form Factor הופך ל-Elo bonus (±30 נקודות מקסימום)
    elo_bonus_home = (form_home - 1.0) * 100
    elo_bonus_away = (form_away - 1.0) * 100

    adj_elo_home = elo_home + elo_bonus_home
    adj_elo_away = elo_away + elo_bonus_away

    p_home = expected_score(adj_elo_home, adj_elo_away)
    p_away = round(1.0 - p_home, 4)
    p_home = round(p_home, 4)

    return {
        "home": p_home,
        "draw": 0.0,
        "away": p_away,
        "has_draw": False,
    }


# ─── Poisson + Dixon-Coles (כדורגל) ────────────────────────────────────────────

def expected_goals(elo_home: float, elo_away: float,
                   home_advantage: float = 0.0,
                   league_avg_goals: float = 1.3,
                   form_home: float = 1.0,
                   form_away: float = 1.0,
                   lineup_home: float = 1.0,
                   lineup_away: float = 1.0) -> tuple[float, float]:
    elo_diff     = (elo_home + home_advantage) - elo_away
    base_xg_home = max(0.1, league_avg_goals + (elo_diff / 250))
    base_xg_away = max(0.1, league_avg_goals - (elo_diff / 250))
    xg_home      = round(max(0.1, base_xg_home * form_home * lineup_home), 3)
    xg_away      = round(max(0.1, base_xg_away * form_away * lineup_away), 3)
    return xg_home, xg_away


def _dixon_coles_tau(home_goals: int, away_goals: int,
                     xg_home: float, xg_away: float,
                     rho: float) -> float:
    i, j = home_goals, away_goals
    lam, mu = xg_home, xg_away
    if   i == 0 and j == 0: return max(1e-9, 1 - lam * mu * rho)
    elif i == 1 and j == 0: return max(1e-9, 1 + mu * rho)
    elif i == 0 and j == 1: return max(1e-9, 1 + lam * rho)
    elif i == 1 and j == 1: return max(1e-9, 1 - rho)
    else:                   return 1.0


def match_probabilities(elo_home: float, elo_away: float,
                        home_advantage: float = 0.0,
                        form_home: float = 1.0,
                        form_away: float = 1.0,
                        lineup_home: float = 1.0,
                        lineup_away: float = 1.0,
                        max_goals: int = 6,
                        rho: float = -0.13) -> dict:
    """Dixon-Coles Bivariate Poisson — לכדורגל בלבד."""
    xg_h, xg_a = expected_goals(
        elo_home, elo_away, home_advantage,
        form_home=form_home, form_away=form_away,
        lineup_home=lineup_home, lineup_away=lineup_away,
    )

    home_pmf = [poisson.pmf(i, xg_h) for i in range(max_goals + 1)]
    away_pmf = [poisson.pmf(i, xg_a) for i in range(max_goals + 1)]

    home_win = draw = away_win = 0.0
    score_matrix = {}

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            tau = _dixon_coles_tau(i, j, xg_h, xg_a, rho)
            p   = max(0.0, home_pmf[i] * away_pmf[j] * tau)
            score_matrix[f"{i}-{j}"] = p
            if i > j:   home_win += p
            elif i == j: draw    += p
            else:        away_win += p

    total = home_win + draw + away_win
    return {
        "home":         round(home_win / total, 4),
        "draw":         round(draw / total, 4),
        "away":         round(away_win / total, 4),
        "xg_home":      xg_h,
        "xg_away":      xg_a,
        "score_matrix": {k: v/total for k, v in score_matrix.items()},
        "rho":          rho,
        "has_draw":     True,
    }


def most_likely_scores(score_matrix: dict, top_n: int = 5) -> list[tuple[str, float]]:
    sorted_scores = sorted(score_matrix.items(), key=lambda x: x[1], reverse=True)
    return [(score, round(prob * 100, 1)) for score, prob in sorted_scores[:top_n]]


# ─── Kelly Criterion ───────────────────────────────────────────────────────────

def implied_probability(odds: float) -> float:
    if odds <= 1.0: return 1.0
    return 1.0 / odds


def overround(odds_home: float, odds_draw: float = 0.0, odds_away: float = 0.0) -> float:
    total = implied_probability(odds_home) + implied_probability(odds_away)
    if odds_draw and odds_draw > 1.0:
        total += implied_probability(odds_draw)
    return round((total - 1.0) * 100, 2)


def fair_odds(our_prob: float) -> float:
    if our_prob <= 0: return 0.0
    return round(1.0 / our_prob, 3)


def expected_value(our_prob: float, odds: float) -> float:
    if odds <= 1.0 or our_prob <= 0: return 0.0
    return round((our_prob * odds) - 1.0, 4)


def kelly_fraction(our_prob: float, odds: float,
                   fraction: float = 0.25,
                   max_bet: float = 0.05) -> float:
    ev = expected_value(our_prob, odds)
    if ev <= 0: return 0.0
    b = odds - 1.0
    q = 1.0 - our_prob
    full_kelly = (our_prob * b - q) / b
    return round(max(min(full_kelly * fraction, max_bet), 0.0), 4)


def closing_line_value(our_prob: float, closing_odds: float) -> float:
    return round(our_prob - implied_probability(closing_odds), 4)


# ─── Odds Freshness ────────────────────────────────────────────────────────────

def odds_freshness(odds_updated_at: str | None) -> dict:
    if not odds_updated_at:
        return {"status": "missing", "hours_ago": None, "label": "⚪ אין odds", "color": "#6b7a99"}
    from datetime import datetime, timezone
    try:
        updated   = datetime.fromisoformat(odds_updated_at.replace("Z", "+00:00"))
        hours_ago = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
        if hours_ago < 1:
            return {"status": "live",  "hours_ago": round(hours_ago,1), "label": f"🟢 חי ({int(hours_ago*60)} דקות)", "color": "#10b981"}
        elif hours_ago < 24:
            return {"status": "fresh", "hours_ago": round(hours_ago,1), "label": f"🟡 {round(hours_ago,1)} שעות",    "color": "#f59e0b"}
        elif hours_ago < 72:
            return {"status": "stale", "hours_ago": round(hours_ago,1), "label": f"🟠 {int(hours_ago/24)} ימים",     "color": "#ef4444"}
        else:
            return {"status": "old",   "hours_ago": round(hours_ago,1), "label": f"🔴 ישן ({int(hours_ago/24)} ימים)","color": "#dc2626"}
    except Exception:
        return {"status": "missing", "hours_ago": None, "label": "⚪ תאריך לא ידוע", "color": "#6b7a99"}


# ─── Full Analysis ──────────────────────────────────────────────────────────────

def full_match_analysis(elo_home: float, elo_away: float,
                        odds: dict,
                        home_advantage: float = 0.0,
                        form_home: float = 1.0,
                        form_away: float = 1.0,
                        lineup_home: float = 1.0,
                        lineup_away: float = 1.0,
                        pure_probs: dict | None = None,
                        odds_updated_at: str | None = None,
                        rho: float = -0.13,
                        has_draw: bool = True,
                        games_home: int = -1,
                        games_away: int = -1) -> dict:
    """
    ניתוח מלא לכל ענפי הספורט.

    has_draw=True  → כדורגל: Dixon-Coles Bivariate Poisson (3-way)
    has_draw=False → ספורט ללא תיקו: נוסחה לוגיסטית (2-way)

    games_home / games_away: מספר משחקים שמופיעים ב-Elo history.
    -1 = לא ידוע → משתמש ב-Elo distance כ-proxy.
    מוחל Elo Confidence Discount — מונע EV מנופח לקבוצות שטרם התכנסו.
    """
    if has_draw:
        # ── כדורגל — Dixon-Coles ────────────────────────────────────────────
        probs = match_probabilities(
            elo_home, elo_away, home_advantage,
            form_home=form_home, form_away=form_away,
            lineup_home=lineup_home, lineup_away=lineup_away,
            rho=rho,
        )
        outcomes = ["home", "draw", "away"]

        # ── Elo Confidence Discount ─────────────────────────────────────────
        # EV ו-Kelly מחושבים על הסתברויות אחרי shrinkage (ev_probs).
        # הצגה בממשק (our_prob) נשארת ללא שינוי — ציון שקוף למשתמש.
        raw_ev_probs = pure_probs if pure_probs else probs
        ev_probs     = apply_elo_confidence(
            raw_ev_probs, elo_home, elo_away, games_home, games_away,
            odds=odds,  # Market-Based Shrinkage — prior = implied market prob
        )
        elo_confidence = ev_probs.get("_elo_confidence", 1.0)

        results = {}
        for outcome in outcomes:
            p_display = probs[outcome]
            p_ev      = ev_probs.get(outcome, p_display)
            o         = odds.get(outcome, 0)
            results[outcome] = {
                "our_prob":     round(p_display * 100, 1),
                "our_prob_raw": p_display,
                "our_prob_ev":  round(p_ev * 100, 1),
                "odds":         o,
                "implied_prob": round(implied_probability(o) * 100, 1),
                "fair_odds":    fair_odds(p_ev),
                "ev":           expected_value(p_ev, o),
                "kelly_pct":    round(kelly_fraction(p_ev, o) * 100, 2),
                "is_value":     expected_value(p_ev, o) > 0,
            }

        results["overround"]      = overround(odds.get("home",1), odds.get("draw",1), odds.get("away",1))
        results["xg_home"]        = probs["xg_home"]
        results["xg_away"]        = probs["xg_away"]
        results["top_scores"]     = most_likely_scores(probs["score_matrix"])
        results["has_draw"]       = True
        results["elo_confidence"] = round(elo_confidence, 3)

    else:
        # ── ספורט 2-way — לוגיסטי ──────────────────────────────────────────
        probs    = match_probabilities_2way(elo_home, elo_away, form_home, form_away)
        outcomes = ["home", "away"]

        # ── Elo Confidence Discount ─────────────────────────────────────────
        raw_ev_probs = pure_probs if pure_probs else probs
        ev_probs     = apply_elo_confidence(
            raw_ev_probs, elo_home, elo_away, games_home, games_away,
            odds=odds,  # Market-Based Shrinkage — prior = implied market prob
        )
        elo_confidence = ev_probs.get("_elo_confidence", 1.0)

        results = {}
        for outcome in outcomes:
            p_display = probs[outcome]
            p_ev      = ev_probs.get(outcome, p_display)
            o         = odds.get(outcome, 0)
            results[outcome] = {
                "our_prob":     round(p_display * 100, 1),
                "our_prob_raw": p_display,
                "our_prob_ev":  round(p_ev * 100, 1),
                "odds":         o,
                "implied_prob": round(implied_probability(o) * 100, 1),
                "fair_odds":    fair_odds(p_ev),
                "ev":           expected_value(p_ev, o),
                "kelly_pct":    round(kelly_fraction(p_ev, o) * 100, 2),
                "is_value":     expected_value(p_ev, o) > 0,
            }
        # draw placeholder ריק (לתאימות עם קוד קיים)
        results["draw"] = {
            "our_prob": 0.0, "our_prob_raw": 0.0, "our_prob_ev": 0.0,
            "odds": 0, "implied_prob": 0.0, "fair_odds": 0.0,
            "ev": 0.0, "kelly_pct": 0.0, "is_value": False,
        }
        results["overround"]     = overround(odds.get("home",1), 0, odds.get("away",1))
        results["xg_home"]       = None
        results["xg_away"]       = None
        results["top_scores"]    = []
        results["has_draw"]      = False
        results["elo_confidence"]= round(elo_confidence, 3)

    results["form_home"]      = round(form_home, 3)
    results["form_away"]      = round(form_away, 3)
    results["lineup_home"]    = round(lineup_home, 3)
    results["lineup_away"]    = round(lineup_away, 3)
    results["odds_freshness"] = odds_freshness(odds_updated_at)
    return results
