"""
scheduler.py — מפעיל את ה-Pipeline פעם אחת ויוצא.
מריץ את main.py ישירות (לא כ-subprocess) כדי שכל שגיאה תופיע ב-logs.
"""

import sys
from datetime import datetime

print(f"\n{'='*50}")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — מריץ pipeline...")

try:
    from main import run_pipeline
    run_pipeline(verbose=True)
    print("✅ הסריקה הושלמה. הסקריפט סיים את ריצתו ומשחרר משאבים.")
    sys.exit(0)

except Exception as e:
    import traceback
    print(f"❌ שגיאה קריטית:")
    traceback.print_exc()
    sys.exit(1)
