"""
main.py — Pipeline ראשי v2
לומד מהיסטוריה + Elo התחלתי מ-FIFA + K דינמי + שומר תחזיות עם Form Factor
"""

from api_client import get_all_fixtures, get_odds, get_team_last_matches
from engine import update_elo, full_match_analysis, get_starting_elo, dynamic_k, calculate_form_factor
from db import upsert_team, update_team_elo, get_team_elo, upsert_match, log_prediction


def run_pipeline(verbose: bool = True):
    if verbose:
        print("🚀 שואב משחקי מונדיאל 2026...")

    fixtures = get_all_fixtures()
    if not fixtures:
        print("❌ לא נמצאו משחקים.")
        return

    if verbose:
        print(f"📊 נמצאו {len(fixtures)} משחקים.")
        print("─" * 60)

    for match in fixtures:
        _process_match(match, verbose)

    if verbose:
        print("─" * 60)
        print("✅ Pipeline הסתיים.")


def _process_match(match: dict, verbose: bool):
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

    # ── 4. ניתוח מלא (לפני עדכון Elo!) ──
    analysis = full_match_analysis(
        elo_home, elo_away, odds,
        home_advantage=0.0,
        form_home=form_home,
        form_away=form_away,
        odds_updated_at=odds_updated_at
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

    # ── 6. אם המשחק הסתיים → למידה ──
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
            print(f"⚽ {home['name']} ({elo_home:.0f}+form{form_home}) {result} {away['name']} ({elo_away:.0f}+form{form_away})")
            print(f"   תחזית: {analysis['home']['our_prob']}% / {analysis['draw']['our_prob']}% / {analysis['away']['our_prob']}%")
            print(f"   K={k} | Elo חדש: {home['name']}→{new_elo_home} | {away['name']}→{new_elo_away}\n")

    upsert_match(match_data)

    # ── 7. שמירת תחזית מפורטת ──
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
        "xg_home":          analysis["xg_home"],
        "xg_away":          analysis["xg_away"],
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
        if home_goals > away_goals:
            pred["actual_result"] = "home"
        elif home_goals < away_goals:
            pred["actual_result"] = "away"
        else:
            pred["actual_result"] = "draw"

    log_prediction(fixture_id, pred)


if __name__ == "__main__":
    run_pipeline(verbose=True)
