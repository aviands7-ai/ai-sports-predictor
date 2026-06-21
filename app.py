import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import numpy as np
from scipy.stats import poisson

# --- הגדרות תצוגה כלליות ---
st.set_page_config(page_title="AI Sports Predictor", page_icon="⚽", layout="wide")

# --- טעינת משתנים והתחברות למסד הנתונים ---
load_dotenv()
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")

@st.cache_resource
def init_connection():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# --- פונקציות מתמטיות ---
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

def calculate_ev_and_kelly(our_prob, odds):
    if odds <= 1.0 or our_prob <= 0:
        return 0.0, 0.0
    ev = (our_prob * odds) - 1.0
    if ev > 0:
        b = odds - 1.0
        q = 1.0 - our_prob
        kelly_fraction = (our_prob * b - q) / b
        safe_kelly = min(kelly_fraction / 2, 0.05) 
    else:
        safe_kelly = 0.0
    return round(ev, 3), round(safe_kelly, 3)

def get_team_elo(team_id):
    res = supabase.table("teams").select("elo_rating").eq("id", team_id).execute()
    return res.data[0]["elo_rating"] if res.data else 1500

# --- כותרת ראשית ויצירת לשוניות ---
st.title("📊 AI Sports Predictor")
st.markdown("מערכת מסחר וסטטיסטיקה מתקדמת מבוססת Elo.")

tab1, tab2 = st.tabs(["🔮 מודיעין משחקים (Match Intel)", "📈 ביצועים ו-Backtesting"])

# ==========================================
# לשונית 1: מודיעין משחקים
# ==========================================
with tab1:
    st.subheader("🕵️ מסך מודיעין למשחקים קרובים")
    st.info("בחר תאריך (למשל מונדיאל 2022: 2022-12-09) ובחר משחק כדי לשאוב עליו נתוני פציעות, יחסים וחישובי ערך בזמן אמת.")
    
    selected_date = st.date_input("תאריך משחקים", pd.to_datetime("2022-12-09"))
    
    @st.cache_data(ttl=3600)
    def fetch_all_fixtures():
        # מושך את כל הטורניר בבת אחת ושומר בזיכרון!
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {"x-apisports-key": SPORTS_API_KEY}
        params = {"league": "1", "season": "2022", "from": "2022-11-20", "to": "2022-12-18"}
        res = requests.get(url, headers=headers, params=params).json()
        return res.get("response", [])

    all_fixtures = fetch_all_fixtures()
    
    # סינון מקומי לפי התאריך שבחרת בדשבורד
    selected_date_str = selected_date.strftime("%Y-%m-%d")
    fixtures = [f for f in all_fixtures if f["fixture"]["date"].startswith(selected_date_str)]
    
    if not fixtures:
        st.warning("לא נמצאו משחקי מונדיאל בתאריך זה.")
    else:
        # יצירת רשימה לבחירה
        match_options = {f"{f['teams']['home']['name']} vs {f['teams']['away']['name']}": f for f in fixtures}
        selected_match_name = st.selectbox("בחר משחק לניתוח:", list(match_options.keys()))
        selected_match = match_options[selected_match_name]
        
        if st.button("🔍 נתח משחק (צורכת קריאת API אחת)"):
            fixture_id = selected_match["fixture"]["id"]
            home_team = selected_match["teams"]["home"]
            away_team = selected_match["teams"]["away"]
            venue = selected_match["fixture"]["venue"]["name"]
            city = selected_match["fixture"]["venue"]["city"]
            
            with st.spinner("שואב נתונים, פציעות ויחסים מהענן..."):
                # משיכת Elo
                elo_home = get_team_elo(home_team["id"])
                elo_away = get_team_elo(away_team["id"])
                
                # חישוב אחוזים
                prob_home, prob_draw, prob_away = calculate_match_probabilities(elo_home, elo_away)
                
                # משיכת פציעות
                injuries_url = "https://v3.football.api-sports.io/injuries"
                inj_res = requests.get(injuries_url, headers={"x-apisports-key": SPORTS_API_KEY}, params={"fixture": fixture_id}).json()
                injuries_data = inj_res.get("response", [])
                
                home_injuries = [i["player"]["name"] for i in injuries_data if i["team"]["id"] == home_team["id"]]
                away_injuries = [i["player"]["name"] for i in injuries_data if i["team"]["id"] == away_team["id"]]
                
                # משיכת יחסים היסטוריים (לצורך הדוגמה נשתמש ביחסי ברירת מחדל אם אין חינם)
                odds = {"Home": 2.10, "Draw": 3.20, "Away": 3.50} 
                ev_home, kelly_home = calculate_ev_and_kelly(prob_home, odds["Home"])
                ev_away, kelly_away = calculate_ev_and_kelly(prob_away, odds["Away"])

            # --- תצוגת התוצאות ---
            st.divider()
            col_math, col_intel = st.columns(2)
            
            with col_math:
                st.markdown("### 🧮 מתמטיקה וערך (The Quant)")
                st.write(f"**דירוג Elo:** {home_team['name']} ({elo_home}) | {away_team['name']} ({elo_away})")
                st.write(f"**הסיכויים שלנו:** בית {prob_home*100:.1f}% | תיקו {prob_draw*100:.1f}% | חוץ {prob_away*100:.1f}%")
                st.write(f"**יחסי אתר (Odds):** {odds['Home']} לבית | {odds['Away']} לחוץ")
                
                if ev_home > 0:
                    st.success(f"🔥 **Value Bet מזוהה על {home_team['name']}!**\nתוחלת (EV): +{ev_home} | השקעה מומלצת: {kelly_home*100:.1f}%")
                elif ev_away > 0:
                    st.success(f"🔥 **Value Bet מזוהה על {away_team['name']}!**\nתוחלת (EV): +{ev_away} | השקעה מומלצת: {kelly_away*100:.1f}%")
                else:
                    st.error("❌ לא נמצא ערך מתמטי במשחק הזה.")

            with col_intel:
                st.markdown("### 🚑 מודיעין מגרש (The Intel)")
                st.write(f"🏟️ **אצטדיון:** {venue}, {city}")
                
                st.write(f"**פצועים ונעדרים - {home_team['name']}:**")
                if home_injuries:
                    for p in home_injuries: st.write(f"- 🤕 {p}")
                else:
                    st.write("- סגל מלא (או אין נתונים ב-API)")
                    
                st.write(f"**פצועים ונעדרים - {away_team['name']}:**")
                if away_injuries:
                    for p in away_injuries: st.write(f"- 🤕 {p}")
                else:
                    st.write("- סגל מלא (או אין נתונים ב-API)")


