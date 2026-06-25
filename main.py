"""
main.py — Pipeline ראשי v4
- Dixon-Coles עם rho מכויל אוטומטית (כדורגל)
- Logistic 2-way (טניס, בייסבול, כדורסל)
- זיהוי אוטומטי has_draw לפי sport_key
- מיון חכם: הסתיים → קרוב → רחוק
- A/B Testing: 3 מודלים בנפרד
"""

from datetime import datetime, timezone

from api_client import get_all_fixtures, get_odds, get_team_last_matches
from engine import (update_elo, update_elo_2way, full_match_analysis,
                    get_starting_elo, dynamic_k, calculate_form_factor,
                    match_probabilities, match_probabilities_2way,
                    sport_has_draw, detect_sport_from_league)
from db import upsert_team, update_team_elo, get_team_elo, upsert_match, log_prediction
from rho_calibrator import calibrate_rho, load_matches_for_calibration, DEFAULT_RHO
from ensemble import fifa_probabilities

# ── rho גלובלי ───────────────────────────────────────────────────────────────
_CURRENT_RHO = DEFAULT_RHO


def _auto_calibrate_rho(verbose: bool = True) -> float:
    global _CURRENT_RHO
    matches = load_matches_for_calibration()
    result  = calibrate_rho(matches)
    if verbose:
        print(f"🔧 כיול Dixon-Coles rho: {result['message']}", flush=True)
    _CURRENT_RHO = result["recommended_rho"]
    return _CURRENT_RHO


def _match_priority(f: dict, now: datetime) -> int:
    """1=הסתיים, 2=קרוב (≤3 ימים), 3=רחוק, 4=אחר."""
    status = f["fixture"]["status"]["short"]
    if status in ("FT", "AET", "PEN"):
        return 1
    if status in ("NS", "TBD"):
        try:
            match_dt = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
            return 2 if (match_dt - now).days <= 3 else 3
        except Exception:
            return 3
    return 4


def _detect_has_draw(match: dict) -> bool:
    """
    מזהה אוטומטית אם הענף כולל תיקו.
    מסתמך על league_id מה-API.
    """
    league_id = match.get("league", {}).get("id", 0)
    sport     = detect_sport_from_league(league_id)
    return sport_has_draw(sport)


def run_pipeline(verbose: bool = True):
    if verbose:
        print("🚀 שואב משחקי כדורגל וספורט...", flush=True)

    rho = _auto_calibrate_rho(verbose)

    fixtures = get_all_fixtures()
    if not fixtures:
        print("❌ לא נמצאו משחקים.", flush=True)
        return

    now = datetime.now(timezone.utc)
    fixtures_sorted = sorted(fixtures, key=lambda f: _match_priority(f, now))

    if verbose:
        finished = sum(1 for f in fixtures if f["fixture"]["status"]["short"] in ("FT","AET","PEN"))
        upcoming = sum(1 for f in fixtures if f["fixture"]["status"]["short"] in ("NS","TBD"))
        print(f"📊 {len(fixtures)} משחקים: {finished} הסתיימו, {upcoming} קרובים", flush=True)
        print("─" * 60, flush=True)

    for match in fixtures_sorted:
        _process_match(match, verbose, rho=rho)

    if verbose:
        print("─" * 60, flush=True)
        print("✅ Pipeline הסתיים.", flush=True)


