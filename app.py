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
from decision_engine import get_flag, analyze_recent_form, calculate_team_score, generate_decision


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
                    live_od = {"home": live_odds_data.get("home"), "draw": live_odds_data.get("draw"), "away": live_odds_data.get("away")}
                    st.session_state["last_live_odds"] = live_od
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

            flag_h = get_flag(home["name"])
            flag_a = get_flag(away["name"])

            # ══════════════════════════════════════════════════════
            # SECTION 1 — כותרת משחק
            # ══════════════════════════════════════════════════════
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#1e3a8a,#312e81);border-radius:16px;padding:24px 32px;margin-bottom:20px;text-align:center">
                <div style="font-size:0.8rem;color:#93c5fd;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:12px">
                    🏟️ {venue}, {city} &nbsp;·&nbsp; {match_time} UTC
                </div>
                <div style="display:flex;align-items:center;justify-content:center;gap:24px">
                    <div style="text-align:center">
                        <div style="font-size:3.5rem">{flag_h}</div>
                        <div style="font-size:1.3rem;font-weight:700;color:#fff;margin-top:6px">{home["name"]}</div>
                        <div style="font-size:0.8rem;color:#93c5fd">Elo {elo_home:.0f}</div>
                    </div>
                    <div style="font-size:2rem;color:#60a5fa;font-weight:300">VS</div>
                    <div style="text-align:center">
                        <div style="font-size:3.5rem">{flag_a}</div>
                        <div style="font-size:1.3rem;font-weight:700;color:#fff;margin-top:6px">{away["name"]}</div>
                        <div style="font-size:0.8rem;color:#93c5fd">Elo {elo_away:.0f}</div>
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
            <div style="background:#ffffff;border:2px solid {d['confidence_color']};border-radius:16px;padding:24px;margin-bottom:20px;box-shadow:0 4px 24px rgba(0,0,0,0.08)">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:16px">
                    <div>
                        <div style="font-size:0.68rem;text-transform:uppercase;color:#6b7280;font-weight:700;letter-spacing:0.12em;margin-bottom:10px">🎯 המלצת המערכת</div>
                        <div style="font-size:2.4rem;font-weight:800;color:#0f172a;line-height:1">{winner_flag} {d['winner_name']}</div>
                        <div style="font-size:1rem;color:{d['confidence_color']};font-weight:600;margin-top:8px">{d['confidence_emoji']} ביטחון {d['confidence']} &nbsp;·&nbsp; {d['winner_prob']:.0f}% הסתברות</div>
                    </div>
                    <div style="text-align:center;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 28px">
                        <div style="font-size:0.68rem;color:#6b7280;margin-bottom:8px;text-transform:uppercase">ציון כולל</div>
                        <div style="font-size:2.2rem;font-weight:800;color:#1d4ed8">{score_home['total']:.0f}</div>
                        <div style="font-size:0.78rem;color:#6b7280;margin-bottom:4px">{home['name']}</div>
                        <div style="font-size:1rem;color:#94a3b8">vs</div>
                        <div style="font-size:2.2rem;font-weight:800;color:#7c3aed">{score_away['total']:.0f}</div>
                        <div style="font-size:0.78rem;color:#6b7280">{away['name']}</div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                    <div>
                        <div style="font-size:0.68rem;font-weight:700;color:#16a34a;text-transform:uppercase;margin-bottom:8px">נימוקים לבחירה</div>
                        {reasons_items}
                    </div>
                    <div>
                        <div style="font-size:0.68rem;font-weight:700;color:#dc2626;text-transform:uppercase;margin-bottom:8px">סיכונים</div>
                        {risks_items}
                    </div>
                </div>
                {bet_section}
            </div>
            """
            st.markdown(decision_html, unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════
            # SECTION 3 — ניתוח קבוצות זה מול זה
            # ══════════════════════════════════════════════════════
            col_h, col_a = st.columns(2)

            def render_team_card(name, flag, elo, score, form, factor):
                trend_icon = {"rising": "📈", "falling": "📉", "stable": "➡️", "unknown": "❓"}.get(form.get("trend",""), "❓")
                trend_label = {"rising": "עלייה", "falling": "ירידה", "stable": "יציב", "unknown": "?"}.get(form.get("trend",""), "")

                results = form.get("results", [])
                result_html = ""
                for r in results:
                    color = {"W": "#16a34a", "D": "#d97706", "L": "#dc2626"}.get(r, "#94a3b8")
                    label = {"W": "נ", "D": "ת", "L": "ה"}.get(r, "?")
                    result_html += f'<span style="background:{color};color:#fff;border-radius:4px;padding:3px 8px;font-size:0.78rem;font-weight:700;margin:2px">{label}</span>'

                # ציוני קטגוריות
                cats = [
                    ("עוצמה (Elo)", score["elo"]),
                    ("טופס", score["form"]),
                    ("התקפה", score["attack"]),
                    ("הגנה", score["defense"]),
                ]
                bars_html = ""
                for cat_name, cat_val in cats:
                    bar_color = "#16a34a" if cat_val >= 65 else "#d97706" if cat_val >= 45 else "#dc2626"
                    bars_html += f"""
                    <div style="margin-bottom:8px">
                        <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#6b7280;margin-bottom:3px">
                            <span>{cat_name}</span><span style="font-weight:600;color:{bar_color}">{cat_val:.0f}</span>
                        </div>
                        <div style="background:#e2e8f0;border-radius:4px;height:8px;overflow:hidden">
                            <div style="background:{bar_color};width:{cat_val}%;height:100%;border-radius:4px"></div>
                        </div>
                    </div>"""

                return f"""
                <div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;height:100%">
                    <div style="text-align:center;margin-bottom:16px">
                        <div style="font-size:2.8rem">{flag}</div>
                        <div style="font-size:1.1rem;font-weight:700;color:#0f172a">{name}</div>
                        <div style="font-size:0.75rem;color:#6b7280">Elo {elo:.0f} · טופס {factor:.2f}x</div>
                    </div>

                    <div style="text-align:center;font-size:2rem;font-weight:800;color:#1d4ed8;margin-bottom:4px">{score['total']:.0f}<span style="font-size:1rem;color:#94a3b8">/100</span></div>
                    <div style="text-align:center;font-size:0.75rem;color:#6b7280;margin-bottom:16px">ציון כולל</div>

                    <div style="margin-bottom:16px">{bars_html}</div>

                    <div style="border-top:1px solid #f1f5f9;padding-top:12px">
                        <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;font-weight:700;margin-bottom:8px">5 משחקים אחרונים</div>
                        <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:10px">{result_html}</div>
                        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center">
                            <div style="background:#f8fafc;border-radius:8px;padding:8px">
                                <div style="font-size:1.1rem;font-weight:700;color:#16a34a">{form.get('avg_scored',0):.1f}</div>
                                <div style="font-size:0.65rem;color:#6b7280">שערים/מ'</div>
                            </div>
                            <div style="background:#f8fafc;border-radius:8px;padding:8px">
                                <div style="font-size:1.1rem;font-weight:700;color:#dc2626">{form.get('avg_conceded',0):.1f}</div>
                                <div style="font-size:0.65rem;color:#6b7280">קבלה/מ'</div>
                            </div>
                            <div style="background:#f8fafc;border-radius:8px;padding:8px">
                                <div style="font-size:1.1rem;font-weight:700;color:#7c3aed">{form.get('clean_sheets',0)}</div>
                                <div style="font-size:0.65rem;color:#6b7280">שערים נקיים</div>
                            </div>
                        </div>
                        <div style="text-align:center;margin-top:10px;font-size:0.82rem;color:#4b5563">
                            {trend_icon} מגמה: <b>{trend_label}</b>
                            {f' · {form.get("win_streak")} ניצחונות ברצף' if form.get("win_streak",0) >= 2 else ''}
                        </div>
                    </div>
                </div>"""

            with col_h:
                st.markdown(render_team_card(home["name"], flag_h, elo_home, score_home, form_home, form_home_factor), unsafe_allow_html=True)
            with col_a:
                st.markdown(render_team_card(away["name"], flag_a, elo_away, score_away, form_away, form_away_factor), unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════
            # SECTION 4 — הסתברויות ותוצאות
            # ══════════════════════════════════════════════════════
            st.markdown("<br>", unsafe_allow_html=True)
            col_probs, col_scores = st.columns([3, 2])

            with col_probs:
                st.markdown("#### 📊 הסתברויות ויחסים")
                rows = []
                for key_o, label_o in [("home", f"{home['name']} מנצחת"), ("draw", "תיקו"), ("away", f"{away['name']} מנצחת")]:
                    la = analysis[key_o]
                    row = {"תוצאה": label_o, "סיכוי %": f"{la['our_prob']}%", "יחס הוגן": la["fair_odds"]}
                    if live_od:
                        odd = live_od.get(key_o, 0)
                        if odd:
                            ev = la["ev"]
                            row["Odds"] = odd
                            row["EV"] = f"+{ev:.1%}" if ev > 0 else f"{ev:.1%}"
                            row["Value?"] = "✅" if la["is_value"] else "❌"
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if live_od:
                    bm = st.session_state.get("last_live_odds", {}).get("bookmaker", "?")
                    st.caption(f"Odds מ-{bm}")

            with col_scores:
                st.markdown("#### ⚽ תוצאות סבירות")
                scores_html = ""
                for score_str, pct in analysis["top_scores"]:
                    scores_html += f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 14px;background:#f8fafc;border-radius:8px;margin-bottom:6px;border:1px solid #e2e8f0">
                        <span style="font-family:monospace;font-size:1.1rem;font-weight:700;color:#0f172a">{score_str}</span>
                        <span style="font-size:0.85rem;color:#6b7280">{pct}%</span>
                    </div>"""
                st.markdown(scores_html, unsafe_allow_html=True)

            # ══════════════════════════════════════════════════════
            # SECTION 5 — מודיעין + ייצוא
            # ══════════════════════════════════════════════════════
            st.markdown("<br>", unsafe_allow_html=True)
            col_intel, col_export = st.columns([2, 1])

            with col_intel:
                # פציעות
                home_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == home["id"]]
                away_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == away["id"]]
                if home_inj or away_inj:
                    st.markdown("**🚑 פצועים ונעדרים:**")
                    inj_cols = st.columns(2)
                    with inj_cols[0]:
                        for p in home_inj:
                            st.markdown(f"🤕 {p} ({home['name']})")
                    with inj_cols[1]:
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

            with col_export:
                st.markdown("**📥 ייצוא:**")
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
                    "injuries_home": home_inj, "injuries_away": away_inj,
                    "h2h": [{"date": g["fixture"]["date"][:10], "home": g["teams"]["home"]["name"], "result": f"{g['goals']['home'] or 0}-{g['goals']['away'] or 0}", "away": g["teams"]["away"]["name"]} for g in h2h[-5:]] if h2h else [],
                }
                excel_bytes = build_excel_report(export_match, st.session_state.get("last_value_bets",[]), get_all_teams())
                st.download_button(
                    label="📥 הורד דוח Excel",
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