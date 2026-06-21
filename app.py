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
st.title("🏆 World Cup 2026 Predictor")
st.caption("מנוע חיזוי מבוסס Elo + Poisson Distribution + Kelly Criterion")
st.divider()

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

            flag_h = get_flag_url(home["name"])
            flag_a = get_flag_url(away["name"])

            # ── כותרת משחק ──────────────────────────────────────
            st.divider()
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                if flag_h:
                    st.image(flag_h, width=80)
                st.markdown(f"### {home['name']}")
                st.caption(f"Elo {elo_h:.0f}")
            with c2:
                st.markdown("<br><br>", unsafe_allow_html=True)
                st.markdown("### VS", help=f"🏟️ {md['venue']}, {md['city']} · {md['match_time']} UTC")
            with c3:
                if flag_a:
                    st.image(flag_a, width=80)
                st.markdown(f"### {away['name']}")
                st.caption(f"Elo {elo_a:.0f}")

            st.divider()

            # ── המלצה ───────────────────────────────────────────
            conf_map = {"גבוה": "success", "בינוני": "warning", "נמוך": "error"}
            msg_type = conf_map.get(d["confidence"], "info")

            winner_text = f"{d['confidence_emoji']} המלצה: **{d['winner_name']}** · ביטחון {d['confidence']} · {d['winner_prob']:.0f}% הסתברות"
            if msg_type == "success":
                st.success(winner_text)
            elif msg_type == "warning":
                st.warning(winner_text)
            else:
                st.error(winner_text)

            if d.get("reasons"):
                with st.expander("✅ נימוקים לבחירה"):
                    for r in d["reasons"]:
                        st.write(f"• {r}")

            if d.get("risks"):
                with st.expander("⚠️ סיכונים"):
                    for r in d["risks"]:
                        st.write(f"• {r}")

            bet = d.get("bet_recommendation")
            if bet:
                st.success(f"💰 **Value Bet:** {bet['kelly']}% מהתקציב על **{bet['outcome']}** · יחס {bet['odds']} · EV +{bet['ev']}%")
            elif live_od:
                st.info("❌ אין Value Bet — אין יתרון מתמטי ביחסים הנוכחיים")
            else:
                st.info("⚠️ אין odds זמינים למשחק זה")

            st.divider()

            # ── ניתוח קבוצות ────────────────────────────────────
            col_h, col_a = st.columns(2)

            def team_panel(col, name, elo, score, form, factor):
                with col:
                    st.markdown(f"#### {name}")

                    # ציונים
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("ציון כולל", f"{score['total']:.0f}/100")
                    m2.metric("עוצמה", f"{score['elo']:.0f}")
                    m3.metric("טופס", f"{score['form']:.0f}")
                    m4.metric("הגנה", f"{score['defense']:.0f}")

                    # 5 משחקים אחרונים
                    st.markdown("**5 משחקים אחרונים:**")
                    results = form.get("results", [])
                    result_map = {"W": "🟢 ניצחון", "D": "🟡 תיקו", "L": "🔴 הפסד"}
                    cols_r = st.columns(len(results)) if results else []
                    for i, r in enumerate(results):
                        cols_r[i].markdown(f"**{result_map.get(r, '?').split()[0]}**")
                        cols_r[i].caption(result_map.get(r,'?').split()[-1])

                    # סטטיסטיקות
                    s1, s2, s3 = st.columns(3)
                    s1.metric("שערים/מ׳", f"{form.get('avg_scored',0):.1f}")
                    s2.metric("קבלה/מ׳", f"{form.get('avg_conceded',0):.1f}")
                    s3.metric("שערים נקיים", form.get('clean_sheets',0))

                    trend_map = {"rising": "📈 עלייה", "falling": "📉 ירידה", "stable": "➡️ יציב", "unknown": "❓"}
                    st.caption(f"מגמה: {trend_map.get(form.get('trend','unknown'), '?')}")
                    if form.get("win_streak", 0) >= 2:
                        st.caption(f"🔥 {form['win_streak']} ניצחונות ברצף")

            team_panel(col_h, home["name"], elo_h, score_h, form_h, form_h_f)
            team_panel(col_a, away["name"], elo_a, score_a, form_a, form_a_f)

            st.divider()

            # ── הסתברויות + תוצאות ──────────────────────────────
            col_probs, col_scores = st.columns([3, 2])

            with col_probs:
                st.markdown("#### 📊 הסתברויות")
                rows = []
                for key_o, label_o in [("home", f"{home['name']} מנצחת"), ("draw", "🤝 תיקו"), ("away", f"{away['name']} מנצחת")]:
                    la = analysis[key_o]
                    row = {
                        "תוצאה": label_o,
                        "סיכוי": f"{la['our_prob']}%",
                        "יחס הוגן": la["fair_odds"],
                    }
                    if live_od:
                        row["Odds"] = live_od.get(key_o, "-")
                        ev = la["ev"]
                        row["EV"] = f"+{ev:.1%}" if ev > 0 else f"{ev:.1%}"
                        row["✓"] = "✅" if la["is_value"] else "❌"
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                if live_od:
                    st.caption(f"Odds מ-{md.get('live_bm','?')}")

            with col_scores:
                st.markdown("#### ⚽ תוצאות סבירות")
                for score_str, pct in analysis["top_scores"]:
                    c1, c2 = st.columns([1, 3])
                    c1.markdown(f"**{score_str}**")
                    c2.progress(int(pct * 4))
                    c2.caption(f"{pct}%")

            st.divider()

            # ── פציעות + H2H + ייצוא ────────────────────────────
            col_info, col_export = st.columns([3, 1])

            with col_info:
                home_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == home["id"]]
                away_inj = [i["player"]["name"] for i in injuries if i["team"]["id"] == away["id"]]
                if home_inj or away_inj:
                    st.markdown("**🚑 פצועים:**")
                    for p in home_inj:
                        st.write(f"• {p} ({home['name']})")
                    for p in away_inj:
                        st.write(f"• {p} ({away['name']})")

                if h2h:
                    h2h_records = []
                    for g in h2h[-5:]:
                        h2h_records.append({
                            "תאריך": g["fixture"]["date"][:10],
                            "ביתית": g["teams"]["home"]["name"],
                            "תוצאה": f"{g['goals']['home'] or 0}-{g['goals']['away'] or 0}",
                            "אורחת": g["teams"]["away"]["name"],
                        })
                    with st.expander(f"⚔️ עימותים ישירים ({len(h2h_records)} אחרונים)"):
                        st.dataframe(pd.DataFrame(h2h_records), hide_index=True, use_container_width=True)

            with col_export:
                st.markdown("**📥 ייצוא**")
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
                st.download_button(
                    label="📥 הורד Excel",
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