def _process_match(match: dict, verbose: bool, rho: float = DEFAULT_RHO):
    fix        = match["fixture"]
    fixture_id = fix["id"]
    match_date = fix["date"]
    status     = fix["status"]["short"]
    round_name = match.get("league", {}).get("round", "")
    league_id  = match.get("league", {}).get("id", 0)

    home = match["teams"]["home"]
    away = match["teams"]["away"]

    # ── זיהוי אוטומטי: כדורגל (3-way) או ספורט אחר (2-way) ─────────────────
    has_draw = _detect_has_draw(match)

    # ── 1. Elo התחלתי ────────────────────────────────────────────────────────
    elo_home = get_team_elo(home["id"], default=None)
    elo_away = get_team_elo(away["id"], default=None)

    if elo_home is None:
        elo_home = get_starting_elo(home["name"])
        upsert_team(home["id"], home["name"], elo=elo_home)
    if elo_away is None:
        elo_away = get_starting_elo(away["name"])
        upsert_team(away["id"], away["name"], elo=elo_away)

    # ── 2. Form Factor ────────────────────────────────────────────────────────
    try:
        form_home = calculate_form_factor(get_team_last_matches(home["id"], last=5), home["id"])
        form_away = calculate_form_factor(get_team_last_matches(away["id"], last=5), away["id"])
    except Exception:
        form_home = form_away = 1.0

    # ── 3. Odds ───────────────────────────────────────────────────────────────
    odds_data       = get_odds(fixture_id)
    odds            = {}
    odds_updated_at = None
    odds_bookmaker  = None
    if odds_data:
        if has_draw:
            odds = {k: odds_data[k] for k in ["home","draw","away"] if k in odds_data}
        else:
            odds = {k: odds_data[k] for k in ["home","away"] if k in odds_data}
        odds_updated_at = odds_data.get("updated_at")
        odds_bookmaker  = odds_data.get("bookmaker")

    # ── 4. ניתוח מלא ─────────────────────────────────────────────────────────
    analysis = full_match_analysis(
        elo_home, elo_away, odds,
        home_advantage=0.0,
        form_home=form_home,
        form_away=form_away,
        odds_updated_at=odds_updated_at,
        rho=rho,
        has_draw=has_draw,
    )

    # ── 5. שמירת משחק ────────────────────────────────────────────────────────
    match_data = {
        "fixture_id":      fixture_id,
        "match_date":      match_date,
        "home_team_id":    home["id"],
        "home_team_name":  home["name"],
        "away_team_id":    away["id"],
        "away_team_name":  away["name"],
        "home_win_prob":   analysis["home"]["our_prob_raw"],
        "draw_prob":       analysis["draw"]["our_prob_raw"],
        "away_win_prob":   analysis["away"]["our_prob_raw"],
        "status":          status,
        "elo_home_before": elo_home,
        "elo_away_before": elo_away,
        "form_home":       form_home,
        "form_away":       form_away,
        "round":           round_name,
        "has_draw":        has_draw,
    }

    # ── 6. משחק שהסתיים → עדכון Elo ──────────────────────────────────────────
    home_goals = away_goals = None

    if status in ("FT","AET","PEN"):
        k = dynamic_k(round_name)

        if has_draw:
            # כדורגל — עם שערים
            home_goals = match["goals"]["home"] or 0
            away_goals = match["goals"]["away"] or 0
            match_data["home_goals"] = home_goals
            match_data["away_goals"] = away_goals

            new_elo_home, new_elo_away = update_elo(
                elo_home, elo_away, home_goals, away_goals, status, k=k)

            if verbose:
                print(f"⚽ {home['name']} ({elo_home:.0f}) "
                      f"{home_goals}-{away_goals} "
                      f"{away['name']} ({elo_away:.0f})", flush=True)
        else:
            # ספורט 2-way — ניצחון/הפסד בלבד (אין שערים)
            home_score = (match.get("goals") or {}).get("home")
            away_score = (match.get("goals") or {}).get("away")
            home_won   = (home_score is not None and away_score is not None
                          and home_score > away_score)

            new_elo_home, new_elo_away = update_elo_2way(
                elo_home, elo_away, home_won, k=k)

            if verbose:
                result_str = f"{home_score}-{away_score}" if home_score is not None else "?"
                print(f"🏆 {home['name']} ({elo_home:.0f}) "
                      f"{result_str} "
                      f"{away['name']} ({elo_away:.0f})", flush=True)

        update_team_elo(home["id"], new_elo_home)
        update_team_elo(away["id"], new_elo_away)
        match_data["elo_home_after"] = new_elo_home
        match_data["elo_away_after"] = new_elo_away

        if verbose:
            print(f"   תחזית: {analysis['home']['our_prob']}% / "
                  f"{analysis['draw']['our_prob']}% / "
                  f"{analysis['away']['our_prob']}%", flush=True)
            print(f"   K={k} | rho={rho if has_draw else 'N/A'} | "
                  f"Elo: {home['name']}→{new_elo_home} | "
                  f"{away['name']}→{new_elo_away}\n", flush=True)

    upsert_match(match_data)

    # ── 7. A/B Testing — 3 מודלים ────────────────────────────────────────────
    if has_draw:
        # מודל A — Elo טהור (כדורגל)
        elo_pure = match_probabilities(elo_home, elo_away, rho=rho)
        # מודל C — Ensemble (Elo 70% + FIFA 30%)
        fifa          = fifa_probabilities(home["name"], away["name"])
        ens_home_raw  = elo_pure["home"] * 0.70 + fifa["home"] * 0.30
        ens_draw_raw  = elo_pure["draw"] * 0.70 + fifa["draw"] * 0.30
        ens_away_raw  = elo_pure["away"] * 0.70 + fifa["away"] * 0.30
        ens_total     = ens_home_raw + ens_draw_raw + ens_away_raw
        ens_home = round(ens_home_raw / ens_total, 4)
        ens_draw = round(ens_draw_raw / ens_total, 4)
        ens_away = round(ens_away_raw / ens_total, 4)
    else:
        # מודל A — Elo לוגיסטי טהור (2-way)
        elo_pure = match_probabilities_2way(elo_home, elo_away)
        ens_home = elo_pure["home"]
        ens_draw = 0.0
        ens_away = elo_pure["away"]

    top_scores = analysis.get("top_scores", [])
    freshness  = analysis.get("odds_freshness", {})

    pred = {
        "home_team_name":       home["name"],
        "away_team_name":       away["name"],
        "match_date":           match_date,
        "elo_home":             elo_home,
        "elo_away":             elo_away,
        "form_home":            form_home,
        "form_away":            form_away,
        "rho_used":             rho if has_draw else None,
        "has_draw":             has_draw,
        "league_id":            league_id,
        # מודל B — Elo + Form
        "prob_home":            analysis["home"]["our_prob_raw"],
        "prob_draw":            analysis["draw"]["our_prob_raw"],
        "prob_away":            analysis["away"]["our_prob_raw"],
        # מודל A — Elo טהור
        "prob_elo_home":        elo_pure["home"],
        "prob_elo_draw":        elo_pure.get("draw", 0.0),
        "prob_elo_away":        elo_pure["away"],
        # מודל C — Ensemble
        "prob_ensemble_home":   ens_home,
        "prob_ensemble_draw":   ens_draw,
        "prob_ensemble_away":   ens_away,
        "xg_home":              analysis.get("xg_home"),
        "xg_away":              analysis.get("xg_away"),
        "odds_home":            odds.get("home"),
        "odds_draw":            odds.get("draw"),
        "odds_away":            odds.get("away"),
        "odds_updated_at":      odds_updated_at,
        "odds_freshness":       freshness.get("status"),
        "odds_bookmaker":       odds_bookmaker,
        "ev_home":              analysis["home"]["ev"],
        "ev_draw":              analysis["draw"]["ev"],
        "ev_away":              analysis["away"]["ev"],
        "kelly_home":           analysis["home"]["kelly_pct"],
        "kelly_draw":           analysis["draw"]["kelly_pct"],
        "kelly_away":           analysis["away"]["kelly_pct"],
        "top_score_1":          top_scores[0][0] if top_scores else None,
        "top_score_1_pct":      top_scores[0][1] if top_scores else None,
        "overround":            analysis.get("overround"),
        "status":               status,
        "round":                round_name,
    }

    # תוצאה בפועל — לכיול rho ו-Backtest
    if status in ("FT","AET","PEN"):
        if has_draw and home_goals is not None:
            # כדורגל — שערים
            pred["actual_home_goals"] = home_goals
            pred["actual_away_goals"] = away_goals
            if home_goals > away_goals:   pred["actual_result"] = "home"
            elif home_goals < away_goals: pred["actual_result"] = "away"
            else:                         pred["actual_result"] = "draw"
        elif not has_draw:
            # ספורט 2-way — ניצחון בלבד
            h_score = (match.get("goals") or {}).get("home")
            a_score = (match.get("goals") or {}).get("away")
            if h_score is not None and a_score is not None:
                pred["actual_result"] = "home" if h_score > a_score else "away"

    log_prediction(fixture_id, pred)


if __name__ == "__main__":
    run_pipeline(verbose=True)
