"""
app.py — World Cup 2026 Predictor Dashboard
ממשק מקצועי: Match Intel + Value Bets + Elo Rankings + Backtesting אמיתי
"""

import os
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="World Cup 2026 Predictor",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Space+Grotesk:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    direction: rtl;
}

.stApp {
    background: #0a0e1a;
    color: #e8eaf0;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #0d1b3e 0%, #1a0a2e 100%);
    border: 1px solid #1e3a6e;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(30, 100, 200, 0.08) 0%, transparent 60%);
    pointer-events: none;
}
.main-header h1 {
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}
.main-header p {
    color: #8899bb;
    margin: 0;
    font-size: 0.95rem;
}

/* Metric cards */
.metric-card {
    background: #111827;
    border: 1px solid #1f2d4a;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
}
.metric-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #60a5fa;
    line-height: 1;
    margin-bottom: 6px;
}
.metric-label {
    font-size: 0.78rem;
    color: #6b7a99;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Probability bars */
.prob-bar-container {
    background: #111827;
    border: 1px solid #1f2d4a;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}
.prob-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
}
.prob-label {
    font-size: 0.85rem;
    color: #8899bb;
    width: 60px;
    text-align: right;
    flex-shrink: 0;
}
.prob-bar-wrap {
    flex: 1;
    background: #1a2234;
    border-radius: 6px;
    height: 28px;
    overflow: hidden;
    position: relative;
}
.prob-bar-fill {
    height: 100%;
    border-radius: 6px;
    display: flex;
    align-items: center;
    padding: 0 10px;
    font-size: 0.82rem;
    font-weight: 600;
    color: #fff;
    transition: width 0.8s ease;
}
.bar-home { background: linear-gradient(90deg, #1d4ed8, #3b82f6); }
.bar-draw { background: linear-gradient(90deg, #6b21a8, #a855f7); }
.bar-away { background: linear-gradient(90deg, #0f766e, #14b8a6); }

/* Value badge */
.value-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}
.value-positive { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.value-negative { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }

/* Score matrix */
.score-item {
    background: #111827;
    border: 1px solid #1f2d4a;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
    margin-bottom: 8px;
}
.score-result { font-family: 'Space Grotesk', monospace; font-size: 1.1rem; font-weight: 700; color: #e8eaf0; }
.score-prob { font-size: 0.75rem; color: #6b7a99; margin-top: 2px; }

/* Intel section */
.intel-box {
    background: #0f1927;
    border: 1px solid #1f2d4a;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.intel-title {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #4a6088;
    margin-bottom: 10px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #111827;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
    border: 1px solid #1f2d4a;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #6b7a99;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: #1d4ed8 !important;
    color: #ffffff !important;
}

/* Data tables */
.dataframe { border: none !important; }
.dataframe thead tr th {
    background: #111827 !important;
    color: #6b7a99 !important;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border: none !important;
}
.dataframe tbody tr td {
    background: #0a0e1a !important;
    color: #c8d0e0 !important;
    border-bottom: 1px solid #1a2234 !important;
    font-size: 0.88rem;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    font-size: 0.9rem !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
}

/* Warning / success boxes */
.alert-box {
    border-radius: 10px;
    padding: 14px 18px;
    margin: 12px 0;
    font-size: 0.88rem;
    line-height: 1.5;
}
.alert-value { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); color: #6ee7b7; }
.alert-warn { background: rgba(251, 191, 36, 0.08); border: 1px solid rgba(251, 191, 36, 0.2); color: #fbbf24; }
.alert-info { background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); color: #93c5fd; }

/* Kelly recommendation */
.kelly-rec {
    background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(16,185,129,0.03));
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 12px;
}
.kelly-rec .k-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: #059669; margin-bottom: 8px; }
.kelly-rec .k-value { font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 700; color: #10b981; }
.kelly-rec .k-sub { font-size: 0.8rem; color: #6b7a99; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ─── Imports (after page config) ───────────────────────────────────────────────
from api_client import get_all_fixtures, get_injuries, get_odds, get_head_to_head, get_api_status
from engine import full_match_analysis, match_probabilities
from db import get_all_teams, get_team_elo
from backtest import run_full_backtest


# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏆 World Cup 2026 Predictor</h1>
    <p>מנוע חיזוי מבוסס Elo + Poisson Distribution + Kelly Criterion · ניתוח Value Bets בזמן אמת</p>
</div>
""", unsafe_allow_html=True)


# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_intel, tab_value, tab_rankings, tab_backtest = st.tabs([
    "🔭 Match Intel",
    "💰 Value Bets",
    "📊 Elo Rankings",
    "🧪 Backtest אמיתי"
])


# ══════════════════════════════════════════════════════
# TAB 1 — MATCH INTEL
# ══════════════════════════════════════════════════════
with tab_intel:
    st.markdown("### ניתוח מעמיק של משחק")

    @st.cache_data(ttl=3600, show_spinner=False)
    def load_all_fixtures():
        return get_all_fixtures()

    with st.spinner("טוען לוח משחקים..."):
        all_fixtures = load_all_fixtures()

    if not all_fixtures:
        st.error("לא ניתן לטעון משחקים. בדוק חיבור ו-API Key.")
    else:
        # Filter by date
        col_date, col_match = st.columns([1, 2])
        with col_date:
            selected_date = st.date_input("תאריך", pd.to_datetime("2026-06-11"), label_visibility="collapsed")

        date_str = selected_date.strftime("%Y-%m-%d")
        day_fixtures = [f for f in all_fixtures if f["fixture"]["date"].startswith(date_str)]

        with col_match:
            if not day_fixtures:
                st.warning("אין משחקים בתאריך זה.")
            else:
                match_options = {
                    f"{f['teams']['home']['name']} נגד {f['teams']['away']['name']}": f
                    for f in day_fixtures
                }
                selected_name = st.selectbox("בחר משחק", list(match_options.keys()), label_visibility="collapsed")
                selected = match_options[selected_name]

        if day_fixtures and st.button("🔍 נתח משחק", use_container_width=False):
            fixture_id = selected["fixture"]["id"]
            home = selected["teams"]["home"]
            away = selected["teams"]["away"]
            venue = selected["fixture"]["venue"]["name"]
            city = selected["fixture"]["venue"]["city"]
            match_time = selected["fixture"]["date"][11:16]

            with st.spinner("שואב נתונים..."):
                elo_home = get_team_elo(home["id"])
                elo_away = get_team_elo(away["id"])
                odds = get_odds(fixture_id) or {"home": 0.0, "draw": 0.0, "away": 0.0}
                analysis = full_match_analysis(elo_home, elo_away, odds, home_advantage=0.0)
                injuries = get_injuries(fixture_id)
                h2h = get_head_to_head(home["id"], away["id"], last=10)

            # ─── Match Summary Row ──────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{elo_home:.0f}</div><div class="metric-label">Elo — {home["name"]}</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{elo_away:.0f}</div><div class="metric-label">Elo — {away["name"]}</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{analysis["xg_home"]}</div><div class="metric-label">xG צפוי — {home["name"]}</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{analysis["xg_away"]}</div><div class="metric-label">xG צפוי — {away["name"]}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            col_quant, col_intel = st.columns([3, 2])

            # ─── Quant Column ───────────────────────────────────────
            with col_quant:
                st.markdown("#### 🧮 ניתוח מתמטי")

                # Probability bars
                probs = {
                    "home": (analysis["home"]["our_prob"], f"{home['name']} מנצחת"),
                    "draw": (analysis["draw"]["our_prob"], "תיקו"),
                    "away": (analysis["away"]["our_prob"], f"{away['name']} מנצחת"),
                }
                bar_classes = {"home": "bar-home", "draw": "bar-draw", "away": "bar-away"}

                bars_html = '<div class="prob-bar-container">'
                for key, (pct, label) in probs.items():
                    ev = analysis[key]["ev"]
                    ev_badge = f'<span class="value-badge value-positive">EV +{ev:.1%}</span>' if ev > 0 else f'<span class="value-badge value-negative">EV {ev:.1%}</span>'
                    bars_html += f"""
                    <div class="prob-row">
                        <div class="prob-label">{label}</div>
                        <div class="prob-bar-wrap">
                            <div class="prob-bar-fill {bar_classes[key]}" style="width:{pct}%">{pct}%</div>
                        </div>
                        {ev_badge}
                    </div>"""
                bars_html += "</div>"
                st.markdown(bars_html, unsafe_allow_html=True)

                # Odds comparison
                if odds.get("home"):
                    st.markdown("**יחסי הימורים vs. תחזית:**")
                    odds_df = pd.DataFrame({
                        "תוצאה": [f"{home['name']} מנצחת", "תיקו", f"{away['name']} מנצחת"],
                        "סיכוי שלנו %": [
                            analysis["home"]["our_prob"],
                            analysis["draw"]["our_prob"],
                            analysis["away"]["our_prob"]
                        ],
                        "יחס אתר": [
                            odds.get("home", "-"), odds.get("draw", "-"), odds.get("away", "-")
                        ],
                        "סיכוי משתמע %": [
                            analysis["home"]["implied_prob"],
                            analysis["draw"]["implied_prob"],
                            analysis["away"]["implied_prob"]
                        ],
                        "יחס הוגן": [
                            analysis["home"]["fair_odds"],
                            analysis["draw"]["fair_odds"],
                            analysis["away"]["fair_odds"]
                        ],
                        "EV": [
                            analysis["home"]["ev"],
                            analysis["draw"]["ev"],
                            analysis["away"]["ev"]
                        ],
                    })
                    st.dataframe(odds_df, use_container_width=True, hide_index=True)
                    st.caption(f"Overround אתר: {analysis['overround']}% (margin של הבית)")

                # Kelly recommendation
                best_ev_key = max(["home", "draw", "away"], key=lambda k: analysis[k]["ev"])
                best = analysis[best_ev_key]
                if best["ev"] > 0:
                    outcome_name = {"home": f"{home['name']} מנצחת", "draw": "תיקו", "away": f"{away['name']} מנצחת"}[best_ev_key]
                    st.markdown(f"""
                    <div class="kelly-rec">
                        <div class="k-title">✅ Value Bet זוהה</div>
                        <div class="k-value">{best['kelly_pct']}% מהתקציב</div>
                        <div class="k-sub">על {outcome_name} · יחס {odds.get(best_ev_key, '?')} · EV {best['ev']:.1%} · Quarter-Kelly</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown('<div class="alert-warn">⚠️ אין Value Bet — המודל לא מצא יתרון מתמטי מול יחסי האתר.</div>', unsafe_allow_html=True)

                # Most likely scores
                st.markdown("**תוצאות הסבירות ביותר:**")
                score_cols = st.columns(5)
                for i, (score, pct) in enumerate(analysis["top_scores"]):
                    with score_cols[i]:
                        st.markdown(f'<div class="score-item"><div class="score-result">{score}</div><div class="score-prob">{pct}%</div></div>', unsafe_allow_html=True)

            # ─── Intel Column ───────────────────────────────────────
            with col_intel:
                st.markdown("#### 🕵️ מודיעין שטח")

                # Venue
                st.markdown(f'<div class="intel-box"><div class="intel-title">אצטדיון</div>🏟️ {venue}, {city} · {match_time}</div>', unsafe_allow_html=True)

                # Injuries
                home_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == home["id"]]
                away_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == away["id"]]

                inj_home_html = "".join([f"<div>🤕 {p}</div>" for p in home_inj]) or "<div style='color:#4a6088'>ללא נפגעים מדווחים</div>"
                inj_away_html = "".join([f"<div>🤕 {p}</div>" for p in away_inj]) or "<div style='color:#4a6088'>ללא נפגעים מדווחים</div>"

                st.markdown(f'<div class="intel-box"><div class="intel-title">פצועים — {home["name"]}</div>{inj_home_html}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="intel-box"><div class="intel-title">פצועים — {away["name"]}</div>{inj_away_html}</div>', unsafe_allow_html=True)

                # H2H
                if h2h:
                    h2h_records = []
                    for g in h2h[-5:]:
                        gh = g["goals"]["home"] or 0
                        ga = g["goals"]["away"] or 0
                        h2h_records.append({
                            "תאריך": g["fixture"]["date"][:10],
                            "ביתית": g["teams"]["home"]["name"],
                            "תוצאה": f"{gh}-{ga}",
                            "אורחת": g["teams"]["away"]["name"],
                        })
                    st.markdown(f'<div class="intel-title" style="margin-top:12px">עימותים ישירים (5 אחרונים)</div>', unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(h2h_records), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════
# TAB 2 — VALUE BETS SCANNER
# ══════════════════════════════════════════════════════
with tab_value:
    st.markdown("### 💰 סורק Value Bets — כל המשחקים")
    st.markdown('<div class="alert-info">סורק את כל המשחקים הקרובים ומחפש הסתברויות שהמודל מעריך גבוה יותר מיחסי האתר.</div>', unsafe_allow_html=True)

    if st.button("🔍 הפעל סריקה מלאה", key="scan_btn"):
        @st.cache_data(ttl=1800, show_spinner=False)
        def load_fixtures_for_scan():
            return get_all_fixtures()

        with st.spinner("סורק משחקים..."):
            fixtures = load_fixtures_for_scan()
            upcoming = [f for f in fixtures if f["fixture"]["status"]["short"] in ("NS", "TBD")]

        value_rows = []

        progress = st.progress(0)
        for i, f in enumerate(upcoming):
            progress.progress((i + 1) / max(len(upcoming), 1))
            home = f["teams"]["home"]
            away = f["teams"]["away"]
            fixture_id = f["fixture"]["id"]
            date = f["fixture"]["date"][:10]

            elo_home = get_team_elo(home["id"])
            elo_away = get_team_elo(away["id"])
            odds = get_odds(fixture_id)

            if not odds or not odds.get("home"):
                continue

            analysis = full_match_analysis(elo_home, elo_away, odds, home_advantage=0.0)

            for outcome, label in [("home", home["name"]), ("draw", "תיקו"), ("away", away["name"])]:
                ev = analysis[outcome]["ev"]
                kelly = analysis[outcome]["kelly_pct"]
                if ev > 0:
                    value_rows.append({
                        "תאריך": date,
                        "משחק": f"{home['name']} vs {away['name']}",
                        "הימור על": label,
                        "יחס אתר": odds.get(outcome, "-"),
                        "סיכוי שלנו %": analysis[outcome]["our_prob"],
                        "סיכוי משתמע %": analysis[outcome]["implied_prob"],
                        "EV": round(ev, 3),
                        "Kelly %": kelly,
                        "Overround %": analysis["overround"],
                    })

        progress.empty()

        if not value_rows:
            st.warning("לא נמצאו Value Bets. ייתכן שאין יחסי הימורים זמינים עדיין.")
        else:
            df_value = pd.DataFrame(value_rows).sort_values("EV", ascending=False)
            st.success(f"נמצאו {len(df_value)} Value Bets פוטנציאליים!")
            st.dataframe(df_value, use_container_width=True, hide_index=True)

            # Summary metrics
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df_value)}</div><div class="metric-label">Value Bets שנמצאו</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{df_value["EV"].max():.1%}</div><div class="metric-label">EV מקסימלי</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{df_value["EV"].mean():.1%}</div><div class="metric-label">EV ממוצע</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TAB 3 — ELO RANKINGS
# ══════════════════════════════════════════════════════
with tab_rankings:
    st.markdown("### 📊 דירוג עוצמת הנבחרות")

    @st.cache_data(ttl=600, show_spinner=False)
    def load_teams():
        return get_all_teams()

    teams = load_teams()
    if not teams:
        st.info("טבלת הקבוצות ריקה. הרץ את main.py תחילה.")
    else:
        df_teams = pd.DataFrame(teams)
        df_teams = df_teams[["name", "elo_rating"]].rename(columns={"name": "נבחרת", "elo_rating": "מדד Elo"})
        df_teams.index = range(1, len(df_teams) + 1)

        # Highlight top 4
        def color_elo(val):
            if val >= df_teams["מדד Elo"].quantile(0.85):
                return "color: #10b981; font-weight: 700"
            elif val >= df_teams["מדד Elo"].quantile(0.5):
                return "color: #60a5fa"
            return "color: #6b7a99"

        st.dataframe(
            df_teams.style.applymap(color_elo, subset=["מדד Elo"]),
            use_container_width=True,
            height=600
        )

        # Mini chart
        st.bar_chart(
            df_teams.set_index("נבחרת")["מדד Elo"].head(16),
            color="#1d4ed8"
        )


# ══════════════════════════════════════════════════════
# TAB 4 — REAL BACKTEST
# ══════════════════════════════════════════════════════
with tab_backtest:
    st.markdown("### 🧪 Backtest אמיתי — תוצאות מול תחזיות היסטוריות")
    st.markdown('<div class="alert-info">הבדיקה רצה על תחזיות ששמרת ב-Supabase שיש להן תוצאה ידועה. זה <b>לא סימולציה אקראית</b> — זה ביצועי המודל בפועל.</div>', unsafe_allow_html=True)

    bankroll_input = st.number_input("תקציב התחלתי לסימולציה ($)", min_value=100, max_value=100000, value=1000, step=100)

    if st.button("▶️ הרץ Backtest", key="bt_btn"):
        with st.spinner("מריץ backtest..."):
            results = run_full_backtest(starting_bankroll=float(bankroll_input))

        if "error" in results:
            st.warning(results["error"])
            st.info("הרץ main.py כדי לאכלס תחזיות, ולאחר שמשחקים יסתיימו — הבדיקה תהיה זמינה.")
        else:
            acc = results["accuracy"]
            roi = results["roi"]
            vb = results["value_bets"]
            bs = results["brier_score"]

            # KPI row
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{acc["accuracy_pct"]}%</div><div class="metric-label">דיוק כולל</div></div>', unsafe_allow_html=True)
            with c2:
                roi_color = "#10b981" if roi["roi_pct"] > 0 else "#ef4444"
                st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{roi_color}">{roi["roi_pct"]}%</div><div class="metric-label">ROI על Value Bets</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{bs}</div><div class="metric-label">Brier Score (מתחת ל-0.20 = טוב)</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{vb.get("total_value_bets", 0)}</div><div class="metric-label">Value Bets שהונחו</div></div>', unsafe_allow_html=True)
            with c5:
                profit = roi["profit"]
                profit_color = "#10b981" if profit > 0 else "#ef4444"
                st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{profit_color}">${profit}</div><div class="metric-label">רווח/הפסד נקי</div></div>', unsafe_allow_html=True)

            # Bankroll chart
            if roi.get("history") and len(roi["history"]) > 1:
                st.markdown("**התפתחות תקציב:**")
                st.line_chart(roi["history"])

            # Calibration
            cal = results.get("calibration", [])
            if cal:
                st.markdown("**Calibration — כשאנחנו אומרים X%, זה קורה X% מהזמן?**")
                cal_df = pd.DataFrame(cal)
                cal_df = cal_df[cal_df["count"] > 0]
                if not cal_df.empty:
                    st.dataframe(cal_df.rename(columns={
                        "range": "טווח הסתברות",
                        "predicted": "צפוי %",
                        "actual": "בפועל %",
                        "count": "מדגם"
                    }), hide_index=True, use_container_width=True)

            # Interpretation
            st.markdown("---")
            if roi["roi_pct"] > 5:
                st.markdown('<div class="alert-box alert-value">✅ המודל מראה יתרון חיובי. אם זה נמשך על 50+ משחקים — אפשר לשקול כסף אמיתי בצנע.</div>', unsafe_allow_html=True)
            elif roi["roi_pct"] > 0:
                st.markdown('<div class="alert-box alert-warn">🔶 יתרון קטן — צריך יותר נתונים לאישור סטטיסטי.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-box alert-warn">⚠️ ROI שלילי. המודל עדיין לא מנצח את השוק. אל תשים כסף.</div>', unsafe_allow_html=True)
