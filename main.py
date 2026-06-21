"""
main.py — Pipeline ראשי v3
לומד מהיסטוריה + Elo התחלתי מ-FIFA + K דינמי + Dixon-Coles עם rho מכויל אוטומטית + A/B Testing
"""

from api_client import get_all_fixtures, get_odds, get_team_last_matches
from engine import update_elo, full_match_analysis, get_starting_elo, dynamic_k, calculate_form_factor
from db import upsert_team, update_team_elo, get_team_elo, upsert_match, log_prediction
from rho_calibrator import calibrate_rho, load_matches_for_calibration, DEFAULT_RHO
from ensemble import ensemble_probabilities


# ── rho גלובלי — מכויל פעם אחת בתחילת כל ריצה ──────────────────────────────
_CURRENT_RHO = DEFAULT_RHO


def _auto_calibrate_rho(verbose: bool = True) -> float:
    """
    מכייל את rho אוטומטית מנתוני המונדיאל.
    מחזיר את ה-rho הטוב ביותר הזמין.
    """
    global _CURRENT_RHO
    matches = load_matches_for_calibration()
    result  = calibrate_rho(matches)

    if verbose:
        print(f"🔧 כיול Dixon-Coles rho: {result['message']}")

    _CURRENT_RHO = result["recommended_rho"]
    return _CURRENT_RHO


def run_pipeline(verbose: bool = True):
    if verbose:
        print("🚀 שואב משחקי מונדיאל 2026...")

    # ── כיול rho אוטומטי בתחילת כל ריצה ──
    rho = _auto_calibrate_rho(verbose)

    fixtures = get_all_fixtures()
    if not fixtures:
        print("❌ לא נמצאו משחקים.")
        return

    if verbose:
        print(f"📊 נמצאו {len(fixtures)} משחקים.")
        print("─" * 60)

    for match in fixtures:
        _process_match(match, verbose, rho=rho)

    if verbose:
        print("─" * 60)
        print("✅ Pipeline הסתיים.")


