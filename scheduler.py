"""
scheduler.py — מפעיל את ה-Pipeline פעם אחת ויוצא.
"""

import sys
import traceback
from datetime import datetime

# force flush כדי שכל הדפסה תופיע מיד ב-logs
import os
os.environ["PYTHONUNBUFFERED"] = "1"

print(f"{'='*50}", flush=True)
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — מתחיל...", flush=True)

try:
    print("📦 טוען main...", flush=True)
    from main import run_pipeline, run_non_football_pipeline
    print("✅ main נטען", flush=True)

    print("🚀 מריץ pipeline...", flush=True)
    run_pipeline(verbose=True)

    print("🏀 מריץ Non-Football Pipeline...", flush=True)
    run_non_football_pipeline(verbose=True)

    print("✅ הסריקה הושלמה. הסקריפט סיים את ריצתו ומשחרר משאבים.", flush=True)
    sys.exit(0)

except Exception as e:
    print(f"❌ שגיאה קריטית: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)
