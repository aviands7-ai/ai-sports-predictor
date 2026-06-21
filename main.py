import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from scipy.stats import poisson

# --- הגדרות והתחברות ---
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")

# --- המודל המתמטי (פואסון + Elo) ---
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

# --- פונקציות עזר למסד הנתונים ---
def ensure_team_exists(team_id, team_name):
    # בודק אם הקבוצה קיימת, אם לא - יוצר אותה עם Elo 1500
    response = supabase.table("teams").select("id, elo_rating").eq("id", team_id).execute()
    if not response.data:
        supabase.table("teams").insert({"id": team_id, "name": team_name, "elo_rating": 1500}).execute()
        return 1500
    return response.data[0]["elo_rating"]

# --- התהליך המרכזי ---
def run_pipeline():
    print("🚀 מתחיל לעבד את משחקי המונדיאל...")
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": SPORTS_API_KEY}
    params = {"league": "1", "season": "2022", "from": "2022-11-20", "to": "2022-12-18"}
    
    response = requests.get(url, headers=headers, params=params).json()
    matches = response.get("response", [])
    
    print(f"📊 נמצאו {len(matches)} משחקים. מתחיל חישובים ושמירה...")
    
    for match in matches:
        fixture_id = match["fixture"]["id"]
        match_date = match["fixture"]["date"]
        status = match["fixture"]["status"]["short"]
        
        home_team_id = match["teams"]["home"]["id"]
        home_team_name = match["teams"]["home"]["name"]
        away_team_id = match["teams"]["away"]["id"]
        away_team_name = match["teams"]["away"]["name"]
        
        # 1. נוודא שהקבוצות קיימות וניקח את הדירוג שלהן
        elo_home = ensure_team_exists(home_team_id, home_team_name)
        elo_away = ensure_team_exists(away_team_id, away_team_name)
        
        # 2. נחשב את התחזית
        home_win, draw, away_win = calculate_match_probabilities(elo_home, elo_away)
        
        # 3. נשמור את המשחק במסד הנתונים
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
        print(f"✅ נשמר: {home_team_name} נגד {away_team_name} | סיכוי לבית: {home_win*100:.1f}%")

if __name__ == "__main__":
    run_pipeline()
    print("🏁 כל המשחקים עובדו ונשמרו בהצלחה ב-Supabase!")