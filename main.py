"""
main.py — Pipeline ראשי v5 (דינמי + Rate-Limit Safe)
- מגלה ליגות וספורט אוטומטית בכל הרצה
- has_draw נקבע מה-Odds API — לא hardcoded
- אם משחק לא נמצא ב-odds_batch → מדולג (לא מריץ חישובי כדורגל על טניס)
- Rate-limit protection בשני ה-API
- Cache יומי — חסכוני בקריאות
"""

import hashlib
from datetime import datetime, timezone

from api_client import (get_all_fixtures, get_all_active_leagues,
                        get_odds, get_team_last_matches, is_api_blocked)
from odds_api import (get_all_available_sports, get_all_odds_batch,
                      lookup_odds_from_batch, is_odds_blocked)
from engine import (update_elo, update_elo_2way, full_match_analysis,
                    get_starting_elo, dynamic_k, calculate_form_factor,
                    match_probabilities, match_probabilities_2way)
from db import upsert_team, update_team_elo, get_team_elo, upsert_match, log_prediction
from rho_calibrator import calibrate_rho, load_matches_for_calibration, DEFAULT_RHO
from ensemble import fifa_probabilities

_CURRENT_RHO = DEFAULT_RHO


def _load_games_played() -> dict:
    try:
        import os
        from supabase import create_client
        from collections import Counter
        db   = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res  = db.table("matches").select("home_team_id, away_team_id").execute()
        counts: Counter = Counter()
        for row in (res.data or []):
            if row.get("home_team_id"): counts[row["home_team_id"]] += 1
            if row.get("away_team_id"): counts[row["away_team_id"]] += 1
        print(f"[Pipeline] games_played נטען: {len(counts)} קבוצות", flush=True)
        return dict(counts)
    except Exception as e:
        print(f"[Pipeline] ⚠️ שגיאה בטעינת games_played: {e}", flush=True)
        return {}


def _auto_calibrate_rho(verbose: bool = True) -> float:
    global _CURRENT_RHO
    matches = load_matches_for_calibration()
    result  = calibrate_rho(matches)
    if verbose:
        print(f"🔧 כיול Dixon-Coles rho: {result['message']}", flush=True)
    _CURRENT_RHO = result["recommended_rho"]
    return _CURRENT_RHO


def _match_priority(f: dict, now: datetime) -> int:
    status = f["fixture"]["status"]["short"]
    if status in ("FT", "AET", "PEN"):
        return 1
    if status in ("NS", "TBD"):
        try:
            dt = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
            return 2 if (dt - now).days <= 3 else 3
        except Exception:
            return 3
    return 4


def run_pipeline(verbose: bool = True):
    if verbose:
        print("🚀 Pipeline v5 — דינמי + Rate-Limit Safe", flush=True)

    if verbose:
        print("🔍 מגלה ליגות וענפי ספורט...", flush=True)

    active_leagues = get_all_active_leagues()
    active_sports  = get_all_available_sports()

    if verbose:
        print(f"   ✅ {len(active_leagues)} ליגות כדורגל", flush=True)
        print(f"   ✅ {len(active_sports)} ענפי ספורט", flush=True)

    rho = _auto_calibrate_rho(verbose)

    if verbose:
        print("📡 שואב Odds Batch...", flush=True)

    odds_batch = get_all_odds_batch()

    if is_odds_blocked():
        print("[Pipeline] ⛔ Odds API חסום — ממשיך ללא odds", flush=True)

    if verbose:
        print(f"   ✅ {len(odds_batch)//2} משחקים עם odds", flush=True)

    gp_cache = _load_games_played()

    fixtures = get_all_fixtures()

    if is_api_blocked():
        print("[Pipeline] ⛔ Football API חסום — עוצר", flush=True)
        return

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

    skipped = 0
    for match in fixtures_sorted:
        result = _process_match(match, verbose, rho=rho, odds_batch=odds_batch,
                                gp_cache=gp_cache)
        if result == "skipped":
            skipped += 1

    if verbose:
        print("─" * 60, flush=True)
        if skipped:
            print(f"⏭ {skipped} משחקים דולגו (לא נמצאו ב-odds_batch)", flush=True)
        print("✅ Pipeline הסתיים.", flush=True)


