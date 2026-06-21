import os
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import numpy as np
from scipy.stats import poisson

# --- הגדרות ---
st.set_page_config(page_title="AI Sports Predictor", page_icon="⚽", layout="wide")
load_dotenv()
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")

@st.cache_resource
def init_connection():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

supabase = init_connection()

# --- פונקציות מתמטיות ---
def calculate_match_probabilities(elo_home, elo_away, home_advantage=50):
    elo_diff = (elo_home + home_advantage) - elo_away
    expected_goals_home = max(0.1, 1.3 + (elo_diff / 200))
    expected_goals_away = max(0.1, 1.3 - (elo_diff / 200))
    max_goals = 5
    home_probs = [poisson.pmf(i, expected_goals_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, expected_goals_away) for i in range(max_goals + 1)]
    home_win, draw, away_win = 0.0, 0.0, 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = home_probs[i] * away_probs[j]
            if i > j: home_win += prob
            elif i == j: draw += prob
            else: away_win += prob
    total = home_win + draw + away_win
    return round(home_win/total, 3), round(draw/total, 3), round(away_win/total, 3)

def fetch_real_odds(fixture_id):
    url = "https://v3.football.api-sports.io/odds"
    headers = {"x-apisports-key": SPORTS_API_KEY}
    params = {"fixture": fixture_id, "bookmaker": "8"} 
    try:
        res = requests.get(url, headers=headers, params=params).json()
        bets = res["response"][0]["bookmakers"][0]["bets"][0]["values"]
        return {b["value"]: float(b["odd"]) for b in bets}
    except:
        return None

def calculate_ev_and_kelly(our_prob, odds):
    if odds is None or odds <= 1.0 or our_prob <= 0: return 0.0, 0.0
    ev = (our_prob * odds) - 1.0
    kelly = ((our_prob * (odds - 1)) - (1 - our_prob)) / (odds - 1) if ev > 0 else 0
    return round(ev, 3), round(min(kelly / 2, 0.05), 3)

def get_team_elo(team_id):
    res = supabase.table("teams").select("elo_rating").eq("id", team_id).execute()
    return res.data[0]["elo_rating"] if res.data else 1500

# --- ממשק משתמש ---
st.title("📊 AI Sports Predictor - Real-Time Pro")
tab1, tab2 = st.tabs(["🔮 מודיעין משחקים", "📈 ביצועים"])

with tab1:
    if st.button("🔄 רענן נתונים מהשרת"):
        st.cache_data.clear()
        st.rerun()

    selected_date = st.date_input("תאריך משחקים", pd.to_datetime("2026-06-21"))
    
    @st.cache_data(ttl=3600)
    def fetch_all_fixtures():
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {"x-apisports-key": SPORTS_API_KEY}
        params = {"league": "1", "season": "2026"}
        return requests.get(url, headers=headers, params=params).json().get("response", [])

    all_data = fetch_all_fixtures()
    
    # סינון תאריכים מדויק
    fixtures = [f for f in all_data if pd.to_datetime(f["fixture"]["date"]).date() == selected_date]
    
    if fixtures:
        match_options = {f"{f['teams']['home']['name']} vs {f['teams']['away']['name']}": f for f in fixtures}
        selected_match_name = st.selectbox("בחר משחק:", list(match_options.keys()))
        selected_match = match_options[selected_match_name]
        
        if st.button("🔍 נתח משחק"):
            with st.spinner("מנתח..."):
                fixture_id = selected_match["fixture"]["id"]
                elo_home = get_team_elo(selected_match["teams"]["home"]["id"])
                elo_away = get_team_elo(selected_match["teams"]["away"]["id"])
                
                prob_home, prob_draw, prob_away = calculate_match_probabilities(elo_home, elo_away)
                odds = fetch_real_odds(fixture_id)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**הסיכויים שלנו:** בית {prob_home*100:.1f}% | חוץ {prob_away*100:.1f}%")
                    if odds:
                        st.write(f"**יחסים (Pinnacle):** {odds.get('Home')} | {odds.get('Away')}")
                        ev, k = calculate_ev_and_kelly(prob_home, odds.get('Home'))
                        if ev > 0: st.success(f"🔥 Value Bet על הבית! (EV: {ev})")
                    else:
                        st.warning("לא נמצאו יחסים זמינים כרגע.")
                with col2:
                    st.write("🚑 *סגל פצועים יעודכן כאן במידה וה-API יחזיר נתונים.*")
    else:
        st.warning("לא נמצאו משחקים לתאריך הנבחר.")

with tab2:
    st.write("Backtesting זמין לניתוח ביצועים.")