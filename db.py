"""
db.py — שכבת מסד הנתונים (Supabase)
כל הגישה ל-Supabase מרוכזת כאן.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase: Client | None = None


def get_db() -> Client:
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY חסרים ב-.env")
        _supabase = create_client(url, key)
    return _supabase


# ─── Teams ─────────────────────────────────────────────────────────────────────

def get_team_elo(team_id: int, default: float = 1500.0) -> float:
    try:
        res = get_db().table("teams").select("elo_rating").eq("id", team_id).execute()
        return res.data[0]["elo_rating"] if res.data else default
    except Exception as e:
        print(f"[DB] get_team_elo error: {e}")
        return default


def upsert_team(team_id: int, name: str, elo: float = 1500.0):
    try:
        get_db().table("teams").upsert({
            "id": team_id,
            "name": name,
            "elo_rating": elo
        }).execute()
    except Exception as e:
        print(f"[DB] upsert_team error: {e}")


def update_team_elo(team_id: int, new_elo: float):
    try:
        get_db().table("teams").update({"elo_rating": new_elo}).eq("id", team_id).execute()
    except Exception as e:
        print(f"[DB] update_team_elo error: {e}")


def get_all_teams() -> list[dict]:
    try:
        res = get_db().table("teams").select("*").order("elo_rating", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] get_all_teams error: {e}")
        return []


# ─── Matches ───────────────────────────────────────────────────────────────────

def upsert_match(data: dict):
    """
    שמירה/עדכון משחק במסד הנתונים.
    data חייב לכלול fixture_id.
    """
    try:
        get_db().table("matches").upsert(data, on_conflict="fixture_id").execute()
    except Exception as e:
        print(f"[DB] upsert_match error: {e}")


def get_matches_by_status(status: str) -> list[dict]:
    try:
        res = get_db().table("matches").select("*").eq("status", status).execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] get_matches_by_status error: {e}")
        return []


def get_finished_matches() -> list[dict]:
    try:
        res = (get_db().table("matches")
               .select("*")
               .in_("status", ["FT", "AET", "PEN"])
               .order("match_date", desc=True)
               .execute())
        return res.data or []
    except Exception as e:
        print(f"[DB] get_finished_matches error: {e}")
        return []


def get_all_matches() -> list[dict]:
    try:
        res = get_db().table("matches").select("*").order("match_date").execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] get_all_matches error: {e}")
        return []


# ─── Predictions Log ───────────────────────────────────────────────────────────

def log_prediction(fixture_id: int, data: dict):
    """
    שמירת תחזית מפורטת לטבלת predictions (נפרדת מ-matches).
    מאפשרת מעקב היסטורי מדויק.
    """
    try:
        get_db().table("predictions").upsert(
            {"fixture_id": fixture_id, **data},
            on_conflict="fixture_id"
        ).execute()
    except Exception as e:
        print(f"[DB] log_prediction error: {e}")


def get_predictions_with_results() -> list[dict]:
    """
    מחזיר תחזיות עם תוצאות בפועל (למטרות backtest / calibration).
    """
    try:
        res = (get_db().table("predictions")
               .select("*")
               .not_.is_("actual_result", "null")
               .execute())
        return res.data or []
    except Exception as e:
        print(f"[DB] get_predictions_with_results error: {e}")
        return []