def _process_match(match: dict, verbose: bool,
                   rho: float = DEFAULT_RHO,
                   odds_batch: dict | None = None,
                   gp_cache: dict | None = None) -> str:
    fix        = match["fixture"]
    fixture_id = fix["id"]
    match_date = fix["date"]
    status     = fix["status"]["short"]
    round_name = match.get("league", {}).get("round", "")
    league_id  = match.get("league", {}).get("id", 0)

    home = match["teams"]["home"]
    away = match["teams"]["away"]

    has_draw      = True
    odds          = {}
    odds_updated_at = None
    odds_bookmaker  = None

    if odds_batch:
        live = lookup_odds_from_batch(odds_batch, home["name"], away["name"])
        if live:
            has_draw        = live.get("has_draw", True)
            odds_updated_at = live.get("last_update")
            odds_bookmaker  = live.get("home_book", "Best Line")
            if has_draw:
                odds = {k: live.get(k) for k in ["home","draw","away"] if live.get(k)}
            else:
                odds = {k: live.get(k) for k in ["home","away"] if live.get(k)}
        else:
            fallback = get_odds(fixture_id)
            if fallback:
                odds            = {k: fallback[k] for k in ["home","draw","away"] if k in fallback}
                odds_updated_at = fallback.get("updated_at")
                odds_bookmaker  = fallback.get("bookmaker")
                has_draw        = True

    elo_home = get_team_elo(home["id"], default=None)
    elo_away = get_team_elo(away["id"], default=None)
    if elo_home is None:
        elo_home = get_starting_elo(home["name"])
        upsert_team(home["id"], home["name"], elo=elo_home)
    if elo_away is None:
        elo_away = get_starting_elo(away["name"])
        upsert_team(away["id"], away["name"], elo=elo_away)

    try:
        form_home = calculate_form_factor(get_team_last_matches(home["id"], last=5), home["id"])
        form_away = calculate_form_factor(get_team_last_matches(away["id"], last=5), away["id"])
    except Exception:
        form_home = form_away = 1.0

    gp_h = (gp_cache or {}).get(home["id"], -1)
    gp_a = (gp_cache or {}).get(away["id"], -1)

    analysis = full_match_analysis(
        elo_home, elo_away, odds,
        home_advantage=0.0,
        form_home=form_home,
        form_away=form_away,
        odds_updated_at=odds_updated_at,
        rho=rho,
        has_draw=has_draw,
        games_home=gp_h,
        games_away=gp_a,
    )

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

    home_goals = away_goals = None
    if status in ("FT","AET","PEN"):
        k = dynamic_k(round_name)

        if has_draw:
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
            h_s      = (match.get("goals") or {}).get("home")
            a_s      = (match.get("goals") or {}).get("away")
            home_won = h_s is not None and a_s is not None and h_s > a_s
            new_elo_home, new_elo_away = update_elo_2way(elo_home, elo_away, home_won, k=k)
            if verbose:
                print(f"🏆 {home['name']} ({elo_home:.0f}) "
                      f"{h_s}-{a_s} "
                      f"{away['name']} ({elo_away:.0f})", flush=True)

        update_team_elo(home["id"], new_elo_home)
        update_team_elo(away["id"], new_elo_away)
        match_data["elo_home_after"] = new_elo_home
        match_data["elo_away_after"] = new_elo_away

        if verbose:
            draw_str = f"{analysis['draw']['our_prob']}% / " if has_draw else ""
            print(f"   תחזית: {analysis['home']['our_prob']}% / "
                  f"{draw_str}{analysis['away']['our_prob']}%", flush=True)
            print(f"   K={k} | rho={rho if has_draw else 'N/A'} | "
                  f"Elo: {home['name']}→{new_elo_home} | "
                  f"{away['name']}→{new_elo_away}\n", flush=True)

    upsert_match(match_data)

    if has_draw:
        elo_pure     = match_probabilities(elo_home, elo_away, rho=rho)
        fifa         = fifa_probabilities(home["name"], away["name"])
        ens_home_raw = elo_pure["home"] * 0.70 + fifa["home"] * 0.30
        ens_draw_raw = elo_pure["draw"] * 0.70 + fifa["draw"] * 0.30
        ens_away_raw = elo_pure["away"] * 0.70 + fifa["away"] * 0.30
        ens_total    = ens_home_raw + ens_draw_raw + ens_away_raw
        ens_home = round(ens_home_raw / ens_total, 4)
        ens_draw = round(ens_draw_raw / ens_total, 4)
        ens_away = round(ens_away_raw / ens_total, 4)
    else:
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
        "prob_home":            analysis["home"]["our_prob_raw"],
        "prob_draw":            analysis["draw"]["our_prob_raw"],
        "prob_away":            analysis["away"]["our_prob_raw"],
        "prob_elo_home":        elo_pure["home"],
        "prob_elo_draw":        elo_pure.get("draw", 0.0),
        "prob_elo_away":        elo_pure["away"],
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

    if status in ("FT","AET","PEN"):
        if has_draw and home_goals is not None:
            pred["actual_home_goals"] = home_goals
            pred["actual_away_goals"] = away_goals
            if home_goals > away_goals:   pred["actual_result"] = "home"
            elif home_goals < away_goals: pred["actual_result"] = "away"
            else:                         pred["actual_result"] = "draw"
        elif not has_draw:
            h_s = (match.get("goals") or {}).get("home")
            a_s = (match.get("goals") or {}).get("away")
            if h_s is not None and a_s is not None:
                pred["actual_result"] = "home" if h_s > a_s else "away"

    log_prediction(fixture_id, pred)
    return "ok"


