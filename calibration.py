"""
calibration.py — פיתוח #7: כיול אוטומטי של המודל
בודק אם כשאמרנו 60% — קרה 60%
ומתקן bias אוטומטית
"""

import os
import math
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()


def get_db():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def calculate_calibration(predictions: list[dict]) -> dict:
    """
    מחשב calibration error ומגלה אם המודל אופטימי/פסימי מדי.
    מחזיר bias correction לכל תוצאה.
    """
    if len(predictions) < 10:
        return {"error": "צריך לפחות 10 תחזיות עם תוצאות"}

    # מחלק לאצוות לפי הסתברות
    buckets = {
        "low":    {"range": (0, 0.35),  "probs": [], "actuals": []},
        "medium": {"range": (0.35, 0.55), "probs": [], "actuals": []},
        "high":   {"range": (0.55, 1.0), "probs": [], "actuals": []},
    }

    for p in predictions:
        actual = p.get("actual_result")
        if not actual:
            continue
        for outcome in ["home", "draw", "away"]:
            prob = p.get(f"prob_{outcome}", 0) or 0
            actual_bin = 1 if actual == outcome else 0
            for bname, bucket in buckets.items():
                lo, hi = bucket["range"]
                if lo <= prob < hi:
                    bucket["probs"].append(prob)
                    bucket["actuals"].append(actual_bin)

    results = {}
    total_bias = 0
    count = 0

    for bname, bucket in buckets.items():
        if not bucket["probs"]:
            results[bname] = None
            continue
        avg_pred = sum(bucket["probs"]) / len(bucket["probs"])
        avg_actual = sum(bucket["actuals"]) / len(bucket["actuals"])
        bias = avg_pred - avg_actual
        results[bname] = {
            "predicted": round(avg_pred * 100, 1),
            "actual": round(avg_actual * 100, 1),
            "bias": round(bias, 3),
            "n": len(bucket["probs"]),
            "status": "✅ מכויל" if abs(bias) < 0.05 else ("📈 אופטימי מדי" if bias > 0 else "📉 פסימי מדי"),
        }
        total_bias += bias * len(bucket["probs"])
        count += len(bucket["probs"])

    overall_bias = round(total_bias / count, 4) if count > 0 else 0

    # Brier Score
    brier = 0
    total = 0
    for p in predictions:
        actual = p.get("actual_result")
        if not actual:
            continue
        for outcome in ["home", "draw", "away"]:
            prob = p.get(f"prob_{outcome}", 0) or 0
            actual_bin = 1 if actual == outcome else 0
            brier += (prob - actual_bin) ** 2
            total += 1
    brier_score = round(brier / total, 4) if total > 0 else 1.0

    return {
        "buckets": results,
        "overall_bias": overall_bias,
        "brier_score": brier_score,
        "n_predictions": len(predictions),
        "recommendation": _get_recommendation(overall_bias),
        "correction_factor": round(1.0 - overall_bias * 0.5, 4),
    }


def _get_recommendation(bias: float) -> str:
    if abs(bias) < 0.02:
        return "✅ המודל מכויל היטב — אין צורך בתיקון"
    elif bias > 0.05:
        return f"📈 המודל אופטימי מדי ב-{bias:.1%} — מומלץ להוריד הסתברויות ב-{bias*50:.0f}%"
    elif bias < -0.05:
        return f"📉 המודל פסימי מדי ב-{abs(bias):.1%} — מומלץ להעלות הסתברויות"
    else:
        return f"🟡 bias קל ({bias:.1%}) — עקוב אחרי המגמה"


def apply_calibration(prob: float, correction_factor: float) -> float:
    """מתקן הסתברות לפי calibration. correction_factor קרוב ל-1.0."""
    return round(max(0.01, min(0.99, prob * correction_factor)), 4)


def run_calibration_check() -> dict:
    """מריץ בדיקת calibration מלאה על כל התחזיות."""
    try:
        res = get_db().table("predictions").select(
            "prob_home,prob_draw,prob_away,actual_result"
        ).not_.is_("actual_result", "null").execute()
        predictions = res.data or []
        return calculate_calibration(predictions)
    except Exception as e:
        return {"error": str(e)}