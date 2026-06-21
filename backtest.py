"""
backtest.py — Backtesting אמיתי על תוצאות היסטוריות
בודק: דיוק תחזיות, ROI, Calibration, Brier Score, CLV
"""

import math
from db import get_predictions_with_results


# ─── Metrics ───────────────────────────────────────────────────────────────────

def accuracy(predictions: list[dict]) -> dict:
    """
    דיוק כולל: כמה פעמים התחזית הכי סבירה (home/draw/away) הייתה נכונה.
    """
    total = len(predictions)
    if total == 0:
        return {"accuracy": 0, "total": 0}

    correct = 0
    for p in predictions:
        pred = _top_prediction(p)
        if pred == p.get("actual_result"):
            correct += 1

    return {
        "correct": correct,
        "total": total,
        "accuracy_pct": round(correct / total * 100, 1),
    }


def roi_simulation(predictions: list[dict],
                   bankroll: float = 1000.0,
                   kelly_fraction: float = 0.25) -> dict:
    """
    סימולציית ROI אמיתית: מהמרים על כל Value Bet שנמצא.
    משתמש ב-Kelly הגדרות שנשמרו בזמן התחזית.
    מחזיר היסטוריית תקציב + מדדי ביצוע.
    """
    history = [bankroll]
    bets_placed = 0
    bets_won = 0
    total_wagered = 0.0
    total_return = 0.0

    for p in predictions:
        actual = p.get("actual_result")
        if not actual:
            continue

        # בדוק כל אפשרות (home / draw / away)
        for outcome in ["home", "draw", "away"]:
            ev = p.get(f"ev_{outcome}", 0) or 0
            kelly = p.get(f"kelly_{outcome}", 0) or 0
            odds = p.get(f"odds_{outcome}", 0) or 0

            if ev > 0 and kelly > 0 and odds > 1:
                bet_size = bankroll * (kelly / 100)
                total_wagered += bet_size
                bets_placed += 1

                if actual == outcome:
                    profit = bet_size * (odds - 1)
                    bankroll += profit
                    total_return += bet_size * odds
                    bets_won += 1
                else:
                    bankroll -= bet_size
                    total_return += 0

                history.append(round(bankroll, 2))
                break  # הימור אחד למשחק

    win_rate = round(bets_won / bets_placed * 100, 1) if bets_placed > 0 else 0
    roi = round((total_return - total_wagered) / total_wagered * 100, 1) if total_wagered > 0 else 0

    return {
        "starting_bankroll": history[0],
        "final_bankroll": round(bankroll, 2),
        "profit": round(bankroll - history[0], 2),
        "bets_placed": bets_placed,
        "bets_won": bets_won,
        "win_rate_pct": win_rate,
        "roi_pct": roi,
        "history": history,
        "total_wagered": round(total_wagered, 2),
    }


def brier_score(predictions: list[dict]) -> float:
    """
    Brier Score — מדד כיול (Calibration).
    טווח: 0 (מושלם) עד 1 (גרוע).
    מתחת ל-0.20 = מודל טוב.
    """
    if not predictions:
        return 1.0

    total = 0.0
    for p in predictions:
        actual = p.get("actual_result")
        if not actual:
            continue
        for outcome in ["home", "draw", "away"]:
            our_prob = p.get(f"prob_{outcome}", 0) or 0
            actual_binary = 1 if actual == outcome else 0
            total += (our_prob - actual_binary) ** 2

    return round(total / len(predictions), 4)


def calibration_chart(predictions: list[dict], bins: int = 5) -> list[dict]:
    """
    Calibration: כשהמודל אומר 70%, האם זה קורה 70% מהזמן?
    מחזיר רשימה של buckets להצגה.
    """
    buckets = [{
        "range": f"{int(i*100/bins)}-{int((i+1)*100/bins)}%",
        "predicted": 0.0,
        "actual": 0.0,
        "count": 0
    } for i in range(bins)]

    for p in predictions:
        actual = p.get("actual_result")
        if not actual:
            continue
        outcome = _top_prediction(p)
        prob = p.get(f"prob_{outcome}", 0) or 0
        bucket_idx = min(int(prob * bins), bins - 1)
        buckets[bucket_idx]["predicted"] += prob
        buckets[bucket_idx]["actual"] += (1 if actual == outcome else 0)
        buckets[bucket_idx]["count"] += 1

    for b in buckets:
        if b["count"] > 0:
            b["predicted"] = round(b["predicted"] / b["count"] * 100, 1)
            b["actual"] = round(b["actual"] / b["count"] * 100, 1)

    return buckets


def value_bet_stats(predictions: list[dict]) -> dict:
    """סטטיסטיקות ספציפיות על Value Bets בלבד."""
    value_bets = []
    for p in predictions:
        for outcome in ["home", "draw", "away"]:
            ev = p.get(f"ev_{outcome}", 0) or 0
            if ev > 0:
                value_bets.append({
                    "outcome": outcome,
                    "ev": ev,
                    "actual": p.get("actual_result"),
                    "correct": p.get("actual_result") == outcome
                })

    total = len(value_bets)
    if total == 0:
        return {"total": 0}

    correct = sum(1 for v in value_bets if v["correct"])
    avg_ev = sum(v["ev"] for v in value_bets) / total

    return {
        "total_value_bets": total,
        "correct": correct,
        "win_rate_pct": round(correct / total * 100, 1),
        "avg_ev": round(avg_ev, 3),
        "expected_win_rate_by_ev": round((1 + avg_ev) * 50, 1),  # הערכה גסה
    }


