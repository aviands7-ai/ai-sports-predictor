"""
export_report.py — ייצוא דוח Excel מקצועי v2
עיצוב נקי, קריא, מאורגן
"""

import io
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def _fill(color): return PatternFill("solid", start_color=color)
def _font(bold=False, size=11, color="000000"): return Font(name="Calibri", bold=bold, size=size, color=color)
def _align(h="right", v="center", wrap=False): return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
def _border_bottom(): return Border(bottom=Side(style="thin", color="E2E8F0"))
def _border_all(): return Border(*[Side(style="thin", color="E2E8F0")]*4)

def _header_row(ws, row, values, bg="1E3A8A", fg="FFFFFF", height=24):
    ws.row_dimensions[row].height = height
    for col, val in enumerate(values, 1):
        c = ws.cell(row, col, val)
        c.font = _font(bold=True, size=10, color=fg)
        c.fill = _fill(bg)
        c.alignment = _align("center")

def _data_row(ws, row, values, bg="FFFFFF", bold=False, color="1E293B"):
    for col, val in enumerate(values, 1):
        c = ws.cell(row, col, val)
        c.font = _font(bold=bold, size=10, color=color)
        c.fill = _fill(bg)
        c.alignment = _align("right" if col == 1 else "center")
        c.border = _border_bottom()

def _section_title(ws, row, text, colspan=6):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=colspan)
    c = ws.cell(row, 1, text)
    c.font = _font(bold=True, size=11, color="1E40AF")
    c.fill = _fill("EFF6FF")
    c.alignment = _align("right")
    ws.row_dimensions[row].height = 20


