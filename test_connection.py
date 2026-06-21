import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. טעינת משתני הסביבה (הסיסמאות) מקובץ ה-.env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")

# 2. התחברות למסד הנתונים Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_supabase():
    print("⏳ בודק חיבור ל-Supabase...")
    try:
        # מושך את הקבוצות שהכנסנו מקודם לטבלת teams
        response = supabase.table("teams").select("*").execute()
        teams = response.data
        if teams:
            print(f"✅ סופאבייס מחובר! מצאתי {len(teams)} קבוצות במסד הנתונים.")
        else:
            print("⚠️ סופאבייס מחובר, אבל הטבלה ריקה.")
    except Exception as e:
        print(f"❌ שגיאת חיבור לסופאבייס: {e}")

def check_sports_api():
    print("\n⏳ מתחבר ל-API של הספורט ומושך את משחקי מונדיאל 2022...")
    
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-apisports-key": SPORTS_API_KEY
    }
    # שינינו לעונת 2022 ולתאריכים של המונדיאל בקטאר
    params = {
        "league": "1",
        "season": "2022",
        "from": "2022-11-20",
        "to": "2022-12-18"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        if "response" in data and len(data["response"]) > 0:
            matches = data["response"]
            print(f"✅ ה-API עובד! נמשכו {len(matches)} משחקים היסטוריים.")
            
            first_match = matches[0]
            home_team = first_match["teams"]["home"]["name"]
            away_team = first_match["teams"]["away"]["name"]
            date = first_match["fixture"]["date"]
            print(f"⚽ דוגמה למשחק: {home_team} נגד {away_team} ({date})")
        else:
            print("❌ ה-API התחבר, אבל לא חזרו משחקים. פלט השרת:", data)
    except Exception as e:
        print(f"❌ שגיאת חיבור ל-API הספורט: {e}")

if __name__ == "__main__":
    print("🚀 מתחיל בדיקת מערכות...")
    print("-" * 30)
    check_supabase()
    check_sports_api()
    print("-" * 30)
    print("🏁 הבדיקה הסתיימה.")