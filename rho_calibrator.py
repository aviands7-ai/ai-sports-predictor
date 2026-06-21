"""
rho_calibrator.py — כיול אוטומטי של פרמטר Dixon-Coles rho
על בסיס נתוני המונדיאל 2026 בפועל.

הרעיון:
- מחפש את ה-rho שמינימיזציה את השגיאה בין
  הסתברויות המודל לתוצאות בפועל (Maximum Likelihood Estimation).
- מתחת ל-20 משחקים: rho=-0.13 (ערך ספרותי קלאסי).
- מעל 20 משחקים: מכייל מחדש על הנתונים האמיתיים שלנו.
"""

import os
import math
from scipy.optimize import minimize_scalar
from scipy.stats import poisson
from dotenv import load_dotenv

load_dotenv()

MIN_MATCHES_FOR_CALIBRATION = 20
DEFAULT_RHO = -0.13
RHO_BOUNDS  = (-0.30, 0.30)   # גבולות פיזיקליים — rho מחוץ לטווח = הסתברות שלילית


def _tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
    """פרמטר תלות Dixon-Coles לתוצאה (i, j)."""
    if i == 0 and j == 0:
        return max(1e-9, 1 - lam * mu * rho)
    elif i == 1 and j == 0:
        return max(1e-9, 1 + mu * rho)
    elif i == 0 and j == 1:
        return max(1e-9, 1 + lam * rho)
    elif i == 1 and j == 1:
        return max(1e-9, 1 - rho)
    return 1.0


def _log_likelihood(rho: float, matches: list[dict]) -> float:
    """
    מחשב negative log-likelihood של rho נתון על נתוני משחקים.
    מינימיזציה = מציאת ה-rho הכי טוב.
    """
    total_ll = 0.0

    for m in matches:
        xg_h = m["xg_home"]
        xg_a = m["xg_away"]
        actual_h = m["actual_home_goals"]
        actual_a = m["actual_away_goals"]

        # הסתברות פואסון
        p_home = poisson.pmf(actual_h, xg_h)
        p_away = poisson.pmf(actual_a, xg_a)

        # תיקון Dixon-Coles
        tau = _tau(actual_h, actual_a, xg_h, xg_a, rho)

        # Log-Likelihood
        p_joint = p_home * p_away * tau
        if p_joint <= 0:
            p_joint = 1e-10

        total_ll += math.log(p_joint)

    return -total_ll  # negative כי minimize_scalar מחפש מינימום


def calibrate_rho(matches: list[dict]) -> dict:
    """
    מכייל את rho על בסיס נתוני משחקים.

    matches: רשימת dict עם:
        - xg_home, xg_away: xG שחזה המודל לפני המשחק
        - actual_home_goals, actual_away_goals: תוצאה בפועל

    מחזיר: rho מכויל + סטטיסטיקות
    """
    n = len(matches)

    if n < MIN_MATCHES_FOR_CALIBRATION:
        return {
            "rho":     DEFAULT_RHO,
            "source":  "ספרותי (Dixon & Coles 1997)",
            "n":       n,
            "calibrated": False,
            "message": f"צריך לפחות {MIN_MATCHES_FOR_CALIBRATION} משחקים. יש {n}.",
            "ll_improvement": None,
        }

    # כיול עם rho=0 (baseline Poisson)
    ll_baseline = _log_likelihood(0.0, matches)

    # אופטימיזציה — מחפש את ה-rho הכי טוב
    result = minimize_scalar(
        _log_likelihood,
        args=(matches,),
        bounds=RHO_BOUNDS,
        method="bounded",
    )

    rho_optimal = round(result.x, 4)
    ll_optimal  = -result.fun
    ll_base     = -ll_baseline

    # שיפור ב-Log-Likelihood
    ll_improvement = round(ll_optimal - ll_base, 3)

    # בדיקה — האם השיפור מובהק?
    # כלל אצבע: שיפור > 2.0 ב-LL = מובהק סטטיסטית
    is_significant = ll_improvement > 2.0

    return {
        "rho":             rho_optimal,
        "source":          f"מכויל על {n} משחקים",
        "n":               n,
        "calibrated":      True,
        "ll_improvement":  ll_improvement,
        "is_significant":  is_significant,
        "message": (
            f"✅ rho מכויל: {rho_optimal} (שיפור LL: +{ll_improvement})"
            if is_significant else
            f"⚠️ rho מכויל: {rho_optimal} אבל השיפור לא מובהק עדיין — נשאר {DEFAULT_RHO}"
        ),
        "recommended_rho": rho_optimal if is_significant else DEFAULT_RHO,
    }


def load_matches_for_calibration() -> list[dict]:
    """
    טוען נתוני משחקים מ-Supabase לכיול.
    דורש: xg_home, xg_away, actual_home_goals, actual_away_goals.
    """
    try:
        from supabase import create_client
        db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        res = db.table("predictions").select(
            "xg_home,xg_away,actual_home_goals,actual_away_goals"
        ).not_.is_("actual_home_goals", "null").execute()

        raw = res.data or []
        matches = [
            {
                "xg_home":           float(r["xg_home"] or 1.0),
                "xg_away":           float(r["xg_away"] or 0.8),
                "actual_home_goals": int(r["actual_home_goals"]),
                "actual_away_goals": int(r["actual_away_goals"]),
            }
            for r in raw
            if r.get("xg_home") and r.get("xg_away")
               and r.get("actual_home_goals") is not None
               and r.get("actual_away_goals") is not None
        ]
        return matches

    except Exception as e:
        print(f"[RhoCalibrator] DB error: {e}")
        return []


def get_current_rho() -> float:
    """
    מחזיר את ה-rho הטוב ביותר הזמין.
    תמיד מחזיר ערך בטוח — לעולם לא זורק exception.
    """
    try:
        matches = load_matches_for_calibration()
        result  = calibrate_rho(matches)
        return result.get("recommended_rho", DEFAULT_RHO)
    except Exception as e:
        print(f"[RhoCalibrator] שגיאה — חוזר ל-{DEFAULT_RHO}: {e}")
        return DEFAULT_RHO


if __name__ == "__main__":
    print("🔧 מכייל rho...")
    matches = load_matches_for_calibration()

    if not matches:
        print(f"⚠️ אין נתונים — משתמש בברירת מחדל rho={DEFAULT_RHO}")
    else:
        result = calibrate_rho(matches)
        print(f"📊 משחקים לכיול: {result['n']}")
        print(f"🎯 {result['message']}")
        print(f"✅ rho מומלץ: {result['recommended_rho']}")

        if result["calibrated"]:
            print()
            print("השוואה:")
            print(f"  rho קלאסי  = {DEFAULT_RHO}")
            print(f"  rho מכויל  = {result['rho']}")
            diff = abs(result['rho'] - DEFAULT_RHO)
            print(f"  הפרש       = {diff:.4f}")
            if diff > 0.05:
                print("  ⚠️ הפרש גדול — כדורגל 2026 שונה מ-1997")
            else:
                print("  ✅ קרוב לערך הקלאסי — המודל יציב")