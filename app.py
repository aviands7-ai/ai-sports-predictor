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

html, body, [class*="css"], .stMarkdown, .stMarkdown p, .stMarkdown div {
    font-family: 'Inter', sans-serif;
    direction: rtl;
    text-align: right;
}

/* כיוון כל המרכיבים */
.stMarkdown { direction: rtl; text-align: right; }
.element-container { direction: rtl; }
div[data-testid="column"] { direction: rtl; }

/* Header */
.main-header {
    background: linear-gradient(135deg, #1d4ed8 0%, #4f46e5 100%);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 24px;
}
.main-header h1 { font-size: 2rem; font-weight: 700; color: #ffffff; margin: 0 0 6px 0; }
.main-header p  { color: #bfdbfe; margin: 0; font-size: 0.92rem; }

/* Metric cards */
.metric-card {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.metric-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.9rem; font-weight: 700; color: #1d4ed8; line-height: 1; margin-bottom: 6px; }
.metric-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }

/* Probability bars */
.prob-bar-container { background: #f8faff; border: 1px solid #dbeafe; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.prob-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.prob-label { font-size: 0.83rem; color: #374151; width: 90px; text-align: right; flex-shrink: 0; font-weight: 500; }
.prob-bar-wrap { flex: 1; background: #e2e8f0; border-radius: 6px; height: 28px; overflow: hidden; }
.prob-bar-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; padding: 0 10px; font-size: 0.82rem; font-weight: 600; color: #fff; }
.bar-home { background: linear-gradient(90deg, #1d4ed8, #3b82f6); }
.bar-draw { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.bar-away { background: linear-gradient(90deg, #0f766e, #2dd4bf); }

/* Value badge */
.value-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.76rem; font-weight: 600; }
.value-positive { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
.value-negative { background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; }

/* Score matrix */
.score-item { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 10px 14px; text-align: center; margin-bottom: 8px; }
.score-result { font-family: 'Space Grotesk', monospace; font-size: 1.1rem; font-weight: 700; color: #0f172a; }
.score-prob { font-size: 0.74rem; color: #64748b; margin-top: 2px; }

/* Intel section */
.intel-box { background: #f8faff; border: 1px solid #dbeafe; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }
.intel-title { font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.1em; color: #6b7280; margin-bottom: 8px; font-weight: 600; }

/* Alert boxes */
.alert-box { border-radius: 10px; padding: 12px 16px; margin: 10px 0; font-size: 0.87rem; line-height: 1.5; }
.alert-value { background: #f0fdf4; border: 1px solid #86efac; color: #15803d; }
.alert-warn  { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; }
.alert-info  { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }

/* Kelly recommendation */
.kelly-rec { background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 16px 20px; margin-top: 12px; }
.kelly-rec .k-title { font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.1em; color: #15803d; margin-bottom: 6px; font-weight: 600; }
.kelly-rec .k-value { font-family: 'Space Grotesk'; font-size: 1.8rem; font-weight: 700; color: #16a34a; }
.kelly-rec .k-sub   { font-size: 0.8rem; color: #4b5563; margin-top: 4px; }

/* Download button */
.stDownloadButton > button {
    background: linear-gradient(135deg, #16a34a, #22c55e) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; font-size: 1rem !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Imports (after page config) ───────────────────────────────────────────────
from api_client import get_all_fixtures, get_injuries, get_odds, get_head_to_head, get_api_status, get_team_last_matches
from engine import full_match_analysis, match_probabilities, calculate_form_factor, get_starting_elo, odds_freshness
from db import get_all_teams, get_team_elo
from backtest import run_full_backtest
from odds_api import get_live_odds, get_best_odds
from export_report import build_excel_report
from decision_engine import get_flag, get_flag_url, analyze_recent_form, calculate_team_score, generate_decision


# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏆 World Cup 2026 Predictor</h1>
    <p>מנוע חיזוי מבוסס Elo + Poisson Distribution + Kelly Criterion · ניתוח Value Bets בזמן אמת</p>
</div>
""", unsafe_allow_html=True)


# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_intel, tab_value, tab_rankings, tab_backtest, tab_glossary = st.tabs([
    "🔭 Match Intel",
    "💰 Value Bets",
    "📊 Elo Rankings",
    "🧪 Backtest אמיתי",
    "📖 מילון מושגים",
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

            with st.spinner("מנתח משחק..."):
                elo_home = get_team_elo(home["id"])
                elo_away = get_team_elo(away["id"])
                last_home = get_team_last_matches(home["id"], last=5)
                last_away = get_team_last_matches(away["id"], last=5)
                form_home_factor = calculate_form_factor(last_home, home["id"])
                form_away_factor = calculate_form_factor(last_away, away["id"])
                form_home = analyze_recent_form(last_home, home["id"])
                form_away = analyze_recent_form(last_away, away["id"])
                score_home = calculate_team_score(elo_home, form_home, form_home_factor)
                score_away = calculate_team_score(elo_away, form_away, form_away_factor)
                odds_data = get_odds(fixture_id)
                odds = {k: odds_data[k] for k in ["home","draw","away"] if odds_data and k in odds_data} or {}
                analysis = full_match_analysis(elo_home, elo_away, odds, home_advantage=0.0, form_home=form_home_factor, form_away=form_away_factor)
                injuries = get_injuries(fixture_id)
                h2h = get_head_to_head(home["id"], away["id"], last=10)
                live_odds_data = get_best_odds(home["name"], away["name"])
                live_od = None
                if live_odds_data:
                    # סינון odds לא הגיוניים — יחס מעל 30 = כנראה American odds לא מומר
                    raw = {"home": live_odds_data.get("home"), "draw": live_odds_data.get("draw"), "away": live_odds_data.get("away")}
                    if all(v and 1.01 <= v <= 25 for v in raw.values()):
                        live_od = raw
                        # חישוב מחדש עם ה-odds האמיתיים
                        analysis = full_match_analysis(elo_home, elo_away, live_od, home_advantage=0.0, form_home=form_home_factor, form_away=form_away_factor)
                        st.session_state["last_live_odds"] = {"bookmaker": live_odds_data.get("home_book","?"), **live_od}
                    else:
                        live_od = None  # odds שבורים — מתעלמים
                decision = generate_decision(
                    home["name"], away["name"],
                    score_home, score_away,
                    form_home, form_away,
                    {"home": analysis["home"]["our_prob"], "draw": analysis["draw"]["our_prob"], "away": analysis["away"]["our_prob"]},
                    {"home": analysis["home"]["fair_odds"], "draw": analysis["draw"]["fair_odds"], "away": analysis["away"]["fair_odds"]},
                    live_od, elo_home, elo_away,
                )

            st.session_state["match_data"] = {
                "fixture_id": fixture_id, "home": home, "away": away,
                "venue": venue, "city": city, "match_time": match_time,
                "elo_home": elo_home, "elo_away": elo_away,
                "form_home": form_home_factor, "form_away": form_away_factor,
                "analysis": analysis, "injuries": injuries, "h2h": h2h,
                "match_date": selected["fixture"]["date"][:10],
                "form_home_data": form_home, "form_away_data": form_away,
                "score_home": score_home, "score_away": score_away,
                "decision": decision, "live_od": live_od,
            }

        if "match_data" in st.session_state:
            md         = st.session_state["match_data"]
            home       = md["home"]
            away       = md["away"]
            venue      = md["venue"]
            city       = md["city"]
            match_time = md["match_time"]
            elo_home   = md["elo_home"]
            elo_away   = md["elo_away"]
            form_home_factor = md["form_home"]
            form_away_factor = md["form_away"]
            analysis   = md["analysis"]
            injuries   = md["injuries"]
            h2h        = md["h2h"]
            form_home  = md["form_home_data"]
            form_away  = md["form_away_data"]
            score_home = md["score_home"]
            score_away = md["score_away"]
            decision   = md["decision"]
            live_od    = md["live_od"]

            flag_url_h = get_flag_url(home["name"])
            flag_url_a = get_flag_url(away["name"])
            flag_img_h = f'<img src="{flag_url_h}" style="width:80px;height:54px;object-fit:cover;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.3)">' if flag_url_h else f'<div style="font-size:2.5rem;font-weight:800;color:#fff">{home["name"][:2].upper()}</div>'
            flag_img_a = f'<img src="{flag_url_a}" style="width:80px;height:54px;object-fit:cover;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.3)">' if flag_url_a else f'<div style="font-size:2.5rem;font-weight:800;color:#fff">{away["name"][:2].upper()}</div>'

            # ══════════════════════════════════════════════════════
            # SECTION 1 — כותרת משחק
            # ══════════════════════════════════════════════════════
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e3a8a,#312e81);border-radius:16px;padding:28px 32px;margin-bottom:20px;text-align:center">
                <div style="font-size:0.78rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:20px">
                    🏟️ {venue}, {city} &nbsp;·&nbsp; {match_time} UTC
                </div>
                <div style="display:flex;align-items:center;justify-content:center;gap:40px">
                    <div style="text-align:center">
                        {flag_img_h}
                        <div style="font-size:1.3rem;font-weight:700;color:#fff;margin-top:10px">{home["name"]}</div>
                        <div style="font-size:0.8rem;color:#93c5fd;margin-top:2px">Elo {elo_home:.0f}</div>
                    </div>
                    <div style="font-size:2.5rem;color:#60a5fa;font-weight:200;padding:0 10px">VS</div>
                    <div style="text-align:center">
                        {flag_img_a}
                        <div style="font-size:1.3rem;font-weight:700;color:#fff;margin-top:10px">{away["name"]}</div>
                        <div style="font-size:0.8rem;color:#93c5fd;margin-top:2px">Elo {elo_away:.0f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════
            # SECTION 2 — החלטת ההשקעה (הכי בולטת)
            # ══════════════════════════════════════════════════════
            d = decision
            bet = d.get("bet_recommendation")
            winner_flag = get_flag(d["winner_name"]) if d["winner"] != "draw" else "🤝"

            reasons_items = "".join([f'<div style="margin:4px 0;padding:6px 10px;background:#f0fdf4;border-radius:6px">✅ {r}</div>' for r in d["reasons"]])
            risks_items   = "".join([f'<div style="margin:4px 0;padding:6px 10px;background:#fef2f2;border-radius:6px">⚠️ {r}</div>' for r in d["risks"]])
            if not reasons_items:
                reasons_items = '<div style="color:#9ca3af;font-size:0.83rem">אין נימוקים בולטים</div>'
            if not risks_items:
                risks_items = '<div style="color:#9ca3af;font-size:0.83rem">סיכון נמוך</div>'

            if bet:
                bet_section = f'<div style="background:rgba(22,163,74,0.12);border:1px solid #16a34a;border-radius:10px;padding:16px;margin-top:16px"><div style="font-size:0.7rem;text-transform:uppercase;color:#16a34a;font-weight:700;margin-bottom:8px">💰 VALUE BET מזוהה</div><div style="font-size:1.6rem;font-weight:800;color:#16a34a">{bet["kelly"]}% מהתקציב</div><div style="font-size:0.85rem;color:#374151;margin-top:6px">על <b>{bet["outcome"]}</b> &nbsp;·&nbsp; יחס {bet["odds"]} &nbsp;·&nbsp; EV +{bet["ev"]}% &nbsp;·&nbsp; יתרון {bet["edge"]}% על יחס הוגן</div></div>'
            elif live_od:
                bet_section = '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:10px;padding:12px;margin-top:16px;font-size:0.85rem;color:#dc2626">❌ אין Value Bet — היחסים לא מציעים יתרון מתמטי</div>'
            else:
                bet_section = '<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;padding:12px;margin-top:16px;font-size:0.85rem;color:#92400e">⚠️ אין odds זמינים — לא ניתן לחשב Value Bet</div>'

            decision_html = f"""
            <div style="background:#ffffff;border:2px solid {d['confidence_color']};border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 4px 24px rgba(0,0,0,0.08);direction:rtl">

                <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
                <tr>
                <td style="width:70%;vertical-align:top;padding-left:20px">
                    <div style="font-size:0.68rem;text-transform:uppercase;color:#6b7280;font-weight:700;letter-spacing:0.12em;margin-bottom:10px">🎯 המלצת המערכת</div>
                    <div style="font-size:2.4rem;font-weight:800;color:#0f172a;line-height:1">{winner_flag} {d['winner_name']}</div>
                    <div style="font-size:1rem;color:{d['confidence_color']};font-weight:600;margin-top:8px">{d['confidence_emoji']} ביטחון {d['confidence']} &nbsp;·&nbsp; {d['winner_prob']:.0f}% הסתברות</div>
                </td>
                <td style="width:30%;vertical-align:top">
                    <div style="text-align:center;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px">
                        <div style="font-size:0.68rem;color:#6b7280;margin-bottom:8px;text-transform:uppercase">ציון כולל</div>
                        <div style="font-size:2rem;font-weight:800;color:#1d4ed8">{score_home['total']:.0f}</div>
                        <div style="font-size:0.78rem;color:#6b7280;margin-bottom:4px">{home['name']}</div>
                        <div style="font-size:1rem;color:#94a3b8">vs</div>
                        <div style="font-size:2rem;font-weight:800;color:#7c3aed">{score_away['total']:.0f}</div>
                        <div style="font-size:0.78rem;color:#6b7280">{away['name']}</div>
                    </div>
                </td>
                </tr>
                </table>

                <table style="width:100%;border-collapse:collapse;margin-bottom:16px">
                <tr>
                <td style="width:50%;vertical-align:top;padding-left:16px">
                    <div style="font-size:0.68rem;font-weight:700;color:#16a34a;text-transform:uppercase;margin-bottom:8px">נימוקים לבחירה</div>
                    {reasons_items}
                </td>
                <td style="width:50%;vertical-align:top">
                    <div style="font-size:0.68rem;font-weight:700;color:#dc2626;text-transform:uppercase;margin-bottom:8px">סיכונים</div>
                    {risks_items}
                </td>
                </tr>
                </table>

                {bet_section}
            </div>
            """
            st.markdown(decision_html, unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════
            # SECTION 3 — כרטיסי קבוצות (Streamlit Native)
            # ══════════════════════════════════════════════════════
            col_h, col_a = st.columns(2)

            def render_team_panel(col, name, flag_url, elo, score, form, factor):
                with col:
                    # כותרת קבוצה
                    if flag_url:
                        st.markdown(f'<div style="text-align:center;margin-bottom:8px"><img src="{flag_url}" style="width:64px;height:42px;object-fit:cover;border-radius:5px;box-shadow:0 2px 6px rgba(0,0,0,0.15)"></div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="text-align:center;font-size:1.2rem;font-weight:700;color:#0f172a;margin-bottom:2px">{name}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="text-align:center;font-size:0.78rem;color:#6b7280;margin-bottom:16px">Elo {elo:.0f} · טופס {factor:.2f}x</div>', unsafe_allow_html=True)

                    # ציון כולל
                    st.markdown(f'<div style="text-align:center;font-size:2.6rem;font-weight:800;color:#1d4ed8;line-height:1">{score["total"]:.0f}<span style="font-size:1rem;color:#94a3b8;font-weight:400">/100</span></div>', unsafe_allow_html=True)
                    st.markdown('<div style="text-align:center;font-size:0.72rem;color:#6b7280;margin-bottom:16px">ציון כולל</div>', unsafe_allow_html=True)

                    # בארים
                    cats = [("עוצמה (Elo)", score["elo"]), ("טופס", score["form"]), ("התקפה", score["attack"]), ("הגנה", score["defense"])]
                    for cat_name, val in cats:
                        color = "#16a34a" if val >= 65 else "#d97706" if val >= 45 else "#dc2626"
                        st.markdown(f"""
                        <div style="margin-bottom:10px">
                            <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#374151;margin-bottom:4px;direction:rtl">
                                <span style="font-weight:500">{cat_name}</span>
                                <span style="font-weight:700;color:{color}">{val:.0f}</span>
                            </div>
                            <div style="background:#e2e8f0;border-radius:4px;height:10px;overflow:hidden">
                                <div style="background:{color};width:{min(val,100)}%;height:100%;border-radius:4px"></div>
                            </div>
                        </div>""", unsafe_allow_html=True)

                    st.divider()

                    # תוצאות אחרונות
                    st.markdown('<div style="font-size:0.72rem;font-weight:700;color:#374151;text-transform:uppercase;margin-bottom:8px;direction:rtl">5 משחקים אחרונים</div>', unsafe_allow_html=True)
                    results = form.get("results", [])
                    result_colors = {"W": "#16a34a", "D": "#d97706", "L": "#dc2626"}
                    result_labels = {"W": "נ", "D": "ת", "L": "ה"}
                    badges = " ".join([
                        f'<span style="background:{result_colors.get(r,"#94a3b8")};color:#fff;border-radius:5px;padding:4px 10px;font-size:0.8rem;font-weight:700">{result_labels.get(r,"?")}</span>'
                        for r in results
                    ])
                    st.markdown(f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">{badges}</div>', unsafe_allow_html=True)

                    # סטטיסטיקות
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f'<div style="text-align:center;background:#f0fdf4;border-radius:8px;padding:8px"><div style="font-size:1.2rem;font-weight:700;color:#16a34a">{form.get("avg_scored",0):.1f}</div><div style="font-size:0.62rem;color:#6b7280">שערים/מ׳</div></div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div style="text-align:center;background:#fef2f2;border-radius:8px;padding:8px"><div style="font-size:1.2rem;font-weight:700;color:#dc2626">{form.get("avg_conceded",0):.1f}</div><div style="font-size:0.62rem;color:#6b7280">קבלה/מ׳</div></div>', unsafe_allow_html=True)
                    with c3:
                        st.markdown(f'<div style="text-align:center;background:#f5f3ff;border-radius:8px;padding:8px"><div style="font-size:1.2rem;font-weight:700;color:#7c3aed">{form.get("clean_sheets",0)}</div><div style="font-size:0.62rem;color:#6b7280">שערים נקיים</div></div>', unsafe_allow_html=True)

                    # מגמה
                    trend_map = {"rising": ("📈", "עלייה", "#16a34a"), "falling": ("📉", "ירידה", "#dc2626"), "stable": ("➡️", "יציב", "#6b7280"), "unknown": ("❓", "?", "#6b7280")}
                    t_icon, t_label, t_color = trend_map.get(form.get("trend","unknown"), ("❓","?","#6b7280"))
                    streak_text = f" · {form.get('win_streak')} ניצחונות ברצף 🔥" if form.get("win_streak",0) >= 2 else ""
                    st.markdown(f'<div style="text-align:center;margin-top:10px;font-size:0.82rem;color:{t_color};font-weight:600">{t_icon} מגמה: {t_label}{streak_text}</div>', unsafe_allow_html=True)

            render_team_panel(col_h, home["name"], flag_url_h, elo_home, score_home, form_home, form_home_factor)
            render_team_panel(col_a, away["name"], flag_url_a, elo_away, score_away, form_away, form_away_factor)

            # ══════════════════════════════════════════════════════
            # SECTION 4 — הסתברויות + תוצאות + ייצוא
            # ══════════════════════════════════════════════════════
            st.markdown("<br>", unsafe_allow_html=True)
            col_probs, col_scores, col_export = st.columns([5, 3, 2])

            with col_probs:
                st.markdown("#### 📊 הסתברויות ויחסים")

                # טבלה מעוצבת במקום dataframe
                probs_html = """
                <table style="width:100%;border-collapse:collapse;font-size:0.88rem;direction:rtl">
                <thead>
                <tr style="background:#f1f5f9;border-bottom:2px solid #e2e8f0">
                    <th style="padding:10px 14px;text-align:right;color:#374151;font-weight:600">תוצאה</th>
                    <th style="padding:10px 14px;text-align:center;color:#374151;font-weight:600">סיכוי %</th>
                    <th style="padding:10px 14px;text-align:center;color:#374151;font-weight:600">יחס הוגן</th>"""
                if live_od:
                    probs_html += """
                    <th style="padding:10px 14px;text-align:center;color:#374151;font-weight:600">Odds</th>
                    <th style="padding:10px 14px;text-align:center;color:#374151;font-weight:600">EV</th>
                    <th style="padding:10px 14px;text-align:center;color:#374151;font-weight:600">Value?</th>"""
                probs_html += "</tr></thead><tbody>"

                outcome_labels = {"home": f"{home['name']} מנצחת", "draw": "תיקו 🤝", "away": f"{away['name']} מנצחת"}
                for i, (key_o, label_o) in enumerate([("home", outcome_labels["home"]), ("draw", outcome_labels["draw"]), ("away", outcome_labels["away"])]):
                    la = analysis[key_o]
                    bg = "#fafafa" if i % 2 == 0 else "#ffffff"
                    prob_bar_color = {"home": "#3b82f6", "draw": "#a855f7", "away": "#14b8a6"}[key_o]
                    prob_bar_w = la['our_prob']

                    prob_cell = f"""
                    <div style="display:flex;align-items:center;gap:8px">
                        <div style="background:#e2e8f0;border-radius:4px;height:8px;width:60px;overflow:hidden;flex-shrink:0">
                            <div style="background:{prob_bar_color};width:{prob_bar_w}%;height:100%;border-radius:4px"></div>
                        </div>
                        <span style="font-weight:700;color:#0f172a">{prob_bar_w}%</span>
                    </div>"""

                    probs_html += f'<tr style="background:{bg};border-bottom:1px solid #f1f5f9"><td style="padding:10px 14px;font-weight:600;color:#1e293b">{label_o}</td><td style="padding:10px 14px;text-align:center">{prob_cell}</td><td style="padding:10px 14px;text-align:center;color:#6b7280;font-family:monospace">{la["fair_odds"]}</td>'

                    if live_od:
                        odd = live_od.get(key_o, 0)
                        ev = la["ev"]
                        is_val = la["is_value"] and abs(ev) < 0.30
                        ev_color = "#16a34a" if ev > 0 else "#dc2626"
                        ev_str = f"+{ev:.1%}" if ev > 0 else f"{ev:.1%}"
                        val_badge = '<span style="color:#16a34a;font-size:1.1rem">✅</span>' if is_val else '<span style="color:#dc2626;font-size:1.1rem">❌</span>'
                        probs_html += f'<td style="padding:10px 14px;text-align:center;font-weight:700;color:#0f172a;font-family:monospace">{odd}</td><td style="padding:10px 14px;text-align:center;font-weight:700;color:{ev_color}">{ev_str}</td><td style="padding:10px 14px;text-align:center">{val_badge}</td>'

                    probs_html += "</tr>"

                probs_html += "</tbody></table>"
                if live_od:
                    bm = st.session_state.get("last_live_odds", {}).get("bookmaker", "?")
                    probs_html += f'<div style="font-size:0.75rem;color:#9ca3af;margin-top:6px;text-align:right">Odds מ-{bm}</div>'

                st.markdown(probs_html, unsafe_allow_html=True)

                # פציעות
                home_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == home["id"]]
                away_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == away["id"]]
                if home_inj or away_inj:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**🚑 פצועים ונעדרים:**")
                    for p in home_inj:
                        st.markdown(f"🤕 {p} ({home['name']})")
                    for p in away_inj:
                        st.markdown(f"🤕 {p} ({away['name']})")

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
                    with st.expander(f"⚔️ עימותים ישירים ({len(h2h_records)} אחרונים)"):
                        st.dataframe(pd.DataFrame(h2h_records), use_container_width=True, hide_index=True)

            with col_scores:
                st.markdown("#### ⚽ תוצאות סבירות")
                scores_html = ""
                colors = ["#1d4ed8","#4f46e5","#7c3aed","#9333ea","#a855f7"]
                for idx, (score_str, pct) in enumerate(analysis["top_scores"]):
                    bar_w = min(pct * 4, 100)
                    c = colors[idx] if idx < len(colors) else "#94a3b8"
                    scores_html += f"""
                    <div style="margin-bottom:10px">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                            <span style="font-family:monospace;font-size:1.15rem;font-weight:800;color:#0f172a">{score_str}</span>
                            <span style="font-size:0.82rem;font-weight:600;color:{c}">{pct}%</span>
                        </div>
                        <div style="background:#e2e8f0;border-radius:4px;height:6px;overflow:hidden">
                            <div style="background:{c};width:{bar_w}%;height:100%;border-radius:4px"></div>
                        </div>
                    </div>"""
                st.markdown(scores_html, unsafe_allow_html=True)

            with col_export:
                st.markdown("#### 📥 ייצוא")
                export_match = {
                    "home_name": home["name"], "away_name": away["name"],
                    "match_date": md.get("match_date",""), "venue": venue, "city": city,
                    "elo_home": elo_home, "elo_away": elo_away,
                    "form_home": form_home_factor, "form_away": form_away_factor,
                    "xg_home": analysis["xg_home"], "xg_away": analysis["xg_away"],
                    "probs": {"home": analysis["home"]["our_prob"], "draw": analysis["draw"]["our_prob"], "away": analysis["away"]["our_prob"]},
                    "fair_odds": {"home": analysis["home"]["fair_odds"], "draw": analysis["draw"]["fair_odds"], "away": analysis["away"]["fair_odds"]},
                    "live_odds": live_od,
                    "ev": {"home": analysis["home"]["ev"] if live_od else 0, "draw": analysis["draw"]["ev"] if live_od else 0, "away": analysis["away"]["ev"] if live_od else 0},
                    "kelly": {"home": analysis["home"]["kelly_pct"] if live_od else 0, "draw": analysis["draw"]["kelly_pct"] if live_od else 0, "away": analysis["away"]["kelly_pct"] if live_od else 0},
                    "top_scores": analysis["top_scores"],
                    "injuries_home": home_inj if 'home_inj' in dir() else [],
                    "injuries_away": away_inj if 'away_inj' in dir() else [],
                    "h2h": [{"date": g["fixture"]["date"][:10], "home": g["teams"]["home"]["name"], "result": f"{g['goals']['home'] or 0}-{g['goals']['away'] or 0}", "away": g["teams"]["away"]["name"]} for g in h2h[-5:]] if h2h else [],
                }
                excel_bytes = build_excel_report(export_match, st.session_state.get("last_value_bets",[]), get_all_teams())
                st.download_button(
                    label="📥 הורד Excel",
                    data=excel_bytes,
                    file_name=f"WC2026_{home['name']}_vs_{away['name']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel",
                    use_container_width=True,
                )


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
            df_teams.style.map(color_elo, subset=["מדד Elo"]),
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

# ══════════════════════════════════════════════════════
# TAB 5 — מילון מושגים
# ══════════════════════════════════════════════════════
with tab_glossary:
    st.markdown('<div style="direction:rtl;text-align:right">', unsafe_allow_html=True)
    st.markdown("### 📖 מילון מושגים — כל מה שצריך לדעת")
    st.markdown("המערכת משתמשת במספר מושגים מתמטיים וסטטיסטיים. הנה הסבר ברור לכל אחד מהם.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    terms = [
        {
            "icon": "🏆",
            "term": "Elo Rating — דירוג עוצמה",
            "color": "#1d4ed8",
            "short": "מספר שמייצג את עוצמת הקבוצה. ככל שגבוה יותר — הקבוצה חזקה יותר.",
            "detail": "שיטה שפותחה על ידי הפיזיקאי ארפד אלו לדירוג שחקני שחמט, ומאז אומצה לכדורגל. כל ניצחון מגדיל את הדירוג, כל הפסד מקטין אותו — בהתאם לעוצמת היריב. ניצחון על קבוצה חזקה שווה יותר נקודות מניצחון על קבוצה חלשה.",
            "example": "ברזיל (Elo 1820) vs ספרד (Elo 1760) — ברזיל מועדפת, אבל אם ספרד תנצח, היא תרוויח הרבה נקודות Elo.",
        },
        {
            "icon": "⚽",
            "term": "xG — שערים צפויים (Expected Goals)",
            "color": "#059669",
            "short": "כמה שערים כל קבוצה צפויה לקלוע בהתבסס על עוצמתה.",
            "detail": "המודל משתמש בהתפלגות פואסון כדי לחשב מה ההסתברות לכל תוצאה אפשרית. xG גבוה = קבוצה חזקה התקפית. xG של 1.5 = הקבוצה צפויה לקלוע 1.5 שערים בממוצע.",
            "example": "ארגנטינה (xG 1.8) vs ערב הסעודית (xG 0.7) — ארגנטינה צפויה לשלוט במשחק.",
        },
        {
            "icon": "📈",
            "term": "טופס — Form Factor",
            "color": "#7c3aed",
            "short": "ביצועי הקבוצה ב-5 המשחקים האחרונים, עם דגש על המשחקים הקרובים.",
            "detail": "המשחק האחרון שווה 30% מהמשקל, הראשון רק 10%. מחושב מנ/ת/ה (ניצחון/תיקו/הפסד). ערך מעל 1.0 = טופס טוב, מתחת ל-1.0 = טופס ירוד. Form Factor משפיע ישירות על ה-xG.",
            "example": "קבוצה עם 4 ניצחונות ומשחק אחד תיקו = טופס 1.13x. המודל יגדיל את ה-xG שלה ב-13%.",
        },
        {
            "icon": "💰",
            "term": "EV — Expected Value (תוחלת רווח)",
            "color": "#d97706",
            "short": "כמה % רווח (או הפסד) צפוי על כל 100₪ שמהמרים לטווח ארוך.",
            "detail": "EV = (הסתברות שלנו × יחס) - 1. EV חיובי = יש לנו יתרון מתמטי. EV שלילי = אנחנו בחסרון. לדוגמה: EV +8% על 100₪ = ריווח ממוצע של 8₪ לטווח ארוך.",
            "example": "המודל: Belgium 50% לנצח. האתר: יחס 2.20. EV = (0.50 × 2.20) - 1 = +10%. כדאי להמר!",
        },
        {
            "icon": "🎯",
            "term": "קריטריון קלי — Kelly Criterion",
            "color": "#dc2626",
            "short": "כמה % מהתקציב כדאי לסכן על הימור ספציפי.",
            "detail": "נוסחה מתמטית שפותחה על ידי ג'ון קלי ב-1956. המערכת משתמשת ב-Quarter-Kelly (25% מקלי מלא) לבטיחות. המקסימום הוא 5% מהתקציב על הימור בודד — גם אם קלי מלא מגיע ל-20%.",
            "example": "תקציב 1,000₪. Kelly 3% = להמר 30₪ על המשחק הזה.",
        },
        {
            "icon": "🔢",
            "term": "יחס הוגן — Fair Odds",
            "color": "#0891b2",
            "short": "היחס שאמור להיות ללא margin של האתר.",
            "detail": "אם המודל נותן 40% לקבוצה, היחס ההוגן הוא 1/0.40 = 2.50. כלומר, אם האתר מציע מעל 2.50 — יש לך יתרון. מתחת ל-2.50 — האתר לוקח margin שהופך אותך לנחות.",
            "example": "יחס הוגן: 2.50. האתר מציע: 2.80. יתרון של 12% — זה Value Bet!",
        },
        {
            "icon": "📊",
            "term": "Overround — Margin של האתר",
            "color": "#6b7280",
            "short": "כמה % האתר לוקח לעצמו על כל שוק.",
            "detail": "הסכום של ההסתברויות המשתמעות מכל היחסים. תמיד מעל 100%. ההפרש הוא הרווח של האתר. Overround 5% = על כל 100₪ שמהמרים, האתר שומר 5₪.",
            "example": "יחסים: 2.0 / 3.5 / 4.0. הסתברויות משתמעות: 50% + 28.6% + 25% = 103.6%. Overround = 3.6%.",
        },
        {
            "icon": "📉",
            "term": "Brier Score — ציון כיול",
            "color": "#7c3aed",
            "short": "מדד דיוק המודל. מתחת ל-0.20 = מודל טוב.",
            "detail": "מודד כמה קרובות ההסתברויות שהמודל נותן לתוצאה שבאמת קרתה. 0 = מושלם. 1 = גרוע מאוד. מודל שמנחש אקראית מקבל ~0.33. מודל טוב בכדורגל מקבל ~0.19-0.22.",
            "example": "Brier Score 0.18 = המודל טוב ומכויל נכון.",
        },
        {
            "icon": "🟢",
            "term": "ציון ביטחון — Confidence Level",
            "color": "#16a34a",
            "short": "עד כמה המערכת בטוחה בהמלצה שלה.",
            "detail": "🟢 גבוה = פער ציונים מעל 20 + הסתברות מעל 60%. 🟡 בינוני = פער 10-20 + הסתברות 50-60%. 🔴 נמוך = משחק מאוזן. ביטחון נמוך לא אומר שלא כדאי להמר — רק שהסיכון גבוה יותר.",
            "example": "ברזיל (ציון 82) vs הונדורס (ציון 41) = ביטחון גבוה לברזיל.",
        },
        {
            "icon": "⚡",
            "term": "Value Bet — הימור ערך",
            "color": "#dc2626",
            "short": "הימור שבו לנו יש יתרון מתמטי על האתר.",
            "detail": "Value Bet קיים כאשר: (הסתברות שלנו) > (הסתברות משתמעת מהיחס). בפועל: EV חיובי + יתרון מינימלי של 3% על היחס ההוגן. לא כל Value Bet מנצח — אבל לטווח ארוך, Value Bets צריכים להניב רווח.",
            "example": "אנחנו: 55% לצרפת. האתר: יחס 2.10 (47.6% משתמע). יתרון של 7.4% — Value Bet!",
        },
        {
            "icon": "🧮",
            "term": "Poisson Distribution — התפלגות פואסון",
            "color": "#1d4ed8",
            "short": "מודל מתמטי לחיזוי מספר אירועים בזמן קבוע — כמו שערים במשחק.",
            "detail": "מודל סטטיסטי שמחשב את ההסתברות לכל מספר שערים אפשרי. אם xG = 1.5, פואסון נותן: 22% לאפס שערים, 33% לשער אחד, 25% לשניים, 12% לשלושה וכו'. שילוב ההתפלגויות של שתי הקבוצות נותן הסתברות לכל תוצאה.",
            "example": "xG בית = 1.5, xG חוץ = 0.8 → P(1-0) = 18.5%, P(0-0) = 10.2%, וכו'.",
        },
    ]

    for i in range(0, len(terms), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(terms):
                break
            t = terms[i + j]
            with col:
                st.markdown(f"""
                <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:22px;margin-bottom:16px;border-top:4px solid {t['color']}">
                    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
                        <span style="font-size:1.8rem">{t['icon']}</span>
                        <div>
                            <div style="font-size:1rem;font-weight:700;color:#0f172a">{t['term']}</div>
                            <div style="font-size:0.82rem;color:{t['color']};font-weight:600;margin-top:2px">{t['short']}</div>
                        </div>
                    </div>
                    <div style="font-size:0.83rem;color:#374151;line-height:1.7;margin-bottom:12px">{t['detail']}</div>
                    <div style="background:#f8fafc;border-right:3px solid {t['color']};padding:10px 14px;border-radius:0 8px 8px 0;font-size:0.8rem;color:#374151">
                        <span style="font-weight:700;color:{t['color']}">דוגמה: </span>{t['example']}
                    </div>
                </div>
                """, unsafe_allow_html=True)