def roi_simulation_ab(predictions: list[dict],
                      bankroll: float = 1000.0,
                      prob_field_home: str = "prob_home",
                      prob_field_draw: str = "prob_draw",
                      prob_field_away: str = "prob_away") -> dict:
    """
    משימה 3 (ג'מיני): A/B Testing — ROI לפי מודל ספציפי.
    prob_field_* מאפשר להחליף את שדה ההסתברות לבדיקת מודל שונה.
    """
    from engine import expected_value, kelly_fraction, fair_odds

    history = [bankroll]
    bets_placed = bets_won = 0
    total_wagered = total_return = 0.0

    for p in predictions:
        actual = p.get("actual_result")
        if not actual:
            continue

        for outcome, pfield in [
            ("home", prob_field_home),
            ("draw", prob_field_draw),
            ("away", prob_field_away),
        ]:
            prob = p.get(pfield, 0) or 0
            odds = p.get(f"odds_{outcome}", 0) or 0
            if prob <= 0 or odds <= 1:
                continue

            ev = expected_value(prob, odds)
            k  = kelly_fraction(prob, odds)

            if ev > 0 and k > 0:
                bet_size = bankroll * k
                total_wagered += bet_size
                bets_placed += 1
                if actual == outcome:
                    bankroll += bet_size * (odds - 1)
                    total_return += bet_size * odds
                    bets_won += 1
                else:
                    bankroll -= bet_size
                history.append(round(bankroll, 2))
                break

    roi = round((total_return - total_wagered) / total_wagered * 100, 1) if total_wagered > 0 else 0
    win_rate = round(bets_won / bets_placed * 100, 1) if bets_placed > 0 else 0

    return {
        "final_bankroll": round(bankroll, 2),
        "profit": round(bankroll - history[0], 2),
        "bets_placed": bets_placed,
        "bets_won": bets_won,
        "win_rate_pct": win_rate,
        "roi_pct": roi,
        "history": history,
    }


def run_full_backtest(starting_bankroll: float = 1000.0) -> dict:
    """מריץ backtest מלא על כל התחזיות עם תוצאות — כולל A/B Testing."""
    predictions = get_predictions_with_results()

    if not predictions:
        return {"error": "אין תחזיות עם תוצאות בסיס לבדיקה."}

    # ── A/B Testing — שלושה מודלים במקביל ──────────────────────────
    # מודל A: Elo טהור — prob_elo_* (אם קיים בDB) או prob_* כברירת מחדל
    has_elo_field = any(p.get("prob_elo_home") for p in predictions)

    ab_results = {}

    # מודל A — Elo בסיסי
    ab_results["elo_pure"] = roi_simulation_ab(
        predictions, bankroll=starting_bankroll,
        prob_field_home="prob_elo_home" if has_elo_field else "prob_home",
        prob_field_draw="prob_elo_draw" if has_elo_field else "prob_draw",
        prob_field_away="prob_elo_away" if has_elo_field else "prob_away",
    )

    # מודל B — Elo + Form + פציעות (prob_home הוא זה)
    ab_results["elo_form"] = roi_simulation_ab(
        predictions, bankroll=starting_bankroll,
        prob_field_home="prob_home",
        prob_field_draw="prob_draw",
        prob_field_away="prob_away",
    )

    # מודל C — Ensemble מלא (prob_ensemble_* אם קיים)
    has_ensemble = any(p.get("prob_ensemble_home") for p in predictions)
    ab_results["ensemble"] = roi_simulation_ab(
        predictions, bankroll=starting_bankroll,
        prob_field_home="prob_ensemble_home" if has_ensemble else "prob_home",
        prob_field_draw="prob_ensemble_draw" if has_ensemble else "prob_draw",
        prob_field_away="prob_ensemble_away" if has_ensemble else "prob_away",
    )

    return {
        "n_matches":   len(predictions),
        "accuracy":    accuracy(predictions),
        "roi":         roi_simulation(predictions, bankroll=starting_bankroll),
        "brier_score": brier_score(predictions),
        "calibration": calibration_chart(predictions),
        "value_bets":  value_bet_stats(predictions),
        "ab_testing":  ab_results,
        "has_ab_data": has_elo_field or has_ensemble,
    }


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _top_prediction(p: dict) -> str:
    """מחזיר את התחזית הסבירה ביותר (home/draw/away)."""
    probs = {
        "home": p.get("prob_home", 0) or 0,
        "draw": p.get("prob_draw", 0) or 0,
        "away": p.get("prob_away", 0) or 0,
    }
    return max(probs, key=probs.get)


if __name__ == "__main__":
    results = run_full_backtest()
    print("\n📊 תוצאות Backtest:")
    print(f"  משחקים שנבדקו: {results.get('n_matches', 0)}")
    acc = results.get("accuracy", {})
    print(f"  דיוק כולל: {acc.get('accuracy_pct', 0)}% ({acc.get('correct', 0)}/{acc.get('total', 0)})")
    roi = results.get("roi", {})
    print(f"  ROI: {roi.get('roi_pct', 0)}%")
    print(f"  Brier Score: {results.get('brier_score', 'N/A')} (מתחת ל-0.20 = טוב)")
    vb = results.get("value_bets", {})
    print(f"  Value Bets: {vb.get('total_value_bets', 0)} | Win Rate: {vb.get('win_rate_pct', 0)}%")