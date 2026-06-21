import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from scipy.stats import poisson

# --- הגדרות והתחברות ---
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")

# --- מודל פואסון לחזיית שערים ---
def calculate_match_probabilities(elo_home, elo_away, home_advantage=50):
    elo_diff = (elo_home + home_advantage) - elo_away
    expected_goals_home = max(0.1, 1.3 + (elo_diff / 200))
    expected_goals_away = max(0.1, 1.3 - (elo_diff / 200))

    max_goals = 5
    home_probs = [poisson.pmf(i, expected_goals_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, expected_goals_away) for i in range(max_goals + 1)]

    home_win_prob, draw_prob, away_win_prob = 0.0, 0.0, 0.0

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = home_probs[i] * away_probs[j]
            if i > j: home_win_prob += prob
            elif i == j: draw_prob += prob
            else: away_win_prob += prob

    total = home_win_prob + draw_prob + away_win_prob
    return round(home_win_prob / total, 3), round(draw_prob / total, 3), round(away_win_prob / total, 3)

# --- מודל Elo (למידה מתוצאות) ---
def calculate_new_elos(elo_home, elo_away, home_goals, away_goals, status, k=40, home_advantage=50):
    # חישוב התוצאה לה ציפה המודל
    expected_home = 1 / (1 + 10 ** ((elo_away - (elo_home + home_advantage)) / 400))
    expected_away = 1 - expected_home

    # קביעת התוצאה בפועל (1 לניצחון, 0 להפסד, 0.5 לתיקו/פנדלים)
    if status == "PEN":
        actual_home, actual_away = 0.5, 0.5
    elif home_goals > away_goals:
        actual_home, actual_away = 1.0, 0.0
    elif home_goals < away_goals:
        actual_home, actual_away = 0.0, 1.0
    else:
        actual_home, actual_away = 0.5, 0.5

    # חישוב הדירוג החדש
    new_elo_home = elo_home + k * (actual_home - expected_home)
    new_elo_away = elo_away + k * (actual_away - expected_away)

    return round(new_elo_home, 1), round(new_elo_away, 1)

# --- פעולות מסד נתונים (Supabase) ---
def ensure_team_exists(team_id, team_name):
    response = supabase.table("teams").select("id, elo_rating").eq("id", team_id).execute()
    if not response.data:
        supabase.table("teams").insert({"id": team_id, "name": team_name, "elo_rating": 1500}).execute()
        return 1500
    return response.data[0]["elo_rating"]

def update_team_elo_db(team_id, new_elo):
    supabase.table("teams").update({"elo_rating": new_elo}).eq("id", team_id).execute()

# --- המוח המרכזי (Pipeline) ---
def run_pipeline():
    print("🚀 שואב את משחקי מונדיאל 2022 מ-API...")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": SPORTS_API_KEY}
    params = {"league": "1", "season": "2022", "from": "2022-11-20", "to": "2022-12-18"}
    
    response = requests.get(url, headers=headers, params=params).json()
    matches = response.get("response", [])
    
    # שלב קריטי: מיון המשחקים כרונולוגית כדי ללמוד לפי הסדר הנכון!
    matches.sort(key=lambda x: x["fixture"]["timestamp"])
    
    print(f"📊 נמצאו {len(matches)} משחקים. מתחיל לרוץ וללמוד...")
    print("-" * 50)
    
    for match in matches:
        fixture_id = match["fixture"]["id"]
        match_date = match["fixture"]["date"]
        status = match["fixture"]["status"]["short"]
        
        home_team_id = match["teams"]["home"]["id"]
        home_team_name = match["teams"]["home"]["name"]
        away_team_id = match["teams"]["away"]["id"]
        away_team_name = match["teams"]["away"]["name"]
        
        # 1. שליפת הדירוג העדכני רגע לפני שריקת הפתיחה
        elo_home = ensure_team_exists(home_team_id, home_team_name)
        elo_away = ensure_team_exists(away_team_id, away_team_name)
        
        # 2. המודל מחשב תחזית
        home_win, draw, away_win = calculate_match_probabilities(elo_home, elo_away)
        
        # 3. שמירת התחזית במסד הנתונים
        match_data = {
            "fixture_id": fixture_id,
            "match_date": match_date,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_win_prob": home_win,
            "draw_prob": draw,
            "away_win_prob": away_win,
            "status": status
        }
        supabase.table("matches").upsert(match_data).execute()
        
        # 4. למידה: אם המשחק הסתיים, המודל מעדכן דירוגים!
        if status in ["FT", "AET", "PEN"]:
            home_goals = match["goals"]["home"]
            away_goals = match["goals"]["away"]
            
            new_elo_home, new_elo_away = calculate_new_elos(
                elo_home, elo_away, home_goals, away_goals, status
            )
            
            update_team_elo_db(home_team_id, new_elo_home)
            update_team_elo_db(away_team_id, new_elo_away)
            
            # הדפסה יפה לטרמינל כדי שתוכל לראות את התהליך בעיניים
            print(f"⚽ {home_team_name} ({elo_home}) נגד {away_team_name} ({elo_away})")
            print(f"   תחזית: {home_win*100:.1f}% ניצחון לבית | תוצאת סיום: {home_goals}-{away_goals}")
            print(f"   📈 דירוג חדש: {home_team_name} -> {new_elo_home} | {away_team_name} -> {new_elo_away}\n")

if __name__ == "__main__":
    run_pipeline()
    print("🏁 התהליך הסתיים! כל הדירוגים עודכנו ב-Supabase.")