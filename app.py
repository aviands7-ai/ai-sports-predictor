"""
app.py — World Cup 2026 Predictor
גרסה נקייה — Streamlit Native בלבד
"""

import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="World Cup 2026 Predictor",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS מינימלי — רק כיוון ופונט
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; direction: rtl; }
.stTabs [data-baseweb="tab"] { font-size: 0.92rem; font-weight: 600; }
.stDownloadButton > button { background: #16a34a !important; color: white !important; font-weight: 700 !important; border-radius: 8px !important; }
div[data-testid="metric-container"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

from api_client import get_all_fixtures, get_injuries, get_head_to_head, get_team_last_matches
from engine import full_match_analysis, calculate_form_factor, apply_lineup_factor
from db import get_all_teams, get_team_elo
from backtest import run_full_backtest
from odds_api import get_best_odds
from export_report import build_excel_report
from decision_engine import get_flag_url, analyze_recent_form, calculate_team_score, generate_decision
from lineup_analyzer import get_lineup_summary, calculate_lineup_factor
from closing_line import get_clv_report, save_opening_odds
from rho_calibrator import get_current_rho
from fatigue_analyzer import get_fatigue_summary
from ensemble import ensemble_probabilities
from calibration import run_calibration_check

# ─── כותרת ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:36px 20px 28px;background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 50%,#0f172a 100%);border-radius:16px;margin-bottom:24px">
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-bottom:12px">
    <!-- גביע -->
    <path d="M20 8 H44 V30 C44 42 32 46 32 46 C32 46 20 42 20 30 Z" fill="#F59E0B" stroke="#D97706" stroke-width="1.5"/>
    <!-- ידיות -->
    <path d="M20 12 C14 12 10 16 10 22 C10 28 14 30 20 28" stroke="#F59E0B" stroke-width="3" stroke-linecap="round" fill="none"/>
    <path d="M44 12 C50 12 54 16 54 22 C54 28 50 30 44 28" stroke="#F59E0B" stroke-width="3" stroke-linecap="round" fill="none"/>
    <!-- גוף תחתון -->
    <rect x="27" y="46" width="10" height="8" fill="#D97706"/>
    <!-- בסיס -->
    <rect x="20" y="54" width="24" height="4" rx="2" fill="#F59E0B" stroke="#D97706" stroke-width="1"/>
    <!-- ברק פנימי -->
    <path d="M28 16 L32 26 L36 16" fill="#FCD34D" opacity="0.6"/>
    <!-- כוכב -->
    <path d="M32 12 L33.2 15.6 L37 15.6 L34 17.8 L35.2 21.4 L32 19.2 L28.8 21.4 L30 17.8 L27 15.6 L30.8 15.6 Z" fill="#FEF3C7"/>
  </svg>
  <div style="font-size:30px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;margin-bottom:8px">World Cup 2026 Predictor</div>
  <div style="font-size:12px;color:#93c5fd;letter-spacing:0.12em;text-transform:uppercase">Elo &nbsp;·&nbsp; Poisson Distribution &nbsp;·&nbsp; Kelly Criterion &nbsp;·&nbsp; Value Bets</div>
</div>
""", unsafe_allow_html=True)

# ─── טאבים ─────────────────────────────────────────────────────────────────────
tab_intel, tab_value, tab_rankings, tab_backtest, tab_glossary, tab_paper = st.tabs([
    "🔭 ניתוח משחק",
    "💰 Value Bets",
    "📊 דירוג קבוצות",
    "🧪 Backtest",
    "📖 מילון מושגים",
    "📒 תיק וירטואלי",
])



def utc_to_israel(utc_str: str) -> str:
    """ממיר שעת UTC לשעון ישראל (UTC+3 קיץ)."""
    from datetime import datetime, timezone, timedelta
    try:
        # פורמט: "2026-06-21T16:00:00+00:00"
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        israel = dt + timedelta(hours=3)  # ישראל = UTC+3 בקיץ
        return israel.strftime("%H:%M")
    except Exception:
        return utc_str[11:16]

# ══════════════════════════════════════════════════════
# TAB 1 — ניתוח משחק
# ══════════════════════════════════════════════════════
with tab_intel:

    @st.cache_data(ttl=3600, show_spinner=False)
    def load_fixtures():
        return get_all_fixtures()

    with st.spinner("טוען לוח משחקים..."):
        all_fixtures = load_fixtures()

    if not all_fixtures:
        st.error("לא ניתן לטעון משחקים. בדוק חיבור ו-API Key.")
    else:
        # ── בחירת תאריך חכמה — מוצא אוטומטית את המשחק הרלוונטי ──
        from datetime import date, datetime, timezone

        def find_smart_date(fixtures):
            """
            מוצא את התאריך הטוב ביותר:
            1. אם היום יש משחקים — היום
            2. אחרת — התאריך הקרוב הבא שיש בו משחקים
            """
            today = date.today().strftime("%Y-%m-%d")
            dates_with_fixtures = sorted(set(
                f["fixture"]["date"][:10] for f in fixtures
            ))
            # האם יש משחקים היום?
            if today in dates_with_fixtures:
                return today
            # מצא את התאריך הקרוב הבא
            future = [d for d in dates_with_fixtures if d >= today]
            if future:
                return future[0]
            # אם הכל בעבר — תאריך אחרון
            return dates_with_fixtures[-1] if dates_with_fixtures else today

        def find_smart_match(day_fixtures):
            """
            מוצא את המשחק הרלוונטי ביותר ביום נתון:
            1. משחק שמתקיים כרגע (LIVE)
            2. המשחק הקרוב ביותר שטרם התחיל
            3. המשחק האחרון שהסתיים
            """
            now_utc = datetime.now(timezone.utc)
            live = [f for f in day_fixtures if f["fixture"]["status"]["short"] in ("1H","2H","HT","ET","BT","P")]
            if live:
                return live[0]
            upcoming = [f for f in day_fixtures if f["fixture"]["status"]["short"] in ("NS","TBD")]
            if upcoming:
                upcoming.sort(key=lambda x: x["fixture"]["timestamp"])
                return upcoming[0]
            # הכל נגמר — החזר אחרון
            return day_fixtures[-1] if day_fixtures else None

        smart_date = find_smart_date(all_fixtures)
        smart_date_pd = pd.to_datetime(smart_date)

        col_date, col_match, col_btn = st.columns([1, 3, 1])

        with col_date:
            selected_date = st.date_input("תאריך", smart_date_pd, label_visibility="collapsed")

        date_str = selected_date.strftime("%Y-%m-%d")
        day_fixtures = [f for f in all_fixtures if f["fixture"]["date"].startswith(date_str)]

        with col_match:
            if not day_fixtures:
                st.warning("אין משחקים בתאריך זה.")
                selected = None
            else:
                # מצא את המשחק החכם לבחירה אוטומטית
                smart_match = find_smart_match(day_fixtures)
                match_options = {
                    f"{f['teams']['home']['name']} נגד {f['teams']['away']['name']}": f
                    for f in day_fixtures
                }
                match_names = list(match_options.keys())
                # קבע index ברירת מחדל
                default_name = f"{smart_match['teams']['home']['name']} נגד {smart_match['teams']['away']['name']}" if smart_match else match_names[0]
                default_idx = match_names.index(default_name) if default_name in match_names else 0

                # הצג סטטוס המשחק החכם
                if smart_match:
                    status = smart_match["fixture"]["status"]["short"]
                    if status in ("1H","2H","HT","ET","BT","P"):
                        st.caption("🔴 משחק חי כרגע")
                    elif status in ("NS","TBD"):
                        match_time_str = utc_to_israel(smart_match["fixture"]["date"])
                        st.caption(f"⏰ המשחק הקרוב — {match_time_str} 🇮🇱")

                selected_name = st.selectbox("בחר משחק", match_names, index=default_idx, label_visibility="collapsed")
                selected = match_options[selected_name]

        with col_btn:
            analyze = st.button("🔍 נתח", use_container_width=True, type="primary")

        if selected and analyze:
            fixture_id = selected["fixture"]["id"]
            home = selected["teams"]["home"]
            away = selected["teams"]["away"]
            venue = selected["fixture"]["venue"]["name"]
            city  = selected["fixture"]["venue"]["city"]
            match_time_utc = selected["fixture"]["date"][11:16]
            match_time_il = utc_to_israel(selected["fixture"]["date"])
            match_time = match_time_il

            with st.spinner("מנתח..."):
                elo_h = get_team_elo(home["id"])
                elo_a = get_team_elo(away["id"])
                last_h = get_team_last_matches(home["id"], last=5)
                last_a = get_team_last_matches(away["id"], last=5)
                form_h_factor = calculate_form_factor(last_h, home["id"])
                form_a_factor = calculate_form_factor(last_a, away["id"])
                form_h = analyze_recent_form(last_h, home["id"])
                form_a = analyze_recent_form(last_a, away["id"])
                score_h = calculate_team_score(elo_h, form_h, form_h_factor)
                score_a = calculate_team_score(elo_a, form_a, form_a_factor)
                injuries = get_injuries(fixture_id)
                h2h = get_head_to_head(home["id"], away["id"], last=10)
                live_raw = get_best_odds(home["name"], away["name"])
                live_od = None
                if live_raw:
                    raw = {k: live_raw.get(k) for k in ["home","draw","away"]}
                    if all(v and 1.01 <= v <= 25 for v in raw.values()):
                        live_od = raw

                # ── rho מכויל אוטומטית ──
                current_rho = get_current_rho()

                # ── Lineup Factor ──
                lineup_data = get_lineup_summary(fixture_id, home["id"], away["id"])
                lineup_f_h = lineup_data["factor_home"]
                lineup_f_a = lineup_data["factor_away"]

                # ── Fatigue Factor ──
                fatigue_data = get_fatigue_summary(home["id"], away["id"])
                fatigue_f_h = fatigue_data["home"]["factor"]
                fatigue_f_a = fatigue_data["away"]["factor"]

                # ── Ensemble ──
                ensemble_data = ensemble_probabilities(
                    elo_h, elo_a, home["name"], away["name"],
                    form_home=form_h_factor, form_away=form_a_factor,
                    lineup_home=lineup_f_h, lineup_away=lineup_f_a,
                    fatigue_home=fatigue_f_h, fatigue_away=fatigue_f_a,
                    live_odds=live_od,
                )

                analysis = full_match_analysis(
                    elo_h, elo_a, live_od or {},
                    home_advantage=0.0,
                    form_home=form_h_factor,
                    form_away=form_a_factor,
                    lineup_home=lineup_f_h,
                    lineup_away=lineup_f_a,
                    pure_probs=ensemble_data.get("pure"),  # EV מבוסס מודל טהור
                    rho=current_rho,
                )

                # שמור opening odds ל-CLV
                if live_od:
                    save_opening_odds(fixture_id, live_od, {
                        "home": analysis["home"]["our_prob_raw"],
                        "draw": analysis["draw"]["our_prob_raw"],
                        "away": analysis["away"]["our_prob_raw"],
                    })
                decision = generate_decision(
                    home["name"], away["name"], score_h, score_a, form_h, form_a,
                    {"home": analysis["home"]["our_prob"], "draw": analysis["draw"]["our_prob"], "away": analysis["away"]["our_prob"]},
                    {"home": analysis["home"]["fair_odds"], "draw": analysis["draw"]["fair_odds"], "away": analysis["away"]["fair_odds"]},
                    live_od, elo_h, elo_a,
                )

            st.session_state["match_data"] = {
                "home": home, "away": away, "venue": venue, "city": city,
                "match_time": match_time, "match_date": selected["fixture"]["date"][:10],
                "elo_h": elo_h, "elo_a": elo_a,
                "form_h_factor": form_h_factor, "form_a_factor": form_a_factor,
                "form_h": form_h, "form_a": form_a,
                "score_h": score_h, "score_a": score_a,
                "analysis": analysis, "injuries": injuries, "h2h": h2h,
                "live_od": live_od, "decision": decision,
                "live_bm": live_raw.get("home_book","?") if live_raw else "?",
                "lineup_data": lineup_data,
                "lineup_f_h": lineup_f_h,
                "lineup_f_a": lineup_f_a,
                "fatigue_data": fatigue_data,
                "ensemble_data": ensemble_data,
            }

        # ─── תצוגת תוצאות ───────────────────────────────────────
        if "match_data" not in st.session_state:
            st.info("בחר תאריך ומשחק ולחץ 'נתח' כדי להתחיל.")
        else:
            md       = st.session_state["match_data"]
            home     = md["home"]
            away     = md["away"]
            elo_h    = md["elo_h"]
            elo_a    = md["elo_a"]
            form_h   = md["form_h"]
            form_a   = md["form_a"]
            form_h_f = md["form_h_factor"]
            form_a_f = md["form_a_factor"]
            score_h  = md["score_h"]
            score_a  = md["score_a"]
            analysis = md["analysis"]
            injuries = md["injuries"]
            h2h      = md["h2h"]
            live_od  = md["live_od"]
            decision = md["decision"]
            lineup_data = md.get("lineup_data", {})
            lineup_f_h  = md.get("lineup_f_h", 1.0)
            lineup_f_a  = md.get("lineup_f_a", 1.0)
            fatigue_data = md.get("fatigue_data", {})
            ensemble_data = md.get("ensemble_data", {})
            d        = decision
            flag_h   = get_flag_url(home["name"])
            flag_a   = get_flag_url(away["name"])

            flag_img_h = f'<img src="{flag_h}" style="width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">' if flag_h else ""
            flag_img_a = f'<img src="{flag_a}" style="width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">' if flag_a else ""

            # ── 1. כותרת משחק ───────────────────────────────────
            st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;margin:16px 0;direction:rtl">
  <div style="text-align:center;font-size:12px;color:#6b7280;margin-bottom:16px">
    🏟️ {md['venue']}, {md['city']} &nbsp;·&nbsp; {md['match_time']} 🇮🇱 &nbsp;·&nbsp; {md['match_date']}
  </div>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="text-align:right;vertical-align:middle;padding:0 16px 0 0">
        {flag_img_h}
        <div style="font-size:22px;font-weight:600;margin-top:8px">{home['name']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px">Elo {elo_h:.0f} &nbsp;·&nbsp; ציון {score_h['total']:.0f}/100</div>
      </td>
      <td style="text-align:center;width:80px;font-size:16px;color:#9ca3af;font-weight:500">VS</td>
      <td style="text-align:left;vertical-align:middle;padding:0 0 0 16px">
        {flag_img_a}
        <div style="font-size:22px;font-weight:600;margin-top:8px">{away['name']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px">Elo {elo_a:.0f} &nbsp;·&nbsp; ציון {score_a['total']:.0f}/100</div>
      </td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)

            # ── 2. המלצה ────────────────────────────────────────
            conf_colors = {"גבוה": ("#f0fdf4","#16a34a","#dcfce7"), "בינוני": ("#fffbeb","#d97706","#fef3c7"), "נמוך": ("#fef2f2","#dc2626","#fee2e2")}
            bg, fg, border_c = conf_colors.get(d["confidence"], ("#f8fafc","#374151","#e2e8f0"))

            reasons_html = "".join([f"<div>• {r}</div>" for r in d.get("reasons",[])])
            risks_html   = "".join([f"<div>• {r}</div>" for r in d.get("risks",[])])

            bet = d.get("bet_recommendation")
            bet_html = ""
            if bet:
                bet_html = f"""<div style="margin-top:12px;padding-top:12px;border-top:1px solid {border_c};font-size:13px;color:{fg}">
  💰 <strong>Value Bet:</strong> {bet['kelly']}% מהתקציב על <strong>{bet['outcome']}</strong> &nbsp;·&nbsp; יחס {bet['odds']} &nbsp;·&nbsp; EV +{bet['ev']}%
</div>"""
            elif live_od:
                bet_html = f'<div style="margin-top:12px;padding-top:12px;border-top:1px solid {border_c};font-size:13px;color:#6b7280">❌ אין Value Bet — אין יתרון מתמטי ביחסים הנוכחיים</div>'
            else:
                bet_html = f'<div style="margin-top:12px;padding-top:12px;border-top:1px solid {border_c};font-size:13px;color:#6b7280">⚠️ אין odds זמינים למשחק זה</div>'

            st.markdown(f"""
<div style="background:{bg};border:1px solid {border_c};border-radius:12px;padding:20px 24px;margin:12px 0;direction:rtl">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
    <span style="font-size:16px;font-weight:600;color:{fg}">{d['confidence_emoji']} המלצה: {d['winner_name']}</span>
    <span style="margin-right:auto;background:white;border:1px solid {border_c};border-radius:6px;padding:2px 10px;font-size:12px;color:{fg}">ביטחון {d['confidence']} · {d['winner_prob']:.0f}%</span>
  </div>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="width:50%;vertical-align:top;padding-left:16px">
        <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;text-align:right">נימוקים לבחירה</div>
        <div style="font-size:13px;line-height:1.9;color:#374151;text-align:right">{reasons_html or "—"}</div>
      </td>
      <td style="width:50%;vertical-align:top">
        <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;text-align:right">סיכונים</div>
        <div style="font-size:13px;line-height:1.9;color:#374151;text-align:right">{risks_html or "—"}</div>
      </td>
    </tr>
  </table>
  {bet_html}
</div>
""", unsafe_allow_html=True)

            # ── 3. ניתוח קבוצות ─────────────────────────────────
            def team_card_html(name, flag_img, elo, score, form, factor):
                results = form.get("results", [])
                badges = ""
                for r in results:
                    c = {"W":"#dcfce7","D":"#fef3c7","L":"#fee2e2"}[r] if r in "WDL" else "#f1f5f9"
                    tc = {"W":"#16a34a","D":"#d97706","L":"#dc2626"}[r] if r in "WDL" else "#6b7280"
                    label = {"W":"נ","D":"ת","L":"ה"}.get(r,"?")
                    badges += f'<span style="background:{c};color:{tc};border-radius:4px;padding:3px 8px;font-size:12px;font-weight:600">{label}</span>'

                trend_map = {"rising":"📈 עלייה","falling":"📉 ירידה","stable":"➡️ יציב","unknown":"—"}
                trend = trend_map.get(form.get("trend","unknown"),"—")
                streak = f" &nbsp;·&nbsp; 🔥 {form['win_streak']} ברצף" if form.get("win_streak",0) >= 2 else ""

                return f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;direction:rtl;height:100%">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
    {flag_img}
    <span style="font-size:15px;font-weight:600">{name}</span>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:14px">
    <tr>
      <td style="text-align:center;background:#f8fafc;border-radius:8px;padding:8px">
        <div style="font-size:11px;color:#6b7280;margin-bottom:2px">ציון כולל</div>
        <div style="font-size:20px;font-weight:600">{score['total']:.0f}<span style="font-size:11px;color:#9ca3af">/100</span></div>
      </td>
      <td style="width:8px"></td>
      <td style="text-align:center;background:#f8fafc;border-radius:8px;padding:8px">
        <div style="font-size:11px;color:#6b7280;margin-bottom:2px">מגמה</div>
        <div style="font-size:13px;font-weight:500">{trend}</div>
      </td>
    </tr>
  </table>
  <div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;text-align:right">5 משחקים אחרונים</div>
  <div style="display:flex;gap:5px;margin-bottom:14px;justify-content:flex-end">{badges}</div>
  <table style="width:100%;border-collapse:collapse;text-align:center">
    <tr>
      <td style="font-size:11px;color:#6b7280;padding:4px">שערים/מ׳</td>
      <td style="font-size:11px;color:#6b7280;padding:4px">קבלה/מ׳</td>
      <td style="font-size:11px;color:#6b7280;padding:4px">שערים נקיים</td>
    </tr>
    <tr>
      <td style="font-size:18px;font-weight:600;color:#16a34a;padding:2px">{form.get('avg_scored',0):.1f}</td>
      <td style="font-size:18px;font-weight:600;color:#dc2626;padding:2px">{form.get('avg_conceded',0):.1f}</td>
      <td style="font-size:18px;font-weight:600;color:#7c3aed;padding:2px">{form.get('clean_sheets',0)}</td>
    </tr>
  </table>
  <div style="font-size:12px;color:#6b7280;margin-top:10px;text-align:center">{streak}</div>
</div>"""

            c_h, c_a = st.columns(2)
            c_h.markdown(team_card_html(home["name"], flag_img_h, elo_h, score_h, form_h, form_h_f), unsafe_allow_html=True)
            c_a.markdown(team_card_html(away["name"], flag_img_a, elo_a, score_a, form_a, form_a_f), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Lineup Factor — שחקנים חסרים ─────────────────────
            missing_h = lineup_data.get("missing_home", [])
            missing_a = lineup_data.get("missing_away", [])

            if missing_h or missing_a or lineup_f_h < 1.0 or lineup_f_a < 1.0:
                lu_h, lu_a = st.columns(2)
                with lu_h:
                    impact_h = round((1.0 - lineup_f_h) * 100)
                    if missing_h:
                        st.markdown(f"**🚨 שחקנים חסרים — {home['name']}** (השפעה: -{impact_h}% על xG)")
                        for p in missing_h:
                            impact_str = f" (כוכב — השפעה גבוהה)" if p.get("impact",0) >= 0.20 else ""
                            st.markdown(f"• 🤕 {p['name']}{impact_str}")
                    else:
                        st.markdown(f"**✅ {home['name']}** — סגל מלא")

                with lu_a:
                    impact_a = round((1.0 - lineup_f_a) * 100)
                    if missing_a:
                        st.markdown(f"**🚨 שחקנים חסרים — {away['name']}** (השפעה: -{impact_a}% על xG)")
                        for p in missing_a:
                            impact_str = f" (כוכב — השפעה גבוהה)" if p.get("impact",0) >= 0.20 else ""
                            st.markdown(f"• 🤕 {p['name']}{impact_str}")
                    else:
                        st.markdown(f"**✅ {away['name']}** — סגל מלא")

                if lineup_data.get("has_confirmed_lineup"):
                    st.caption("✅ הרכב מאושר זמין")

            # ── עייפות ──────────────────────────────────────────
            if fatigue_data:
                fat_h = fatigue_data.get("home", {})
                fat_a = fatigue_data.get("away", {})
                adv   = fatigue_data.get("relative_advantage")

                f_h_label = fat_h.get("label","")
                f_a_label = fat_a.get("label","")
                f_h_color = fat_h.get("color","#6b7280")
                f_a_color = fat_a.get("color","#6b7280")

                if fat_h.get("days") is not None or fat_a.get("days") is not None:
                    fh_col, fa_col = st.columns(2)
                    fh_col.markdown(f'<span style="color:{f_h_color}">⏱️ **{home["name"]}:** {f_h_label}</span>', unsafe_allow_html=True)
                    fa_col.markdown(f'<span style="color:{f_a_color}">⏱️ **{away["name"]}:** {f_a_label}</span>', unsafe_allow_html=True)
                    if adv == "home":
                        st.caption(f"💪 יתרון מנוחה ל-{home['name']}")
                    elif adv == "away":
                        st.caption(f"💪 יתרון מנוחה ל-{away['name']}")

            # ── Ensemble — השוואת מודלים ─────────────────────────
            if ensemble_data:
                with st.expander("🔬 השוואת מודלים (Ensemble)"):
                    ens = ensemble_data.get("ensemble", {})
                    elo = ensemble_data.get("elo", {})
                    fifa = ensemble_data.get("fifa", {})
                    mkt = ensemble_data.get("market")
                    weights = ensemble_data.get("weights", {})

                    rows_ens = []
                    for key_o, lbl in [("home",f"{home['name']} מנצחת"),("draw","תיקו"),("away",f"{away['name']} מנצחת")]:
                        row = {
                            "תוצאה": lbl,
                            f"Elo+Poisson ({int(weights.get('elo',0)*100)}%)": f"{elo.get(key_o,0)*100:.1f}%",
                            f"FIFA Ranking ({int(weights.get('fifa',0)*100)}%)": f"{fifa.get(key_o,0)*100:.1f}%",
                            "🎯 Ensemble": f"{ens.get(key_o,0)*100:.1f}%",
                        }
                        if mkt:
                            row[f"שוק ({int(weights.get('market',0)*100)}%)"] = f"{mkt.get(key_o,0)*100:.1f}%"
                        rows_ens.append(row)
                    st.dataframe(pd.DataFrame(rows_ens), hide_index=True, use_container_width=True)
                    st.caption("Ensemble = ממוצע משוקלל של כל המודלים")
            col_probs, col_scores = st.columns([3, 2])

            with col_probs:
                rows_html = ""
                for key_o, label_o in [
                    ("home", f"{home['name']} מנצחת"),
                    ("draw", "תיקו"),
                    ("away", f"{away['name']} מנצחת"),
                ]:
                    la = analysis[key_o]
                    ev_str = ""
                    odds_str = "—"
                    val_str = ""
                    if live_od:
                        ev = la["ev"]
                        ev_color = "#16a34a" if ev > 0 else "#dc2626"
                        ev_str = f'<td style="text-align:center;font-weight:600;color:{ev_color};padding:10px 8px">{"+{:.1%}".format(ev) if ev > 0 else "{:.1%}".format(ev)}</td>'
                        odds_str = str(live_od.get(key_o,"—"))
                        val_badge = "✅" if la["is_value"] else "❌"
                        val_str = f'<td style="text-align:center;padding:10px 8px">{val_badge}</td>'

                    rows_html += f"""
<tr style="border-bottom:1px solid #f1f5f9">
  <td style="padding:10px 8px;font-weight:500;text-align:right">{label_o}</td>
  <td style="text-align:center;font-weight:600;padding:10px 8px">{la['our_prob']}%</td>
  <td style="text-align:center;color:#6b7280;padding:10px 8px">{la['fair_odds']}</td>
  <td style="text-align:center;font-weight:500;padding:10px 8px">{odds_str}</td>
  {ev_str}
  {val_str}
</tr>"""

                headers = "<th style='padding:8px;color:#6b7280;font-weight:500;font-size:11px;text-align:right'>תוצאה</th><th style='text-align:center;padding:8px;color:#6b7280;font-weight:500;font-size:11px'>סיכוי</th><th style='text-align:center;padding:8px;color:#6b7280;font-weight:500;font-size:11px'>יחס הוגן</th><th style='text-align:center;padding:8px;color:#6b7280;font-weight:500;font-size:11px'>Odds</th>"
                if live_od:
                    headers += "<th style='text-align:center;padding:8px;color:#6b7280;font-weight:500;font-size:11px'>EV</th><th style='text-align:center;padding:8px;color:#6b7280;font-weight:500;font-size:11px'>Value?</th>"

                st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;direction:rtl;margin-bottom:8px">
  <div style="padding:12px 16px;border-bottom:1px solid #f1f5f9;font-weight:600;font-size:14px;text-align:right">📊 הסתברויות</div>
  <table style="width:100%;border-collapse:collapse;font-size:13px">
    <thead><tr style="background:#f8fafc">{headers}</tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)
                if live_od:
                    st.caption(f"Odds מ-{md.get('live_bm','?')}")

            with col_scores:
                home_name_short = home["name"]
                away_name_short = away["name"]
                scores_rows = ""
                for score_str, pct in analysis["top_scores"]:
                    bar_w = min(int(pct * 5), 100)
                    # פרסר את התוצאה לשני מספרים
                    parts = score_str.split("-")
                    home_goals = parts[0] if len(parts) == 2 else "?"
                    away_goals = parts[1] if len(parts) == 2 else "?"
                    scores_rows += f"""
<div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid #f8fafc;direction:rtl">
  <span style="font-size:12px;color:#374151;min-width:28px;text-align:right">{home_goals}</span>
  <span style="font-size:11px;color:#9ca3af">—</span>
  <span style="font-size:12px;color:#374151;min-width:28px">{away_goals}</span>
  <div style="flex:1;background:#f1f5f9;border-radius:4px;height:6px;overflow:hidden">
    <div style="background:#3b82f6;width:{bar_w}%;height:100%;border-radius:4px"></div>
  </div>
  <span style="font-size:12px;color:#6b7280;min-width:36px;text-align:left">{pct}%</span>
</div>"""

                st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;direction:rtl">
  <div style="font-weight:600;font-size:14px;margin-bottom:8px;text-align:right">⚽ תוצאות סבירות</div>
  <div style="display:flex;font-size:11px;color:#6b7280;margin-bottom:10px;gap:10px">
    <span style="min-width:28px;text-align:right;font-weight:600;color:#1d4ed8">{home_name_short}</span>
    <span>—</span>
    <span style="font-weight:600;color:#7c3aed">{away_name_short}</span>
  </div>
  {scores_rows}
</div>
""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── 5. H2H + פציעות + ייצוא ─────────────────────────
            home_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == home["id"]]
            away_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == away["id"]]

            col_info, col_export = st.columns([3, 1])
            with col_info:
                if home_inj or away_inj:
                    inj_html = "".join([f"<div>🤕 {p} ({home['name']})</div>" for p in home_inj])
                    inj_html += "".join([f"<div>🤕 {p} ({away['name']})</div>" for p in away_inj])
                    st.markdown(f'<div style="direction:rtl;font-size:13px;color:#374151;margin-bottom:12px"><strong>🚑 פצועים ונעדרים:</strong><br>{inj_html}</div>', unsafe_allow_html=True)

                if h2h:
                    h2h_rows = ""
                    for g in h2h[-5:]:
                        gh = g["goals"]["home"] or 0
                        ga = g["goals"]["away"] or 0
                        h2h_rows += f"<tr><td style='padding:6px 8px;color:#6b7280'>{g['fixture']['date'][:10]}</td><td style='padding:6px 8px;text-align:right;direction:rtl'>{g['teams']['home']['name']}</td><td style='padding:6px 8px;text-align:center;font-family:monospace;font-weight:600'>{gh}-{ga}</td><td style='padding:6px 8px'>{g['teams']['away']['name']}</td></tr>"
                    st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;direction:rtl">
  <div style="padding:10px 16px;border-bottom:1px solid #f1f5f9;font-weight:600;font-size:13px">⚔️ עימותים ישירים</div>
  <table style="width:100%;border-collapse:collapse;font-size:13px"><tbody>{h2h_rows}</tbody></table>
