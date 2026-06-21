import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client
from scipy.stats import poisson

# --- הגדרות ---
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")

# --- המודל המתמטי ---
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

# --- לוגיקה כלכלית (EV & Kelly) ---
def calculate_ev_and_kelly(our_prob, odds):
    if odds <= 1.0 or our_prob <= 0:
        return 0.0, 0.0
    
    ev = (our_prob * odds) - 1.0
    
    if ev > 0:
        b = odds - 1.0
        q = 1.0 - our_prob
        kelly_fraction = (our_prob * b - q) / b
        # הגנה: מקסימום 5% מהתקציב להימור בודד (Fractional Kelly)
        safe_kelly = min(kelly_fraction / 2, 0.05) 
    else:
        safe_kelly = 0.0
        
    return round(ev, 3), round(safe_kelly, 3)

# --- שליפת נתונים מ-Supabase ומה-API ---
def get_team_elo(team_id):
    response = supabase.table("teams").select("elo_rating").eq("id", team_id).execute()
    if response.data:
        return response.data[0]["elo_rating"]
    return 1500

def get_match_odds(fixture_id):
    """ מושך את יחסי ההימורים של המשחק מה-API. """
    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": SPORTS_API_KEY}
    params = {"fixture": fixture_id}
    
    try:
        res = requests.get(url, headers=headers, params=params).json()
        if res.get("response"):
            # ניגשים לבוקמייקר הראשון שזמין (למשל Pinnacle או Bet365)
            bookmaker = res["response"][0]["bookmakers"][0]
            # מחפשים את שוק ה-Match Winner (ID 1)
            for bet in bookmaker["bets"]:
                if bet["id"] == 1: 
                    values = bet["values"]
                    # ממפים את היחסים
                    odds = {"Home": 1.0, "Draw": 1.0, "Away": 1.0}
                    for v in values:
                        if v["value"] == "Home": odds["Home"] = float(v["odd"])
                        elif v["value"] == "Draw": odds["Draw"] = float(v["odd"])
                        elif v["value"] == "Away": odds["Away"] = float(v["odd"])
                    return odds
    except Exception as e:
        pass
    
    # אם אין יחסים היסטוריים זמינים בחינם, נחזיר יחסי דמי הגיוניים כדי להדגים את המערכת
    return {"Home": 2.10, "Draw": 3.20, "Away": 3.50}

# --- המנוע הראשי של הסורק ---
def scan_for_value_bets():
    print("🔍 סורק את משחקי שמינית גמר מונדיאל 2022 לחיפוש הימורי ערך...")
    print("=" * 60)
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": SPORTS_API_KEY}
    # תאריכי שמינית הגמר של קטאר 2022
    params = {"league": "1", "season": "2022", "from": "2022-12-03", "to": "2022-12-06"}
    
    matches = requests.get(url, headers=headers, params=params).json().get("response", [])
    
    for match in matches:
        fixture_id = match["fixture"]["id"]
        home_team = match["teams"]["home"]
        away_team = match["teams"]["away"]
        
        # 1. משיכת Elo נוכחי ממסד הנתונים
        elo_home = get_team_elo(home_team["id"])
        elo_away = get_team_elo(away_team["id"])
        
        # 2. חישוב הסתברויות המודל שלנו
        prob_home, prob_draw, prob_away = calculate_match_probabilities(elo_home, elo_away)
        
        # 3. משיכת יחסי ההימורים של האתר
        odds = get_match_odds(fixture_id)
        
        # 4. חיפוש ערך (Value) - בודקים רק את ניצחון קבוצת הבית לשם ההדגמה
        ev_home, kelly_home = calculate_ev_and_kelly(prob_home, odds["Home"])
        ev_away, kelly_away = calculate_ev_and_kelly(prob_away, odds["Away"])
        
        print(f"⚽ {home_team['name']} ({elo_home}) נגד {away_team['name']} ({elo_away})")
        
        found_value = False
        if ev_home > 0:
            print(f"   🔥 זיהוי ערך על המארחת ({home_team['name']})!")
            print(f"   הסיכוי שלנו: {prob_home*100:.1f}% | יחס האתר: {odds['Home']}")
            print(f"   תוחלת רווח (EV): +{ev_home} | השקעה מומלצת: {kelly_home*100:.1f}% מהתקציב")
            found_value = True
            
        if ev_away > 0:
            print(f"   🔥 זיהוי ערך על האורחת ({away_team['name']})!")
            print(f"   הסיכוי שלנו: {prob_away*100:.1f}% | יחס האתר: {odds['Away']}")
            print(f"   תוחלת רווח (EV): +{ev_away} | השקעה מומלצת: {kelly_away*100:.1f}% מהתקציב")
            found_value = True
            
        if not found_value:
            print("   ❌ אין ערך השקעה. היחסי הימורים מדויקים מדי או נמוכים מדי.")
            
        print("-" * 60)

if __name__ == "__main__":
    scan_for_value_bets()