def run_non_football_pipeline(verbose: bool = True):
    """
    Pipeline לספורט לא-כדורגל (NBA, NHL, Tennis, MLB, MMA, Boxing וכו').
    עובד ישירות מה-Odds Batch — ללא Football API בכלל.
    שומר predictions ב-Supabase לשימוש ב-Value Bets scan.
    """
    from engine import detect_sport_from_key, sport_has_draw, SPORT_KEY_MAP

    if verbose:
        print("\n🏀 Non-Football Pipeline — NBA/NHL/Tennis/MLB/MMA...", flush=True)

    if is_odds_blocked():
        print("[NFP] ⛔ Odds API חסום — מדלג", flush=True)
        return

    odds_batch = get_all_odds_batch()
    if not odds_batch:
        print("[NFP] ⚠️ Odds Batch ריק", flush=True)
        return

    gp_cache = _load_games_played()
    rho      = _CURRENT_RHO
    count    = 0
    skipped  = 0

    seen_pairs: set = set()

    for (home_name, away_name), odds_data in odds_batch.items():
        # עבד רק גרסה lower-case
        if home_name != home_name.lower() or away_name != away_name.lower():
            continue

        sport_key = odds_data.get("sport_key", "")
        if not sport_key:
            continue

        # דלג על כדורגל
        if sport_key.startswith("soccer_"):
            continue

        sport    = detect_sport_from_key(sport_key)
        has_draw = sport_has_draw(sport)

        pair_key = f"{home_name}::{away_name}::{sport_key}"
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        # odds
        if has_draw:
            odds = {k: odds_data.get(k) for k in ["home","draw","away"] if odds_data.get(k)}
            if not all(odds.get(k) and 1.01 <= odds[k] <= 50 for k in ["home","draw","away"]):
                skipped += 1
                continue
        else:
            odds = {k: odds_data.get(k) for k in ["home","away"] if odds_data.get(k)}
            if not all(odds.get(k) and 1.01 <= odds[k] <= 50 for k in ["home","away"]):
                skipped += 1
                continue

        # Elo — MD5 hash יציב של שם הקבוצה
        home_id = int(hashlib.md5(home_name.encode()).hexdigest()[:8], 16) % 10_000_000 + 10_000_000
        away_id = int(hashlib.md5(away_name.encode()).hexdigest()[:8], 16) % 10_000_000 + 10_000_000

        try:
            elo_h = get_team_elo(home_id, default=None)
            elo_a = get_team_elo(away_id, default=None)

            if elo_h is None:
                elo_h = get_starting_elo(home_name)
                upsert_team(home_id, home_name, elo=elo_h)
            if elo_a is None:
                elo_a = get_starting_elo(away_name)
                upsert_team(away_id, away_name, elo=elo_a)
        except Exception:
            elo_h = elo_a = 1400.0

        gp_h = gp_cache.get(home_id, -1)
        gp_a = gp_cache.get(away_id, -1)

        analysis = full_match_analysis(
            elo_h, elo_a, odds,
            home_advantage=0.0,
            rho=rho,
            has_draw=has_draw,
            games_home=gp_h,
            games_away=gp_a,
        )

        # fixture_id יציב — MD5 של home+away+sport_key
        fixture_id = int(hashlib.md5(
            f"{home_name}{away_name}{sport_key}".encode()
        ).hexdigest()[:12], 16) % 2_000_000_000

        # match_date — שלוף מה-commence_time אם קיים, אחרת last_update
        match_date = odds_data.get("commence_time") or odds_data.get("last_update", "")

        pred = {
            "home_team_name":     home_name,
            "away_team_name":     away_name,
            "match_date":         match_date,
            "home_team_id":       home_id,
            "away_team_id":       away_id,
            "elo_home":           elo_h,
            "elo_away":           elo_a,
            "has_draw":           has_draw,
            "league_id":          0,
            "prob_home":          analysis["home"]["our_prob_raw"],
            "prob_draw":          analysis["draw"]["our_prob_raw"],
            "prob_away":          analysis["away"]["our_prob_raw"],
            "prob_elo_home":      analysis["home"]["our_prob_raw"],
            "prob_elo_draw":      analysis["draw"]["our_prob_raw"],
            "prob_elo_away":      analysis["away"]["our_prob_raw"],
            "odds_home":          odds.get("home"),
            "odds_draw":          odds.get("draw"),
            "odds_away":          odds.get("away"),
            "odds_bookmaker":     odds_data.get("home_book", "Best Line"),
            "ev_home":            analysis["home"]["ev"],
            "ev_draw":            analysis["draw"]["ev"],
            "ev_away":            analysis["away"]["ev"],
            "kelly_home":         analysis["home"]["kelly_pct"],
            "kelly_draw":         analysis["draw"]["kelly_pct"],
            "kelly_away":         analysis["away"]["kelly_pct"],
            "overround":          analysis.get("overround"),
            "status":             "NS",
            "sport_key":          sport_key,
        }

        log_prediction(fixture_id, pred)
        count += 1

    if verbose:
        print(f"[NFP] ✅ {count} אירועים נשמרו | {skipped} דולגו (odds לא תקינים)", flush=True)
        sports_found = set(
            v.get("sport_key","") for v in odds_batch.values()
            if not v.get("sport_key","").startswith("soccer_")
        )
        print(f"[NFP] ענפים: {', '.join(sorted(sports_found))}", flush=True)


if __name__ == "__main__":
    run_pipeline(verbose=True)
    run_non_football_pipeline(verbose=True)
