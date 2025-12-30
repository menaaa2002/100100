from flask import Flask, request
import requests
from datetime import datetime, date
import threading
import time

app = Flask(__name__)

# ================== TELEGRAM ==================
BOT_TOKEN = "8272965030:AAERrS7zgQFpLVfLYTsaz81wG0wzYXh0FXg"
CHAT_ID   = "1292725273"

def send_telegram(msg):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )

# ================== MARKET TIMES ==================
MARKET_OPEN  = "10:00"
MARKET_CLOSE = "14:30"

# ================== DAILY FLAGS ==================
OPEN_SENT   = False
CLOSE_SENT  = False
LAST_SIGNAL_DAY = None
LAST_RESET_DAY  = None

# ================== MARKET OPEN / CLOSE ==================
def check_market_notifications():
    global OPEN_SENT, CLOSE_SENT

    now = datetime.now().strftime("%H:%M")

    # فتح السوق
    if now >= MARKET_OPEN and not OPEN_SENT:
        send_telegram(
            "🟢 EGX – Market Open\n\n"
            "📈 تم فتح جلسة التداول\n"
            f"⏰ {MARKET_OPEN}\n\n"
            "📌 النظام جاهز للمتابعة"
        )
        OPEN_SENT = True

    # غلق السوق
    if now >= MARKET_CLOSE and not CLOSE_SENT:
        send_telegram(
            "🔴 EGX – Market Close\n\n"
            "📉 تم إغلاق جلسة التداول\n"
            f"⏰ {MARKET_CLOSE}\n\n"
            "📌 انتهى التداول اليوم"
        )
        CLOSE_SENT = True

# ================== DAILY RESET ==================
def daily_reset():
    global OPEN_SENT, CLOSE_SENT, LAST_SIGNAL_DAY, LAST_RESET_DAY
    today = date.today().isoformat()

    if LAST_RESET_DAY != today:
        OPEN_SENT = False
        CLOSE_SENT = False
        LAST_SIGNAL_DAY = None
        LAST_RESET_DAY = today

# ================== SCHEDULER THREAD ==================
def scheduler():
    while True:
        daily_reset()
        check_market_notifications()
        time.sleep(30)

threading.Thread(target=scheduler, daemon=True).start()

# ================== WEBHOOK (11:45 SIGNAL) ==================
@app.route("/webhook", methods=["POST"])
def webhook():
    global LAST_SIGNAL_DAY

    today = date.today().isoformat()
    if LAST_SIGNAL_DAY == today:
        return {"status": "duplicate"}

    d = request.get_json(silent=True)
    if not d:
        return {"status": "no_data"}

    notes = []
    score = 0

    # ===== Trend =====
    if d.get("ema20", 0) > d.get("ema50", 0):
        notes.append("الاتجاه قصير الأجل: مستقر")
        score += 1
    else:
        notes.append("الاتجاه قصير الأجل: ضعيف")
        score -= 1

    # ===== RSI =====
    rsi = d.get("rsi", 50)
    if rsi > 45:
        notes.append("الزخم: إيجابي")
        score += 1
    elif rsi < 40:
        notes.append("الزخم: سلبي")
        score -= 1

    # ===== Volume =====
    volr = d.get("volr", 1)
    if volr > 1.3:
        notes.append("السيولة: توزيع ملحوظ")
        score -= 1
    else:
        notes.append("السيولة: طبيعية")

    # ===== Close behavior =====
    high  = d.get("high", 0)
    low   = d.get("low", 0)
    close = d.get("close", 0)

    rng = high - low
    if rng > 0 and (close - low) / rng < 0.3:
        notes.append("الإغلاق: قريب من القاع")
        score -= 1
    else:
        notes.append("الإغلاق: متماسك")

    # ===== Final Decision =====
    if score <= -2:
        decision = "🔴 بيع وحدات صندوق بلتون 100 اليوم"
        outlook  = "احتمال هبوط غدًا مرتفع"
    else:
        decision = "🟢 الاحتفاظ بوحدات صندوق بلتون 100"
        outlook  = "لا توجد مخاطر واضحة غدًا"

    msg = (
        "📊 EGX100 – Outlook for Tomorrow\n\n"
        "🔍 ملخص سريع:\n• " + "\n• ".join(notes) +
        f"\n\n⚠️ التوقع:\n{outlook}\n\n📌 التوصية:\n{decision}"
    )

    send_telegram(msg)
    LAST_SIGNAL_DAY = today

    return {"status": "ok"}

# ================== RUN APP ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