def _process_match(match: dict, verbose: bool, rho: float = DEFAULT_RHO):
    fix     = match["fixture"]
    fixture_id  = fix["id"]
    match_date  = fix["date"]
    status      = fix["status"]["short"]
    round_name  = match.get("league", {}).get("round", "")

    home = match["teams"]["home"]
    away = match["teams"]["away"]

    # ── 1. Elo התחלתי מ-FIFA אם הקבוצה חדשה ──
    existing_home = get_team_elo(home["id"], default=None)
    existing_away = get_team_elo(away["id"], default=None)

    if existing_home is None:
        starting = get_starting_elo(home["name"])
        upsert_team(home["id"], home["name"], elo=starting)
        existing_home = starting

    if existing_away is None:
        starting = get_starting_elo(away["name"])
        upsert_team(away["id"], away["name"], elo=starting)
        existing_away = starting

    elo_home = existing_home
    elo_away = existing_away

    # ── 2. Form Factor (5 משחקים אחרונים) ──
    try:
        last_home = get_team_last_matches(home["id"], last=5)
        last_away = get_team_last_matches(away["id"], last=5)
        form_home = calculate_form_factor(last_home, home["id"])
        form_away = calculate_form_factor(last_away, away["id"])
    except Exception:
        form_home = form_away = 1.0

    # ── 3. Odds ──
    odds_data = get_odds(fixture_id)
    odds = {}
    odds_updated_at = None
    odds_bookmaker = None
    if odds_data:
        odds = {k: odds_data[k] for k in ["home", "draw", "away"] if k in odds_data}
        odds_updated_at = odds_data.get("updated_at")
        odds_bookmaker  = odds_data.get("bookmaker")

    # ── 3.5. חישוב Ensemble ──
    ensemble_data = ensemble_probabilities(
        elo_home, elo_away, home["name"], away["name"],
        form_home=form_home, form_away=form_away,
        live_odds=odds,
    )

    # ── 4. ניתוח מלא עם rho מכויל ──
    analysis = full_match_analysis(
        elo_home, elo_away, odds,
        home_advantage=0.0,
        form_home=form_home,
        form_away=form_away,
        odds_updated_at=odds_updated_at,
        rho=rho,  # Dixon-Coles rho מכויל אוטומטית
        pure_probs=ensemble_data.get("pure") # קריטי כדי שה-EV יחושב נכון!
    )

    # ── 5. שמירת משחק ──
    match_data = {
        "fixture_id":       fixture_id,
        "match_date":       match_date,
        "home_team_id":     home["id"],
        "home_team_name":   home["name"],
        "away_team_id":     away["id"],
        "away_team_name":   away["name"],
        "home_win_prob":    analysis["home"]["our_prob_raw"],
        "draw_prob":        analysis["draw"]["our_prob_raw"],
        "away_win_prob":    analysis["away"]["our_prob_raw"],
        "status":           status,
        "elo_home_before":  elo_home,
        "elo_away_before":  elo_away,
        "form_home":        form_home,
        "form_away":        form_away,
        "round":            round_name,
    }

    # ── 6. אם המשחק הסתיים → למידה + שמירת actual_goals לכיול ──
    if status in ("FT", "AET", "PEN"):
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        match_data["home_goals"] = home_goals
        match_data["away_goals"] = away_goals

        k = dynamic_k(round_name)
        new_elo_home, new_elo_away = update_elo(
            elo_home, elo_away, home_goals, away_goals, status, k=k
        )
        update_team_elo(home["id"], new_elo_home)
        update_team_elo(away["id"], new_elo_away)
        match_data["elo_home_after"] = new_elo_home
        match_data["elo_away_after"] = new_elo_away

        if verbose:
            result = f"{home_goals}-{away_goals}"
            print(f"⚽ {home['name']} ({elo_home:.0f}) {result} {away['name']} ({elo_away:.0f})")
            print(f"   תחזית: {analysis['home']['our_prob']}% / {analysis['draw']['our_prob']}% / {analysis['away']['our_prob']}%")
            print(f"   K={k} | rho={rho} | Elo: {home['name']}→{new_elo_home} | {away['name']}→{new_elo_away}\n")

    upsert_match(match_data)

    # ── 7. שמירת תחזית מפורטת + actual_goals לכיול rho ──
    top_scores = analysis.get("top_scores", [])
    freshness  = analysis.get("odds_freshness", {})

    pred = {
        "home_team_name":   home["name"],
        "away_team_name":   away["name"],
        "match_date":       match_date,
        "elo_home":         elo_home,
        "elo_away":         elo_away,
        "form_home":        form_home,
        "form_away":        form_away,
        "prob_home":        analysis["home"]["our_prob_raw"],
        "prob_draw":        analysis["draw"]["our_prob_raw"],
        "prob_away":        analysis["away"]["our_prob_raw"],
        
        # -------- התוספת החדשה ל- A/B Testing --------
        "prob_elo_home":    ensemble_data["elo"]["home"],
        "prob_elo_draw":    ensemble_data["elo"]["draw"],
        "prob_elo_away":    ensemble_data["elo"]["away"],
        "prob_ensemble_home": ensemble_data["ensemble"]["home"],
        "prob_ensemble_draw": ensemble_data["ensemble"]["draw"],
        "prob_ensemble_away": ensemble_data["ensemble"]["away"],
        # -----------------------------------------------

        "xg_home":          analysis["xg_home"],
        "xg_away":          analysis["xg_away"],
        "rho_used":         rho,   # שמירת rho לכיול עתידי
        "odds_home":        odds.get("home"),
        "odds_draw":        odds.get("draw"),
        "odds_away":        odds.get("away"),
        "odds_updated_at":  odds_updated_at,
        "odds_freshness":   freshness.get("status"),
        "odds_bookmaker":   odds_bookmaker,
        "ev_home":          analysis["home"]["ev"],
        "ev_draw":          analysis["draw"]["ev"],
        "ev_away":          analysis["away"]["ev"],
        "kelly_home":       analysis["home"]["kelly_pct"],
        "kelly_draw":       analysis["draw"]["kelly_pct"],
        "kelly_away":       analysis["away"]["kelly_pct"],
        "top_score_1":      top_scores[0][0] if top_scores else None,
        "top_score_1_pct":  top_scores[0][1] if top_scores else None,
        "overround":        analysis.get("overround"),
        "status":           status,
        "round":            round_name,
    }

    if status in ("FT", "AET", "PEN"):
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        # שמירת תוצאות בפועל — קריטי לכיול rho!
        pred["actual_home_goals"] = home_goals
        pred["actual_away_goals"] = away_goals
        if home_goals > away_goals:
            pred["actual_result"] = "home"
        elif home_goals < away_goals:
            pred["actual_result"] = "away"
        else:
            pred["actual_result"] = "draw"

    log_prediction(fixture_id, pred)


if __name__ == "__main__":
    run_pipeline(verbose=True)