def build_excel_report(match_data: dict, value_bets: list, elo_rankings: list) -> bytes:
    wb = Workbook()

    # ══════════════════════════════════════════════════════
    # גיליון 1 — ניתוח משחק
    # ══════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = "ניתוח משחק"
    ws1.sheet_view.rightToLeft = True
    ws1.column_dimensions["A"].width = 22
    ws1.column_dimensions["B"].width = 16
    ws1.column_dimensions["C"].width = 16
    ws1.column_dimensions["D"].width = 14
    ws1.column_dimensions["E"].width = 14
    ws1.column_dimensions["F"].width = 14

    if match_data:
        home = match_data.get("home_name", "")
        away = match_data.get("away_name", "")
        date = match_data.get("match_date", "")
        venue = match_data.get("venue", "")
        city  = match_data.get("city", "")

        # כותרת ראשית
        ws1.merge_cells("A1:F1")
        c = ws1.cell(1, 1, f"{home}  vs  {away}")
        c.font = _font(bold=True, size=16, color="FFFFFF")
        c.fill = _fill("1E3A8A")
        c.alignment = _align("center")
        ws1.row_dimensions[1].height = 36

        ws1.merge_cells("A2:F2")
        c = ws1.cell(2, 1, f"{date}  ·  {venue}, {city}")
        c.font = _font(size=10, color="64748B")
        c.fill = _fill("F8FAFC")
        c.alignment = _align("center")
        ws1.row_dimensions[2].height = 18

        row = 4

        # ── נתוני עוצמה ──
        _section_title(ws1, row, "📊 נתוני עוצמה")
        row += 1
        _header_row(ws1, row, ["מדד", home, away], bg="334155", height=20)
        row += 1
        for label, h_val, a_val in [
            ("Elo Rating", f"{match_data.get('elo_home',0):.0f}", f"{match_data.get('elo_away',0):.0f}"),
            ("Form Factor", f"{match_data.get('form_home',1):.2f}x", f"{match_data.get('form_away',1):.2f}x"),
            ("xG צפוי", f"{match_data.get('xg_home',0):.2f}", f"{match_data.get('xg_away',0):.2f}"),
        ]:
            bg = "FFFFFF" if row % 2 == 0 else "F8FAFC"
            _data_row(ws1, row, [label, h_val, a_val], bg=bg)
            row += 1
        row += 1

        # ── הסתברויות ──
        _section_title(ws1, row, "🎯 הסתברויות ויחסים")
        row += 1
        has_odds = bool(match_data.get("live_odds"))
        headers = ["תוצאה", "סיכוי %", "יחס הוגן", "Odds", "EV", "Value?"] if has_odds else ["תוצאה", "סיכוי %", "יחס הוגן"]
        _header_row(ws1, row, headers, bg="334155", height=20)
        row += 1

        probs = match_data.get("probs", {})
        fair  = match_data.get("fair_odds", {})
        odds  = match_data.get("live_odds") or {}
        evs   = match_data.get("ev", {})

        outcomes = [(f"{home} מנצחת","home"), ("תיקו","draw"), (f"{away} מנצחת","away")]
        for label, key in outcomes:
            p    = probs.get(key, 0)
            f_o  = fair.get(key, 0)
            o    = odds.get(key, "—")
            ev   = evs.get(key, 0)
            is_v = has_odds and ev > 0

            if has_odds:
                ev_str = f"+{ev:.1%}" if ev > 0 else f"{ev:.1%}"
                vals = [label, f"{p:.1f}%", f"{f_o:.3f}", o, ev_str, "✅" if is_v else "❌"]
            else:
                vals = [label, f"{p:.1f}%", f"{f_o:.3f}"]

            bg = "F0FDF4" if is_v else ("FFFFFF" if row % 2 == 0 else "F8FAFC")
            ev_color = "16A34A" if is_v else "000000"
            _data_row(ws1, row, vals, bg=bg)
            if has_odds:
                ws1.cell(row, 5).font = _font(bold=is_v, size=10, color=ev_color)
            row += 1
        row += 1

        # ── תוצאות סבירות ──
        _section_title(ws1, row, "⚽ תוצאות סבירות")
        row += 1
        _header_row(ws1, row, ["תוצאה", "הסתברות %"], bg="334155", height=20)
        row += 1
        for score_str, pct in match_data.get("top_scores", []):
            bg = "FFFFFF" if row % 2 == 0 else "F8FAFC"
            _data_row(ws1, row, [score_str, f"{pct}%"], bg=bg)
            row += 1
        row += 1

        # ── פציעות ──
        home_inj = match_data.get("injuries_home", [])
        away_inj = match_data.get("injuries_away", [])
        if home_inj or away_inj:
            _section_title(ws1, row, "🚑 פצועים ונעדרים")
            row += 1
            for name in home_inj:
                _data_row(ws1, row, [f"{name} ({home})"], bg="FEF2F2", color="DC2626")
                row += 1
            for name in away_inj:
                _data_row(ws1, row, [f"{name} ({away})"], bg="FEF2F2", color="DC2626")
                row += 1
            row += 1

        # ── H2H ──
        h2h = match_data.get("h2h", [])
        if h2h:
            _section_title(ws1, row, "⚔️ עימותים ישירים")
            row += 1
            _header_row(ws1, row, ["תאריך", "ביתית", "תוצאה", "אורחת"], bg="334155", height=20)
            row += 1
            for g in h2h:
                bg = "FFFFFF" if row % 2 == 0 else "F8FAFC"
                _data_row(ws1, row, [g.get("date",""), g.get("home",""), g.get("result",""), g.get("away","")], bg=bg)
                row += 1

    # ══════════════════════════════════════════════════════
    # גיליון 2 — Value Bets
    # ══════════════════════════════════════════════════════
    ws2 = wb.create_sheet("Value Bets")
    ws2.sheet_view.rightToLeft = True
    for col, w in zip("ABCDEFGH", [12, 28, 18, 8, 10, 12, 8, 8]):
        ws2.column_dimensions[col].width = w

    ws2.merge_cells("A1:H1")
    c = ws2.cell(1, 1, f"💰 Value Bets — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.font = _font(bold=True, size=14, color="FFFFFF")
    c.fill = _fill("065F46")
    c.alignment = _align("center")
    ws2.row_dimensions[1].height = 30

    if value_bets:
        _header_row(ws2, 2, ["תאריך", "משחק", "הימור על", "Odds", "סיכוי %", "EV", "Kelly %", "Overround %"], bg="064E3B", height=22)
        for i, vb in enumerate(value_bets, 3):
            bg = "F0FDF4" if i % 2 == 0 else "ECFDF5"
            vals = [
                vb.get("תאריך",""), vb.get("משחק",""), vb.get("הימור על",""),
                vb.get("Odds",""), vb.get("סיכוי %",""), vb.get("EV",""),
                vb.get("Kelly %",""), vb.get("Overround %",""),
            ]
            _data_row(ws2, i, vals, bg=bg, color="065F46")
    else:
        ws2.cell(3, 1, "לא נמצאו Value Bets בסריקה האחרונה").font = _font(size=11, color="6B7280")

    # ══════════════════════════════════════════════════════
    # גיליון 3 — דירוג Elo
    # ══════════════════════════════════════════════════════
    ws3 = wb.create_sheet("דירוג Elo")
    ws3.sheet_view.rightToLeft = True
    ws3.column_dimensions["A"].width = 6
    ws3.column_dimensions["B"].width = 24
    ws3.column_dimensions["C"].width = 14

    ws3.merge_cells("A1:C1")
    c = ws3.cell(1, 1, "📊 דירוג עוצמת הנבחרות — מונדיאל 2026")
    c.font = _font(bold=True, size=14, color="FFFFFF")
    c.fill = _fill("1E3A8A")
    c.alignment = _align("center")
    ws3.row_dimensions[1].height = 30

    _header_row(ws3, 2, ["#", "נבחרת", "Elo"], bg="334155", height=22)

    for i, team in enumerate(elo_rankings, 1):
        elo = team.get("elo_rating", 0)
        if elo >= 1700: bg, fg = "DBEAFE", "1E40AF"
        elif elo >= 1600: bg, fg = "F0FDF4", "166534"
        else: bg, fg = "FFFFFF" if i%2==0 else "F8FAFC", "374151"

        ws3.cell(i+2, 1, i).alignment = _align("center")
        ws3.cell(i+2, 2, team.get("name","")).font = _font(bold=(elo>=1700), size=10, color=fg)
        ws3.cell(i+2, 3, elo).font = _font(bold=(elo>=1700), size=10, color=fg)
        ws3.cell(i+2, 3).alignment = _align("center")
        for col in range(1,4):
            ws3.cell(i+2, col).fill = _fill(bg)
            ws3.cell(i+2, col).border = _border_bottom()

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()