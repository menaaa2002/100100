from flask import Flask, request
import requests
from datetime import datetime, date, time
import os

app = Flask(__name__)

# ================= TELEGRAM =================
BOT_TOKEN = "8272965030:AAERrS7zgQFpLVfLYTsaz81wG0wzYXh0FXg"
CHAT_ID   = "1292725273"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ============== GLOBAL STATE ==============
LAST_SIGNAL_DAY = None
OPEN_SENT = False
CLOSE_SENT = False

MARKET_OPEN  = time(10, 0)
MARKET_CLOSE = time(14, 30)

# ============== MARKET NOTIFICATIONS ==============
def check_market_notifications():
    global OPEN_SENT, CLOSE_SENT

    now = datetime.now().time()

    if now >= MARKET_OPEN and not OPEN_SENT:
        send_telegram("📢 فتح سوق EGX")
        OPEN_SENT = True

    if now >= MARKET_CLOSE and not CLOSE_SENT:
        send_telegram("⏹️ إغلاق سوق EGX")
        CLOSE_SENT = True

# ============== WEBHOOK =================
@app.route("/webhook", methods=["POST"])
def webhook():
    global LAST_SIGNAL_DAY

    today = date.today().isoformat()
    if LAST_SIGNAL_DAY == today:
        return {"status": "duplicate"}

    data = request.get_json()

    ema20 = float(data["ema20"])
    ema50 = float(data["ema50"])
    rsi   = float(data["rsi"])
    volr  = float(data["volr"])
    high  = float(data["high"])
    low   = float(data["low"])
    close = float(data["close"])

    notes = []
    score = 0

    # Trend
    if ema20 > ema50:
        notes.append("الاتجاه قصير الأجل إيجابي")
        score += 1
    else:
        notes.append("الاتجاه قصير الأجل ضعيف")
        score -= 1

    # RSI
    if rsi > 45:
        notes.append("الزخم إيجابي")
        score += 1
    elif rsi < 40:
        notes.append("الزخم سلبي")
        score -= 1

    # Volume
    if volr > 1.3:
        notes.append("سيولة توزيعية")
        score -= 1
    else:
        notes.append("السيولة طبيعية")

    # Close behavior
    rng = high - low
    if rng > 0 and (close - low) / rng < 0.3:
        notes.append("الإغلاق قريب من القاع")
        score -= 1
    else:
        notes.append("الإغلاق متماسك")

    # Decision
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

# ============== HEALTH CHECK ==============
@app.route("/")
def health():
    check_market_notifications()
    return "EGX100 Bot Running"

# ============== RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