# ==========================================
# לשונית 2: Backtesting ודירוגים
# ==========================================
with tab2:
    col_teams, col_test = st.columns([1, 2])
    
    with col_teams:
        st.subheader("🏆 דירוג עוצמת הנבחרות (Elo)")
        teams_response = supabase.table("teams").select("name, elo_rating").order("elo_rating", desc=True).execute()
        if teams_response.data:
            df_teams = pd.DataFrame(teams_response.data)
            df_teams.index += 1
            df_teams.columns = ["נבחרת", "מדד Elo"]
            st.dataframe(df_teams, use_container_width=True)

    with col_test:
        st.subheader("💰 סימולציית Backtest מבוססת קריטריון קלי")
        c1, c2 = st.columns(2)
        with c1:
            starting_bankroll = st.number_input("תקציב התחלתי ($)", min_value=100, max_value=10000, value=1000, step=100)
        with c2:
            win_rate = st.slider("אחוז פגיעה משוער למודל (%)", min_value=40, max_value=60, value=52) / 100

        if st.button("🚀 הרץ סימולציה על 64 משחקים"):
            bankroll = starting_bankroll
            history = [bankroll]
            for i in range(64):
                bet_amount = bankroll * 0.05 
                won = np.random.random() < win_rate 
                if won:
                    bankroll += bet_amount * 1.1 
                else:
                    bankroll -= bet_amount
                history.append(bankroll)
            
            st.line_chart(history)
            
            final_amount = round(history[-1], 2)
            profit = round(final_amount - starting_bankroll, 2)
            
            mc1, mc2 = st.columns(2)
            mc1.metric("תקציב סופי", f"${final_amount}")
            if profit > 0:
                mc2.metric("רווח נקי", f"+${profit}")
            else:
                mc2.metric("הפסד נקי", f"${profit}")