</div>""", unsafe_allow_html=True)

            with col_export:
                export_match = {
                    "home_name": home["name"], "away_name": away["name"],
                    "match_date": md["match_date"], "venue": md["venue"], "city": md["city"],
                    "elo_home": elo_h, "elo_away": elo_a,
                    "form_home": form_h_f, "form_away": form_a_f,
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
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 הורד דוח Excel",
                    data=excel_bytes,
                    file_name=f"WC2026_{home['name']}_vs_{away['name']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_excel",
                    use_container_width=True,
                )


# ══════════════════════════════════════════════════════
# TAB 2 — VALUE BETS
# ══════════════════════════════════════════════════════
with tab_value:
    st.markdown("### 💰 סורק Value Bets")
    st.info("סורק את כל המשחקים הקרובים ומחפש יתרון מתמטי מול יחסי ההימורים.")

    if st.button("🔍 הפעל סריקה", key="scan_btn", type="primary"):
        @st.cache_data(ttl=1800, show_spinner=False)
        def load_for_scan():
            return get_all_fixtures()

        with st.spinner("סורק..."):
            fixtures = load_for_scan()
            upcoming = [f for f in fixtures if f["fixture"]["status"]["short"] in ("NS","TBD")]

        # ── משימה 2 (ג'מיני): קריאת Odds אחת לכל המשחקים ──
        from odds_api import get_all_odds_batch, lookup_odds_from_batch
        with st.spinner("שואב Odds — קריאה אחת לכל המשחקים..."):
            odds_batch = get_all_odds_batch()
        st.caption(f"נטענו Odds ל-{len(odds_batch)//2} משחקים בקריאה אחת")

        value_rows = []
        progress = st.progress(0)
        for i, f in enumerate(upcoming):
            progress.progress((i+1)/max(len(upcoming),1))
            h = f["teams"]["home"]
            a = f["teams"]["away"]
            elo_h = get_team_elo(h["id"])
            elo_a = get_team_elo(a["id"])

            # שליפה מהמילון — ללא קריאת API נוספת
            live = lookup_odds_from_batch(odds_batch, h["name"], a["name"])
            if not live:
                continue
            odds = {k: live.get(k) for k in ["home","draw","away"]}
            if not all(v and 1.01 <= v <= 25 for v in odds.values()):
                continue

            an = full_match_analysis(elo_h, elo_a, odds, home_advantage=0.0)
            for outcome, label in [("home", h["name"]), ("draw", "תיקו"), ("away", a["name"])]:
                ev = an[outcome]["ev"]
                kelly = an[outcome]["kelly_pct"]
                if ev > 0.03:
                    value_rows.append({
                        "תאריך": f["fixture"]["date"][:10],
                        "משחק": f"{h['name']} vs {a['name']}",
                        "הימור על": label,
                        "Odds": odds[outcome],
                        "סיכוי %": an[outcome]["our_prob"],
                        "EV": f"+{ev:.1%}",
                        "Kelly %": f"{kelly:.1f}%",
                    })
        progress.empty()

        if not value_rows:
            st.warning("לא נמצאו Value Bets.")
        else:
            df_vb = pd.DataFrame(value_rows).sort_values("EV", ascending=False)
            st.session_state["last_value_bets"] = value_rows
            st.success(f"נמצאו {len(df_vb)} Value Bets!")
            st.dataframe(df_vb, hide_index=True, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Value Bets שנמצאו", len(df_vb))


# ══════════════════════════════════════════════════════
# TAB 3 — דירוג קבוצות
# ══════════════════════════════════════════════════════
with tab_rankings:
    st.markdown("### 📊 דירוג עוצמת הנבחרות (Elo)")

    @st.cache_data(ttl=600, show_spinner=False)
    def load_teams():
        return get_all_teams()

    teams = load_teams()
    if not teams:
        st.info("אין נתונים. הרץ main.py תחילה.")
    else:
        df = pd.DataFrame(teams)[["name","elo_rating"]].rename(columns={"name":"נבחרת","elo_rating":"Elo"})
        df.index = range(1, len(df)+1)
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index("נבחרת")["Elo"].head(16))


# ══════════════════════════════════════════════════════
# TAB 4 — BACKTEST
# ══════════════════════════════════════════════════════
with tab_backtest:
    st.markdown("### 🧪 Backtest אמיתי")
    st.info("בדיקה על תחזיות שנשמרו עם תוצאות ידועות. לא סימולציה.")

    bankroll = st.number_input("תקציב ($)", min_value=100, max_value=100000, value=1000, step=100)

    if st.button("▶️ הרץ Backtest", type="primary"):
        with st.spinner("מריץ..."):
            results = run_full_backtest(starting_bankroll=float(bankroll))

        if "error" in results:
            st.warning(results["error"])
        else:
            acc = results["accuracy"]
            roi = results["roi"]
            vb  = results["value_bets"]
            bs  = results["brier_score"]

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("דיוק כולל", f"{acc['accuracy_pct']}%")
            c2.metric("ROI", f"{roi['roi_pct']}%")
            c3.metric("Brier Score", bs)
            c4.metric("Value Bets", vb.get("total_value_bets",0))
            profit = roi["profit"]
            c5.metric("רווח/הפסד", f"${profit:+.0f}")

            if roi.get("history") and len(roi["history"]) > 1:
                st.line_chart(roi["history"])

            if roi["roi_pct"] > 5:
                st.success("✅ יתרון חיובי. אחרי 50+ משחקים — אפשר לשקול כסף אמיתי.")
            elif roi["roi_pct"] > 0:
                st.warning("🔶 יתרון קטן — צריך יותר נתונים.")
            else:
                st.error("⚠️ ROI שלילי. אל תשים כסף.")

            # ── A/B Testing ──────────────────────────────────────
            ab = results.get("ab_testing", {})
            if ab:
                st.divider()
                st.markdown("### 🔬 A/B Testing — השוואת מודלים")
                st.caption("איזה מודל מייצר הכי הרבה רווח? ROI לכל תצורה במקביל.")

                ab_rows = []
                model_labels = {
                    "elo_pure": "A — Elo טהור",
                    "elo_form": "B — Elo + Form + פציעות",
                    "ensemble": "C — Ensemble מלא",
                }
                for key, label in model_labels.items():
                    m = ab.get(key, {})
                    if m:
                        ab_rows.append({
                            "מודל": label,
                            "ROI %": f"{m['roi_pct']:+.1f}%",
                            "רווח/הפסד": f"${m['profit']:+.0f}",
                            "הימורים": m["bets_placed"],
                            "Win Rate": f"{m['win_rate_pct']:.1f}%",
                            "תקציב סופי": f"${m['final_bankroll']:,.0f}",
                        })

                if ab_rows:
                    st.dataframe(pd.DataFrame(ab_rows), hide_index=True, use_container_width=True)

                    if not results.get("has_ab_data"):
                        st.info("⏳ כרגע כל המודלים מחושבים על אותן הסתברויות. לאחר הוספת עמודות prob_elo_* ו-prob_ensemble_* לטבלת predictions — ההשוואה תהיה מלאה.")

    st.divider()
    st.markdown("### 🎯 Calibration — כיול המודל")
    st.caption("כשאמרנו 60% — האם קרה 60%? זה המדד האמיתי לאיכות מודל.")
    cal = run_calibration_check()
    if "error" in cal:
        st.info(f"⏳ {cal['error']}")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Brier Score", cal["brier_score"], help="מתחת ל-0.20 = מודל טוב")
        c2.metric("Bias כולל", f"{cal['overall_bias']:.1%}")
        c3.metric("תחזיות שנבדקו", cal["n_predictions"])
        st.info(cal["recommendation"])
        if cal.get("buckets"):
            rows_cal = []
            for bname, bdata in cal["buckets"].items():
                if bdata:
                    label = {"low":"הסתברות נמוכה (<35%)","medium":"הסתברות בינונית (35-55%)","high":"הסתברות גבוהה (>55%)"}.get(bname,bname)
                    rows_cal.append({"טווח": label, "צפוי %": bdata["predicted"], "בפועל %": bdata["actual"], "Bias": f"{bdata['bias']:.1%}", "מצב": bdata["status"], "n": bdata["n"]})
            if rows_cal:
                st.dataframe(pd.DataFrame(rows_cal), hide_index=True, use_container_width=True)
    st.caption("האם המודל מנצח את השוק? CLV חיובי = המודל זיהה ערך לפני שהשוק הגיע לאותה מסקנה.")
    clv = get_clv_report()
    if "error" in clv:
        st.info(f"⏳ {clv['error']}")
    else:
        c1, c2, c3 = st.columns(3)
        clv_color = "normal" if clv["avg_clv"] > 0 else "inverse"
        c1.metric("ממוצע CLV", f"{clv['avg_clv']:.1%}", delta=clv["interpretation"].split()[0])
        c2.metric("ניצחנו את השוק", f"{clv['beat_market_pct']}%", delta=f"{clv['positive_clv']}/{clv['n_predictions']}")
        c3.metric("תחזיות עם CLV", clv["n_predictions"])
        st.info(clv["interpretation"])


# ══════════════════════════════════════════════════════
# TAB 5 — מילון מושגים
# ══════════════════════════════════════════════════════
with tab_glossary:
    st.markdown("### 📖 מילון מושגים")
    st.caption("כל המושגים המתמטיים שהמערכת משתמשת בהם — בשפה פשוטה.")
    st.divider()

    terms = [
        ("🏆 Elo Rating — דירוג עוצמה",
         "מספר שמייצג את עוצמת הקבוצה. ככל שגבוה יותר — הקבוצה חזקה יותר.",
         "כל ניצחון מגדיל את הדירוג, כל הפסד מקטין. ניצחון על קבוצה חזקה שווה יותר נקודות. טווח במונדיאל: 1350–1900.",
         "ברזיל (1820) vs ספרד (1760) — ברזיל מועדפת אבל לא בוודאות."),

        ("⚽ xG — שערים צפויים",
         "כמה שערים כל קבוצה צפויה לקלוע על בסיס עוצמתה.",
         "xG 1.5 = הקבוצה צפויה לקלוע 1.5 שערים בממוצע. המודל משתמש בהתפלגות פואסון.",
         "ארגנטינה xG=1.8 vs ערב הסעודית xG=0.7 — ארגנטינה שולטת."),

        ("📈 Form Factor — ביצועים אחרונים",
         "ביצועי הקבוצה ב-5 המשחקים האחרונים. מוצג כ-🟢 ניצחון, 🟡 תיקו, 🔴 הפסד.",
         "המשחק האחרון שווה 30% מהמשקל, הראשון 10%. ערך מעל 1.0 = ביצועים טובים.",
         "4 ניצחונות + תיקו = 1.13x (המודל יגדיל xG ב-13%)."),

        ("💰 EV — תוחלת רווח",
         "כמה % רווח צפוי על כל 100₪ שמהמרים לטווח ארוך.",
         "EV = (הסתברות שלנו × יחס) - 1. EV חיובי = יתרון מתמטי. EV שלילי = חסרון.",
         "המודל: Belgium 50%. האתר: יחס 2.20. EV = (0.50×2.20)−1 = +10%."),

        ("🎯 Kelly Criterion — גודל הימור",
         "כמה % מהתקציב להמר. המערכת משתמשת ב-Quarter-Kelly לבטיחות.",
         "מקסימום 5% מהתקציב על הימור בודד. Quarter-Kelly = חלוקה ב-4 של קלי מלא.",
         "תקציב 1,000₪ · Kelly 3% = להמר 30₪."),

        ("🔢 יחס הוגן — Fair Odds",
         "היחס שאמור להיות ללא margin של האתר.",
         "אם המודל נותן 40% — יחס הוגן = 1/0.40 = 2.50. אם האתר מציע מעל 2.50 = יתרון.",
         "יחס הוגן 2.50 · האתר מציע 2.80 = יתרון 12% — זה Value Bet."),

        ("📊 Overround — Margin של האתר",
         "כמה % האתר לוקח לעצמו. תמיד מעל 100%.",
         "Overround 5% = על כל 100₪ שמהמרים, האתר שומר 5₪ לעצמו.",
         "יחסים 2.0/3.5/4.0 = 50%+28.6%+25% = 103.6% → Overround 3.6%."),

        ("📉 Brier Score — דיוק המודל",
         "מדד כיול. מתחת ל-0.20 = מודל טוב. 0 = מושלם.",
         "מודד כמה קרובות ההסתברויות שהמודל נתן לתוצאה שקרתה בפועל.",
         "Brier Score 0.18 = המודל מדויק ומכויל נכון."),

        ("⚡ Value Bet — הימור ערך",
         "הימור שבו יש לנו יתרון מתמטי על האתר.",
         "Value = EV חיובי + הסתברות שלנו גבוהה יותר מהמשתמעת מהיחס.",
         "אנחנו: 55% לצרפת. האתר: יחס 2.10 (47.6% משתמע). יתרון 7.4% = Value Bet!"),

        ("🧮 Poisson — מודל השערים",
         "מודל מתמטי לחיזוי מספר שערים במשחק.",
         "אם xG=1.5: 22% לאפס שערים, 33% לשער אחד, 25% לשניים. מחשב הסתברות לכל תוצאה.",
         "xG בית=1.5, xG חוץ=0.8 → P(1-0)=18.5%, P(0-0)=10.2%."),
    ]

    for i in range(0, len(terms), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(terms):
                break
            title, short, detail, example = terms[i+j]
            with col:
                with st.expander(title, expanded=False):
                    st.markdown(f"**{short}**")
                    st.divider()
                    st.write(detail)
                    st.info(f"📌 דוגמה: {example}")

    st.divider()
    st.markdown("### ⚙️ איך המערכת מחשבת — תהליך שלב אחר שלב")
    st.markdown("")

    steps = [
        ("1️⃣", "שלב הנתונים", "#e0f2fe", "#0369a1",
         "המערכת שואבת מה-API את נתוני הקבוצות, ה-Elo הנוכחי, ו-5 המשחקים האחרונים של כל קבוצה.",
         "Japan: Elo=1534, 5 משחקים: W W D W W"),

        ("2️⃣", "חישוב Form Factor", "#fef3c7", "#d97706",
         "כל משחק מוערך (נ=1, ת=0.5, ה=0). המשחק האחרון שווה 30%, הקודם 25%, 20%, 15%, 10%. הממוצע המשוקלל הופך למכפיל xG.",
         "Japan: 4W+1D → Form = 1.14x (המודל יגדיל את שעריה ב-14%)"),

        ("3️⃣", "חישוב xG (שערים צפויים)", "#f0fdf4", "#16a34a",
         "הפרש ה-Elo קובע את בסיס השערים הצפויים. Form Factor מגדיל/מקטין אותו. נוסחה: xG = 1.3 + (הפרש_Elo / 250) × Form.",
         "Japan (Elo 1534) vs Tunisia (Elo 1449): xG_יפן = 1.3 + (85/250) × 1.14 = 1.69"),

        ("4️⃣", "התפלגות פואסון", "#fdf4ff", "#9333ea",
         "עבור כל xG, מחשבים הסתברות לכל מספר שערים (0,1,2,3...). כופלים את הסתברויות שתי הקבוצות כדי לקבל הסתברות לכל תוצאה אפשרית.",
         "P(יפן 2-0) = P(יפן_קולעת_2) × P(תוניסיה_קולעת_0) = 28% × 39% = 10.9%"),

        ("5️⃣", "הסתברויות סופיות", "#fff7ed", "#ea580c",
         "סוכמים כל התוצאות: P(ניצחון_בית) = סכום כל P(i-j) כאשר i>j. P(תיקו) = סכום P(i-i). P(ניצחון_חוץ) = היתרה.",
         "Japan: 59%, תיקו: 22.4%, Tunisia: 18.6%"),

        ("6️⃣", "השוואה ל-Odds", "#f0fdf4", "#16a34a",
         "משווים את ההסתברות שלנו ל-Odds של האתר. אם ההסתברות שלנו גדולה יותר מהמשתמעת מה-Odds — זה Value Bet. EV = (הסתברות × Odds) - 1.",
         "אנחנו: Japan 59%. האתר: Odds 1.85 (= 54% משתמע). EV = (0.59×1.85)-1 = +9.2% ✅"),

        ("7️⃣", "Kelly Criterion", "#eff6ff", "#1d4ed8",
         "מחשבים כמה % מהתקציב לסכן. מחלקים ב-4 (Quarter-Kelly) לבטיחות. מוגבל ל-5% מקסימום.",
         "Kelly מלא = 18% → Quarter-Kelly = 4.5% מהתקציב"),
    ]

    for step in steps:
        icon, title_s, bg, color, desc, ex = step
        st.markdown(f"""
