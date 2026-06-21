"""
main.py — Pipeline ראשי
1. שואב את כל משחקי מונדיאל 2026
2. מעדכן Elo מכל משחק שהסתיים (כרונולוגית)
3. שומר תחזיות למשחקים עתידיים
"""

from api_client import get_all_fixtures, get_odds
from engine import update_elo, full_match_analysis
from db import (
    upsert_team, update_team_elo, get_team_elo,
    upsert_match, log_prediction
)


def run_pipeline(verbose: bool = True):
    from api_client import get_all_fixtures

    if verbose:
        print("🚀 שואב משחקי מונדיאל 2026...")

    fixtures = get_all_fixtures()
    if not fixtures:
        print("❌ לא נמצאו משחקים. בדוק API key וחיבור.")
        return

    if verbose:
        print(f"📊 נמצאו {len(fixtures)} משחקים. מתחיל לעבד...")
        print("─" * 60)

    for match in fixtures:
        _process_match(match, verbose)

    if verbose:
        print("─" * 60)
        print("✅ Pipeline הסתיים. כל הדירוגים עודכנו ב-Supabase.")


def _process_match(match: dict, verbose: bool):
    """מעבד משחק בודד: עדכון Elo + שמירת תחזית."""
    fix = match["fixture"]
    fixture_id = fix["id"]
    match_date = fix["date"]
    status = fix["status"]["short"]

    home = match["teams"]["home"]
    away = match["teams"]["away"]

    # 1. ודא שהקבוצות קיימות ב-DB (Elo=1500 אם חדשות)
    elo_home = get_team_elo(home["id"])
    elo_away = get_team_elo(away["id"])

    if elo_home == 1500.0:
        upsert_team(home["id"], home["name"])
    if elo_away == 1500.0:
        upsert_team(away["id"], away["name"])

    # 2. חישוב תחזית לפי Elo הנוכחי (לפני עדכון!)
    #    מונדיאל = מגרש נייטרלי → home_advantage=0
    odds = get_odds(fixture_id) or {"home": 0.0, "draw": 0.0, "away": 0.0}
    analysis = full_match_analysis(elo_home, elo_away, odds, home_advantage=0.0)

    # 3. שמירת המשחק הבסיסי
    match_data = {
        "fixture_id": fixture_id,
        "match_date": match_date,
        "home_team_id": home["id"],
        "home_team_name": home["name"],
        "away_team_id": away["id"],
        "away_team_name": away["name"],
        "home_win_prob": analysis["home"]["our_prob_raw"],
        "draw_prob": analysis["draw"]["our_prob_raw"],
        "away_win_prob": analysis["away"]["our_prob_raw"],
        "status": status,
        "elo_home_before": elo_home,
        "elo_away_before": elo_away,
    }

    if status in ("FT", "AET", "PEN"):
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        match_data["home_goals"] = home_goals
        match_data["away_goals"] = away_goals

        # 4. למידה: עדכון Elo
        new_elo_home, new_elo_away = update_elo(
            elo_home, elo_away, home_goals, away_goals, status, k=40
        )
        update_team_elo(home["id"], new_elo_home)
        update_team_elo(away["id"], new_elo_away)

        match_data["elo_home_after"] = new_elo_home
        match_data["elo_away_after"] = new_elo_away

        if verbose:
            result = f"{home_goals}-{away_goals}"
            pred = "בית" if analysis["home"]["our_prob_raw"] > analysis["away"]["our_prob_raw"] else "חוץ"
            actual = "בית" if home_goals > away_goals else ("תיקו" if home_goals == away_goals else "חוץ")
            correct = "✅" if pred == actual or actual == "תיקו" else "❌"
            print(f"{correct} {home['name']} ({elo_home:.0f}) {result} {away['name']} ({elo_away:.0f})")
            print(f"   תחזית: {analysis['home']['our_prob']}% / {analysis['draw']['our_prob']}% / {analysis['away']['our_prob']}%")
            print(f"   Elo חדש: {home['name']}→{new_elo_home} | {away['name']}→{new_elo_away}\n")

    upsert_match(match_data)

    # 5. שמירת תחזית מפורטת בטבלה נפרדת (לbacktest)
    top_scores = analysis.get("top_scores", [])
    prediction_data = {
        "home_team_name": home["name"],
        "away_team_name": away["name"],
        "match_date": match_date,
        "elo_home": elo_home,
        "elo_away": elo_away,
        "prob_home": analysis["home"]["our_prob_raw"],
        "prob_draw": analysis["draw"]["our_prob_raw"],
        "prob_away": analysis["away"]["our_prob_raw"],
        "xg_home": analysis["xg_home"],
        "xg_away": analysis["xg_away"],
        "odds_home": odds.get("home"),
        "odds_draw": odds.get("draw"),
        "odds_away": odds.get("away"),
        "ev_home": analysis["home"]["ev"],
        "ev_draw": analysis["draw"]["ev"],
        "ev_away": analysis["away"]["ev"],
        "kelly_home": analysis["home"]["kelly_pct"],
        "kelly_draw": analysis["draw"]["kelly_pct"],
        "kelly_away": analysis["away"]["kelly_pct"],
        "top_score_1": top_scores[0][0] if top_scores else None,
        "top_score_1_pct": top_scores[0][1] if top_scores else None,
        "overround": analysis.get("overround"),
        "status": status,
    }

    # אם המשחק הסתיים, שמור גם תוצאה בפועל
    if status in ("FT", "AET", "PEN"):
        home_goals = match["goals"]["home"] or 0
        away_goals = match["goals"]["away"] or 0
        if home_goals > away_goals:
            prediction_data["actual_result"] = "home"
        elif home_goals < away_goals:
            prediction_data["actual_result"] = "away"
        else:
            prediction_data["actual_result"] = "draw"

    log_prediction(fixture_id, prediction_data)


if __name__ == "__main__":
    run_pipeline(verbose=True)
