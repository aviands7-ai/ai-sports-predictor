"""
closing_line.py — Closing Line Value (CLV)
פיתוח #2: השוואת תחזיות שלנו ל-closing odds
מדד אמיתי לטיב המודל
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


def get_db():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def save_opening_odds(fixture_id: int, odds: dict, our_probs: dict):
    """
    שומר odds בזמן התחזית (opening/mid odds).
    נקרא כשמנתחים משחק.
    """
    try:
        get_db().table("predictions").update({
            "opening_odds_home": odds.get("home"),
            "opening_odds_draw": odds.get("draw"),
            "opening_odds_away": odds.get("away"),
        }).eq("fixture_id", fixture_id).execute()
    except Exception as e:
        print(f"[CLV] save_opening_odds error: {e}")


def save_closing_odds(fixture_id: int, closing_odds: dict):
    """
    שומר closing odds (הOdds הסופיים לפני הקיקאוף).
    נקרא מ-main.py כשמשחק עובר מ-NS ל-1H.
    """
    try:
        get_db().table("predictions").update({
            "closing_odds_home": closing_odds.get("home"),
            "closing_odds_draw": closing_odds.get("draw"),
            "closing_odds_away": closing_odds.get("away"),
        }).eq("fixture_id", fixture_id).execute()
    except Exception as e:
        print(f"[CLV] save_closing_odds error: {e}")


def calculate_clv(our_prob: float, closing_odds: float) -> float:
    """
    CLV = הסתברות_שלנו - הסתברות_משתמעת_מ_closing_odds
    חיובי = ניצחנו את השוק
    שלילי = השוק ידע יותר ממנו
    """
    if not closing_odds or closing_odds <= 1.0:
        return 0.0
    closing_prob = 1.0 / closing_odds
    return round(our_prob - closing_prob, 4)


def get_clv_report() -> dict:
    """
    מחשב CLV על כל התחזיות שיש להן closing odds.
    מחזיר ממוצע CLV וסטטיסטיקות.
    """
    try:
        res = get_db().table("predictions").select(
            "fixture_id,home_team_name,away_team_name,match_date,"
            "prob_home,prob_draw,prob_away,"
            "closing_odds_home,closing_odds_draw,closing_odds_away,"
            "actual_result"
        ).not_.is_("closing_odds_home", "null").execute()

        predictions = res.data or []
        if not predictions:
            return {"error": "אין תחזיות עם closing odds עדיין"}

        clv_values = []
        beat_market = 0

        for p in predictions:
            actual = p.get("actual_result")
            if not actual:
                continue

            our_prob = p.get(f"prob_{actual}", 0) or 0
            closing = p.get(f"closing_odds_{actual}", 0) or 0

            if closing > 1.0:
                clv = calculate_clv(our_prob, closing)
                clv_values.append(clv)
                if clv > 0:
                    beat_market += 1

        if not clv_values:
            return {"error": "אין נתוני CLV מספיקים"}

        avg_clv = round(sum(clv_values) / len(clv_values), 4)
        beat_pct = round(beat_market / len(clv_values) * 100, 1)

        return {
            "n_predictions": len(clv_values),
            "avg_clv": avg_clv,
            "beat_market_pct": beat_pct,
            "positive_clv": beat_market,
            "interpretation": (
                "✅ המודל מנצח את השוק באופן עקבי" if avg_clv > 0.02 else
                "🟡 המודל בערך שווה לשוק" if avg_clv > -0.01 else
                "❌ השוק עדיין טוב יותר מהמודל"
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def add_clv_columns_sql() -> str:
    """מחזיר SQL להוספת עמודות CLV לטבלת predictions."""
    return """
ALTER TABLE predictions
ADD COLUMN IF NOT EXISTS opening_odds_home float,
ADD COLUMN IF NOT EXISTS opening_odds_draw float,
ADD COLUMN IF NOT EXISTS opening_odds_away float,
ADD COLUMN IF NOT EXISTS closing_odds_home float,
ADD COLUMN IF NOT EXISTS closing_odds_draw float,
ADD COLUMN IF NOT EXISTS closing_odds_away float;
"""