<div style="background:{bg};border-right:4px solid {color};border-radius:8px;padding:14px 18px;margin-bottom:10px;direction:rtl">
  <div style="font-size:15px;font-weight:600;color:{color};margin-bottom:6px">{icon} {title_s}</div>
  <div style="font-size:13px;color:#374151;margin-bottom:8px">{desc}</div>
  <div style="font-size:12px;color:#6b7280;background:white;border-radius:6px;padding:8px 12px">📌 {ex}</div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TAB 6 — תיק וירטואלי (Paper Trading)
# ══════════════════════════════════════════════════════
with tab_paper:
    import uuid
    INITIAL_BANKROLL = 300.0

    st.markdown("### 📒 תיק וירטואלי — Paper Trading")
    st.caption(f"תקציב התחלתי: ₪{INITIAL_BANKROLL:.0f} · המערכת שומרת את כל הנתונים אוטומטית")

    # ── DB Functions ─────────────────────────────────────
    def load_trades() -> list[dict]:
        try:
            from supabase import create_client
            db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            res = db.table("paper_trades").select("*").order("created_at").execute()
            return res.data or []
        except Exception:
            return st.session_state.get("paper_trades_db", [])

    def save_trade(trade: dict):
        try:
            from supabase import create_client
            db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            db.table("paper_trades").upsert(trade).execute()
        except Exception:
            trades = st.session_state.get("paper_trades_db", [])
            idx = next((i for i,t in enumerate(trades) if t["id"] == trade["id"]), None)
            if idx is not None:
                trades[idx] = trade
            else:
                trades.append(trade)
            st.session_state["paper_trades_db"] = trades

    def delete_trade(trade_id: str):
        try:
            from supabase import create_client
            db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            db.table("paper_trades").delete().eq("id", trade_id).execute()
        except Exception:
            trades = st.session_state.get("paper_trades_db", [])
            st.session_state["paper_trades_db"] = [t for t in trades if t["id"] != trade_id]

    trades = load_trades()

    # ── KPI ──────────────────────────────────────────────
    closed = [t for t in trades if t.get("status") in ("זכה","הפסיד")]
    current_bankroll = INITIAL_BANKROLL
    for t in trades:
        stake = float(t.get("stake", 0))
        odds  = float(t.get("exec_odds", 1))
        if t.get("status") == "זכה":
            current_bankroll += stake * (odds - 1)
        elif t.get("status") == "הפסיד":
            current_bankroll -= stake

    roi      = (current_bankroll - INITIAL_BANKROLL) / INITIAL_BANKROLL * 100
    wins     = sum(1 for t in closed if t.get("status") == "זכה")
    win_rate = wins / len(closed) * 100 if closed else 0

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("תקציב התחלתי", f"₪{INITIAL_BANKROLL:.0f}")
    k2.metric("תקציב נוכחי",  f"₪{current_bankroll:.1f}",
              delta=f"{current_bankroll-INITIAL_BANKROLL:+.1f}")
    k3.metric("ROI", f"{roi:+.1f}%")
    k4.metric("הימורים", len(trades))
    k5.metric("Win Rate", f"{win_rate:.0f}%",
              delta=f"{wins}/{len(closed)}" if closed else "0/0")
    st.divider()

    # ── טופס הוספה ───────────────────────────────────────
    st.markdown("#### ➕ הוסף עסקה")

    vb_data = st.session_state.get("last_value_bets", [])

    # בניית מילון Value Bets
    vb_map = {}
    if vb_data:
        for v in vb_data:
            label = f"{v.get('משחק','')} → {v.get('הימור על','')} (Kelly {v.get('Kelly %','')}, Odds {v.get('Odds','')})"
            vb_map[label] = v

    vb_labels = ["— הזן ידנית —"] + list(vb_map.keys())

    # שמירת הבחירה הקודמת לזיהוי שינוי
    prev_sel = st.session_state.get("pt_prev_sel", "— הזן ידנית —")

    reset_counter = st.session_state.get("pt_reset_counter", 0)

    selected_vb = st.selectbox(
        "משוך מ-Value Bets" if vb_data else "אין Value Bets — הפעל סריקה",
        vb_labels,
        key=f"pt_vb_select_{reset_counter}",
        disabled=not bool(vb_data),
    )

    # כשהבחירה משתנה — אפס את ה-state של הטופס
    if selected_vb != prev_sel:
        st.session_state["pt_prev_sel"] = selected_vb
        if selected_vb != "— הזן ידנית —":
            vb = vb_map[selected_vb]
            st.session_state["pt_auto_date"]  = str(vb.get("תאריך",""))
            st.session_state["pt_auto_match"] = str(vb.get("משחק",""))
            st.session_state["pt_auto_bet"]   = str(vb.get("הימור על",""))
            st.session_state["pt_auto_kelly"] = float(str(vb.get("Kelly %","1")).replace("%",""))
            st.session_state["pt_auto_odds"]  = float(vb.get("Odds", 2.0))
        else:
            st.session_state.pop("pt_auto_date",  None)
            st.session_state.pop("pt_auto_match", None)
            st.session_state.pop("pt_auto_bet",   None)
            st.session_state.pop("pt_auto_kelly", None)
            st.session_state.pop("pt_auto_odds",  None)
        st.rerun()

    # ערכים מה-state (אחרי rerun)
    auto_date  = st.session_state.get("pt_auto_date",  str(pd.Timestamp.now().date()))
    auto_match = st.session_state.get("pt_auto_match", "")
    auto_bet   = st.session_state.get("pt_auto_bet",   "")
    auto_kelly = st.session_state.get("pt_auto_kelly", 1.0)
    auto_odds  = st.session_state.get("pt_auto_odds",  2.0)
    from_vb    = selected_vb != "— הזן ידנית —"

    # שדות
    f1, f2, f3 = st.columns(3)
    with f1:
        pt_date  = st.text_input("תאריך", value=auto_date,
                                  disabled=from_vb, key="pt_f_date")
    with f2:
        pt_match = st.text_input("משחק", value=auto_match,
                                  disabled=from_vb, key="pt_f_match")
    with f3:
        pt_bet   = st.text_input("הימור על", value=auto_bet,
                                  disabled=from_vb, key="pt_f_bet")

    f4, f5, f6 = st.columns(3)
    with f4:
        pt_kelly = st.number_input(
            "Kelly %", value=auto_kelly,
            min_value=0.0, max_value=5.0, step=0.1,
            format="%.1f", disabled=from_vb, key="pt_f_kelly",
        )
    with f5:
        # Stake — ברירת מחדל 20₪ (לא תלוי ב-Kelly)
        pt_stake = st.number_input(
            "סכום השקעה (₪)", value=20.0,
            min_value=1.0, step=1.0, format="%.1f", key="pt_f_stake",
        )
    with f6:
        # Executed Odds — תמיד פתוח לעריכה
        pt_odds = st.number_input(
            "יחס לביצוע (Executed Odds)",
            value=auto_odds,
            min_value=1.01, max_value=200.0,
            step=0.05, format="%.2f", key="pt_f_odds",
            help="הזן את היחס האמיתי מאתר ההימורים. ⚠️ P&L יחושב לפי ערך זה בלבד.",
        )

    # תצוגת P&L צפוי
    expected_win  = round(pt_stake * (pt_odds - 1), 2)
    st.caption(f"💡 אם ינצח: +₪{expected_win:.1f}  |  אם יפסיד: -₪{pt_stake:.1f}")

    if st.button("➕ הוסף להימורים", type="primary", use_container_width=True, key="pt_add"):
        match_val = pt_match or auto_match
        bet_val   = pt_bet   or auto_bet
        if match_val and bet_val and pt_stake > 0:
            new_trade = {
                "id":         str(uuid.uuid4()),
                "date":       pt_date or auto_date,
                "match":      match_val,
                "bet":        bet_val,
                "kelly_pct":  float(pt_kelly),
                "stake":      float(pt_stake),
                "exec_odds":  float(pt_odds),
                "status":     "ממתין",
                "created_at": str(pd.Timestamp.now()),
            }
            save_trade(new_trade)
            # נקה את ה-state של הטופס — בלי לגעת ב-widget key
            for k in ["pt_prev_sel","pt_auto_date","pt_auto_match",
                      "pt_auto_bet","pt_auto_kelly","pt_auto_odds"]:
                st.session_state.pop(k, None)
            # איפוס הselectbox דרך counter נפרד
            st.session_state["pt_reset_counter"] = \
                st.session_state.get("pt_reset_counter", 0) + 1
            st.success(f"✅ נוסף: {match_val} → {bet_val} · Odds {pt_odds} · ₪{pt_stake}")
            st.rerun()
        else:
            st.error("⚠️ מלא: משחק, הימור וסכום")

    st.divider()

    # ── יומן עסקאות ──────────────────────────────────────
    st.markdown("#### 📋 יומן עסקאות")

    if not trades:
        st.info("אין עסקאות עדיין. הוסף הימור למעלה.")
    else:
        running = INITIAL_BANKROLL
        rows_display = []
        for t in trades:
            stake     = float(t.get("stake", 0))
            exec_odds = float(t.get("exec_odds", 1))
            status    = t.get("status", "ממתין")
            pnl = round(stake*(exec_odds-1), 2) if status=="זכה" else \
                  -round(stake, 2)              if status=="הפסיד" else 0.0
            running = round(running + pnl, 2)
            rows_display.append({
                "_id": t["id"], "_obj": t,
                "תאריך":    t.get("date",""),
                "משחק":     t.get("match",""),
                "הימור על": t.get("bet",""),
                "Kelly %":  f"{t.get('kelly_pct',0):.1f}%",
                "סכום":     stake,
                "exec_odds":exec_odds,
                "status":   status,
                "pnl":      pnl,
                "bankroll": running,
            })

        # כותרות
        hcols = st.columns([1.4, 2.5, 1.5, 0.7, 0.7, 0.85, 1.3, 0.8, 1.0, 0.45])
        for col, lbl in zip(hcols, ["תאריך","משחק","הימור","Kelly","₪","Odds","סטטוס","P&L","Bankroll","🗑"]):
            col.markdown(f"**{lbl}**")

        for row in rows_display:
            tid  = row["_id"]
            tobj = row["_obj"]
            locked = tobj["status"] != "ממתין"

            cols = st.columns([1.4, 2.5, 1.5, 0.7, 0.7, 0.85, 1.3, 0.8, 1.0, 0.45])
            cols[0].caption(row["תאריך"])
            cols[1].caption(row["משחק"])
            cols[2].caption(row["הימור על"])
            cols[3].caption(row["Kelly %"])
            cols[4].caption(f"₪{row['סכום']:.1f}")

            # Odds — עריכה רק כשממתין
            if not locked:
                new_odds = cols[5].number_input(
                    "", value=float(tobj.get("exec_odds", 2.0)),
                    min_value=1.01, max_value=200.0, step=0.05,
                    format="%.2f", key=f"odds_{tid}",
                    label_visibility="collapsed",
                )
                if abs(new_odds - float(tobj.get("exec_odds", 2.0))) > 0.001:
                    tobj["exec_odds"] = new_odds
                    save_trade(tobj)
                    st.rerun()
            else:
                cols[5].caption(f"{row['exec_odds']:.2f} 🔒")

            # סטטוס
            status_opts = ["ממתין","זכה","הפסיד"]
            new_status = cols[6].selectbox(
                "", options=status_opts,
                index=status_opts.index(tobj["status"]),
                key=f"status_{tid}", label_visibility="collapsed",
            )
            if new_status != tobj["status"]:
                tobj["status"] = new_status
                save_trade(tobj)
                st.rerun()

            # P&L
            pnl = row["pnl"]
            if pnl > 0:
                cols[7].markdown(f"**:green[+{pnl:.1f}]**")
            elif pnl < 0:
                cols[7].markdown(f"**:red[{pnl:.1f}]**")
            else:
                cols[7].caption("—")

            cols[8].caption(f"₪{row['bankroll']:.1f}")

            if cols[9].button("🗑", key=f"del_{tid}"):
                delete_trade(tid)
                st.rerun()

        st.divider()

        # ── גרף ──────────────────────────────────────────
        closed_history = [INITIAL_BANKROLL] + [
            r["bankroll"] for r in rows_display if r["status"] != "ממתין"
        ]
        if len(closed_history) >= 3:
            st.markdown("#### 📈 התפתחות התקציב")
            st.line_chart(closed_history)
