def calculate_ev_and_kelly(our_prob, odds):
    """
    הפונקציה מקבלת את ההסתברות שלנו (0 עד 1) ואת יחס ההימורים העשרוני,
    ומחזירה את התוחלת (EV) ואת אחוז ההשקעה המומלץ לפי קריטריון קלי.
    """
    # אם אין יחס הימורים תקין, נחזיר 0
    if odds <= 1.0 or our_prob <= 0:
        return 0.0, 0.0
        
    # 1. חישוב Expected Value (תוחלת)
    ev = (our_prob * odds) - 1.0
    
    # 2. חישוב קריטריון קלי
    # מחשבים רק אם התוחלת חיובית (אנחנו לא מהמרים על תוחלת שלילית)
    if ev > 0:
        b = odds - 1.0
        q = 1.0 - our_prob
        kelly_fraction = (our_prob * b - q) / b
        
        # הגנה: לעולם לא נמליץ לסכן יותר מ-5% מהתקציב על משחק בודד (Fractional Kelly)
        # מהמרים מקצועיים תמיד מחלקים את קלי ב-2 או ב-4 כדי להקטין תנודתיות
        safe_kelly = min(kelly_fraction / 2, 0.05) 
    else:
        safe_kelly = 0.0
        
    return round(ev, 3), round(safe_kelly, 3)

# --- בדיקת המערכת (Test) ---
if __name__ == "__main__":
    print("💰 בודק את מודול ההימורים...")
    
    # נניח שהמודל שלנו אומר שלברזיל יש 60% לנצח (0.60)
    # ואתר ההימורים מציע יחס של 1.90
    test_prob = 0.60
    test_odds = 1.90
    
    ev, kelly = calculate_ev_and_kelly(test_prob, test_odds)
    
    print(f"הסתברות מודל: {test_prob*100}% | יחס אתר: {test_odds}")
    print(f"תוחלת רווח (EV): {ev}")
    if ev > 0:
        print(f"✅ הימור ערך נמצא! מומלץ להשקיע: {kelly*100}% מהתקציב.")
    else:
        print("❌ תוחלת שלילית. לא להמר.")