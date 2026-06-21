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
from engine import full_match_analysis, calculate_form_factor
from db import get_all_teams, get_team_elo
from backtest import run_full_backtest
from odds_api import get_best_odds
from export_report import build_excel_report
from decision_engine import get_flag_url, analyze_recent_form, calculate_team_score, generate_decision

# ─── כותרת ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:32px 20px 24px;background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 50%,#0f172a 100%);border-radius:16px;margin-bottom:24px">
  <div style="font-size:48px;margin-bottom:8px">🏆</div>
  <div style="font-size:32px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;margin-bottom:6px">World Cup 2026 Predictor</div>
  <div style="font-size:13px;color:#93c5fd;letter-spacing:0.1em;text-transform:uppercase">Elo &nbsp;·&nbsp; Poisson Distribution &nbsp;·&nbsp; Kelly Criterion &nbsp;·&nbsp; Value Bets</div>
</div>
""", unsafe_allow_html=True)

# ─── טאבים ─────────────────────────────────────────────────────────────────────
tab_intel, tab_value, tab_rankings, tab_backtest, tab_glossary = st.tabs([
    "🔭 ניתוח משחק",
    "💰 Value Bets",
    "📊 דירוג קבוצות",
    "🧪 Backtest",
    "📖 מילון מושגים",
])


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
        col_date, col_match, col_btn = st.columns([1, 3, 1])

        with col_date:
            selected_date = st.date_input("תאריך", pd.to_datetime("2026-06-21"), label_visibility="collapsed")

        date_str = selected_date.strftime("%Y-%m-%d")
        day_fixtures = [f for f in all_fixtures if f["fixture"]["date"].startswith(date_str)]

        with col_match:
            if not day_fixtures:
                st.warning("אין משחקים בתאריך זה.")
                selected = None
            else:
                match_options = {
                    f"{f['teams']['home']['name']} נגד {f['teams']['away']['name']}": f
                    for f in day_fixtures
                }
                selected_name = st.selectbox("בחר משחק", list(match_options.keys()), label_visibility="collapsed")
                selected = match_options[selected_name]

        with col_btn:
            analyze = st.button("🔍 נתח", use_container_width=True, type="primary")

        if selected and analyze:
            fixture_id = selected["fixture"]["id"]
            home = selected["teams"]["home"]
            away = selected["teams"]["away"]
            venue = selected["fixture"]["venue"]["name"]
            city  = selected["fixture"]["venue"]["city"]
            match_time = selected["fixture"]["date"][11:16]

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
                analysis = full_match_analysis(elo_h, elo_a, live_od or {}, home_advantage=0.0, form_home=form_h_factor, form_away=form_a_factor)
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
            d        = decision
            flag_h   = get_flag_url(home["name"])
            flag_a   = get_flag_url(away["name"])

            flag_img_h = f'<img src="{flag_h}" style="width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">' if flag_h else ""
            flag_img_a = f'<img src="{flag_a}" style="width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">' if flag_a else ""

            # ── 1. כותרת משחק ───────────────────────────────────
            st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;margin:16px 0;direction:rtl">
  <div style="text-align:center;font-size:12px;color:#6b7280;margin-bottom:16px">
    🏟️ {md['venue']}, {md['city']} &nbsp;·&nbsp; {md['match_time']} UTC &nbsp;·&nbsp; {md['match_date']}
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

            # ── 4. הסתברויות + תוצאות ───────────────────────────
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

        value_rows = []
        progress = st.progress(0)
        for i, f in enumerate(upcoming):
            progress.progress((i+1)/max(len(upcoming),1))
            h = f["teams"]["home"]
            a = f["teams"]["away"]
            fid = f["fixture"]["id"]
            elo_h = get_team_elo(h["id"])
            elo_a = get_team_elo(a["id"])
            live = get_best_odds(h["name"], a["name"])
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