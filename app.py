import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import numpy as np

# --- הגדרות תצוגה כלליות ---
st.set_page_config(page_title="AI Sports Predictor", page_icon="⚽", layout="wide")

# --- טעינת משתנים והתחברות למסד הנתונים ---
load_dotenv()
@st.cache_resource
def init_connection():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# --- כותרת ראשית ---
st.title("📊 AI Sports Predictor - Backtesting Dashboard")
st.markdown("ברוך הבא למרכז השליטה שלך. כאן אנחנו בודקים את ביצועי העבר ומאתרים הזדמנויות לפני שמסכנים כסף אמיתי.")

st.divider()

# --- אזור 1: משיכת הדירוגים העדכניים (Elo) ---
st.subheader("🏆 דירוג עוצמת הנבחרות (Elo) - לאחר האימון")
teams_response = supabase.table("teams").select("name, elo_rating").order("elo_rating", desc=True).execute()

if teams_response.data:
    df_teams = pd.DataFrame(teams_response.data)
    df_teams.index += 1 # שהמספרים יתחילו מ-1 ולא מ-0
    df_teams.columns = ["נבחרת", "מדד Elo"]
    # הצגת הטבלה במסך
    st.dataframe(df_teams, use_container_width=True)
else:
    st.warning("לא נמצאו נתונים בטבלת הקבוצות.")

st.divider()

# --- אזור 2: סימולציית מסחר (Backtest) ---
st.subheader("💰 סימולציית Backtest מבוססת קריטריון קלי")
st.markdown("""
*הערה מקצועית:* מכיוון שה-API החינמי לא מספק יחסי הימורים (Odds) היסטוריים מדויקים ממשחקי 2022, 
הסימולציה הזו משתמשת בהגרלה סטטיסטית שמבוססת על יחסי סוכנות ממוצעים כדי להדגים איך מודל Value Bets מנהל את התקציב שלך, שומר עליך מפשיטת רגל, ומייצר צמיחה ארוכת טווח.
""")

col1, col2 = st.columns(2)
with col1:
    starting_bankroll = st.number_input("הגדר תקציב התחלתי ($)", min_value=100, max_value=10000, value=1000, step=100)
with col2:
    win_rate = st.slider("הגדר אחוז פגיעה משוער למודל (%)", min_value=40, max_value=60, value=52) / 100

# כפתור ההפעלה
if st.button("🚀 הרץ סימולציית מסחר על 64 משחקי מונדיאל"):
    bankroll = starting_bankroll
    history = [bankroll]
    
    for i in range(64):
        # המערכת מסכנת מקסימום 5% לפי קריטריון קלי Fractional
        bet_amount = bankroll * 0.05 
        
        # הגרלת תוצאת המשחק לפי אחוז הפגיעה הסטטיסטי שהוגדר
        won = np.random.random() < win_rate 
        
        if won:
            # נניח רווח ממשחק Value Bet עם יחס ממוצע של 2.10
            bankroll += bet_amount * 1.1 
        else:
            bankroll -= bet_amount
            
        history.append(bankroll)
    
    # ציור הגרף של התקציב
    st.line_chart(history)
    
    # הצגת נתונים סופיים
    final_amount = round(history[-1], 2)
    profit = round(final_amount - starting_bankroll, 2)
    
    metrics_col1, metrics_col2 = st.columns(2)
    metrics_col1.metric("תקציב סופי (לאחר 64 הימורים)", f"${final_amount}")
    
    # צביעת הרווח/הפסד בירוק או אדום
    if profit > 0:
        metrics_col2.metric("רווח נקי", f"+${profit}")
    else:
        metrics_col2.metric("הפסד נקי", f"${profit}")