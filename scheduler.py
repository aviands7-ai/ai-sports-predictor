"""
scheduler.py — מפעיל את ה-Pipeline פעם אחת ויוצא.
התזמון מנוהל על ידי Railway Cron (06:00 + 23:00 UTC).
"""

import subprocess
import sys
from datetime import datetime


def run_pipeline():
    print(f"\n{'='*50}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} — מריץ pipeline...")

    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True, text=True, timeout=300
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ Pipeline הסתיים בהצלחה")
        else:
            print(f"❌ שגיאה:\n{result.stderr}")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print("⏱️ Pipeline חרג מ-5 דקות")
        sys.exit(1)
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
    print("✅ הסריקה הושלמה. הסקריפט סיים את ריצתו ומשחרר משאבים.")
    sys.exit(0)
