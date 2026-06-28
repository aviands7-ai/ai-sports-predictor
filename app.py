"""
app.py — Sports Predictor Dashboard v5
Sport-Agnostic: כדורגל, טניס, בייסבול, כדורסל ועוד.
"""

import os
import uuid
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Sports Predictor",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    direction: rtl;
    color: #1e293b;
}

/* ── App background ── */
.stApp { background-color: #f8fafc; }
.block-container {
    padding-top: 1.5rem;
    max-width: 1200px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #ffffff;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.85rem;
    font-weight: 600;
    color: #64748b;
    border-radius: 7px;
    padding: 8px 16px;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: #1d4ed8 !important;
    color: #ffffff !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Metrics ── */
div[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s, border-color 0.2s;
}
div[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 12px rgba(29,78,216,0.1);
    border-color: #bfdbfe;
}
div[data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #0f172a !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
}
div[data-testid="metric-container"] [data-testid="metric-delta"] {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}

/* ── Dataframes / Tables ── */
div[data-testid="stDataFrame"] {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
div[data-testid="stDataFrame"] th {
    background: #f1f5f9 !important;
    color: #475569 !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    border-bottom: 1px solid #e2e8f0 !important;
}
div[data-testid="stDataFrame"] td {
    color: #334155 !important;
    font-size: 0.875rem !important;
    border-bottom: 1px solid #f1f5f9 !important;
}
div[data-testid="stDataFrame"] tr:hover td {
    background: #eff6ff !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #1d4ed8 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 10px 24px !important;
    font-size: 0.875rem !important;
    box-shadow: 0 2px 6px rgba(29,78,216,0.25) !important;
    transition: background 0.2s, box-shadow 0.2s, transform 0.1s !important;
}
.stButton > button:hover {
    background: #1e40af !important;
    box-shadow: 0 4px 12px rgba(29,78,216,0.35) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

.stDownloadButton > button {
    background: #ffffff !important;
    color: #16a34a !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    border: 1.5px solid #16a34a !important;
    box-shadow: none !important;
}
.stDownloadButton > button:hover {
    background: #f0fdf4 !important;
}

/* ── Inputs / Selects ── */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    color: #1e293b !important;
}
.stSelectbox > div > div:focus-within,
.stTextInput > div > div > input:focus {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 0 3px rgba(29,78,216,0.12) !important;
}

/* ── Toggle ── */
.stToggle > label { color: #475569 !important; font-size: 0.875rem; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
.streamlit-expanderContent {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ── Divider ── */
hr { border-color: #e2e8f0 !important; margin: 1.5rem 0 !important; }

/* ── Alerts ── */
div[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-width: 1px !important;
    font-size: 0.875rem !important;
}

/* ── Progress ── */
.stProgress > div > div {
    background: #1d4ed8 !important;
    border-radius: 4px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f1f5f9; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>
""", unsafe_allow_html=True)

from api_client import get_all_fixtures, get_injuries, get_head_to_head, get_team_last_matches
from engine import full_match_analysis, calculate_form_factor, match_probabilities_2way
from db import get_all_teams, get_team_elo
from backtest import run_full_backtest
from odds_api import get_best_odds, get_all_odds_batch, lookup_odds_from_batch
from export_report import build_excel_report
from decision_engine import get_flag_url, analyze_recent_form, calculate_team_score, generate_decision
from lineup_analyzer import get_lineup_summary, calculate_lineup_factor
from closing_line import get_clv_report, save_opening_odds
from rho_calibrator import get_current_rho
from fatigue_analyzer import get_fatigue_summary
from ensemble import ensemble_probabilities
from calibration import run_calibration_check


# ── games_played cache (session-level) ───────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _load_games_played_cache() -> dict:
    """
    טוען מ-Supabase את מספר המשחקים האמיתי לכל קבוצה.
    משמש ל-Elo Confidence Discount — מונע EV מנופח לקבוצות שטרם התכנסו.
    Cache יומי — קריאה אחת בלבד לסשן.
    """
    try:
        from supabase import create_client
        db  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res = db.rpc("get_team_games_played").execute()
        if res.data:
            return {row["team_id"]: row["games_played"] for row in res.data}
    except Exception:
        pass
    # Fallback: ספור ידני מטבלת matches
    try:
        from supabase import create_client
        db   = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        res  = db.table("matches").select("home_team_id, away_team_id").execute()
        from collections import Counter
        counts: Counter = Counter()
        for row in (res.data or []):
            if row.get("home_team_id"): counts[row["home_team_id"]] += 1
            if row.get("away_team_id"): counts[row["away_team_id"]] += 1
        return dict(counts)
    except Exception:
        return {}


def get_games_played(team_id: int, cache: dict) -> int:
    """מחזיר מספר משחקים אמיתי מה-cache, או -1 אם לא ידוע (proxy יופעל)."""
    return cache.get(team_id, -1)


# ── מיפוי sport_key → תווית עברית ────────────────────────────────────────────
SPORT_LABELS = {
    "soccer_fifa_world_cup":    "⚽ מונדיאל 2026",
    "soccer_international":     "⚽ בינלאומי",
    "soccer_usa_mls":           "⚽ MLS",
    "soccer_japan_j_league":    "⚽ J-League",
    "soccer_brazil_campeonato": "⚽ ברזיל",
    "soccer_sweden_allsvenskan":"⚽ שוודיה",
    "soccer_norway_eliteserien":"⚽ נורווגיה",
    "soccer_finland_veikkausliiga":"⚽ פינלנד",
    "soccer_epl":               "⚽ Premier League",
    "soccer_spain_la_liga":     "⚽ La Liga",
    "soccer_germany_bundesliga":"⚽ Bundesliga",
    "soccer_italy_serie_a":     "⚽ Serie A",
    "soccer_france_ligue_one":  "⚽ Ligue 1",
    "soccer_uefa_champs_league":"⚽ Champions League",
    "soccer_uefa_europa_league":"⚽ Europa League",
    "tennis_atp":               "🎾 ATP",
    "tennis_wta":               "🎾 WTA",
    "baseball_mlb":             "⚾ MLB",
    "basketball_nba":           "🏀 NBA",
    "basketball_euroleague":    "🏀 EuroLeague",
}

def sport_label(key: str) -> str:
    return SPORT_LABELS.get(key, f"🏅 {key}")

def utc_to_israel(utc_str: str) -> str:
    from datetime import datetime, timedelta
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return (dt + timedelta(hours=3)).strftime("%H:%M")
    except Exception:
        return utc_str[11:16]

def safe_pct(val, default="—") -> str:
    try:
        return f"{float(val):.1f}%" if val is not None else default
    except Exception:
        return default

def safe_float(val, default="—") -> str:
    try:
        return f"{float(val):.2f}" if val is not None else default
    except Exception:
        return default


# ─── כותרת ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:32px 20px 28px;background:#ffffff;border-radius:16px;margin-bottom:24px;border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
  <div style="font-size:13px;font-weight:600;color:#1d4ed8;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:12px">Sports Predictor</div>
  <div style="font-size:30px;font-weight:700;color:#0f172a;letter-spacing:-0.5px;margin-bottom:14px">מערכת חיזוי ספורט כמותית 🏆</div>
  <div style="display:flex;justify-content:center;gap:24px;flex-wrap:wrap;">
    <span style="font-size:11px;font-weight:600;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase">ELO</span>
    <span style="color:#e2e8f0">·</span>
    <span style="font-size:11px;font-weight:600;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase">Dixon-Coles</span>
    <span style="color:#e2e8f0">·</span>
    <span style="font-size:11px;font-weight:600;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase">Kelly Criterion</span>
    <span style="color:#e2e8f0">·</span>
    <span style="font-size:11px;font-weight:600;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase">Value Bets</span>
    <span style="color:#e2e8f0">·</span>
    <span style="font-size:11px;font-weight:600;color:#94a3b8;letter-spacing:0.1em;text-transform:uppercase">Multi-Sport</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── טאבים ────────────────────────────────────────────────────────────────────
tab_intel, tab_value, tab_rankings, tab_backtest, tab_glossary, tab_paper = st.tabs([
    "🔭 ניתוח משחק",
    "💰 Value Bets",
    "📊 דירוג קבוצות",
    "🧪 Backtest",
    "📖 מילון מושגים",
    "📒 תיק וירטואלי",
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
        from datetime import date, datetime, timezone

        def find_smart_date(fixtures):
            today  = date.today().strftime("%Y-%m-%d")
            dates  = sorted(set(f["fixture"]["date"][:10] for f in fixtures))
            if today in dates:
                return today
            future = [d for d in dates if d >= today]
            return future[0] if future else (dates[-1] if dates else today)

        def find_smart_match(day_fixtures):
            live = [f for f in day_fixtures if f["fixture"]["status"]["short"] in ("1H","2H","HT","ET","BT","P")]
            if live:
                return live[0]
            upcoming = sorted([f for f in day_fixtures if f["fixture"]["status"]["short"] in ("NS","TBD")],
                               key=lambda x: x["fixture"]["timestamp"])
            return upcoming[0] if upcoming else (day_fixtures[-1] if day_fixtures else None)

        smart_date    = find_smart_date(all_fixtures)
        smart_date_pd = pd.to_datetime(smart_date)

        # ── פילטר ענפי ספורט ────────────────────────────────────────────────
        all_sport_keys = sorted(set(
            f.get("league", {}).get("name", "") for f in all_fixtures
        ))
        # מיפוי לפי שם ליגה (API-Football מחזיר name, לא sport_key)
        sport_filter = st.multiselect(
            "ענפי ספורט / ליגות",
            options=all_sport_keys,
            default=all_sport_keys,
            label_visibility="collapsed",
            placeholder="בחר ליגות להצגה...",
        )
        filtered_fixtures = [
            f for f in all_fixtures
            if f.get("league", {}).get("name", "") in sport_filter
        ] if sport_filter else all_fixtures

        col_date, col_match, col_btn = st.columns([1, 3, 1])
        with col_date:
            selected_date = st.date_input("תאריך", smart_date_pd, label_visibility="collapsed")

        date_str     = selected_date.strftime("%Y-%m-%d")
        day_fixtures = [f for f in filtered_fixtures if f["fixture"]["date"].startswith(date_str)]

        with col_match:
            if not day_fixtures:
                st.warning("אין משחקים בתאריך ובפילטר הנוכחיים.")
                selected = None
            else:
                smart_match  = find_smart_match(day_fixtures)
                match_options = {
                    f"{f['teams']['home']['name']} נגד {f['teams']['away']['name']}": f
                    for f in day_fixtures
                }
                match_names  = list(match_options.keys())
                default_name = (
                    f"{smart_match['teams']['home']['name']} נגד {smart_match['teams']['away']['name']}"
                    if smart_match else match_names[0]
                )
                default_idx = match_names.index(default_name) if default_name in match_names else 0

                if smart_match:
                    status_s = smart_match["fixture"]["status"]["short"]
                    if status_s in ("1H","2H","HT","ET","BT","P"):
                        st.caption("🔴 משחק חי כרגע")
                    elif status_s in ("NS","TBD"):
                        st.caption(f"⏰ המשחק הקרוב — {utc_to_israel(smart_match['fixture']['date'])} 🇮🇱")

                selected_name = st.selectbox(
                    "בחר משחק", match_names, index=default_idx,
                    label_visibility="collapsed",
                )
                selected = match_options[selected_name]

        with col_btn:
            analyze = st.button("🔍 נתח", use_container_width=True, type="primary")

        if selected and analyze:
            fixture_id = selected["fixture"]["id"]
            home       = selected["teams"]["home"]
            away       = selected["teams"]["away"]
            venue      = selected["fixture"].get("venue", {}).get("name", "—")
            city       = selected["fixture"].get("venue", {}).get("city", "—")
            match_time = utc_to_israel(selected["fixture"]["date"])

            # has_draw מה-league — API-Football = כדורגל = תמיד True
            has_draw = True

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
                injuries     = get_injuries(fixture_id)
                h2h          = get_head_to_head(home["id"], away["id"], last=10)
                live_raw     = get_best_odds(home["name"], away["name"])
                live_od      = None
                if live_raw:
                    has_draw = live_raw.get("has_draw", True)
                    if has_draw:
                        raw = {k: live_raw.get(k) for k in ["home","draw","away"]}
                    else:
                        raw = {k: live_raw.get(k) for k in ["home","away"]}
                    if all(v and 1.01 <= v <= 25 for v in raw.values() if v):
                        live_od = raw

                current_rho  = get_current_rho()
                lineup_data  = get_lineup_summary(fixture_id, home["id"], away["id"])
                lineup_f_h   = lineup_data.get("factor_home", 1.0)
                lineup_f_a   = lineup_data.get("factor_away", 1.0)
                fatigue_data = get_fatigue_summary(home["id"], away["id"])
                fatigue_f_h  = fatigue_data.get("home", {}).get("factor", 1.0)
                fatigue_f_a  = fatigue_data.get("away", {}).get("factor", 1.0)

                if has_draw:
                    ensemble_data = ensemble_probabilities(
                        elo_h, elo_a, home["name"], away["name"],
                        form_home=form_h_factor, form_away=form_a_factor,
                        lineup_home=lineup_f_h, lineup_away=lineup_f_a,
                        fatigue_home=fatigue_f_h, fatigue_away=fatigue_f_a,
                        live_odds=live_od,
                    )
                    pure_p = ensemble_data.get("pure")
                else:
                    ensemble_data = {}
                    pure_p = None

                analysis = full_match_analysis(
                    elo_h, elo_a, live_od or {},
                    home_advantage=0.0,
                    form_home=form_h_factor,
                    form_away=form_a_factor,
                    lineup_home=lineup_f_h,
                    lineup_away=lineup_f_a,
                    pure_probs=pure_p,
                    rho=current_rho,
                    has_draw=has_draw,
                )

                if live_od:
                    save_opening_odds(fixture_id, live_od, {
                        "home": analysis["home"]["our_prob_raw"],
                        "draw": analysis["draw"]["our_prob_raw"],
                        "away": analysis["away"]["our_prob_raw"],
                    })

                decision = generate_decision(
                    home["name"], away["name"], score_h, score_a, form_h, form_a,
                    {"home": analysis["home"]["our_prob"],
                     "draw": analysis["draw"]["our_prob"],
                     "away": analysis["away"]["our_prob"]},
                    {"home": analysis["home"]["fair_odds"],
                     "draw": analysis["draw"]["fair_odds"],
                     "away": analysis["away"]["fair_odds"]},
                    live_od, elo_h, elo_a,
                )

            st.session_state["match_data"] = {
                "home": home, "away": away, "venue": venue, "city": city,
                "match_time": match_time,
                "match_date": selected["fixture"]["date"][:10],
                "elo_h": elo_h, "elo_a": elo_a,
                "form_h_factor": form_h_factor, "form_a_factor": form_a_factor,
                "form_h": form_h, "form_a": form_a,
                "score_h": score_h, "score_a": score_a,
                "analysis": analysis, "injuries": injuries, "h2h": h2h,
                "live_od": live_od, "decision": decision,
                "live_bm": live_raw.get("home_book","?") if live_raw else "?",
                "lineup_data": lineup_data,
                "lineup_f_h": lineup_f_h, "lineup_f_a": lineup_f_a,
                "fatigue_data": fatigue_data,
                "ensemble_data": ensemble_data,
                "has_draw": has_draw,
            }

        if "match_data" not in st.session_state:
            st.info("בחר תאריך ומשחק ולחץ 'נתח' כדי להתחיל.")
        else:
            md        = st.session_state["match_data"]
            home      = md["home"]
            away      = md["away"]
            elo_h     = md["elo_h"]
            elo_a     = md["elo_a"]
            form_h    = md["form_h"]
            form_a    = md["form_a"]
            analysis  = md["analysis"]
            injuries  = md["injuries"]
            h2h       = md["h2h"]
            live_od   = md["live_od"]
            decision  = md["decision"]
            has_draw  = md.get("has_draw", True)
            d         = decision
            flag_h    = get_flag_url(home["name"])
            flag_a    = get_flag_url(away["name"])
            flag_img_h = f'<img src="{flag_h}" onerror="this.style.display=\'none\'" style="width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">' if flag_h else ""
            flag_img_a = f'<img src="{flag_a}" onerror="this.style.display=\'none\'" style="width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">' if flag_a else ""

            # כותרת
            st.markdown(f"""
<div style="border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;margin:16px 0;direction:rtl;background:#ffffff;box-shadow:0 1px 4px rgba(0,0,0,0.05)">
  <div style="text-align:center;font-size:12px;color:#6b7280;margin-bottom:16px">
    🏟️ {md['venue']}, {md['city']} &nbsp;·&nbsp; {md['match_time']} 🇮🇱 &nbsp;·&nbsp; {md['match_date']}
    {"&nbsp;·&nbsp; 🎾 2-way" if not has_draw else ""}
  </div>
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="text-align:center;width:40%;vertical-align:middle;padding:0">
        {flag_img_h}
        <div style="font-size:22px;font-weight:600;margin-top:8px">{home['name']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px">Elo {elo_h:.0f}</div>
      </td>
      <td style="text-align:center;width:20%;font-size:16px;color:#9ca3af;font-weight:500">VS</td>
      <td style="text-align:center;width:40%;vertical-align:middle;padding:0">
        {flag_img_a}
        <div style="font-size:22px;font-weight:600;margin-top:8px">{away['name']}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px">Elo {elo_a:.0f}</div>
      </td>
    </tr>
  </table>
</div>""", unsafe_allow_html=True)

            # הסתברויות
            st.markdown("#### 📊 הסתברויות")
            elo_conf = analysis.get("elo_confidence", 1.0)
            if elo_conf < 0.7:
                st.warning(
                    f"⚠️ **Elo טרם התכנס** — ביטחון מודל: {elo_conf:.0%}. "
                    f"EV ו-Kelly מוקטנים אוטומטית (Shrinkage). "
                    f"נדרשים עוד משחקים לדיוק מלא."
                )
            outcomes = ["home","away"] if not has_draw else ["home","draw","away"]
            outcome_labels = {
                "home": home["name"], "draw": "תיקו", "away": away["name"]
            }
            pcols = st.columns(len(outcomes))
            for col, outcome in zip(pcols, outcomes):
                a = analysis.get(outcome, {})
                col.metric(
                    label=outcome_labels[outcome],
                    value=f"{safe_pct(a.get('our_prob'))}",
                    delta=f"Fair: {safe_float(a.get('fair_odds'))}",
                )

            # Value Bets
            value_rows = []
            for outcome in outcomes:
                a = analysis.get(outcome, {})
                ev = a.get("ev", 0) or 0
                if ev > 0:
                    value_rows.append({
                        "הימור": outcome_labels[outcome],
                        "Odds": safe_float(a.get("odds")),
                        "הסתברות": safe_pct(a.get("our_prob")),
                        "EV": f"+{ev:.1%}",
                        "Kelly %": f"{a.get('kelly_pct',0):.1f}%",
                    })
            if value_rows:
                st.markdown("#### 💰 Value Bets")
                st.dataframe(pd.DataFrame(value_rows), hide_index=True, use_container_width=True)

            # תוצאות סבירות (כדורגל בלבד)
            if has_draw and analysis.get("top_scores"):
                st.markdown("#### 🎯 תוצאות סבירות")
                score_cols = st.columns(min(len(analysis["top_scores"]), 5))
                for col, (sc, prob) in zip(score_cols, analysis["top_scores"][:5]):
                    col.metric(label=sc, value=f"{prob}%")

            # H2H
            if h2h:
                st.markdown("#### 🔄 נתוני עבר (H2H)")
                h2h_rows = []
                for m in h2h[:5]:
                    goals = m.get("goals") or {}
                    hg = goals.get("home") if isinstance(goals, dict) else None
                    ag = goals.get("away") if isinstance(goals, dict) else None
                    score_str = f"{hg}-{ag}" if hg is not None and ag is not None else "—"
                    teams = m.get("teams", {})
                    h2h_rows.append({
                        "תאריך": m.get("fixture", {}).get("date", "")[:10],
                        "ביתי":  teams.get("home", {}).get("name", "Unknown"),
                        "תוצאה": score_str,
                        "אורח":  teams.get("away", {}).get("name", "Unknown"),
                    })
                st.dataframe(pd.DataFrame(h2h_rows), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 2 — Value Bets
# ══════════════════════════════════════════════════════
with tab_value:
    st.markdown("### 💰 Value Bets — סריקת כל הספורט")
    st.caption("סריקה על כל ענפי הספורט הפעילים. EV > 3% בלבד.")

    if st.button("🔍 הפעל סריקה", key="scan_btn", type="primary"):

        with st.spinner("שואב Odds — קריאה אחת לכל הספורט..."):
            odds_batch = get_all_odds_batch()
        st.caption(f"נטענו Odds ל-{len(odds_batch)//2} משחקים בקריאה אחת")

        # ── טוען משחקים עתידיים ישירות מה-DB (לא תלוי בFootball API) ──────────
        @st.cache_data(ttl=1800, show_spinner=False)
        def load_upcoming_from_db() -> list[dict]:
            """
            קורא predictions עתידיות מ-Supabase.
            כדורגל: מסונן לפי match_date עתידי.
            NFP (sport_key קיים): נטען ללא סינון תאריך (match_date = last_update, לא זמן משחק).
            """
            try:
                from supabase import create_client
                import datetime
                db  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
                now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

                # כדורגל — עם סינון תאריך
                res_soccer = (db.table("predictions")
                         .select("*")
                         .eq("status", "NS")
                         .is_("sport_key", "null")
                         .gte("match_date", now_str)
                         .order("match_date")
                         .execute())

                # NFP — ללא סינון תאריך (match_date לא אמין)
                res_nfp = (db.table("predictions")
                         .select("*")
                         .eq("status", "NS")
                         .not_.is_("sport_key", "null")
                         .neq("sport_key", "")
                         .execute())

                return (res_soccer.data or []) + (res_nfp.data or [])
            except Exception as e:
                st.warning(f"⚠️ שגיאה בטעינת DB: {e}")
                return []

        with st.spinner("טוען משחקים מה-DB..."):
            db_predictions_raw = load_upcoming_from_db()
            # dedup לפי fixture_id
            seen_ids = set()
            db_predictions = []
            for p in db_predictions_raw:
                fid = p.get("fixture_id")
                if fid not in seen_ids:
                    seen_ids.add(fid)
                    db_predictions.append(p)

        if not db_predictions:
            st.warning("לא נמצאו משחקים עתידיים ב-DB. הרץ Pipeline תחילה.")
            st.stop()

        # ── פילטר ליגות ────────────────────────────────────────────────────────
        league_names = sorted(set(
            p.get("home_team_name","").split(" ")[0]  # placeholder
            for p in db_predictions
        ))
        # פילטר פשוט לפי has_draw (כדורגל/לא כדורגל) — ניתן להרחיב
        value_rows = []
        unverified_rows = []
        current_rho = get_current_rho()
        progress = st.progress(0)

        # טוען games_played אמיתי מ-Supabase
        gp_cache = _load_games_played_cache()

        for i, pred in enumerate(db_predictions):
            progress.progress((i + 1) / max(len(db_predictions), 1))

            home_name = pred.get("home_team_name", "")
            away_name = pred.get("away_team_name", "")
            has_draw  = pred.get("has_draw", True)
            match_date = pred.get("match_date", "")[:10]

            # שלוף odds מה-batch
            live = lookup_odds_from_batch(odds_batch, home_name, away_name)
            if not live:
                # fallback: השתמש ב-odds מה-DB
                o_h = pred.get("odds_home")
                o_d = pred.get("odds_draw")
                o_a = pred.get("odds_away")
                if not o_h or not o_a:
                    continue
                if has_draw:
                    odds = {"home": float(o_h), "draw": float(o_d or 0), "away": float(o_a)}
                else:
                    odds = {"home": float(o_h), "away": float(o_a)}
            else:
                has_draw = live.get("has_draw", has_draw)
                if has_draw:
                    odds = {k: live.get(k) for k in ["home","draw","away"] if live.get(k)}
                    if not all(isinstance(odds.get(k), float) and 1.01 <= odds.get(k,0) <= 25
                               for k in ["home","draw","away"]):
                        continue
                else:
                    odds = {k: live.get(k) for k in ["home","away"] if live.get(k)}
                    if not all(isinstance(odds.get(k), float) and 1.01 <= odds.get(k,0) <= 100
                               for k in ["home","away"]):
                        continue

            # Elo מה-DB
            elo_h = pred.get("elo_home") or 1400.0
            elo_a = pred.get("elo_away") or 1400.0

            # games_played
            home_id = pred.get("home_team_id")
            away_id = pred.get("away_team_id")
            gp_h = get_games_played(home_id, gp_cache) if home_id else -1
            gp_a = get_games_played(away_id, gp_cache) if away_id else -1

            an = full_match_analysis(
                elo_h, elo_a, odds,
                home_advantage=0.0,
                rho=current_rho,
                has_draw=has_draw,
                games_home=gp_h,
                games_away=gp_a,
            )

            sport_key  = (live.get("sport_key", "") if live else "") or pred.get("sport_key", "")
            sport_disp = sport_label(sport_key) if sport_key else "⚽ כדורגל"

            outcomes = ["home","away"] if not has_draw else ["home","draw","away"]
            outcome_labels = {"home": home_name, "draw": "תיקו", "away": away_name}

            elo_confidence = an.get("elo_confidence", 1.0)
            is_nfp = bool(pred.get("sport_key", ""))

            if not is_nfp:
                MIN_GAMES_FOR_VB = 3
                gp_min_known = [g for g in [gp_h, gp_a] if g >= 0]
                if gp_min_known and min(gp_min_known) < MIN_GAMES_FOR_VB:
                    continue

            EV_HARD_CAP = 0.40
            for outcome in outcomes:
                ev    = an[outcome].get("ev", 0) or 0
                kelly = an[outcome].get("kelly_pct", 0) or 0
                if ev <= 0.03:
                    continue
                if ev > EV_HARD_CAP:
                    continue

                row = {
                    "תאריך":       match_date,
                    "ענף":         sport_disp,
                    "משחק":        f"{home_name} vs {away_name}",
                    "הימור על":    outcome_labels[outcome],
                    "Odds":        odds.get(outcome, 0),
                    "סיכוי %":     an[outcome].get("our_prob", 0),
                    "EV":          f"+{ev:.1%}",
                    "Kelly %":     f"{kelly:.1f}%",
                    "Elo ביטחון":  f"{elo_confidence:.0%}",
                }

                # סף אחיד 0.70 לכולם — כדורגל ו-NFP
                if elo_confidence < 0.70:
                    unverified_rows.append(row)
                else:
                    value_rows.append(row)

        progress.empty()
        st.session_state["last_value_bets"] = [
            {
                "תאריך":    r["תאריך"],
                "משחק":     r["משחק"],
                "הימור על": r["הימור על"],
                "Odds":     r["Odds"],
                "Kelly %":  r["Kelly %"],
            }
            for r in value_rows
        ]

        if not value_rows:
            st.info("לא נמצאו Value Bets כרגע.")
        else:
            df_vb = pd.DataFrame(value_rows).sort_values("EV", ascending=False)
            st.dataframe(df_vb, hide_index=True, use_container_width=True)
            st.metric("Value Bets שנמצאו", len(df_vb))

        if unverified_rows:
            with st.expander(f"⚠️ הזדמנויות לא מאומתות ({len(unverified_rows)}) — Elo < 70%, לא לביצוע"):
                st.caption("הימורים שלא עברו את סף הביטחון (Elo < 70%). EV לא אמין — המודל לא מכיר מספיק את הקבוצות.")
                df_uv = pd.DataFrame(unverified_rows).sort_values("EV", ascending=False)
                st.dataframe(df_uv, hide_index=True, use_container_width=True)

            try:
                buf = build_excel_report(value_rows)
                st.download_button(
                    "📥 ייצוא Excel",
                    data=buf,
                    file_name="value_bets.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception:
                pass


# ══════════════════════════════════════════════════════
# TAB 3 — דירוג קבוצות
# ══════════════════════════════════════════════════════
with tab_rankings:
    st.markdown("### 📊 דירוג עוצמת הקבוצות (Elo)")

    @st.cache_data(ttl=600, show_spinner=False)
    def load_teams():
        return get_all_teams()

    teams = load_teams()
    if not teams:
        st.info("אין נתונים. הרץ main.py תחילה.")
    else:
        df = pd.DataFrame(teams)[["name","elo_rating"]].rename(
            columns={"name":"קבוצה","elo_rating":"Elo"})
        df.index = range(1, len(df)+1)
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index("קבוצה")["Elo"].head(20))


# ══════════════════════════════════════════════════════
# TAB 4 — Backtest
# ══════════════════════════════════════════════════════
with tab_backtest:
    st.markdown("### 🧪 Backtest אמיתי")
    st.info("בדיקה על תחזיות שנשמרו עם תוצאות ידועות.")

    bankroll = st.number_input(
        "תקציב ($)", min_value=100, max_value=100000,
        value=1000, step=100, label_visibility="visible",
    )

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

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("דיוק", f"{acc.get('accuracy_pct',0)}%")
            c2.metric("ROI", f"{roi.get('roi_pct',0)}%")
            c3.metric("Brier Score", bs)
            c4.metric("Value Bets", vb.get("total_value_bets",0))
            c5.metric("רווח", f"${roi.get('profit',0):+.0f}")

            if roi.get("history") and len(roi["history"]) > 1:
                st.line_chart(roi["history"])

            roi_pct = roi.get("roi_pct", 0) or 0
            if roi_pct > 5:
                st.success("✅ יתרון חיובי. אחרי 50+ משחקים — אפשר לשקול כסף אמיתי.")
            elif roi_pct > 0:
                st.warning("🔶 יתרון קטן — צריך יותר נתונים.")
            else:
                st.error("⚠️ ROI שלילי.")

            ab = results.get("ab_testing", {})
            if ab:
                st.divider()
                st.markdown("### 🔬 A/B Testing")
                ab_rows = []
                for key, label in [("elo_pure","A — Elo טהור"),("elo_form","B — Elo + Form"),("ensemble","C — Ensemble")]:
                    m = ab.get(key, {})
                    if m:
                        ab_rows.append({
                            "מודל": label,
                            "ROI %": f"{m.get('roi_pct',0):+.1f}%",
                            "רווח": f"${m.get('profit',0):+.0f}",
                            "הימורים": m.get("bets_placed",0),
                            "Win Rate": f"{m.get('win_rate_pct',0):.1f}%",
                        })
                if ab_rows:
                    st.dataframe(pd.DataFrame(ab_rows), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("### 🎯 Calibration")
    cal = run_calibration_check()
    if "error" in cal:
        st.info(f"⏳ {cal['error']}")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("Brier Score", cal.get("brier_score","—"))
        c2.metric("Bias", f"{cal.get('overall_bias',0):.1%}")
        c3.metric("תחזיות", cal.get("n_predictions",0))
        st.info(cal.get("recommendation",""))

    st.caption("CLV — Closing Line Value")
    clv = get_clv_report()
    if "error" in clv:
        st.info(f"⏳ {clv['error']}")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("ממוצע CLV", f"{clv.get('avg_clv',0):.1%}")
        c2.metric("ניצחנו שוק", f"{clv.get('beat_market_pct',0)}%")
        c3.metric("תחזיות", clv.get("n_predictions",0))
        st.info(clv.get("interpretation",""))


# ══════════════════════════════════════════════════════
# TAB 5 — מילון מושגים
# ══════════════════════════════════════════════════════
with tab_glossary:
    st.markdown("### 📖 מילון מושגים")
    terms = [
        ("🏆 Elo Rating","דירוג עוצמת קבוצה. מתעדכן אחרי כל משחק.",
         "ניצחון על חזק = יותר נקודות. טווח: 1350–1900.","ברזיל 1820 vs ספרד 1760."),
        ("⚽ xG","שערים צפויים לפי Poisson.","xG 1.5 = 1.5 שערים בממוצע.",
         "ארגנטינה xG=1.8 vs ערב הסעודית xG=0.7"),
        ("🎯 Logistic 2-way","מודל לספורט ללא תיקו (טניס/בייסבול).",
         "P = 1/(1+10^((EloAway-EloHome)/400))","Tennis: Djokovic 1800 vs Alcaraz 1750 → 57% Djokovic"),
        ("💰 EV","תוחלת רווח. EV חיובי = יתרון מתמטי.",
         "EV = (הסתברות × יחס) - 1","Belgium 50%, יחס 2.20 → EV = +10%"),
        ("🎯 Kelly Criterion","גודל הימור מיטבי. Quarter-Kelly לבטיחות.",
         "מקסימום 5% מהתקציב.","1000₪ × 3% = 30₪"),
        ("📊 Brier Score","דיוק הסתברויות. <0.20 = טוב.",
         "0 = מושלם, 0.33 = אקראי.","0.18 = מודל מכויל."),
        ("⚡ Value Bet","הסתברות שלנו > הסתברות משתמעת מה-Odds.",
         "EV > 0 = Value Bet.","צרפת 59%, יחס 1.85 (54%) → EV +9.2%"),
        ("📈 CLV","Closing Line Value — ניצחנו את השוק?",
         "CLV > 0 = זיהינו ערך לפני השוק.","הימרנו ב-1.85, נסגר ב-1.70 → CLV חיובי"),
    ]
    for i in range(0, len(terms), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i+j >= len(terms):
                break
            title, short, detail, example = terms[i+j]
            with col:
                with st.expander(title):
                    st.markdown(f"**{short}**")
                    st.write(detail)
                    st.info(f"📌 {example}")


# ══════════════════════════════════════════════════════
# TAB 6 — תיק וירטואלי
# ══════════════════════════════════════════════════════
with tab_paper:
    INITIAL_BANKROLL = 300.0

    st.markdown("### 📒 תיק וירטואלי — Paper Trading")
    st.caption(f"תקציב התחלתי: ₪{INITIAL_BANKROLL:.0f}")

    def load_trades() -> list[dict]:
        try:
            from supabase import create_client
            db  = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
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
    k2.metric("תקציב נוכחי", f"₪{current_bankroll:.1f}",
              delta=f"{current_bankroll-INITIAL_BANKROLL:+.1f}")
    k3.metric("ROI", f"{roi:+.1f}%")
    k4.metric("הימורים", len(trades))
    k5.metric("Win Rate", f"{win_rate:.0f}%",
              delta=f"{wins}/{len(closed)}" if closed else "0/0")
    st.divider()

    st.markdown("#### ➕ הוסף עסקה")
    vb_data  = st.session_state.get("last_value_bets", [])
    vb_map   = {}
    if vb_data:
        sorted_vb = sorted(vb_data, key=lambda v: str(v.get("תאריך","")))
        for v in sorted_vb:
            date_str_vb = str(v.get("תאריך",""))[:10]
            label = f"[{date_str_vb}] {v.get('משחק','')} → {v.get('הימור על','')} (Kelly {v.get('Kelly %','')}, Odds {v.get('Odds','')})"
            vb_map[label] = v

    vb_labels    = ["— הזן ידנית —"] + list(vb_map.keys())
    reset_counter = st.session_state.get("pt_reset_counter", 0)

    selected_vb = st.selectbox(
        "משוך מ-Value Bets" if vb_data else "אין Value Bets — הפעל סריקה",
        vb_labels,
        key=f"pt_vb_select_{reset_counter}",
        disabled=not bool(vb_data),
        label_visibility="visible",
    )

    prev_sel = st.session_state.get("pt_prev_sel","— הזן ידנית —")
    if selected_vb != prev_sel:
        st.session_state["pt_prev_sel"] = selected_vb
        if selected_vb != "— הזן ידנית —":
            vb = vb_map[selected_vb]
            st.session_state["pt_auto_date"]  = str(vb.get("תאריך",""))
            st.session_state["pt_auto_match"] = str(vb.get("משחק",""))
            st.session_state["pt_auto_bet"]   = str(vb.get("הימור על",""))
            st.session_state["pt_auto_kelly"] = float(str(vb.get("Kelly %","1")).replace("%",""))
            st.session_state["pt_auto_odds"]  = float(vb.get("Odds",2.0))
        else:
            for k in ["pt_auto_date","pt_auto_match","pt_auto_bet","pt_auto_kelly","pt_auto_odds"]:
                st.session_state.pop(k, None)
        st.rerun()

    auto_date  = st.session_state.get("pt_auto_date",  str(pd.Timestamp.now().date()))
    auto_match = st.session_state.get("pt_auto_match", "")
    auto_bet   = st.session_state.get("pt_auto_bet",   "")
    auto_kelly = st.session_state.get("pt_auto_kelly", 1.0)
    auto_odds  = st.session_state.get("pt_auto_odds",  2.0)
    from_vb    = selected_vb != "— הזן ידנית —"

    sel_key = selected_vb.replace(" ","_").replace("→","_").replace("/","_")[:30]

    f1,f2,f3 = st.columns(3)
    with f1:
        pt_date  = st.text_input("תאריך", value=auto_date, disabled=from_vb, key=f"pt_f_date_{sel_key}")
    with f2:
        pt_match = st.text_input("משחק",  value=auto_match, disabled=from_vb, key=f"pt_f_match_{sel_key}")
    with f3:
        pt_bet   = st.text_input("הימור על", value=auto_bet, disabled=from_vb, key=f"pt_f_bet_{sel_key}")

    f4,f5,f6 = st.columns(3)
    with f4:
        pt_kelly = st.number_input("Kelly %", value=float(auto_kelly), min_value=0.0,
                                   max_value=5.0, step=0.1, format="%.1f",
                                   disabled=from_vb, key=f"pt_f_kelly_{sel_key}",
                                   label_visibility="visible")
    with f5:
        pt_stake = st.number_input("סכום השקעה (₪)", value=20.0, min_value=1.0,
                                   step=1.0, format="%.1f", key=f"pt_f_stake_{sel_key}",
                                   label_visibility="visible")
    with f6:
        pt_odds  = st.number_input("יחס לביצוע (Executed Odds)", value=float(auto_odds),
                                   min_value=1.01, max_value=200.0, step=0.05, format="%.2f",
                                   key=f"pt_f_odds_{sel_key}", label_visibility="visible",
                                   help="הזן את היחס האמיתי מאתר ההימורים.")

    expected_win = round(pt_stake * (pt_odds - 1), 2)
    st.caption(f"💡 אם ינצח: +₪{expected_win:.1f} | אם יפסיד: -₪{pt_stake:.1f}")

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
            for k in ["pt_prev_sel","pt_auto_date","pt_auto_match","pt_auto_bet","pt_auto_kelly","pt_auto_odds"]:
                st.session_state.pop(k, None)
            st.session_state["pt_reset_counter"] = reset_counter + 1
            st.success(f"✅ נוסף: {match_val} → {bet_val} · Odds {pt_odds} · ₪{pt_stake}")
            st.rerun()
        else:
            st.error("⚠️ מלא: משחק, הימור וסכום")

    st.divider()
    st.markdown("#### 📋 יומן עסקאות")

    if not trades:
        st.info("אין עסקאות עדיין.")
    else:
        running = INITIAL_BANKROLL
        rows_display = []
        for t in trades:
            stake     = float(t.get("stake", 0))
            exec_odds = float(t.get("exec_odds", 1))
            status    = t.get("status","ממתין")
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

        hcols = st.columns([1.4,2.5,1.5,0.7,0.7,0.85,1.3,0.8,1.0,0.45])
        for col, lbl in zip(hcols, ["תאריך","משחק","הימור","Kelly","₪","Odds","סטטוס","P&L","Bankroll","🗑"]):
            col.markdown(f"**{lbl}**")

        for row in rows_display:
            tid  = row["_id"]
            tobj = row["_obj"]
            locked = tobj["status"] != "ממתין"

            cols = st.columns([1.4,2.5,1.5,0.7,0.7,0.85,1.3,0.8,1.0,0.45])
            cols[0].caption(row["תאריך"])
            cols[1].caption(row["משחק"])
            cols[2].caption(row["הימור על"])
            cols[3].caption(row["Kelly %"])
            cols[4].caption(f"₪{row['סכום']:.1f}")

            if not locked:
                new_odds = cols[5].number_input(
                    "Odds", value=float(tobj.get("exec_odds",2.0)),
                    min_value=1.01, max_value=200.0, step=0.05, format="%.2f",
                    key=f"odds_{tid}", label_visibility="collapsed",
                )
                if abs(new_odds - float(tobj.get("exec_odds",2.0))) > 0.001:
                    tobj["exec_odds"] = new_odds
                    save_trade(tobj)
                    st.rerun()
            else:
                cols[5].caption(f"{row['exec_odds']:.2f} 🔒")

            status_opts = ["ממתין","זכה","הפסיד"]
            new_status = cols[6].selectbox(
                "סטטוס", options=status_opts,
                index=status_opts.index(tobj["status"]),
                key=f"status_{tid}", label_visibility="collapsed",
            )
            if new_status != tobj["status"]:
                tobj["status"] = new_status
                save_trade(tobj)
                st.rerun()

            pnl = row["pnl"]
            if pnl > 0:   cols[7].markdown(f"**:green[+{pnl:.1f}]**")
            elif pnl < 0: cols[7].markdown(f"**:red[{pnl:.1f}]**")
            else:         cols[7].caption("—")

            cols[8].caption(f"₪{row['bankroll']:.1f}")
            if cols[9].button("🗑", key=f"del_{tid}"):
                delete_trade(tid)
                st.rerun()

        st.divider()
        closed_history = [INITIAL_BANKROLL] + [
            r["bankroll"] for r in rows_display if r["status"] != "ממתין"
        ]
        if len(closed_history) >= 3:
            st.markdown("#### 📈 התפתחות התקציב")
            st.line_chart(closed_history)
